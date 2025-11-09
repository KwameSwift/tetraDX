from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from medics.models import Facility, Test, TestType

User = get_user_model()


class CreateReferralTestCase(BaseTestCase):
    """
    Test case for create referral API endpoint.
    """

    def setUp(self):
        self.url = reverse_lazy("medics:create-referral")

        # Create test user
        self.test_user = User.objects.create_user(
            username="test_user",
            full_name="Test User",
            phone_number="1234567890",
        )

        # Create facility and test type
        self.facility = Facility.objects.create(name="Test Lab")
        self.facility.users.add(self.test_user)
        self.test_type = TestType.objects.create(name="Blood Test")
        self.test = Test.objects.create(name="Complete Blood Count")
        self.test.test_types.add(self.test_type)
        self.facility.test_types.add(self.test_type)

        # Login to get token
        login_data = {"phone_number": "1234567890"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        self.access_token = login_response.json()["data"]["access_token"]

    def test_create_referral_success(self):
        """
        Test successful creation of referral.
        """

        referral_data = {
            "patient_full_name_or_id": "John Doe",
            "patient_contact_number": "0987654321",
            "test_id": self.test.id,
            "facility_id": self.facility.id,
            "clinical_notes": "Test notes",
        }

        response = self.client.post(
            self.url,
            data=referral_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 201)
        response = response.json()
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["message"], "Referral created successfully")
        self.assertIn("data", response)
        self.assertEqual(response["data"]["patient_name_or_id"], "John Doe")
        self.assertEqual(response["data"]["test_type_name"], "Blood Test")
        self.assertEqual(response["data"]["facility"], "Test Lab")

    def test_create_referral_missing_fields(self):
        """
        Test creation of referral with missing required fields.
        """

        referral_data = {
            # Missing patient_full_name_or_id, test_type_id, facility_id
            "patient_contact_number": "0987654321",
        }

        response = self.client.post(
            self.url,
            data=referral_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_referral_invalid_facility(self):
        """
        Test creation of referral with invalid facility ID.
        """

        referral_data = {
            "patient_full_name_or_id": "John Doe",
            "test_id": self.test.id,
            "facility_id": 999,  # Invalid ID
        }

        response = self.client.post(
            self.url,
            data=referral_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_referral_invalid_test_type(self):
        """
        Test creation of referral with invalid test type ID.
        """

        referral_data = {
            "patient_full_name_or_id": "John Doe",
            "facility_id": self.facility.id,
            "test_id": 999,  # Invalid ID
        }

        response = self.client.post(
            self.url,
            data=referral_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 400)

    def tearDown(self):
        User.objects.all().delete()
        Facility.objects.all().delete()
        TestType.objects.all().delete()
        Test.objects.all().delete()
