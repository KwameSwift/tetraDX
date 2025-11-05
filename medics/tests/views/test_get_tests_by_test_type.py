from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from medics.models import Test, TestType


class GetTestsByTestTypeTestCase(BaseTestCase):
    """
    Test case for get tests by test type API endpoint.
    """

    def setUp(self):
        # Create test types and tests
        self.test_type1 = TestType.objects.create(name="Blood Test")
        self.test_type2 = TestType.objects.create(name="Urine Test")
        self.test1 = Test.objects.create(name="Complete Blood Count")
        self.test2 = Test.objects.create(name="Blood Glucose")
        self.test3 = Test.objects.create(name="Urinalysis")

        # Associate tests with test types
        self.test_type1.tests.add(self.test1, self.test2)
        self.test_type2.tests.add(self.test3)

    def test_get_tests_by_test_type_success(self):
        """
        Test successful retrieval of tests for a test type.
        """
        url = reverse_lazy(
            "medics:get-tests-by-test-type", kwargs={"test_type_id": self.test_type1.id}
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["status"], "success")
        self.assertEqual(
            response["message"], "Tests for test type retrieved successfully"
        )
        self.assertEqual(len(response["data"]), 2)
        # Check if the tests are in the response
        test_names = [t["name"] for t in response["data"]]
        self.assertIn("Complete Blood Count", test_names)
        self.assertIn("Blood Glucose", test_names)
        self.assertNotIn("Urinalysis", test_names)

    def test_get_tests_by_test_type_different_test_type(self):
        """
        Test retrieval of tests for a different test type.
        """
        url = reverse_lazy(
            "medics:get-tests-by-test-type", kwargs={"test_type_id": self.test_type2.id}
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["status"], "success")
        self.assertEqual(len(response["data"]), 1)
        self.assertEqual(response["data"][0]["name"], "Urinalysis")

    def test_get_tests_by_test_type_not_found(self):
        """
        Test retrieval of tests for non-existent test type.
        """
        url = reverse_lazy(
            "medics:get-tests-by-test-type", kwargs={"test_type_id": 999}
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        response = response.json()
        self.assertEqual(response["status"], "error")
        self.assertIn("Test type with the given ID does not exist", response["detail"])

    def tearDown(self):
        Test.objects.all().delete()
        TestType.objects.all().delete()
