from rest_framework import serializers

from medics.models import Facility, Test, TestType


class TestTypeSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True)
    tests = serializers.ListField(
        child=serializers.CharField(max_length=255, required=True),
        help_text="List of tests associated with this test type",
        required=True,
        allow_empty=False,
    )

    def validate(self, attrs):
        name = attrs.get("name")
        facility: Facility = self.context.get("facility")
        print("Facility in serializer validate:", facility)

        if facility.test_types and facility.test_types.filter(name=name).exists():
            raise serializers.ValidationError(
                {"name": "A test type with this name already exists."}
            )

        return attrs

    def create(self, validated_data):
        name = validated_data.get("name")
        tests = validated_data.get("tests", [])
        facility: Facility = self.context.get("facility")

        test_type = TestType.objects.create(name=name)
        facility.test_types.add(test_type)

        for test_name in tests:
            test = Test.objects.create(name=test_name)
            test_type.tests.add(test)

        return test_type
