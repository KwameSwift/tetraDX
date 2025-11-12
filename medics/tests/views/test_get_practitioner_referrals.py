from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from authentication.models import UserType
from medics.models import Facility, Patient, Referral, ReferralTest, Test, TestType

User = get_user_model()


class GetPractitionerReferralsTestCase(BaseTestCase):
    """
    Test case for get practitioner referrals API endpoint.
    """

    def setUp(self):
        self.url = reverse_lazy("medics:get-practitioner-referrals")

        # Create practitioner user
        self.practitioner_user = User.objects.create_user(
            username="pract_user",
            full_name="Pract User",
            phone_number="1234567890",
            user_type=UserType.MEDICAL_PRACTITIONER.value,
        )

        # Create facility
        self.facility = Facility.objects.create(name="Test Lab")

        # Create test type and patient
        self.test_type = TestType.objects.create(name="Blood Test")
        self.test = Test.objects.create(name="Complete Blood Count")
        self.test.test_types.add(self.test_type)
        self.facility.test_types.add(self.test_type)
        self.patient = Patient.objects.create(
            full_name_or_id="John Doe", contact_number="1111111111"
        )

        # Create referral by the practitioner
        self.referral = Referral.objects.create(
            patient=self.patient,
            facility=self.facility,
            referred_by=self.practitioner_user,
        )
        # Create ReferralTest to link the test to the referral
        from medics.models import ReferralTest

        ReferralTest.objects.create(
            referral=self.referral,
            test=self.test,
        )

        # Login to get token
        login_data = {"phone_number": "1234567890"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        self.access_token = login_response.json()["data"]["access_token"]

    def test_get_practitioner_referrals_success(self):
        """
        Test successful retrieval of practitioner referrals.
        """

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["message"], "Referrals retrieved successfully")
        self.assertIn("data", response)
        self.assertIn("referrals", response["data"])
        self.assertIn("data_summary", response["data"])
        self.assertIn("pagination", response["data"])
        # Check that test_type_name is included in the referral data
        self.assertGreater(len(response["data"]["referrals"]), 0)
        referral = response["data"]["referrals"][0]
        self.assertIn("tests", referral)
        self.assertGreater(len(referral["tests"]), 0)
        self.assertEqual(referral["tests"][0]["test_type_name"], "Blood Test")

    def test_get_practitioner_referrals_unauthorized_user_type(self):
        """
        Test retrieval by non-practitioner user.
        """

        # Create non-pract user
        User.objects.create_user(
            username="non_pract",
            full_name="Non Pract",
            phone_number="0987654321",
            user_type=UserType.LAB_TECHNICIAN.value,
        )
        login_data = {"phone_number": "0987654321"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        non_pract_token = login_response.json()["data"]["access_token"]

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {non_pract_token}",
        )
        self.assertEqual(response.status_code, 400)

    def tearDown(self):
        User.objects.all().delete()
        Facility.objects.all().delete()
        TestType.objects.all().delete()
        Patient.objects.all().delete()
        Referral.objects.all().delete()
        ReferralTest.objects.all().delete()
