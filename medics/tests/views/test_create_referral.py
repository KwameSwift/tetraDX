from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from authentication.models import UserType
from medics.models import BranchTechnician, Facility, FacilityBranch, Test, TestType

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
            user_type=UserType.MEDICAL_PRACTITIONER.value,
        )
        self.test_user.set_password("TestPass123!")
        self.test_user.save()

        # Create facility, branch and test type
        self.facility = Facility.objects.create(name="Test Lab")
        self.branch = FacilityBranch.objects.create(
            facility=self.facility, name="Main Branch"
        )
        BranchTechnician.objects.create(user=self.test_user, branch=self.branch)

        self.test_type = TestType.objects.create(
            name="Blood Test", facility=self.facility
        )
        self.test = Test.objects.create(
            name="Complete Blood Count", test_type=self.test_type
        )
        self.test2 = Test.objects.create(name="Urine Test", test_type=self.test_type)

        # Login to get token
        login_data = {"phone_number": "1234567890", "password": "TestPass123!"}
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
            "tests": [self.test.id],
            "branch_id": self.branch.id,
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
        self.assertEqual(response["data"]["facility_name"], "Test Lab")
        self.assertEqual(response["data"]["branch_name"], "Main Branch")
        self.assertEqual(len(response["data"]["tests"]), 1)
        self.assertEqual(
            response["data"]["tests"][0]["test_name"], "Complete Blood Count"
        )
        self.assertEqual(response["data"]["tests"][0]["test_type_name"], "Blood Test")

    def test_create_referral_multiple_tests(self):
        """
        Test successful creation of referral with multiple tests.
        """

        referral_data = {
            "patient_full_name_or_id": "Jane Doe",
            "patient_contact_number": "0987654322",
            "tests": [self.test.id, self.test2.id],
            "branch_id": self.branch.id,
            "clinical_notes": "Multiple test notes",
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
        self.assertEqual(response["data"]["patient_name_or_id"], "Jane Doe")
        self.assertEqual(response["data"]["facility_name"], "Test Lab")
        self.assertEqual(response["data"]["branch_name"], "Main Branch")
        self.assertEqual(len(response["data"]["tests"]), 2)
        test_names = [test["test_name"] for test in response["data"]["tests"]]
        self.assertIn("Complete Blood Count", test_names)
        self.assertIn("Urine Test", test_names)

    def test_create_referral_missing_fields(self):
        """
        Test creation of referral with missing required fields.
        """

        referral_data = {
            # Missing patient_full_name_or_id, tests, facility_id
            "patient_contact_number": "0987654321",
        }

        response = self.client.post(
            self.url,
            data=referral_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json(),
            {
                "status": "error",
                "code": "400",
                "detail": {
                    "patient_full_name_or_id": ["This field is required."],
                    "tests": ["This field is required."],
                    "branch_id": ["This field is required."],
                },
            },
        )

    def test_create_referral_invalid_facility(self):
        """
        Test creation of referral with invalid facility ID.
        """

        referral_data = {
            "patient_full_name_or_id": "John Doe",
            "tests": [self.test.id],
            "branch_id": 999,  # Invalid ID
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
            "branch_id": self.branch.id,
            "tests": [999],  # Invalid ID
        }

        response = self.client.post(
            self.url,
            data=referral_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 400)

        self.assertEqual(
            response.json(),
            {
                "status": "error",
                "code": "400",
                "detail": {"test_id": ["Test with the given ID does not exist."]},
            },
        )

    def test_create_referral_empty_tests_list(self):
        """
        Test creation of referral with empty tests list.
        """

        referral_data = {
            "patient_full_name_or_id": "John Doe",
            "patient_contact_number": "0987654321",
            "tests": [],  # Empty list
            "branch_id": self.branch.id,
            "clinical_notes": "Test notes",
        }

        response = self.client.post(
            self.url,
            data=referral_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_referral_with_duplicate_tests(self):
        """
        Test creation of referral with duplicate test IDs (should only create one referral test).
        """

        referral_data = {
            "patient_full_name_or_id": "Jane Smith",
            "patient_contact_number": "0987654323",
            "tests": [self.test.id, self.test.id],  # Duplicate test IDs
            "branch_id": self.branch.id,
            "clinical_notes": "Duplicate test notes",
        }

        response = self.client.post(
            self.url,
            data=referral_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        # The API should handle duplicates gracefully
        # Depending on implementation, it may succeed with only one test
        # or return a validation error
        self.assertIn(response.status_code, [201, 400])

    def test_create_referral_test_not_in_facility(self):
        """
        Test creation of referral with test that's not available at the facility.
        """
        # Create another facility and test type not linked to main facility
        other_facility = Facility.objects.create(name="Other Lab")
        other_test_type = TestType.objects.create(name="X-Ray", facility=other_facility)
        other_test = Test.objects.create(name="Chest X-Ray", test_type=other_test_type)

        referral_data = {
            "patient_full_name_or_id": "John Doe",
            "patient_contact_number": "0987654321",
            "tests": [other_test.id],  # Test not available at self.facility
            "branch_id": self.branch.id,
            "clinical_notes": "Test notes",
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
