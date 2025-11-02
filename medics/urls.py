from django.urls import path

from medics.views.medics_views import (
    CreateReferralView,
    GetAndUpdateReferralView,
    GetFacilitiesView,
    GetPractitionerReferralsView,
    GetTechnicianReferralsView,
    GetTestTypesView,
)

app_name = "medics"

urlpatterns = [
    # Get facilities
    path(
        "facilities",
        GetFacilitiesView.as_view(),
        name="get-facilities",
    ),
    # Get Test Types
    path(
        "test-types",
        GetTestTypesView.as_view(),
        name="get-test-types",
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
]
