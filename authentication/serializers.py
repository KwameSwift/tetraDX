from django.contrib.auth import get_user_model
from rest_framework import serializers

from authentication.models import UserType
from medics.models import Facility

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, required=True)
    phone_number = serializers.CharField(max_length=255, required=True)
    user_type = serializers.CharField(write_only=True, min_length=8, required=False)
    facility_id = serializers.IntegerField(required=False)

    def validate(self, attrs):
        phone_number = attrs.get("phone_number")
        user_type = attrs.get("user_type")
        facility_id = attrs.get("facility_id")

        # Enforce facility_id required field for lab technicians
        if user_type == "Lab Technician" and not facility_id:
            raise serializers.ValidationError(
                {"facility_id": "This field is required."}
            )

        # Validate facility_id
        if facility_id:
            try:
                facility = Facility.objects.get(id=facility_id)
                attrs["facility"] = facility
            except Facility.DoesNotExist:
                raise serializers.ValidationError(
                    {"facility_id": "Invalid facility ID."}
                )

        # Validate phone_number
        if User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError(
                {"phone_number": "A user with this phone number already exists."}
            )

        # Validate user_type
        if user_type and user_type not in UserType.values():
            raise serializers.ValidationError({"user_type": "Invalid user type."})

        return attrs

    def create(self, validated_data):
        facility = validated_data.get("facility")
        full_name = validated_data["full_name"]
        phone_number = validated_data["phone_number"]

        # Create User
        user = User.objects.create(
            full_name=full_name,
            phone_number=phone_number,
            user_type=validated_data.get(
                "user_type", UserType.MEDICAL_PRACTITIONER.value
            ),
        )

        # Facility association can be handled here if needed
        if facility:
            facility.users.add(user)

        user_data = {
            "id": str(user.id),
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "user_type": user.user_type,
        }

        if facility:
            user_data["facilities"] = [
                {
                    "id": str(facility.id),
                    "name": facility.name,
                }
                for facility in user.facilities.all()
            ]

        return user_data


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=255, required=True)

    def validate(self, attrs):
        phone_number = attrs.get("phone_number")

        try:
            user = User.objects.get(phone_number=phone_number)
            attrs["user"] = user
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"phone_number": "No user found with this phone number."}
            )

        return attrs
