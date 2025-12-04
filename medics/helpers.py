from functools import wraps

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import PermissionDenied

from _tetradx.helpers import api_exception
from medics import models


def referral_permission_required():
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            referral_id = kwargs.get("referral_id")

            if referral_id is None:
                return api_exception("Missing referral_id.")

            try:
                referral = models.Referral.objects.select_related(
                    "referred_by", "facility_branch__facility__admin"
                ).get(id=referral_id)
            except ObjectDoesNotExist:
                raise api_exception("Referral does not exist.")

            user = request.user

            # === Your original permission checks ===
            is_doctor = referral.referred_by == user
            branch = referral.facility_branch

            is_facility_worker = models.BranchTechnician.objects.filter(
                branch=branch, user=user
            ).exists()

            is_facility_admin = branch.facility.admin == user

            if not (is_doctor or is_facility_worker or is_facility_admin):
                raise PermissionDenied(
                    "You do not have permission to view or update this referral."
                )

            # If permitted, continue to view
            return func(self, request, *args, **kwargs)

        return wrapper

    return decorator


def get_user_branches(user):
    """
    Returns a list of branch IDs based on the user's relationship:
    - If user has branches: return those branch IDs.
    - If user has no branches but is a facility admin: return all branches under that facility.
    - Otherwise: return an empty list.
    """

    # Check if user is a branch technician
    user_branches = models.FacilityBranch.objects.filter(technicians__user=user)

    if user_branches.exists():
        # User belongs to one or more branches
        return list(user_branches)

    # If user has no branch, check if user is a facility admin
    facility = models.Facility.objects.filter(admin=user).first()

    if facility:
        # Return all branches for this facility
        return list(facility.branches.all())

    # User has no branch and is not a facility admin
    return None
