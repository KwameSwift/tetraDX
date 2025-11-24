from django.http import JsonResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from _tetradx.helpers import api_exception
from authentication.models import UserType
from medics.models import Facility
from utilities.serializers import TestTypeSerializer


class AddTestTypes(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data.copy()

        if user.user_type != UserType.LAB_TECHNICIAN.value and not user.is_staff:
            raise api_exception(
                "Unauthorized: Only Lab Technicians can add test types.",
            )
        facility = Facility.objects.filter(users__id=user.id).first()

        if not facility and not user.is_staff:
            raise api_exception(
                "Unauthorized: User is not associated with any facility.",
            )

        if facility:
            data["facility_ids"] = [facility.id]

        serializer = TestTypeSerializer(data=data)
        if serializer.is_valid():
            tests_data = serializer.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Test type and tests added successfully",
                    "data": tests_data,
                },
                status=status.HTTP_200_OK,
            )
        return JsonResponse(serializer.errors, status=400)
