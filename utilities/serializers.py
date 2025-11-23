from django.db import transaction
from rest_framework import serializers

from medics.models import Facility, Test, TestType


class SingleTestSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )


class TestTypeSerializer(serializers.Serializer):
    facility_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )
    name = serializers.CharField(max_length=255, required=True)
    tests = serializers.ListSerializer(
        child=SingleTestSerializer(),
        help_text="List of tests associated with this test type",
        required=True,
        allow_empty=False,
    )

    def validate(self, attrs):
        facility_ids = attrs.get("facility_ids", None)

        if facility_ids:
            facilities = Facility.objects.filter(id__in=facility_ids)
            if facilities.count() != len(facility_ids):
                raise serializers.ValidationError(
                    {"facility_ids": "One or more facility IDs are invalid."}
                )
            attrs["facilities"] = facilities

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        name = str(validated_data.get("name")).strip().upper()
        tests_data = validated_data.get("tests", [])
        facility: Facility = self.context.get("facility")
        facilities = validated_data.get("facilities", [])

        # Get or create the test type
        test_type, _ = TestType.objects.get_or_create(name=name)

        # Associate facilities with test type
        if facilities:
            for new_facility in facilities:
                test_type.facilities.add(new_facility)
        else:
            test_type.facilities.add(facility)

        # Get or create tests (prevents duplicates)
        for test_data in tests_data:
            test_name = str(test_data.get("name")).strip().upper()
            test_price = test_data.get("price", 0.0)

            # Use get_or_create to avoid duplicate tests
            test, created = Test.objects.get_or_create(
                name=test_name, test_type=test_type, defaults={"price": test_price}
            )

            # Update price if test already exists and new price is provided
            if not created and test_price is not None:
                test.price = test_price
                test.save(update_fields=["price"])

        return test_type
