from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import TestCase

from medics.admin import ReferralAdmin
from medics.models import Facility, Patient, Referral, ReferralTest, Test, TestType

User = get_user_model()


class ReferralAdminTestCase(TestCase):
    """
    Test case for ReferralAdmin.
    """

    def setUp(self):
        self.site = AdminSite()
        self.admin = ReferralAdmin(Referral, self.site)

        # Create test data
        self.user = User.objects.create_user(
            username="test_user",
            full_name="Test User",
            phone_number="1234567890",
            user_type="Medical Practitioner",
        )
        self.facility = Facility.objects.create(name="Test Lab")
        self.facility.users.add(self.user)
        self.test_type = TestType.objects.create(name="Blood Test")
        self.test = Test.objects.create(name="Complete Blood Count")
        self.test.test_types.add(self.test_type)
        self.facility.test_types.add(self.test_type)
        self.patient = Patient.objects.create(
            full_name_or_id="John Doe", contact_number="0987654321"
        )
        self.referral = Referral.objects.create(
            patient=self.patient,
            facility=self.facility,
            referred_by=self.user,
            status="Pending",
        )
        # Create ReferralTest to link the test to the referral
        from medics.models import ReferralTest

        ReferralTest.objects.create(
            referral=self.referral,
            test=self.test,
        )

    def test_list_display(self):
        """
        Test that list_display includes the expected fields.
        """
        expected = (
            "referral_id",
            "patient_name",
            "test_types",
            "tests",
            "facility",
            "status_display",
            "referred_at",
        )
        self.assertEqual(self.admin.list_display, expected)

    def test_readonly_fields(self):
        """
        Test that readonly_fields is empty (no read-only fields configured).
        """
        # The admin doesn't currently define readonly_fields
        expected = ()
        self.assertEqual(self.admin.readonly_fields, expected)

    def test_search_fields(self):
        """
        Test that search_fields includes the expected fields.
        """
        expected = (
            "patient__full_name_or_id",
            "facility__name",
            "referral_tests__test__name",
            "referral_tests__test__test_types__name",
        )
        self.assertEqual(self.admin.search_fields, expected)

    def test_list_filter(self):
        """
        Test that list_filter includes the expected fields.
        """
        expected = ("status", "referred_at", "facility__name")
        self.assertEqual(self.admin.list_filter, expected)

    def test_ordering(self):
        """
        Test that ordering is set correctly.
        """
        expected = ("-referred_at",)
        self.assertEqual(self.admin.ordering, expected)

    def test_referral_id_method(self):
        """
        Test the referral_id method.
        """
        self.assertEqual(self.admin.referral_id(self.referral), self.referral.id)

    def test_patient_name_method(self):
        """
        Test the patient_name method.
        """
        self.assertEqual(
            self.admin.patient_name(self.referral),
            self.referral.patient.full_name_or_id,
        )

    def test_test_types_method(self):
        """
        Test the test_types method.
        """
        self.assertEqual(self.admin.test_types(self.referral), "Blood Test")

    def test_tests_method(self):
        """
        Test the tests method.
        """
        self.assertEqual(self.admin.tests(self.referral), "Complete Blood Count")

    def test_status_display_method(self):
        """
        Test the status_display method.
        """
        self.assertEqual(self.admin.status_display(self.referral), "Pending")

    def tearDown(self):
        User.objects.all().delete()
        Facility.objects.all().delete()
        TestType.objects.all().delete()
        Test.objects.all().delete()
        Patient.objects.all().delete()
        Referral.objects.all().delete()
        ReferralTest.objects.all().delete()
