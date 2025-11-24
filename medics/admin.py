from django.contrib import admin

from medics.models import Facility, Patient, Referral, ReferralTest, Test, TestType


@admin.register(TestType)
class TestTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "facility_name", "created_at")
    search_fields = ("name",)
    ordering = ("-created_at",)

    def facility_name(self, obj):
        if obj.facility:
            return obj.facility.name
        return None

    facility_name.short_description = "Facility"


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "contact_number", "created_at")
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("full_name_or_id", "contact_number", "created_at")
    search_fields = ("full_name_or_id", "contact_number")
    ordering = ("-created_at",)


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = (
        "referral_id",
        "patient_name",
        "test_types",
        "tests",
        "facility",
        "status_display",
        "referred_at",
    )

    search_fields = (
        "patient__full_name_or_id",
        "facility__name",
        "referral_tests__test__name",
        "referral_tests__test__test_type__name",
    )
    list_filter = ("status", "referred_at", "facility__name")
    ordering = ("-referred_at",)

    # Add inline to show referral tests with their statuses
    class ReferralTestInline(admin.TabularInline):
        model = ReferralTest
        extra = 0
        readonly_fields = (
            "test",
            "test_type_display",
            "status",
            "created_at",
            "updated_at",
            "completed_at",
        )
        can_delete = False

        def test_type_display(self, obj):
            if obj.test and obj.test.test_type:
                return obj.test.test_type.name
            return None

        test_type_display.short_description = "Test Type"

    inlines = [ReferralTestInline]

    def referral_id(self, obj):
        return obj.id

    def patient_name(self, obj):
        return obj.patient.full_name_or_id

    def facility_name(self, obj):
        return obj.facility.name

    def test_types(self, obj):
        test_types = set()
        for referral_test in obj.referral_tests.all():
            if referral_test.test.test_type:
                test_types.add(referral_test.test.test_type.name)
        return ", ".join(sorted(test_types)) if test_types else None

    def tests(self, obj):
        test_names = [rt.test.name for rt in obj.referral_tests.all()]
        return ", ".join(sorted(test_names)) if test_names else None

    def status_display(self, obj):
        return obj.status

    status_display.short_description = "Status"
    test_types.short_description = "Test Types"
    tests.short_description = "Tests"

    patient_name.short_description = "Patient Name / ID"


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ("name", "test_type", "facility_name", "created_at")
    search_fields = ("name", "test_type__name")
    list_filter = ("test_type",)
    ordering = ("-created_at",)

    def facility_name(self, obj):
        if obj.test_type and obj.test_type.facility:
            return obj.test_type.facility.name
        return None

    facility_name.short_description = "Facility"


@admin.register(ReferralTest)
class ReferralTestAdmin(admin.ModelAdmin):
    list_display = (
        "referral_id",
        "facility_name",
        "test_name",
        "test_type_name",
        "status_display",
        "created_at",
    )
    search_fields = (
        "referral__id",
        "referral__facility__name",
        "test__name",
        "test__test_type__name",
    )
    list_filter = (
        "status",
        "created_at",
        "test__test_type__name",
        "referral__facility__name",
    )
    ordering = ("-created_at",)

    def referral_id(self, obj):
        return obj.referral.id

    def facility_name(self, obj):
        return obj.referral.facility.name

    def test_name(self, obj):
        return obj.test.name

    def test_type_name(self, obj):
        if obj.test.test_type:
            return obj.test.test_type.name
        return None

    def status_display(self, obj):
        return obj.status

    referral_id.short_description = "Referral ID"
    facility_name.short_description = "Facility"
    test_name.short_description = "Test Name"
    test_type_name.short_description = "Test Type"
    status_display.short_description = "Status"
