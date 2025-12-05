import re

from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _
from rest_framework import serializers

from authentication.models import UserType

User = get_user_model()


def validate_strong_password(password):
    """
    Custom password validator function that enforces strong password requirements.
    """
    min_length = 8

    if len(password) < min_length:
        raise serializers.ValidationError(
            _("Password must be at least %(min_length)d characters long."),
            code="password_too_short",
        )

    # Check for at least one uppercase letter
    if not re.search(r"[A-Z]", password):
        raise serializers.ValidationError(
            _("Password must contain at least one uppercase letter."),
            code="password_no_upper",
        )

    # Check for at least one lowercase letter
    if not re.search(r"[a-z]", password):
        raise serializers.ValidationError(
            _("Password must contain at least one lowercase letter."),
            code="password_no_lower",
        )

    # Check for at least one digit
    if not re.search(r"\d", password):
        raise serializers.ValidationError(
            _("Password must contain at least one number."),
            code="password_no_digit",
        )

    # Check for at least one special character
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        raise serializers.ValidationError(
            _("Password must contain at least one special character."),
            code="password_no_special",
        )


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, required=True)
    phone_number = serializers.CharField(max_length=255, required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_strong_password],
        style={"input_type": "password"},
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_strong_password],
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        phone_number = attrs.get("phone_number")
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

        # Validate phone_number
        if User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError(
                {"phone_number": "A user with this phone number already exists."}
            )

        # Validate password match
        if password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "Password and confirm password do not match."}
            )

        attrs["user_type"] = UserType.MEDICAL_PRACTITIONER.value

        return attrs

    def create(self, validated_data):
        full_name = validated_data["full_name"]
        phone_number = validated_data["phone_number"]
        password = validated_data["password"]
        user_type = validated_data.get("user_type")

        # Create User
        user = User.objects.create(
            full_name=full_name,
            phone_number=phone_number,
            user_type=user_type,
        )
        user.set_password(password)
        user.save()

        user_data = {
            "id": str(user.id),
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "user_type": user.user_type,
        }

        return user_data


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=255, required=True)
    password = serializers.CharField(max_length=255, required=True, write_only=True)

    def validate(self, attrs):
        phone_number = attrs.get("phone_number")
        password = attrs.get("password")

        try:
            user = User.objects.get(phone_number=phone_number)
            attrs["user"] = user
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"phone_number_and_password": "Invalid phone number or password."}
            )

        if user and not user.check_password(password):
            raise serializers.ValidationError(
                {"phone_number_and_password": "Invalid phone number or password."}
            )

        return attrs
