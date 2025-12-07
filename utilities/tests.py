from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from authentication.models import UserType
from medics.models import BranchTechnician, Facility, FacilityBranch, Test, TestType

User = get_user_model()


class AddTestTypesTestCase(BaseTestCase):
    """
    Test case for add test types utility API endpoint.
    """

    def setUp(self):
        self.url = reverse_lazy("utilities:add-test-types")

        # Create lab technician user
        self.tech_user = User.objects.create_user(
            username="tech_user",
            full_name="Tech User",
            phone_number="1234567890",
            user_type=UserType.LAB_TECHNICIAN.value,
        )
        self.tech_user.set_password("TestPass123!")
        self.tech_user.save()

        # Create facility, branch and associate with tech user
        self.facility = Facility.objects.create(name="Test Lab")
        self.branch = FacilityBranch.objects.create(
            facility=self.facility, name="Main Branch"
        )
        BranchTechnician.objects.create(user=self.tech_user, branch=self.branch)

        # Create practitioner user
        self.pract_user = User.objects.create_user(
            username="pract_user",
            full_name="Pract User",
            phone_number="0987654321",
            user_type=UserType.MEDICAL_PRACTITIONER.value,
        )
        self.pract_user.set_password("TestPass123!")
        self.pract_user.save()

        # Login as tech user to get token
        login_data = {"phone_number": "1234567890", "password": "TestPass123!"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        self.access_token = login_response.json()["data"]["access_token"]

        # Login as practitioner to get token
        login_data_pract = {"phone_number": "0987654321", "password": "TestPass123!"}
        login_response_pract = self.client.post(
            reverse_lazy("auth:login"),
            data=login_data_pract,
            content_type="application/json",
        )
        self.practitioner_token = login_response_pract.json()["data"]["access_token"]

    def test_add_test_types_success(self):
        """
        Test successful addition of test types by lab technician.
        """
        test_data = {
            "name": "Cardiology Tests",
            "tests": [
                {"name": "ECG"},
                {"name": "Echo"},
                {"name": "Stress Test"},
            ],
        }

        response = self.client.post(
            self.url,
            data=test_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )

        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["message"], "Test type and tests added successfully")
        self.assertIn("data", response)
        self.assertEqual(response["data"]["name"], "CARDIOLOGY TESTS")
        self.assertEqual(len(response["data"]["tests"]), 3)

        # Verify database objects were created
        test_type = TestType.objects.get(
            name="CARDIOLOGY TESTS", facility=self.facility
        )
        self.assertEqual(test_type.facility, self.facility)

        # Verify tests were created and associated
        tests = Test.objects.filter(test_type=test_type)
        self.assertEqual(tests.count(), 3)
        test_names = [test.name for test in tests]
        self.assertIn("ECG", test_names)
        self.assertIn("ECHO", test_names)
        self.assertIn("STRESS TEST", test_names)

    def test_add_test_types_unauthorized_user_type(self):
        """
        Test that only lab technicians can add test types.
        """
        test_data = {"name": "Unauthorized Test Type", "tests": [{"name": "Test 1"}]}

        response = self.client.post(
            self.url,
            data=test_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.practitioner_token}",
        )

        self.assertEqual(response.status_code, 400)
        response = response.json()
        self.assertEqual(response["status"], "error")
        self.assertIn(
            "Unauthorized: Only Lab Technicians can add test types", response["detail"]
        )

    def test_add_test_types_duplicate_name_same_facility(self):
        """
        Test that duplicate test type names are not allowed for the same facility.
        """
        # First create a test type
        test_data = {"name": "Duplicate Test", "tests": [{"name": "Test 1"}]}

        response1 = self.client.post(
            self.url,
            data=test_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response1.status_code, 200)

        # Try to create the same test type again - should be rejected
        response2 = self.client.post(
            self.url,
            data=test_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )

        # Should return validation error
        self.assertEqual(response2.status_code, 400)
        response2_json = response2.json()
        self.assertIn("detail", response2_json)
        self.assertIn("name", response2_json["detail"])
        self.assertIn("already exists", response2_json["detail"]["name"][0])

    def test_add_test_types_missing_required_fields(self):
        """
        Test validation of missing required fields.
        """
        # Missing name
        test_data = {"tests": [{"name": "Test 1"}]}

        response = self.client.post(
            self.url,
            data=test_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )

        self.assertEqual(response.status_code, 400)
        response = response.json()
        self.assertIn("detail", response)
        self.assertIn("name", response["detail"])

        # Missing tests
        test_data2 = {"name": "Test Type"}

        response2 = self.client.post(
            self.url,
            data=test_data2,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )

        self.assertEqual(response2.status_code, 400)
        response2 = response2.json()
        self.assertIn("detail", response2)
        self.assertIn("tests", response2["detail"])

        # Empty tests list
        test_data3 = {"name": "Test Type", "tests": []}

        response3 = self.client.post(
            self.url,
            data=test_data3,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )

        self.assertEqual(response3.status_code, 400)
        response3 = response3.json()
        self.assertIn("detail", response3)
        self.assertIn("tests", response3["detail"])

    def test_add_test_types_unauthenticated(self):
        """
        Test that unauthenticated users cannot add test types.
        """
        test_data = {"name": "Unauthenticated Test", "tests": [{"name": "Test 1"}]}

        response = self.client.post(
            self.url,
            data=test_data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def tearDown(self):
        User.objects.all().delete()
        Facility.objects.all().delete()
        TestType.objects.all().delete()
        Test.objects.all().delete()
