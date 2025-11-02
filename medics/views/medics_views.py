import logging

from django.contrib.auth import get_user_model
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import F
from django.http import JsonResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from _tetradx.helpers import api_exception
from authentication.models import UserType
from medics.models import Facility, Referral, TestStatus, TestType
from medics.serializers import CreateReferralSerializer, UpdateReferralStatusSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class GetTestTypesView(APIView):
    """
    Retrieve all test types.
    """

    def get(self, request, *args, **kwargs):
        try:
            test_types = TestType.objects.all().values("id", "name").order_by("id")
            return JsonResponse(
                {
                    "status": "success",
                    "message": "Test types retrieved successfully",
                    "data": list(test_types),
                },
                safe=False,
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Error retrieving test types: {e}")
            raise api_exception(
                f"An error occurred while retrieving test types. Please try again. {e}"
            )


class GetFacilitiesView(APIView):
    """
    Retrieve all facilities.
    """

    def get(self, request, *args, **kwargs):
        facilities = Facility.objects.all().values("id", "name").order_by("id")
        return JsonResponse(
            {
                "status": "success",
                "message": "Facilities retrieved successfully",
                "data": list(facilities),
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
            referral = Referral.objects.get(id=referral_id)
            is_doctor = referral.referred_by == user
            is_facility_worker = referral.facility in user.facilities.all()
            if not is_doctor and not is_facility_worker:
                raise api_exception("You do not have permission to view this referral.")
        except Referral.DoesNotExist:
            raise api_exception("Referral with the given ID does not exist.")

        return JsonResponse(
            {
                "status": "success",
                "message": "Referral retrieved successfully",
                "data": {
                    "referral_id": referral.id,
                    "facility": referral.facility.name,
                    "patient_name_or_id": referral.patient.full_name_or_id,
                    "test_type": referral.test_type.name,
                    "referring_doctor": referral.referred_by.full_name,
                    "referred_at": referral.referred_at,
                    "status": referral.status,
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
        user = request.user

        if not user.user_type == UserType.LAB_TECHNICIAN.value:
            raise api_exception("You do not have permission to view these referrals.")

        # Get all facilities the user is linked to
        facilities = user.facilities.all()

        # Base queryset
        referrals = Referral.objects.filter(facility__in=facilities).annotate(
            referral_id=F("id"),
            patient_name_or_id=F("patient__full_name_or_id"),
            test_type_name=F("test_type__name"),
            facility_name=F("facility__name"),
            referral_doctor=F("referred_by__full_name"),
        )

        # Sorting map
        sort_map = {
            "time": "-referred_at" if sort_type == "desc" else "referred_at",
            "doctor": "-referral_doctor" if sort_type == "desc" else "referral_doctor",
            "test_type": "-test_type_name" if sort_type == "desc" else "test_type_name",
        }
        referrals = referrals.order_by(sort_map.get(sort_by, "-referred_at"))

        # Project to dicts
        referrals = referrals.values(
            "referral_id",
            "status",
            "patient_name_or_id",
            "test_type_name",
            "facility_name",
            "clinical_notes",
            "referral_doctor",
            "referred_at",
        )

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
        user = request.user

        if not user.user_type == UserType.MEDICAL_PRACTITIONER.value:
            raise api_exception("You do not have permission to view these referrals.")

        referrals = (
            Referral.objects.filter(referred_by=user)
            .annotate(
                referral_id=F("id"),
                patient_name_or_id=F("patient__full_name_or_id"),
                test_type_name=F("test_type__name"),
                facility_name=F("facility__name"),
            )
            .values(
                "referral_id",
                "patient_name_or_id",
                "test_type_name",
                "facility_name",
                "clinical_notes",
                "status",
                "referred_at",
            )
            .order_by("-referred_at")
        )

        data_summary = {
            "total_referrals": referrals.count(),
            "total_completed": referrals.filter(
                status=TestStatus.COMPLETED.value
            ).count(),
            "total_pending": referrals.filter(status=TestStatus.PENDING.value).count(),
            "total_received": referrals.filter(
                status=TestStatus.RECEIVED.value
            ).count(),
        }

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
