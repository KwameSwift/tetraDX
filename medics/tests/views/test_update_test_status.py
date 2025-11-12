from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from authentication.models import UserType
from medics.models import (
    Facility,
    Patient,
    Referral,
    ReferralTest,
    Test,
    TestStatus,
    TestType,
)

User = get_user_model()


class UpdateTestStatusTestCase(BaseTestCase):
    """
    Test case for update test status API endpoint.
    """

    def setUp(self):
        self.url_name = "medics:update-test-status"

        # Create test users
        self.doctor = User.objects.create_user(
            username="doctor",
            full_name="Dr. Smith",
            phone_number="1111111111",
            user_type=UserType.MEDICAL_PRACTITIONER.value,
        )

        self.technician = User.objects.create_user(
            username="technician",
            full_name="Lab Tech",
            phone_number="2222222222",
            user_type=UserType.LAB_TECHNICIAN.value,
        )

        self.unauthorized_user = User.objects.create_user(
            username="unauthorized",
            full_name="Unauthorized User",
            phone_number="3333333333",
            user_type=UserType.MEDICAL_PRACTITIONER.value,
        )

        # Create facility and test type
        self.facility = Facility.objects.create(name="Test Lab")
        self.facility.users.add(self.technician)
        self.test_type = TestType.objects.create(name="Blood Test")
        self.test = Test.objects.create(name="Complete Blood Count")
        self.test.test_types.add(self.test_type)
        self.facility.test_types.add(self.test_type)

        # Create patient
        self.patient = Patient.objects.create(
            full_name_or_id="John Doe", contact_number="0987654321"
        )

        # Create referral
        self.referral = Referral.objects.create(
            patient=self.patient,
            facility=self.facility,
            clinical_notes="Test referral",
            referred_by=self.doctor,
        )

        # Create referral test
        self.referral_test = ReferralTest.objects.create(
            referral=self.referral,
            test=self.test,
        )

        # Login as doctor to get token
        login_data = {"phone_number": "1111111111"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        self.doctor_token = login_response.json()["data"]["access_token"]

        # Login as technician to get token
        login_data = {"phone_number": "2222222222"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        self.technician_token = login_response.json()["data"]["access_token"]

        # Login as unauthorized user to get token
        login_data = {"phone_number": "3333333333"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        self.unauthorized_token = login_response.json()["data"]["access_token"]

    def test_update_test_status_success_by_doctor(self):
        """
        Test successful status update by the referring doctor.
        """
        url = reverse_lazy(
            self.url_name, kwargs={"referral_test_id": self.referral_test.id}
        )

        update_data = {
            "status": TestStatus.COMPLETED.value,
        }

        response = self.client.put(
            url,
            data=update_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.doctor_token}",
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(response_data["message"], "Test status updated successfully")
        self.assertIn("data", response_data)
        self.assertEqual(response_data["data"]["referral_id"], self.referral.id)
        self.assertEqual(response_data["data"]["test_id"], self.referral_test.id)
        self.assertEqual(response_data["data"]["status"], TestStatus.COMPLETED.value)

        # Verify the status was actually updated in the database
        self.referral_test.refresh_from_db()
        self.assertEqual(self.referral_test.status, TestStatus.COMPLETED.value)

    def test_update_test_status_success_by_technician(self):
        """
        Test successful status update by a facility technician.
        """
        url = reverse_lazy(
            self.url_name, kwargs={"referral_test_id": self.referral_test.id}
        )

        update_data = {
            "status": TestStatus.RECEIVED.value,
        }

        response = self.client.put(
            url,
            data=update_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.technician_token}",
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(response_data["message"], "Test status updated successfully")
        self.assertEqual(response_data["data"]["status"], TestStatus.RECEIVED.value)

        # Verify the status was actually updated
        self.referral_test.refresh_from_db()
        self.assertEqual(self.referral_test.status, TestStatus.RECEIVED.value)

    def test_update_test_status_invalid_referral_test_id(self):
        """
        Test update with invalid referral test ID.
        """
        url = reverse_lazy(self.url_name, kwargs={"referral_test_id": 99999})

        update_data = {
            "status": TestStatus.COMPLETED.value,
        }

        response = self.client.put(
            url,
            data=update_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.doctor_token}",
        )

        self.assertEqual(response.status_code, 400)

    def test_update_test_status_permission_denied(self):
        """
        Test update by unauthorized user.
        """
        url = reverse_lazy(
            self.url_name, kwargs={"referral_test_id": self.referral_test.id}
        )

        update_data = {
            "status": TestStatus.COMPLETED.value,
        }

        response = self.client.put(
            url,
            data=update_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.unauthorized_token}",
        )

        self.assertEqual(response.status_code, 400)

    def test_update_test_status_invalid_status(self):
        """
        Test update with invalid status value.
        """
        url = reverse_lazy(
            self.url_name, kwargs={"referral_test_id": self.referral_test.id}
        )

        update_data = {
            "status": "InvalidStatus",
        }

        response = self.client.put(
            url,
            data=update_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.doctor_token}",
        )

        self.assertEqual(response.status_code, 400)

    def test_update_test_status_missing_status(self):
        """
        Test update without status field.
        """
        url = reverse_lazy(
            self.url_name, kwargs={"referral_test_id": self.referral_test.id}
        )

        update_data = {}  # Missing status field

        response = self.client.put(
            url,
            data=update_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.doctor_token}",
        )

        self.assertEqual(response.status_code, 400)

    def tearDown(self):
        User.objects.all().delete()
        Facility.objects.all().delete()
        TestType.objects.all().delete()
        Test.objects.all().delete()
        Patient.objects.all().delete()
        Referral.objects.all().delete()
        ReferralTest.objects.all().delete()
