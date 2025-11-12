import random
import string
from enum import Enum

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class TestStatus(Enum):
    PENDING = "Pending"
    RECEIVED = "Received"
    COMPLETED = "Completed"


class Test(models.Model):
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


class TestType(models.Model):
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
    tests = models.ManyToManyField(
        Test,
        related_name="test_types",
        help_text="Tests associated with this test type",
        blank=True,
    )

    class Meta:
        db_table = "TestType"
        verbose_name = "Test Type"
        verbose_name_plural = "Test Types"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"


class Facility(models.Model):
    name = models.CharField(
        max_length=255,
        help_text="Name of the patient",
        null=True,
        blank=True,
    )

    users = models.ManyToManyField(
        User,
        related_name="facilities",
        help_text="Users associated with the facility",
        blank=True,
    )
    contact_number = models.CharField(
        max_length=15,
        help_text="Contact number of the laboratory",
        null=True,
        blank=True,
    )
    test_types = models.ManyToManyField(
        TestType,
        related_name="facilities",
        help_text="Test types available at the facility",
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


class Patient(models.Model):
    full_name_or_id = models.CharField(
        max_length=255,
        help_text="Name or IDof the patient",
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
    while True:
        code = "".join(random.choices(chars, k=10))
        if not Referral.objects.filter(id=code).exists():
            return code


class Referral(models.Model):
    id = models.CharField(
        max_length=10,
        primary_key=True,
        unique=True,
        editable=False,
        default=generate_referral_id,
    )
    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="facility",
        help_text="Facility to which the patient is referred",
        null=True,
        blank=True,
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="patient",
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
        related_name="referred_by",
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

    class Meta:
        db_table = "Referral"
        verbose_name = "Referral"
        verbose_name_plural = "Referrals"
        ordering = ["-referred_at"]


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

    class Meta:
        db_table = "ReferralTest"
        verbose_name = "Referral Test"
        verbose_name_plural = "Referral Tests"
        unique_together = ("referral", "test")

    def __str__(self):
        return f"Referral {self.referral.id} - Test {self.test.name}"
