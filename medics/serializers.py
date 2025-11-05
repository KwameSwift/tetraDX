from rest_framework import serializers

from medics.models import Facility, Patient, Referral, Test, TestStatus


class CreateReferralSerializer(serializers.Serializer):
    patient_full_name_or_id = serializers.CharField(max_length=255, required=True)
    patient_contact_number = serializers.CharField(max_length=15, required=False)
    test_id = serializers.IntegerField(required=True)
    facility_id = serializers.IntegerField(required=True)
    clinical_notes = serializers.CharField(max_length=255, required=False)

    def validate(self, attrs):
        facility_id = attrs.get("facility_id")
        test_id = attrs.get("test_id")

        # Validate facility_id
        try:
            attrs["facility"] = Facility.objects.get(id=facility_id)
        except Facility.DoesNotExist:
            raise serializers.ValidationError(
                {"facility_id": "Facility with the given ID does not exist."}
            )

        # Validate test_id
        test = Test.objects.filter(id=test_id, test_types__facilities__id=facility_id)
        if not test.exists():
            raise serializers.ValidationError(
                {"test_id": "Test with the given ID does not exist."}
            )
        attrs["test"] = test.first()

        return attrs

    def create(self, validated_data):
        patient_full_name_or_id = validated_data.get("patient_full_name_or_id", None)
        patient_contact_number = validated_data.get("patient_contact_number", None)
        test = validated_data.get("test")
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
            test=test,
            facility=facility,
            clinical_notes=clinical_notes,
            referred_by=self.context["user"],
        )

        return {
            "referral_id": referral.id,
            "patient_name_or_id": patient.full_name_or_id,
            "test_type_name": test.test_types.first().name
            if test.test_types.exists()
            else None,
            "test_name": test.name,
            "facility": facility.name,
            "referring_doctor": referral.referred_by.full_name,
            "referred_at": referral.referred_at,
            "status": referral.status,
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
        instance.status = validated_data.get("status", instance.status)
        instance.save()

        return {
            "referral_id": instance.id,
            "facility": instance.facility.name,
            "patient_name_or_id": instance.patient.full_name_or_id,
            "test": instance.test.name,
            "test_type": instance.test.test_types.first().name
            if instance.test.test_types.exists()
            else None,
            "referring_doctor": instance.referred_by.full_name,
            "referred_at": instance.referred_at,
            "status": instance.status,
        }
