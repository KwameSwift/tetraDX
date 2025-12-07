import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from _tetradx.helpers import api_exception
from authentication.models import UserType
from authentication.serializers import LoginSerializer, RegisterSerializer
from medics.helpers import get_user_branches

logger = logging.getLogger(__name__)
User = get_user_model()


class UserRegistrationView(APIView):
    """
    Register a new user account.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        data = self.request.data
        """Register a new user"""
        serializer = RegisterSerializer(data=data)

        if serializer.is_valid():
            try:
                with transaction.atomic():
                    # Create the user
                    user_data = serializer.save()

                    # Successful registration response
                    return JsonResponse(
                        {
                            "status": "success",
                            "message": "User registered successfully",
                            "data": user_data,
                        },
                        safe=False,
                        status=status.HTTP_201_CREATED,
                    )

            except Exception as e:
                logger.error(f"Error during user registration: {e}")
                raise api_exception(
                    f"An error occurred during registration. Please try again. {e}"
                )
        # Raise validation errors
        raise api_exception(serializer.errors)


class LoginView(APIView):
    """
    User login view.
    Authenticates user and returns authentication tokens.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid()

        if serializer.is_valid():
            user = serializer.validated_data["user"]

            data = {
                "refresh_token": None,
                "access_token": None,
                "user_data": self._get_base_user_data(user),
            }

            # Auth tokens
            refresh = RefreshToken.for_user(user)
            data["refresh_token"] = str(refresh)
            data["access_token"] = str(refresh.access_token)

            # Extra info for lab technicians
            if user.user_type == UserType.LAB_TECHNICIAN.value:
                self._attach_lab_technician_data(user, data["user_data"])

            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Login successful",
                    "data": data,
                },
                safe=False,
                status=status.HTTP_200_OK,
            )

        # Raise validation errors
        raise api_exception(serializer.errors)

    # ----------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------
    def _get_base_user_data(self, user):
        """Return user fields common to all user types."""
        return {
            "id": str(user.id),
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "user_type": user.user_type,
            "date_joined": user.date_joined,
        }

    def _attach_lab_technician_data(self, user, user_data):
        """
        Adds facility + branch info to user_data for lab technicians.
        """
        user_branches_info = get_user_branches(user)
        user_branches = user_branches_info["branches"]
        facility = user_branches_info["facility"]

        # Branch list formatting
        branches = [
            {
                "id": str(branch.id),
                "name": branch.name,
            }
            for branch in user_branches
        ]

        user_data.update(
            {
                "is_new_user": user.last_login is None,
                "is_admin": facility.admin == user if facility else False,
                "facility": {
                    "id": facility.id,
                    "name": facility.name,
                }
                if facility
                else None,
                "branches": branches,
            }
        )
