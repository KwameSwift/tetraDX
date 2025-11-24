import logging

from django.contrib.auth import get_user_model
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from _tetradx.helpers import api_exception
from authentication.models import UserType
from medics.models import Facility, Referral, ReferralTest, Test, TestStatus, TestType
from medics.serializers import CreateReferralSerializer, UpdateReferralStatusSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class GetFacilitiesView(APIView):
    """
    Retrieve all facilities.
    """

    def get(self, request, *args, **kwargs):
        facilities = Facility.objects.all().values("id", "name")
        return JsonResponse(
            {
                "status": "success",
                "message": "Facilities retrieved successfully",
                "data": list(facilities),
            },
            safe=False,
            status=status.HTTP_200_OK,
        )


class GetTestTypesByFacilityView(APIView):
    """
    Retrieve test types available at a specific facility.
    """

    def get(self, request, *args, **kwargs):
        facility_id = kwargs.get("facility_id")
        try:
            facility = Facility.objects.get(id=facility_id)
            # Get test types for the facility
            test_types = (
                TestType.objects.filter(facility=facility)
                .values("id", "name")
                .order_by("name")
            )
            return JsonResponse(
                {
                    "status": "success",
                    "message": "Test types for facility retrieved successfully",
                    "data": list(test_types),
                },
                safe=False,
                status=status.HTTP_200_OK,
            )
        except Facility.DoesNotExist:
            raise api_exception("Facility with the given ID does not exist.")


class GetTestsByTestTypeView(APIView):
    """
    Retrieve tests under a specific test type.
    """

    def get(self, request, *args, **kwargs):
        test_type_id = kwargs.get("test_type_id")

        # Check if test type exists
        try:
            test_type = TestType.objects.get(id=test_type_id)
        except TestType.DoesNotExist:
            raise api_exception("Test type with the given ID does not exist.")

        # Get tests for a specific test type
        tests = (
            Test.objects.filter(test_type=test_type)
            .distinct()
            .values("id", "name")
            .order_by("name")
        )
        return JsonResponse(
            {
                "status": "success",
                "message": "Tests for test type retrieved successfully",
                "data": list(tests),
            },
            safe=False,
            status=status.HTTP_200_OK,
        )


class CreateReferralView(APIView):
    """
    Create a new referral.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        user = self.request.user

        if user.user_type != UserType.MEDICAL_PRACTITIONER.value:
            raise api_exception("Only medical practitioners can create referrals.")

        serializer = CreateReferralSerializer(data=data, context={"user": user})
        if serializer.is_valid():
            # Save referral
            referral_data = serializer.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Referral created successfully",
                    "data": referral_data,
                },
                status=status.HTTP_201_CREATED,
            )

        # Handle validation errors
        raise api_exception(serializer.errors)


class GetAndUpdateReferralView(APIView):
    """
    Get and Update the status of an existing referral.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        data = request.data
        user = request.user
        referral_id = kwargs.get("referral_id")

        data["referral_id"] = referral_id

        serializer = UpdateReferralStatusSerializer(data=data)

        if serializer.is_valid():
            # Update referral status
            validated_data = serializer.validated_data
            referral = validated_data["referral"]

            # Check permissions
            is_doctor = referral.referred_by == user
            is_facility_worker = referral.facility in user.facilities.all()
            if not is_doctor and not is_facility_worker:
                raise api_exception(
                    "You do not have permission to update this referral."
                )

            # Update referral
            referral_data = serializer.update(referral, validated_data)

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Referral status updated successfully",
                    "data": referral_data,
                },
                status=status.HTTP_200_OK,
            )
        # Handle validation errors
        raise api_exception(serializer.errors)

    def get(self, request, *args, **kwargs):
        referral_id = kwargs.get("referral_id")
        user = request.user

        try:
            referral = Referral.objects.select_related(
                "facility", "patient", "referred_by"
            ).get(id=referral_id)
            is_doctor = referral.referred_by == user
            is_facility_worker = referral.facility in user.facilities.all()
            if not is_doctor and not is_facility_worker:
                raise api_exception("You do not have permission to view this referral.")
        except Referral.DoesNotExist:
            raise api_exception("Referral with the given ID does not exist.")

        # Get tests associated with the referral
        referral_tests = (
            ReferralTest.objects.filter(referral=referral)
            .select_related("test")
            .prefetch_related("test__test_type")
        )

        return JsonResponse(
            {
                "status": "success",
                "message": "Referral retrieved successfully",
                "data": {
                    "referral_id": referral.id,
                    "facility": referral.facility.name,
                    "patient_name_or_id": referral.patient.full_name_or_id,
                    "referring_doctor": referral.referred_by.full_name,
                    "referred_at": referral.referred_at,
                    "status": referral.status,
                    "tests": [
                        {
                            "test_id": rt.id,
                            "test_name": rt.test.name,
                            "test_type_name": rt.test.test_type.name
                            if rt.test.test_type
                            else None,
                            "status": rt.status,
                            "created_at": rt.created_at,
                        }
                        for rt in referral_tests
                    ],
                },
            },
            safe=False,
            status=status.HTTP_200_OK,
        )


class GetTechnicianReferralsView(APIView):
    """
    Retrieve all referrals received by the laboratory.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        sort_by = request.GET.get("sort_by")
        sort_type = request.GET.get("sort_type", "desc")
        page_number = request.GET.get("page_number", 1)
        page_size = request.GET.get("page_size", 10)
        search_query = request.GET.get("search_query", "")
        user = request.user

        if not user.user_type == UserType.LAB_TECHNICIAN.value:
            raise api_exception("You do not have permission to view these referrals.")

        # Get all facilities the user is linked to
        facilities = user.facilities.all()

        # Base queryset with optimized select/prefetch
        referrals_qs = (
            Referral.objects.filter(facility__in=facilities)
            .select_related("patient", "facility", "referred_by")
            .prefetch_related("referral_tests__test__test_type")
        )

        # Apply search filters
        if search_query:
            referrals_qs = referrals_qs.filter(
                Q(patient__full_name_or_id__icontains=search_query)
                | Q(facility__name__icontains=search_query)
                | Q(referred_by__full_name__icontains=search_query)
                | Q(referral_tests__test__name__icontains=search_query)
                | Q(referral_tests__test__test_type__name__icontains=search_query)
            ).distinct()

        # Sorting map
        sort_map = {
            "time": "-referred_at" if sort_type == "desc" else "referred_at",
            "doctor": "-referred_by__full_name"
            if sort_type == "desc"
            else "referred_by__full_name",
        }
        referrals_qs = referrals_qs.order_by(sort_map.get(sort_by, "-referred_at"))

        # Convert to list with all data preloaded
        referrals = [
            {
                "referral_id": ref.id,
                "status": ref.status,
                "patient_name_or_id": ref.patient.full_name_or_id,
                "facility_name": ref.facility.name,
                "clinical_notes": ref.clinical_notes,
                "referral_doctor": ref.referred_by.full_name,
                "referred_at": ref.referred_at,
                "tests": [
                    {
                        "test_id": rt.id,
                        "test_name": rt.test.name,
                        "test_type_name": rt.test.test_type.name
                        if rt.test.test_type
                        else None,
                        "status": rt.status,
                        "created_at": rt.created_at,
                    }
                    for rt in ref.referral_tests.all()
                ],
            }
            for ref in referrals_qs
        ]

        # Paginate referrals
        paginator = Paginator(referrals, int(page_size))

        try:
            paginated_referrals = paginator.page(int(page_number))
        except PageNotAnInteger:
            paginated_referrals = paginator.page(1)
        except EmptyPage:
            # Return last page instead of empty list
            paginated_referrals = paginator.page(paginator.num_pages)

        return JsonResponse(
            {
                "status": "success",
                "message": "Referrals retrieved successfully",
                "data": {
                    "referrals": list(paginated_referrals),
                    "pagination": {
                        "current_page": paginated_referrals.number,
                        "page_size": int(page_size),
                        "total_pages": paginator.num_pages,
                        "total_referrals": paginator.count,
                        "has_next": paginated_referrals.has_next(),
                        "has_previous": paginated_referrals.has_previous(),
                    },
                },
            },
            safe=False,
            status=status.HTTP_200_OK,
        )


class GetPractitionerReferralsView(APIView):
    """
    Retrieve all referrals made by the Practitioner.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        page_number = request.GET.get("page_number", 1)
        page_size = request.GET.get("page_size", 10)
        search_query = request.GET.get("search_query", "")
        user = request.user

        if not user.user_type == UserType.MEDICAL_PRACTITIONER.value:
            raise api_exception("You do not have permission to view these referrals.")

        # Get referrals with optimized queries
        referrals_qs = (
            Referral.objects.filter(referred_by=user)
            .select_related("patient", "facility", "referred_by")
            .prefetch_related("referral_tests__test__test_type")
            .order_by("-referred_at")
        )

        # Apply search filters
        if search_query:
            referrals_qs = referrals_qs.filter(
                Q(patient__full_name_or_id__icontains=search_query)
                | Q(facility__name__icontains=search_query)
                | Q(referred_by__full_name__icontains=search_query)
                | Q(referral_tests__test__name__icontains=search_query)
                | Q(referral_tests__test__test_type__name__icontains=search_query)
            ).distinct()

        # Calculate summary statistics before converting to list
        total_referrals = referrals_qs.count()
        total_completed = referrals_qs.filter(status=TestStatus.COMPLETED.value).count()
        total_pending = referrals_qs.filter(status=TestStatus.PENDING.value).count()
        total_received = referrals_qs.filter(status=TestStatus.RECEIVED.value).count()

        data_summary = {
            "total_referrals": total_referrals,
            "total_completed": total_completed,
            "total_pending": total_pending,
            "total_received": total_received,
        }

        # Convert to list with all data preloaded
        referrals = [
            {
                "referral_id": ref.id,
                "patient_name_or_id": ref.patient.full_name_or_id,
                "facility_name": ref.facility.name,
                "clinical_notes": ref.clinical_notes,
                "status": ref.status,
                "referred_at": ref.referred_at,
                "tests": [
                    {
                        "test_id": rt.id,
                        "test_name": rt.test.name,
                        "test_type_name": rt.test.test_type.name
                        if rt.test.test_type
                        else None,
                        "status": rt.status,
                        "created_at": rt.created_at,
                    }
                    for rt in ref.referral_tests.all()
                ],
            }
            for ref in referrals_qs
        ]

        # Paginate referrals
        paginator = Paginator(referrals, int(page_size))

        try:
            paginated_referrals = paginator.page(int(page_number))
        except PageNotAnInteger:
            paginated_referrals = paginator.page(1)
        except EmptyPage:
            # Return last page instead of empty list
            paginated_referrals = paginator.page(paginator.num_pages)

        return JsonResponse(
            {
                "status": "success",
                "message": "Referrals retrieved successfully",
                "data": {
                    "referrals": list(paginated_referrals),
                    "data_summary": data_summary,
                    "pagination": {
                        "current_page": paginated_referrals.number,
                        "page_size": int(page_size),
                        "total_pages": paginator.num_pages,
                        "total_referrals": paginator.count,
                        "has_next": paginated_referrals.has_next(),
                        "has_previous": paginated_referrals.has_previous(),
                    },
                },
            },
            safe=False,
            status=status.HTTP_200_OK,
        )


class UpdateTestStatusView(APIView):
    """
    Update the status of a test within a referral.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        referral_test_id = kwargs.get("referral_test_id")
        new_status = request.data.get("status")
        user = request.user

        try:
            referral_test = (
                ReferralTest.objects.select_related(
                    "referral__facility", "referral__referred_by", "test"
                )
                .prefetch_related("test__test_type")
                .get(id=referral_test_id)
            )
            referral = referral_test.referral

            # Check permissions
            is_doctor = referral.referred_by == user
            is_facility_worker = referral.facility in user.facilities.all()

            if not is_doctor and not is_facility_worker:
                raise api_exception(
                    "You do not have permission to update this test status."
                )

            # Validate new status
            valid_statuses = [test_status.value for test_status in TestStatus]
            if new_status not in valid_statuses:
                raise api_exception("Invalid status value.")

            if referral_test.status == new_status:
                raise api_exception(f"The test is already in the {new_status} state.")

            # Update status
            referral_test.status = new_status
            referral.updated_at = timezone.now()

            if new_status == TestStatus.COMPLETED.value:
                referral_test.completed_at = timezone.now()

            referral_test.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Test status updated successfully",
                    "data": {
                        "referral_id": referral_test.referral.id,
                        "test_id": referral_test.id,
                        "test_name": referral_test.test.name,
                        "test_type_name": referral_test.test.test_type.name
                        if referral_test.test.test_type
                        else None,
                        "status": referral_test.status,
                        "updated_at": referral_test.updated_at,
                        "completed_at": referral_test.completed_at,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except ReferralTest.DoesNotExist:
            raise api_exception("Referral test with the given ID does not exist.")
