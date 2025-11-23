from django.urls import path

from medics.views.medics_views import (
    CreateReferralView,
    GetAndUpdateReferralView,
    GetFacilitiesView,
    GetPractitionerReferralsView,
    GetTechnicianReferralsView,
    GetTestsByTestTypeView,
    GetTestTypesByFacilityView,
    UpdateTestStatusView,
)

app_name = "medics"

urlpatterns = [
    # Get Test Types by Facility
    path(
        "facilities/<str:facility_id>/test-types",
        GetTestTypesByFacilityView.as_view(),
        name="get-test-types-by-facility",
    ),
    # Get Tests by Test Type
    path(
        "test-types/<str:test_type_id>/tests",
        GetTestsByTestTypeView.as_view(),
        name="get-tests-by-test-type",
    ),
    # Get facilities
    path(
        "facilities",
        GetFacilitiesView.as_view(),
        name="get-facilities",
    ),
    # Create Referral
    path(
        "referral",
        CreateReferralView.as_view(),
        name="create-referral",
    ),
    # Edit or Retrieve Referral
    path(
        "referral/<str:referral_id>",
        GetAndUpdateReferralView.as_view(),
        name="get-update-referral",
    ),
    path(
        "referrals/practitioner",
        GetPractitionerReferralsView.as_view(),
        name="get-practitioner-referrals",
    ),
    path(
        "referrals/technician",
        GetTechnicianReferralsView.as_view(),
        name="get-technician-referrals",
    ),
    path(
        "referral-tests/<str:referral_test_id>/status",
        UpdateTestStatusView.as_view(),
        name="update-test-status",
    ),
]
