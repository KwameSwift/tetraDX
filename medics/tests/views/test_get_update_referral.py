from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from medics.models import (
    BranchTechnician,
    Facility,
    FacilityBranch,
    Patient,
    Referral,
    ReferralTest,
    Test,
    TestType,
)

User = get_user_model()


class GetAndUpdateReferralTestCase(BaseTestCase):
    """
    Test case for get and update referral API endpoint.
    """

    def setUp(self):
        # Create test user
        self.test_user = User.objects.create_user(
            username="test_user",
            full_name="Test User",
            phone_number="1234567890",
        )
        self.test_user.set_password("TestPass123!")
        self.test_user.save()

        # Create another user for facility
        self.facility_user = User.objects.create_user(
            username="facility_user",
            full_name="Facility User",
            phone_number="0987654321",
        )
        self.facility_user.set_password("TestPass123!")
        self.facility_user.save()

        # Create facility, branch and test type
        self.facility = Facility.objects.create(name="Test Lab")
        self.branch = FacilityBranch.objects.create(
            facility=self.facility, name="Main Branch"
        )
        BranchTechnician.objects.create(user=self.facility_user, branch=self.branch)
        self.test_type = TestType.objects.create(
            name="Blood Test", facility=self.facility
        )
        self.test = Test.objects.create(
            name="Complete Blood Count", test_type=self.test_type
        )

        # Create patient
        self.patient = Patient.objects.create(
            full_name_or_id="John Doe", contact_number="1111111111"
        )

        # Create referral
        self.referral = Referral.objects.create(
            patient=self.patient,
            facility_branch=self.branch,
            referred_by=self.test_user,
        )
        # Create ReferralTest to link the test to the referral
        ReferralTest.objects.create(
            referral=self.referral,
            test=self.test,
        )

        # Login as test_user to get token
        login_data = {"phone_number": "1234567890", "password": "TestPass123!"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        self.access_token = login_response.json()["data"]["access_token"]

        # Login as facility_user
        login_data2 = {"phone_number": "0987654321", "password": "TestPass123!"}
        login_response2 = self.client.post(
            reverse_lazy("auth:login"),
            data=login_data2,
            content_type="application/json",
        )
        self.facility_token = login_response2.json()["data"]["access_token"]

        self.url = reverse_lazy(
            "medics:get-update-referral", kwargs={"referral_id": self.referral.id}
        )

    def test_get_referral_success_by_doctor(self):
        """
        Test successful retrieval of referral by referring doctor.
        """

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["message"], "Referral retrieved successfully")
        self.assertEqual(response["data"]["referral_id"], self.referral.id)
        self.assertEqual(response["data"]["patient_name_or_id"], "John Doe")
        self.assertEqual(len(response["data"]["tests"]), 1)
        self.assertEqual(response["data"]["tests"][0]["test_type_name"], "Blood Test")

    def test_get_referral_success_by_facility_worker(self):
        """
        Test successful retrieval of referral by facility worker.
        """

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {self.facility_token}",
        )
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["status"], "success")

    def test_get_referral_unauthorized(self):
        """
        Test retrieval of referral by unauthorized user.
        """

        # Create another user not associated
        unauth_user = User.objects.create_user(
            username="unauth_user",
            full_name="Unauthorized User",
            phone_number="2222222222",
        )
        unauth_user.set_password("TestPass123!")
        unauth_user.save()

        login_data = {"phone_number": "2222222222", "password": "TestPass123!"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        unauth_token = login_response.json()["data"]["access_token"]

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {unauth_token}",
        )
        self.assertEqual(response.status_code, 403)

    def test_get_referral_not_found(self):
        """
        Test retrieval of non-existent referral.
        """

        url = reverse_lazy(
            "medics:get-update-referral", kwargs={"referral_id": "INVALIDID"}
        )
        # Need to use client with raise_request_exception=False to properly test 400 errors
        self.client.raise_request_exception = False
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.client.raise_request_exception = True
        self.assertEqual(response.status_code, 400)

    def test_update_referral_status_success(self):
        """
        Test successful update of referral status.
        """

        update_data = {
            "status": "Received",
            "referral_id": self.referral.id,
        }

        response = self.client.put(
            self.url,
            data=update_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.facility_token}",
        )
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["message"], "Referral status updated successfully")
        self.assertEqual(response["data"]["status"], "Received")
        self.assertEqual(len(response["data"]["tests"]), 1)
        self.assertEqual(response["data"]["tests"][0]["test_type_name"], "Blood Test")

    def test_update_referral_status_invalid(self):
        """
        Test update of referral with invalid status.
        """

        update_data = {
            "status": "InvalidStatus",
            "referral_id": self.referral.id,
        }

        response = self.client.put(
            self.url,
            data=update_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.facility_token}",
        )
        self.assertEqual(response.status_code, 400)

    def tearDown(self):
        User.objects.all().delete()
        Facility.objects.all().delete()
        TestType.objects.all().delete()
        Patient.objects.all().delete()
        Referral.objects.all().delete()
        ReferralTest.objects.all().delete()
