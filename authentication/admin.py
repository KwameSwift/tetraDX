from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.http import JsonResponse
from django.urls import path

from authentication.models import User, UserType
from medics.models import BranchTechnician, Facility, FacilityBranch


class UserAddForm(UserCreationForm):
    """
    Custom form for adding new users via Django Admin.
    Extends UserCreationForm to include custom fields.
    """

    full_name = forms.CharField(
        max_length=255, required=True, help_text="Enter the user's full name"
    )
    phone_number = forms.CharField(
        max_length=15, required=False, help_text="Enter the user's phone number"
    )
    facility = forms.ModelChoiceField(
        queryset=Facility.objects.all(),
        required=False,
        help_text="Select the facility to assign this user to (optional)",
    )
    branches = forms.ModelMultipleChoiceField(
        queryset=FacilityBranch.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select one or more branches within the facility (optional)",
    )
    make_facility_admin = forms.BooleanField(
        required=False,
        initial=False,
        help_text="Check if this user should be the facility administrator",
    )

    class Meta:
        model = User
        fields = (
            "full_name",
            "phone_number",
            "facility",
            "branches",
            "make_facility_admin",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["password1"].label = "Password"
        self.fields["password1"].help_text = "Enter a strong password"
        self.fields["password2"].label = "Confirm Password"
        self.fields[
            "password2"
        ].help_text = "Re-enter the same password for verification"

        # Start with empty branches queryset, will be populated dynamically
        self.fields["branches"].queryset = FacilityBranch.objects.none()

        # Dynamic branch filtering based on facility
        if "facility" in self.data:
            try:
                facility_id = int(self.data.get("facility"))
                self.fields["branches"].queryset = FacilityBranch.objects.filter(
                    facility_id=facility_id
                )
            except (ValueError, TypeError):
                pass
        elif (
            self.instance.pk
            and hasattr(self.instance, "facility")
            and self.instance.facility
        ):
            # For edit forms, filter branches by the selected facility
            self.fields["branches"].queryset = self.instance.facility.branches.all()

    def clean(self):
        cleaned_data = super().clean()
        branches = cleaned_data.get("branches")
        facility = cleaned_data.get("facility")

        # Validate that if branches are selected, a facility must also be selected
        if branches and not facility:
            raise forms.ValidationError(
                "You must select a facility before selecting branches."
            )

        # Validate that all branches belong to the selected facility
        if branches and facility:
            for branch in branches:
                if branch.facility != facility:
                    raise forms.ValidationError(
                        f"The branch '{branch.name}' does not belong to the selected facility."
                    )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.full_name = self.cleaned_data["full_name"]
        user.phone_number = self.cleaned_data.get("phone_number")
        user.user_type = UserType.LAB_TECHNICIAN.value

        user.save()

        # Handle facility admin assignment
        facility = self.cleaned_data.get("facility")
        make_facility_admin = self.cleaned_data.get("make_facility_admin")
        if facility and make_facility_admin:
            facility.admin = user
            facility.save()

        # Handle branch assignments for lab technicians
        branches = self.cleaned_data.get("branches")
        if branches:
            # Create a BranchTechnician entry for each selected branch
            for branch in branches:
                BranchTechnician.objects.get_or_create(
                    user=user, branch=branch, defaults={"is_admin": False}
                )

        return user


class UserChangeForm(UserChangeForm):
    """
    Custom form for editing existing users via Django Admin.
    Allows changing branch assignments within the same facility.
    """

    facility = forms.ModelChoiceField(
        queryset=Facility.objects.all(),
        required=False,
        help_text="Select the facility for this user (optional)",
    )
    branches = forms.ModelMultipleChoiceField(
        queryset=FacilityBranch.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select branches within the facility (optional)",
    )

    class Meta:
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get current facility and branches for this user
        if self.instance.pk:
            # Get facility where user is admin or has branches
            user_facility = None
            if (
                hasattr(self.instance, "facility_admin")
                and self.instance.facility_admin.exists()
            ):
                user_facility = self.instance.facility_admin.first()
            elif self.instance.branch_technicians.exists():
                first_branch = self.instance.branch_technicians.first().branch
                user_facility = first_branch.facility

            # Set initial facility
            if user_facility:
                self.fields["facility"].initial = user_facility
                self.fields["branches"].queryset = FacilityBranch.objects.filter(
                    facility=user_facility
                )

                # Set initial branches
                current_branches = self.instance.branch_technicians.values_list(
                    "branch_id", flat=True
                )
                self.fields["branches"].initial = current_branches
            else:
                self.fields["branches"].queryset = FacilityBranch.objects.none()

        # Dynamic branch filtering based on facility in submitted data
        if "facility" in self.data:
            try:
                facility_id = int(self.data.get("facility"))
                self.fields["branches"].queryset = FacilityBranch.objects.filter(
                    facility_id=facility_id
                )
            except (ValueError, TypeError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        branches = cleaned_data.get("branches")
        facility = cleaned_data.get("facility")

        # Validate that all branches belong to the selected facility
        if branches and facility:
            for branch in branches:
                if branch.facility != facility:
                    raise forms.ValidationError(
                        f"The branch '{branch.name}' does not belong to the selected facility."
                    )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=commit)

        if commit:
            # Handle branch assignments - remove old ones and add new ones
            facility = self.cleaned_data.get("facility")
            branches = self.cleaned_data.get("branches")

            if facility:
                # Remove all existing branch assignments for this user
                BranchTechnician.objects.filter(user=user).delete()

                # Add new branch assignments
                if branches:
                    for branch in branches:
                        BranchTechnician.objects.create(
                            user=user, branch=branch, is_admin=False
                        )

        return user


# User administration
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserAddForm
    form = UserChangeForm

    list_display = (
        "id",
        "full_name",
        "phone_number",
        "user_type_display",
        "is_active",
        "date_joined",
    )
    list_filter = ("is_active", "user_type", "is_staff")
    search_fields = ("full_name", "phone_number", "user_type")
    ordering = ("-date_joined",)

    # Fields to display when editing an existing user
    fieldsets = (
        (
            "User Information",
            {"fields": ("full_name", "phone_number", "user_type_display", "is_active")},
        ),
        (
            "Facility & Branch Assignment",
            {
                "fields": ("facility", "branches"),
                "description": "Manage facility and branch assignments. Changing branches will update the user's access.",
            },
        ),
        (
            "Important dates",
            {"fields": ("last_login", "date_joined"), "classes": ("collapse",)},
        ),
    )

    # Readonly fields for existing users
    readonly_fields = ("date_joined", "last_login", "user_type_display")

    # Add custom template for change form
    change_form_template = "admin/authentication/user/change_form.html"
    add_form_template = "admin/authentication/user/change_form.html"

    # Specify which form to use for adding users
    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        if obj is None:
            defaults["form"] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    # Customize the add view fieldsets
    add_fieldsets = (
        (
            "User Information",
            {
                "classes": ("wide",),
                "fields": (
                    "full_name",
                    "phone_number",
                ),
            },
        ),
        (
            "Facility Assignment",
            {
                "classes": ("wide",),
                "fields": (
                    "facility",
                    "make_facility_admin",
                    "branches",
                ),
                "description": "Assign the user to a facility and/or branches. Branch assignment is only applicable for Lab Technicians.",
            },
        ),
        (
            "Password",
            {
                "classes": ("wide",),
                "fields": (
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def response_add(self, request, obj, post_url_continue=None):
        """
        Override to redirect to the changelist after successfully adding a user.
        """
        from django.contrib import messages
        from django.http import HttpResponseRedirect
        from django.urls import reverse

        messages.success(request, f'The user "{obj.full_name}" was added successfully.')
        return HttpResponseRedirect(reverse("admin:authentication_user_changelist"))

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "api/facility-branches/",
                self.admin_site.admin_view(self.facility_branches_view),
                name="facility-branches",
            ),
        ]
        return custom_urls + urls

    def facility_branches_view(self, request):
        """API endpoint to fetch branches for a given facility"""
        facility_id = request.GET.get("facility_id")
        if not facility_id:
            return JsonResponse({"branches": []})

        branches = FacilityBranch.objects.filter(facility_id=facility_id).values(
            "id", "name"
        )
        return JsonResponse({"branches": list(branches)})

    def user_type_display(self, obj):
        return obj.get_user_type_display()

    user_type_display.short_description = "User Type"
