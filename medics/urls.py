from django.urls import path

from medics.views import medics_views

app_name = "medics"

urlpatterns = [
    # Get Test Types by Facility
    path(
        "facilities/<str:facility_id>/test-types",
        medics_views.GetTestTypesByFacilityView.as_view(),
        name="get-test-types-by-facility",
    ),
    # Get Branches by Facility
    path(
        "facilities/<str:facility_id>/branches",
        medics_views.GetBranchView.as_view(),
        name="get-branches-by-facility",
    ),
    # Get Tests by Test Type
    path(
        "test-types/<str:test_type_id>/tests",
        medics_views.GetTestsByTestTypeView.as_view(),
        name="get-tests-by-test-type",
    ),
    # Get facilities
    path(
        "facilities",
        medics_views.GetFacilitiesView.as_view(),
        name="get-facilities",
    ),
    # Add Branch
    path(
        "branches/add",
        medics_views.FacilityBranchView.as_view(),
        name="add-branch",
    ),
    # Get All Branches
    path(
        "branches/deactivate/<str:branch_id>",
        medics_views.FacilityBranchView.as_view(),
        name="get-branches",
    ),
    # Create Referral
    path(
        "referral",
        medics_views.CreateReferralView.as_view(),
        name="create-referral",
    ),
    # Edit or Retrieve Referral
    path(
        "referral/<str:referral_id>",
        medics_views.GetAndUpdateReferralView.as_view(),
        name="get-update-referral",
    ),
    path(
        "referrals/practitioner",
        medics_views.GetPractitionerReferralsView.as_view(),
        name="get-practitioner-referrals",
    ),
    path(
        "referrals/technician",
        medics_views.GetTechnicianReferralsView.as_view(),
        name="get-technician-referrals",
    ),
    path(
        "referral-tests/<str:referral_test_id>/status",
        medics_views.UpdateTestStatusView.as_view(),
        name="update-test-status",
    ),
    # Add Lab Technician
    path(
        "lab-technicians/add",
        medics_views.AddLabTechnicianView.as_view(),
        name="add-lab-technician",
    ),
    # Change Password
    path(
        "change-password",
        medics_views.ChangePasswordView.as_view(),
        name="change-password",
    ),
]
