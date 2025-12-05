from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from authentication.models import UserType
from authentication.serializers import validate_strong_password
from medics import models

User = get_user_model()


class CreateReferralSerializer(serializers.Serializer):
    patient_full_name_or_id = serializers.CharField(max_length=255, required=True)
    patient_contact_number = serializers.CharField(max_length=15, required=False)
    tests = serializers.ListField(child=serializers.IntegerField(), required=True)
    branch_id = serializers.IntegerField(required=True)
    clinical_notes = serializers.CharField(max_length=255, required=False)

    def validate(self, attrs):
        branch_id = attrs.get("branch_id")
        tests = attrs.get("tests")

        # Validate Facility Branch
        try:
            facility_branch = models.FacilityBranch.objects.get(id=branch_id)
            attrs["facility"] = facility_branch.facility
            attrs["facility_branch"] = facility_branch
        except models.FacilityBranch.DoesNotExist:
            raise serializers.ValidationError(
                {"facility_id": "Facility with the given ID does not exist."}
            )

        # Validate test_id
        referral_tests = models.Test.objects.filter(
            id__in=tests, test_type__facility=facility_branch.facility
        )
        if not referral_tests.exists():
            raise serializers.ValidationError(
                {"test_id": "Test with the given ID does not exist."}
            )
        attrs["tests"] = referral_tests

        return attrs

    def create(self, validated_data):
        patient_full_name_or_id = validated_data.get("patient_full_name_or_id", None)
        patient_contact_number = validated_data.get("patient_contact_number", None)
        tests = validated_data.get("tests", [])
        facility = validated_data.get("facility")
        facility_branch = validated_data.get("facility_branch")
        clinical_notes = validated_data.get("clinical_notes", None)

        # Create Patient if not existing
        patient, _ = models.Patient.objects.get_or_create(
            full_name_or_id=patient_full_name_or_id,
            defaults={
                "contact_number": patient_contact_number,
            },
        )

        # Create Referral
        referral = models.Referral.objects.create(
            patient=patient,
            facility_branch=facility_branch,
            clinical_notes=clinical_notes,
            referred_by=self.context["user"],
        )
        # Create ReferralTest entries
        referral_tests = []
        for test in tests:
            referral_test = models.ReferralTest.objects.create(
                referral=referral, test=test
            )
            referral_tests.append(referral_test)

        # Prepare response data

        return {
            "referral_id": referral.id,
            "patient_name_or_id": patient.full_name_or_id,
            "facility_name": facility.name,
            "branch_name": facility_branch.name,
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
        }


class UpdateReferralStatusSerializer(serializers.Serializer):
    status = serializers.CharField(max_length=50, required=True)
    referral_id = serializers.CharField(max_length=50, required=True)

    def validate(self, attrs):
        status = attrs.get("status")
        referral_id = attrs.get("referral_id")

        # Validate status
        valid_statuses = [test_status.value for test_status in models.TestStatus]
        if status not in valid_statuses:
            raise serializers.ValidationError("Invalid status value.")

        # Validate referral
        try:
            referral = models.Referral.objects.get(id=referral_id)
            attrs["referral"] = referral
        except models.Referral.DoesNotExist:
            raise serializers.ValidationError(
                "Referral with the given ID does not exist."
            )
        return attrs

    def update(self, instance, validated_data):
        status = validated_data.get("status", instance.status)
        instance.status = status
        instance.updated_at = timezone.now()

        if status == models.TestStatus.COMPLETED.value:
            instance.completed_at = timezone.now()

        instance.save()

        # Get referral tests
        referral_tests = models.ReferralTest.objects.filter(referral=instance)
        tests_data = [
            {
                "test_id": rt.id,
                "test_name": rt.test.name,
                "test_type_name": rt.test.test_type.name if rt.test.test_type else None,
                "status": rt.status,
                "created_at": rt.created_at,
            }
            for rt in referral_tests
        ]

        return {
            "referral_id": instance.id,
            "facility_name": instance.facility_branch.facility.name,
            "branch_name": instance.facility_branch.name,
            "patient_name_or_id": instance.patient.full_name_or_id,
            "referring_doctor": instance.referred_by.full_name,
            "referred_at": instance.referred_at,
            "status": instance.status,
            "updated_at": instance.updated_at,
            "completed_at": instance.completed_at,
            "tests": tests_data,
        }


class FacilityBranchSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True)

    def validate(self, attrs):
        name = attrs.get("name")
        facility = self.context.get("facility")

        # Validate unique branch name
        if models.FacilityBranch.objects.filter(name=name, facility=facility).exists():
            raise serializers.ValidationError(
                {"name": "A facility branch with this name already exists."}
            )

        return attrs

    def create(self, validated_data):
        name = validated_data.get("name")
        facility = self.context.get("facility")

        branch = models.FacilityBranch.objects.create(
            name=name,
            facility=facility,
        )

        return {
            "id": str(branch.id),
            "name": branch.name,
            "facility_name": facility.name,
            "facility_branch_id": branch.id,
            "facility_branch_name": branch.name,
            "created_at": branch.created_at,
        }


class LabTechnicianSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, required=True)
    phone_number = serializers.CharField(max_length=15, required=False)
    branch_id = serializers.IntegerField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_strong_password],
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        phone_number = attrs.get("phone_number")
        facility = self.context.get("facility")

        # Validate unique phone number
        if User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError(
                {"phone_number": "A user with this phone number already exists."}
            )

        # Validate branch
        branch_id = attrs.get("branch_id")
        try:
            facility_branch = models.FacilityBranch.objects.get(
                id=branch_id, facility=facility
            )
            attrs["facility_branch"] = facility_branch
        except models.FacilityBranch.DoesNotExist:
            raise serializers.ValidationError(
                {"branch_id": "Facility branch with the given ID does not exist."}
            )

        return attrs

    def create(self, validated_data):
        full_name = validated_data.get("full_name")
        phone_number = validated_data.get("phone_number")
        password = validated_data.get("password")
        facility_branch = validated_data.get("facility_branch")
        facility = facility_branch.facility

        # Create User
        user = User.objects.create(
            full_name=full_name,
            phone_number=phone_number,
            user_type=UserType.LAB_TECHNICIAN.value,
        )
        user.set_password(password)
        user.save()

        # Create Lab Technician Profile
        lab_technician = models.BranchTechnician.objects.create(
            user=user,
            branch=facility_branch,
        )

        return {
            "id": str(user.id),
            "full_name": user.full_name,
            "phone_number": user.phone_number,
            "user_type": user.user_type,
            "facility_name": facility.name,
            "facility_branch_name": facility_branch.name,
            "created_at": lab_technician.assigned_at,
        }


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_strong_password],
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_strong_password],
        style={"input_type": "password"},
    )
    confirm_new_password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_strong_password],
        style={"input_type": "password"},
    )

    def validate(self, attrs):
        current_password = attrs.get("current_password")
        new_password = attrs.get("new_password")
        confirm_new_password = attrs.get("confirm_new_password")
        user = self.context["user"]

        # Validate current password
        if not user.check_password(current_password):
            raise serializers.ValidationError(
                {"current_password": "Current password is incorrect."}
            )

        # Validate new password match
        if new_password != confirm_new_password:
            raise serializers.ValidationError(
                {
                    "confirm_new_password": "New password and confirm password do not match."
                }
            )

        return attrs

    def create(self, validated_data):
        user = self.context["user"]
        new_password = validated_data["new_password"]

        user.set_password(new_password)
        user.save()

        return user
