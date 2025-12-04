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

from _tetradx.helpers import BaseAPIView, api_exception
from authentication.models import UserType
from medics import models, serializers
from medics.helpers import get_user_branches, referral_permission_required

logger = logging.getLogger(__name__)
User = get_user_model()


class GetFacilitiesView(APIView):
    """
    Retrieve all facilities.
    """

    def get(self, request, *args, **kwargs):
        facilities = models.Facility.objects.all().values("id", "name")
        return JsonResponse(
            {
                "status": "success",
                "message": "Facilities retrieved successfully",
                "data": list(facilities),
            },
            safe=False,
            status=status.HTTP_200_OK,
        )


class GetBranchView(APIView):
    """
    Retrieve all branches.
    """

    def get(self, request, *args, **kwargs):
        facility_id = kwargs.get("facility_id")

        branches = models.FacilityBranch.objects.filter(
            facility__id=facility_id
        ).values("id", "name")

        return JsonResponse(
            {
                "status": "success",
                "message": "Branches retrieved successfully",
                "data": list(branches),
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
            facility = models.Facility.objects.get(id=facility_id)
            # Get test types for the facility
            test_types = (
                models.TestType.objects.filter(facility=facility)
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
        except models.Facility.DoesNotExist:
            raise api_exception("Facility with the given ID does not exist.")


class GetTestsByTestTypeView(APIView):
    """
    Retrieve tests under a specific test type.
    """

    def get(self, request, *args, **kwargs):
        test_type_id = kwargs.get("test_type_id")

        # Check if test type exists
        try:
            test_type = models.TestType.objects.get(id=test_type_id)
        except models.TestType.DoesNotExist:
            raise api_exception("Test type with the given ID does not exist.")

        # Get tests for a specific test type
        tests = (
            models.Test.objects.filter(test_type=test_type)
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


class CreateReferralView(BaseAPIView):
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

        serializer = serializers.CreateReferralSerializer(
            data=data, context={"user": user}
        )
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


class GetAndUpdateReferralView(BaseAPIView):
    """
    Get and Update the status of an existing referral.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @referral_permission_required()
    def put(self, request, *args, **kwargs):
        data = request.data
        referral_id = kwargs.get("referral_id")

        data["referral_id"] = referral_id

        serializer = serializers.UpdateReferralStatusSerializer(data=data)

        if serializer.is_valid():
            # Update referral status
            validated_data = serializer.validated_data
            referral = validated_data["referral"]

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

    @referral_permission_required()
    def get(self, request, *args, **kwargs):
        referral_id = kwargs.get("referral_id")

        try:
            referral = models.Referral.objects.select_related(
                "facility_branch", "patient", "referred_by"
            ).get(id=referral_id)
        except models.Referral.DoesNotExist:
            raise api_exception("Referral does not exist.")

        # Get tests associated with the referral
        referral_tests = (
            models.ReferralTest.objects.filter(referral=referral)
            .select_related("test")
            .prefetch_related("test__test_type")
        )

        return JsonResponse(
            {
                "status": "success",
                "message": "Referral retrieved successfully",
                "data": {
                    "referral_id": referral.id,
                    "facility_name": referral.facility_branch.facility.name,
                    "branch_name": referral.facility_branch.name,
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


class GetTechnicianReferralsView(BaseAPIView):
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

        user_branches = get_user_branches(user)

        if not user_branches:
            referrals_qs = models.Referral.objects.none()
        else:
            # Base queryset with optimized select/prefetch
            referrals_qs = (
                models.Referral.objects.filter(facility_branch__in=user_branches)
                .select_related("patient", "facility_branch", "referred_by")
                .prefetch_related("referral_tests__test__test_type")
            )

        # Apply search filters
        if search_query:
            referrals_qs = referrals_qs.filter(
                Q(patient__full_name_or_id__icontains=search_query)
                | Q(facility_branch__name__icontains=search_query)
                | Q(facility_branch__facility__name__icontains=search_query)
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
                "facility_name": ref.facility_branch.facility.name,
                "branch_name": ref.facility_branch.name,
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


class GetPractitionerReferralsView(BaseAPIView):
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
            models.Referral.objects.filter(referred_by=user)
            .select_related("patient", "facility_branch", "referred_by")
            .prefetch_related("referral_tests__test__test_type")
            .order_by("-referred_at")
        )

        # Apply search filters
        if search_query:
            referrals_qs = referrals_qs.filter(
                Q(patient__full_name_or_id__icontains=search_query)
                | Q(facility_branch__name__icontains=search_query)
                | Q(facility_branch__facility__name__icontains=search_query)
                | Q(referred_by__full_name__icontains=search_query)
                | Q(referral_tests__test__name__icontains=search_query)
                | Q(referral_tests__test__test_type__name__icontains=search_query)
            ).distinct()

        # Calculate summary statistics before converting to list
        total_referrals = referrals_qs.count()
        total_completed = referrals_qs.filter(
            status=models.TestStatus.COMPLETED.value
        ).count()
        total_pending = referrals_qs.filter(
            status=models.TestStatus.PENDING.value
        ).count()
        total_received = referrals_qs.filter(
            status=models.TestStatus.RECEIVED.value
        ).count()

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
                "facility_name": ref.facility_branch.facility.name,
                "branch_name": ref.facility_branch.name,
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


class UpdateTestStatusView(BaseAPIView):
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
                models.ReferralTest.objects.select_related(
                    "referral__facility_branch", "referral__referred_by", "test"
                )
                .prefetch_related("test__test_type")
                .get(id=referral_test_id)
            )
            referral = referral_test.referral
            branch = referral.facility_branch

            # Check permissions
            is_doctor = referral.referred_by == user
            is_facility_worker = models.BranchTechnician.objects.filter(
                branch=branch, user=user
            ).exists()

            if not is_doctor and not is_facility_worker:
                raise api_exception(
                    "You do not have permission to update this test status."
                )

            # Validate new status
            valid_statuses = [test_status.value for test_status in models.TestStatus]
            if new_status not in valid_statuses:
                raise api_exception("Invalid status value.")

            if referral_test.status == new_status:
                raise api_exception(f"The test is already in the {new_status} state.")

            # Update status
            referral_test.status = new_status
            referral.updated_at = timezone.now()

            if new_status == models.TestStatus.COMPLETED.value:
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
                safe=False,
            )

        except models.ReferralTest.DoesNotExist:
            raise api_exception("Referral test with the given ID does not exist.")


class FacilityBranchView(BaseAPIView):
    """
    Add a new facility branch.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user

        facility_branch = models.BranchTechnician.objects.filter(
            user__id=user.id
        ).first()

        facility = facility_branch.branch.facility if facility_branch else None

        if not facility:
            raise api_exception(
                "Unauthorized: User is not associated with any facility.",
            )

        if not facility.admin == user:
            raise api_exception(
                "Unauthorized: Only facility admins can add branches.",
            )

        serializer = serializers.FacilityBranchSerializer(
            data=request.data, context={"facility": facility}
        )

        if serializer.is_valid():
            branch_data = serializer.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Facility branch added successfully",
                    "data": branch_data,
                },
                status=status.HTTP_201_CREATED,
                safe=False,
            )

        # Handle validation errors
        raise api_exception(serializer.errors)

    def delete(self, request, *args, **kwargs):
        user = request.user
        branch_id = self.kwargs.get("branch_id")

        technician = models.BranchTechnician.objects.filter(user__id=user.id).first()

        facility = (
            technician.branch.facility if technician and technician.branch else None
        )

        if not facility:
            raise api_exception(
                "Unauthorized: User is not associated with any facility.",
            )

        if not facility.admin == user:
            raise api_exception(
                "Unauthorized: Only facility admins can delete branches.",
            )

        try:
            branch = models.FacilityBranch.objects.get(id=branch_id, facility=facility)
            branch.is_active = False
            branch.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Facility branch deleted successfully",
                },
                status=status.HTTP_200_OK,
                safe=False,
            )
        except models.FacilityBranch.DoesNotExist:
            raise api_exception("Facility branch with the given ID does not exist.")


class AddLabTechnicianView(BaseAPIView):
    """
    Add a lab technician to a facility branch.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user

        technician = models.BranchTechnician.objects.filter(user__id=user.id).first()

        facility = (
            technician.branch.facility if technician and technician.branch else None
        )
        if not facility:
            raise api_exception(
                "Unauthorized: User is not associated with any facility.",
            )

        if not facility.admin == user:
            raise api_exception(
                "Unauthorized: Only facility admins can add lab technicians.",
            )

        serializer = serializers.LabTechnicianSerializer(
            data=request.data, context={"facility": facility}
        )

        if serializer.is_valid():
            # Save lab technician
            technician_data = serializer.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Lab technician added successfully",
                    "data": technician_data,
                },
                status=status.HTTP_201_CREATED,
                safe=False,
            )

        # Handle validation errors
        raise api_exception(serializer.errors)
