import random
import string
from enum import Enum

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

User = get_user_model()


class TestStatus(Enum):
    PENDING = "Pending"
    RECEIVED = "Received"
    COMPLETED = "Completed"


class Facility(models.Model):
    name = models.CharField(
        max_length=255,
        help_text="Name of the facility",
        null=True,
        blank=True,
    )
    contact_number = models.CharField(
        max_length=15,
        help_text="Contact number of the laboratory",
        null=True,
        blank=True,
    )
    admin = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="facility_admin",
        help_text="Administrator of the facility",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Facility creation timestamp"
    )

    class Meta:
        db_table = "Facility"
        verbose_name = "Facility"
        verbose_name_plural = "Facilities"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"


class FacilityBranch(models.Model):
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="branches",
        help_text="Facility to which this branch belongs",
        null=True,
        blank=True,
    )
    name = models.CharField(
        max_length=255,
        help_text="Name of the facility branch",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Facility branch creation timestamp"
    )
    is_active = models.BooleanField(
        default=True, help_text="Indicates if the branch is active"
    )

    class Meta:
        db_table = "Facility_Branch"
        verbose_name = "Facility Branch"
        verbose_name_plural = "Facility Branches"
        ordering = ["name"]

    def __str__(self):
        return f"{self.facility.name} - {self.name}"


class BranchTechnician(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="branch_technicians",
        help_text="Lab technician assigned to the branch",
        null=True,
        blank=True,
    )
    branch = models.ForeignKey(
        FacilityBranch,
        on_delete=models.CASCADE,
        related_name="technicians",
        help_text="Facility branch to which the technician is assigned",
        null=True,
        blank=True,
    )
    is_admin = models.BooleanField(
        default=False,
        help_text="Indicates if the technician has admin privileges at the branch",
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when the technician was assigned"
    )

    class Meta:
        db_table = "Branch_Technician"
        verbose_name = "Branch Technician"
        verbose_name_plural = "Branch Technicians"
        unique_together = ("user", "branch")

    def __str__(self):
        return f"{self.user.full_name} - {self.branch.name}"


class TestType(models.Model):
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="test_types",
        help_text="Facility offering this test type",
        null=True,
        blank=True,
    )
    name = models.CharField(
        max_length=255,
        help_text="Name of the test type",
        null=True,
        blank=True,
    )
    description = models.TextField(
        help_text="Description of the test type",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Test type creation timestamp",
    )

    class Meta:
        db_table = "TestType"
        verbose_name = "Test Type"
        verbose_name_plural = "Test Types"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"


class Test(models.Model):
    test_type = models.ForeignKey(
        TestType,
        on_delete=models.CASCADE,
        related_name="tests",
        help_text="Type of the test",
        null=True,
        blank=True,
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price of the test",
        default=0.0,
    )
    name = models.CharField(
        max_length=255,
        help_text="Name of the test",
        null=True,
        blank=True,
    )
    description = models.TextField(
        help_text="Description of the test",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        help_text="Test creation timestamp", default=timezone.now
    )

    class Meta:
        db_table = "Test"
        verbose_name = "Test"
        verbose_name_plural = "Tests"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"

    def get_facilities(self):
        """Get all facilities that offer this test (through its TestType)"""
        return self.test_type.facilities.all()


class Patient(models.Model):
    full_name_or_id = models.CharField(
        max_length=255,
        help_text="Name or ID of the patient",
        null=True,
        blank=True,
    )
    contact_number = models.CharField(
        max_length=15,
        help_text="Contact number of the patient",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Patient creation timestamp"
    )

    class Meta:
        db_table = "Patient"
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = ["-created_at"]

    def __str__(self):
        return self.full_name_or_id


def generate_referral_id():
    chars = string.ascii_uppercase + string.digits
    attempts = 0
    while attempts < 100:
        code = "".join(random.choices(chars, k=10))
        if not Referral.objects.filter(id=code).exists():
            return code
        attempts += 1
    raise Exception("Could not generate unique referral ID")


class Referral(models.Model):
    id = models.CharField(
        max_length=10,
        primary_key=True,
        unique=True,
        editable=False,
        default=generate_referral_id,
    )
    facility_branch = models.ForeignKey(
        FacilityBranch,
        on_delete=models.CASCADE,
        related_name="referrals",
        help_text="Facility branch to which the patient is referred",
        null=True,
        blank=True,
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="referrals",
        help_text="Patient being referred to the laboratory",
    )
    clinical_notes = models.TextField(
        help_text="Clinical notes for the referral",
        null=True,
        blank=True,
    )
    referred_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="medical_practitioner",
        help_text="Doctor who referred the patient",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=10,
        choices=[(status.value, status.value) for status in TestStatus],
        help_text="Status of the referral",
        default=TestStatus.PENDING.value,
    )
    referred_at = models.DateTimeField(
        auto_now_add=True, help_text="Referral creation timestamp"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Referral last update timestamp"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp when the referral was completed"
    )

    class Meta:
        db_table = "Referral"
        verbose_name = "Referral"
        verbose_name_plural = "Referrals"
        ordering = ["-referred_at"]

    def __str__(self):
        return f"Referral {self.id} - {self.patient}"

    def turnaround_time(self):
        """Calculate turnaround time from referred_at to completed_at in hours"""
        if self.completed_at:
            delta = self.completed_at - self.referred_at
            return delta.total_seconds() / 3600  # Return hours
        return None


class ReferralTest(models.Model):
    referral = models.ForeignKey(
        Referral,
        on_delete=models.CASCADE,
        related_name="referral_tests",
        help_text="Referral associated with the test",
    )
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="referral_tests",
        help_text="Test associated with the referral",
    )
    status = models.CharField(
        max_length=10,
        choices=[(status.value, status.value) for status in TestStatus],
        help_text="Status of the referral test",
        default=TestStatus.PENDING.value,
    )
    created_at = models.DateTimeField(
        default=timezone.now, help_text="ReferralTest creation timestamp"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="ReferralTest last update timestamp"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp when the test was completed"
    )

    class Meta:
        db_table = "ReferralTest"
        verbose_name = "Referral Test"
        verbose_name_plural = "Referral Tests"
        unique_together = ("referral", "test")

    def __str__(self):
        return f"Referral {self.referral.id} - Test {self.test.name}"

    def clean(self):
        """Validate that the test's TestType is offered by the referral's facility"""
        super().clean()
        if self.referral.facility_branch and self.test.test_type:
            if (
                not self.test.test_type.facility
                == self.referral.facility_branch.facility
            ):
                raise ValidationError(
                    f"Test '{self.test.name}' (type: {self.test.test_type.name}) "
                    f"is not available at branch '{self.referral.facility_branch.name}'"
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    # Implement a turnaround time calculation method
    def turnaround_time(self):
        """Calculate turnaround time from created_at to completed_at in hours"""
        if self.completed_at:
            delta = self.completed_at - self.created_at
            return delta.total_seconds() / 3600  # Return hours
        return None
