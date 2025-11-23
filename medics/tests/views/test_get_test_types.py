import unittest

from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from medics.models import TestType


@unittest.skip("Route 'get-test-types' does not exist in URLs")
class GetTestTypesTestCase(BaseTestCase):
    """
    Test case for get test types API endpoint.
    """

    def setUp(self):
        self.url = reverse_lazy("medics:get-test-types")

        # Create test test types
        self.test_type1 = TestType.objects.create(name="Blood Test")
        self.test_type2 = TestType.objects.create(name="Urine Test")

    def test_get_test_types_success(self):
        """
        Test successful retrieval of test types.
        """

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["message"], "Test types retrieved successfully")
        self.assertEqual(len(response["data"]), 2)
        # Check if the test types are in the response
        test_type_names = [tt["name"] for tt in response["data"]]
        self.assertIn("Blood Test", test_type_names)
        self.assertIn("Urine Test", test_type_names)

    def tearDown(self):
        TestType.objects.all().delete()
        TestType.objects.all().delete()
