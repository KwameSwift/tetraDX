from django.contrib import admin

# Test Type administration
from medics.models import Facility, Referral, Test, TestType


@admin.register(TestType)
class TestTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_at")
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("name", "contact_number", "created_at")
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = (
        "referral_id",
        "patient_name",
        "test_type",
        "test",
        "facility",
        "status_display",
        "referred_at",
    )
    readonly_fields = (
        "referral_id",
        "patient",
        "facility",
        "test_type",
        "test",
        "referred_by",
        "clinical_notes",
    )
    search_fields = ("patient_name", "facility_name", "test__name")
    list_filter = ("status", "referred_at", "facility__name")
    ordering = ("-referred_at",)

    def referral_id(self, obj):
        return obj.id

    def patient_name(self, obj):
        return obj.patient.full_name_or_id

    def facility_name(self, obj):
        return obj.facility.name

    def test_type(self, obj):
        test = obj.test
        if not test:
            return None
        test_types = test.test_types.all()
        if not test_types.exists():
            return None
        return obj.test.test_types.first().name

    def test(self, obj):
        return obj.test.name if obj.test else None

    def status_display(self, obj):
        return obj.get_status_display()

    status_display.short_description = "Status"

    patient_name.short_description = "Patient Name / ID"


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_at")
    search_fields = ("name",)
