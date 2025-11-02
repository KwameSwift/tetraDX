import uuid
from enum import Enum

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserType(Enum):
    MEDICAL_PRACTITIONER = "Medical Practitioner"
    LAB_TECHNICIAN = "Lab Technician"
    PATIENT = "Patient"

    @classmethod
    def values(cls):
        return [member.value for member in cls]


class User(AbstractUser):
    """
    Custom User model focused on authentication
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the user",
    )
    full_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Full name of the user",
    )
    phone_number = models.CharField(
        max_length=15, unique=True, null=True, blank=True, help_text="User phone number"
    )
    user_type = models.CharField(
        max_length=30,
        choices=[(_(tag.name), _(tag.value)) for tag in UserType],
        help_text="Type of user",
        default=UserType.MEDICAL_PRACTITIONER.value,
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Account creation timestamp"
    )

    updated_at = models.DateTimeField(auto_now=True, help_text="Last update timestamp")

    class Meta:
        db_table = "User"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} ({self.facilities.all().first().name if self.facilities.exists() else 'No Facility'})"

    def save(self, *args, **kwargs):
        # If full_name is provided and is a string, set username to a lowercased,
        # space-free version of full_name
        if self.full_name and isinstance(self.full_name, str):
            processed_username = self.full_name.replace(" ", "").lower()
            self.username = processed_username
        super().save(*args, **kwargs)
