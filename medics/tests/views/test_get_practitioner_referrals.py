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
        self.practitioner_user.set_password("TestPass123!")
        self.practitioner_user.save()

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
        login_data = {"phone_number": "1234567890", "password": "TestPass123!"}
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
        non_pract_user = User.objects.create_user(
            username="non_pract",
            full_name="Non Pract",
            phone_number="0987654321",
            user_type=UserType.LAB_TECHNICIAN.value,
        )
        non_pract_user.set_password("TestPass123!")
        non_pract_user.save()

        login_data = {"phone_number": "0987654321", "password": "TestPass123!"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        non_pract_token = login_response.json()["data"]["access_token"]

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {non_pract_token}",
        )
        self.assertEqual(response.status_code, 400)

    def test_search_by_patient_name(self):
        """
        Test search functionality by patient name.
        """
        # Create additional referrals with different patients
        patient2 = Patient.objects.create(
            full_name_or_id="Jane Smith", contact_number="2222222222"
        )
        referral2 = Referral.objects.create(
            patient=patient2,
            facility=self.facility,
            referred_by=self.practitioner_user,
        )
        ReferralTest.objects.create(referral=referral2, test=self.test)

        # Search for John
        response = self.client.get(
            self.url,
            {"search_query": "John"},
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["referrals"]), 1)
        self.assertIn("John", data["referrals"][0]["patient_name_or_id"])

    def test_search_by_facility_name(self):
        """
        Test search functionality by facility name.
        """
        # Create another facility and referral
        facility2 = Facility.objects.create(name="City Hospital")
        patient2 = Patient.objects.create(
            full_name_or_id="Alice Brown", contact_number="3333333333"
        )
        referral2 = Referral.objects.create(
            patient=patient2,
            facility=facility2,
            referred_by=self.practitioner_user,
        )
        ReferralTest.objects.create(referral=referral2, test=self.test)

        # Search for Test Lab
        response = self.client.get(
            self.url,
            {"search_query": "Test Lab"},
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["referrals"]), 1)
        self.assertEqual(data["referrals"][0]["facility_name"], "Test Lab")

    def test_search_by_test_name(self):
        """
        Test search functionality by test name.
        """
        # Create another test and referral
        test2 = Test.objects.create(name="X-Ray Chest")
        test2.test_types.add(self.test_type)
        patient2 = Patient.objects.create(
            full_name_or_id="Bob Wilson", contact_number="4444444444"
        )
        referral2 = Referral.objects.create(
            patient=patient2,
            facility=self.facility,
            referred_by=self.practitioner_user,
        )
        ReferralTest.objects.create(referral=referral2, test=test2)

        # Search for Blood Count
        response = self.client.get(
            self.url,
            {"search_query": "Blood Count"},
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["referrals"]), 1)
        self.assertEqual(
            data["referrals"][0]["tests"][0]["test_name"], "Complete Blood Count"
        )

    def test_search_by_test_type_name(self):
        """
        Test search functionality by test type name.
        """
        # Create another test type and referral
        test_type2 = TestType.objects.create(name="Radiology")
        test2 = Test.objects.create(name="MRI Scan")
        test2.test_types.add(test_type2)
        patient2 = Patient.objects.create(
            full_name_or_id="Carol Davis", contact_number="5555555555"
        )
        referral2 = Referral.objects.create(
            patient=patient2,
            facility=self.facility,
            referred_by=self.practitioner_user,
        )
        ReferralTest.objects.create(referral=referral2, test=test2)

        # Search for Blood Test
        response = self.client.get(
            self.url,
            {"search_query": "Blood Test"},
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["referrals"]), 1)
        self.assertEqual(
            data["referrals"][0]["tests"][0]["test_type_name"], "Blood Test"
        )

    def test_search_no_results(self):
        """
        Test search functionality with no matching results.
        """
        response = self.client.get(
            self.url,
            {"search_query": "NonExistentQuery"},
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["referrals"]), 0)
        self.assertEqual(data["pagination"]["total_referrals"], 0)

    def test_search_case_insensitive(self):
        """
        Test that search is case-insensitive.
        """
        # Search with lowercase
        response = self.client.get(
            self.url,
            {"search_query": "john doe"},
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["referrals"]), 1)
        self.assertIn("John", data["referrals"][0]["patient_name_or_id"])

    def test_search_partial_match(self):
        """
        Test that search works with partial matches.
        """
        # Search with partial patient name
        response = self.client.get(
            self.url,
            {"search_query": "Joh"},
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["referrals"]), 1)
        self.assertIn("John", data["referrals"][0]["patient_name_or_id"])

    def tearDown(self):
        User.objects.all().delete()
        Facility.objects.all().delete()
        TestType.objects.all().delete()
        Patient.objects.all().delete()
        Referral.objects.all().delete()
        ReferralTest.objects.all().delete()
