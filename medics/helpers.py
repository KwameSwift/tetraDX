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
    - If user is admin of a facility: return ALL branches for that facility.
    - If user is not an admin but has assigned branches: return the FIRST branch only.
    - Otherwise: return None.
    """

    # First check if user is a facility admin
    facility_as_admin = models.Facility.objects.filter(admin=user).first()

    if facility_as_admin:
        # If user is admin of a facility, return ALL branches for that facility
        return {
            "branches": list(facility_as_admin.branches.all()),
            "facility": facility_as_admin,
        }

    # If user is not a facility admin, check if user is assigned to any branches
    # This uses the BranchTechnician model through the related_name
    branch_technician_assignments = models.BranchTechnician.objects.filter(user=user)

    if branch_technician_assignments.exists():
        # Get the first branch assignment (ordered by assigned_at or primary key)
        # You might want to add ordering if you have specific criteria
        first_assignment = branch_technician_assignments.first()
        # Return a list with just the first branch
        return {
            "branches": [first_assignment.branch],
            "facility": first_assignment.branch.facility,
        }

    # User is not a facility admin and not assigned to any branches
    return {"branches": [], "facility": None}
