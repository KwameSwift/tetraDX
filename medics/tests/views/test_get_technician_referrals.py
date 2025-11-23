from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from authentication.models import UserType
from medics.models import Facility, Patient, Referral, ReferralTest, Test, TestType

User = get_user_model()


class GetTechnicianReferralsTestCase(BaseTestCase):
    """
    Test case for get technician referrals API endpoint.
    """

    def setUp(self):
        self.url = reverse_lazy("medics:get-technician-referrals")

        # Create lab technician user
        self.tech_user = User.objects.create_user(
            username="tech_user",
            full_name="Tech User",
            phone_number="1234567890",
            user_type=UserType.LAB_TECHNICIAN.value,
        )
        self.tech_user.set_password("TestPass123!")
        self.tech_user.save()

        # Create facility
        self.facility = Facility.objects.create(name="Test Lab")
        self.facility.users.add(self.tech_user)

        # Create test type and patient
        self.test_type = TestType.objects.create(name="Blood Test")
        self.facility.test_types.add(self.test_type)
        self.test = Test.objects.create(
            name="Complete Blood Count", test_type=self.test_type
        )
        self.patient = Patient.objects.create(
            full_name_or_id="John Doe", contact_number="1111111111"
        )

        # Create referral to the facility
        self.referral = Referral.objects.create(
            patient=self.patient,
            facility=self.facility,
            referred_by=self.tech_user,  # Even though tech can't refer, for test
        )
        # Create ReferralTest to link the test to the referral
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

    def test_get_technician_referrals_success(self):
        """
        Test successful retrieval of technician referrals.
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
        self.assertIn("pagination", response["data"])
        # Check that test_type_name is included in the referral data
        self.assertGreater(len(response["data"]["referrals"]), 0)
        referral = response["data"]["referrals"][0]
        self.assertIn("tests", referral)
        self.assertGreater(len(referral["tests"]), 0)
        self.assertEqual(referral["tests"][0]["test_type_name"], "Blood Test")

    def test_get_technician_referrals_unauthorized_user_type(self):
        """
        Test retrieval by non-technician user.
        """

        # Create non-tech user
        non_tech_user = User.objects.create_user(
            username="non_tech",
            full_name="Non Tech",
            phone_number="0987654321",
            user_type=UserType.MEDICAL_PRACTITIONER.value,
        )
        non_tech_user.set_password("TestPass123!")
        non_tech_user.save()

        login_data = {"phone_number": "0987654321", "password": "TestPass123!"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        non_tech_token = login_response.json()["data"]["access_token"]

        response = self.client.get(
            self.url,
            HTTP_AUTHORIZATION=f"Bearer {non_tech_token}",
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
        doctor = User.objects.create_user(
            username="doctor",
            full_name="Dr. House",
            phone_number="9999999999",
            user_type=UserType.MEDICAL_PRACTITIONER.value,
        )
        referral2 = Referral.objects.create(
            patient=patient2, facility=self.facility, referred_by=doctor
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

    def test_search_by_referring_doctor_name(self):
        """
        Test search functionality by referring doctor name.
        """
        # Create another doctor and referral
        doctor = User.objects.create_user(
            username="doctor",
            full_name="Dr. Strange",
            phone_number="8888888888",
            user_type=UserType.MEDICAL_PRACTITIONER.value,
        )
        patient2 = Patient.objects.create(
            full_name_or_id="Alice Brown", contact_number="3333333333"
        )
        referral2 = Referral.objects.create(
            patient=patient2, facility=self.facility, referred_by=doctor
        )
        ReferralTest.objects.create(referral=referral2, test=self.test)

        # Search for Dr. Strange
        response = self.client.get(
            self.url,
            {"search_query": "Strange"},
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["referrals"]), 1)
        self.assertIn("Strange", data["referrals"][0]["referral_doctor"])

    def test_search_by_test_name(self):
        """
        Test search functionality by test name.
        """
        # Create another test and referral
        test2 = Test.objects.create(name="Urinalysis", test_type=self.test_type)
        patient2 = Patient.objects.create(
            full_name_or_id="Bob Wilson", contact_number="4444444444"
        )
        referral2 = Referral.objects.create(
            patient=patient2, facility=self.facility, referred_by=self.tech_user
        )
        ReferralTest.objects.create(referral=referral2, test=test2)

        # Search for Complete
        response = self.client.get(
            self.url,
            {"search_query": "Complete"},
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
        test_type2 = TestType.objects.create(name="Imaging")
        self.facility.test_types.add(test_type2)
        test2 = Test.objects.create(name="CT Scan", test_type=test_type2)
        patient2 = Patient.objects.create(
            full_name_or_id="Carol Davis", contact_number="5555555555"
        )
        referral2 = Referral.objects.create(
            patient=patient2, facility=self.facility, referred_by=self.tech_user
        )
        ReferralTest.objects.create(referral=referral2, test=test2)

        # Search for Blood Test
        response = self.client.get(
            self.url,
            {"search_query": "Blood"},
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
            {"search_query": "NonExistentQuery123"},
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

    def test_search_with_pagination(self):
        """
        Test search functionality with pagination.
        """
        # Create multiple referrals with similar names
        for i in range(5):
            patient = Patient.objects.create(
                full_name_or_id=f"Search Patient {i}",
                contact_number=f"600000000{i}",
            )
            referral = Referral.objects.create(
                patient=patient, facility=self.facility, referred_by=self.tech_user
            )
            ReferralTest.objects.create(referral=referral, test=self.test)

        # Search with pagination
        response = self.client.get(
            self.url,
            {"search_query": "Search Patient", "page_size": "2", "page_number": "1"},
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data["referrals"]), 2)
        self.assertEqual(data["pagination"]["total_referrals"], 5)
        self.assertEqual(data["pagination"]["total_pages"], 3)

    def tearDown(self):
        User.objects.all().delete()
        Facility.objects.all().delete()
        TestType.objects.all().delete()
        Patient.objects.all().delete()
        Referral.objects.all().delete()
        ReferralTest.objects.all().delete()
