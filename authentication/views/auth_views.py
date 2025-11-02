import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from _tetradx.helpers import api_exception
from authentication.serializers import LoginSerializer, RegisterSerializer

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

    Authenticates user and returns a token.
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=self.request.data)

        if serializer.is_valid():
            user = serializer.validated_data.get("user")

            # Update last_login field
            user.last_login = timezone.now()
            user.save()

            # Generate authorization tokens for user
            refresh = RefreshToken.for_user(user)
            data = {
                "refresh_token": str(refresh),
                "access_token": str(refresh.access_token),
                "user_data": {
                    "id": str(user.id),
                    "full_name": user.full_name,
                    "phone_number": user.phone_number,
                    "user_type": user.user_type,
                    "date_joined": user.date_joined,
                    "facilities": [
                        {
                            "id": str(facility.id),
                            "name": facility.name,
                            "contact_number": facility.contact_number,
                        }
                        for facility in user.facilities.all()
                    ],
                },
            }
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
