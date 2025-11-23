from django.utils import timezone
from rest_framework import serializers

from medics.models import Facility, Patient, Referral, ReferralTest, Test, TestStatus


class CreateReferralSerializer(serializers.Serializer):
    patient_full_name_or_id = serializers.CharField(max_length=255, required=True)
    patient_contact_number = serializers.CharField(max_length=15, required=False)
    tests = serializers.ListField(child=serializers.IntegerField(), required=True)
    facility_id = serializers.IntegerField(required=True)
    clinical_notes = serializers.CharField(max_length=255, required=False)

    def validate(self, attrs):
        facility_id = attrs.get("facility_id")
        tests = attrs.get("tests")

        # Validate facility_id
        try:
            attrs["facility"] = Facility.objects.get(id=facility_id)
        except Facility.DoesNotExist:
            raise serializers.ValidationError(
                {"facility_id": "Facility with the given ID does not exist."}
            )

        # Validate test_id
        referral_tests = Test.objects.filter(
            id__in=tests, test_type__facilities__id=facility_id
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
        clinical_notes = validated_data.get("clinical_notes", None)

        # Create Patient if not existing
        patient, _ = Patient.objects.get_or_create(
            full_name_or_id=patient_full_name_or_id,
            defaults={
                "contact_number": patient_contact_number,
            },
        )

        # Create Referral
        referral = Referral.objects.create(
            patient=patient,
            facility=facility,
            clinical_notes=clinical_notes,
            referred_by=self.context["user"],
        )
        # Create ReferralTest entries
        referral_tests = []
        for test in tests:
            referral_test = ReferralTest.objects.create(referral=referral, test=test)
            referral_tests.append(referral_test)

        # Prepare response data

        return {
            "referral_id": referral.id,
            "patient_name_or_id": patient.full_name_or_id,
            "facility": facility.name,
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
    status = serializers.CharField(max_length=10, required=True)
    referral_id = serializers.CharField(max_length=10, required=True)

    def validate(self, attrs):
        status = attrs.get("status")
        referral_id = attrs.get("referral_id")

        # Validate status
        valid_statuses = [test_status.value for test_status in TestStatus]
        if status not in valid_statuses:
            raise serializers.ValidationError("Invalid status value.")

        # Validate referral
        try:
            referral = Referral.objects.get(id=referral_id)
            attrs["referral"] = referral
        except Referral.DoesNotExist:
            raise serializers.ValidationError(
                "Referral with the given ID does not exist."
            )
        return attrs

    def update(self, instance, validated_data):
        status = validated_data.get("status", instance.status)
        instance.status = status
        instance.updated_at = timezone.now()

        if status == TestStatus.COMPLETED.value:
            instance.completed_at = timezone.now()

        instance.save()

        # Get referral tests
        referral_tests = ReferralTest.objects.filter(referral=instance)
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
            "facility": instance.facility.name,
            "patient_name_or_id": instance.patient.full_name_or_id,
            "referring_doctor": instance.referred_by.full_name,
            "referred_at": instance.referred_at,
            "status": instance.status,
            "updated_at": instance.updated_at,
            "completed_at": instance.completed_at,
            "tests": tests_data,
        }
