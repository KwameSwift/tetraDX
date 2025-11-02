from django.contrib import admin

# Test Type administration
from medics.models import Facility, Referral, TestType


@admin.register(TestType)
class TestTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "description", "created_at")
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "contact_number", "created_at")
    search_fields = ("name",)
    ordering = ("-created_at",)


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "patient_id",
        "patient_name",
        "test_type",
        "facility",
        "referral_status",
        "referred_at",
    )
    readonly_fields = (
        "id",
        "patient",
        "facility",
        "test_type",
        "referred_by",
        "clinical_notes",
    )
    search_fields = ("patient_name", "facility_name", "test_type")
    ordering = ("-referred_at",)

    def referral_status(self, obj):
        return obj.status

    def patient_name(self, obj):
        return obj.patient.full_name

    def facility_name(self, obj):
        return obj.facility.name

    def test_type(self, obj):
        return obj.test_type.name

    def patient_id(self, obj):
        return obj.patient.patient_id
