from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from medics.models import Facility, TestType


class GetTestTypesByFacilityTestCase(BaseTestCase):
    """
    Test case for get test types by facility API endpoint.
    """

    def setUp(self):
        # Create facility and test types
        self.facility1 = Facility.objects.create(name="Test Lab 1")
        self.facility2 = Facility.objects.create(name="Test Lab 2")
        self.test_type1 = TestType.objects.create(
            name="Blood Test", facility=self.facility1
        )
        self.test_type2 = TestType.objects.create(
            name="Urine Test", facility=self.facility1
        )
        self.test_type3 = TestType.objects.create(name="X-Ray", facility=self.facility2)

    def test_get_test_types_by_facility_success(self):
        """
        Test successful retrieval of test types for a facility.
        """
        url = reverse_lazy(
            "medics:get-test-types-by-facility",
            kwargs={"facility_id": self.facility1.id},
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["status"], "success")
        self.assertEqual(
            response["message"], "Test types for facility retrieved successfully"
        )
        self.assertEqual(len(response["data"]), 2)
        # Check if the test types are in the response
        test_type_names = [tt["name"] for tt in response["data"]]
        self.assertIn("Blood Test", test_type_names)
        self.assertIn("Urine Test", test_type_names)
        self.assertNotIn("X-Ray", test_type_names)

    def test_get_test_types_by_facility_different_facility(self):
        """
        Test retrieval of test types for a different facility.
        """
        url = reverse_lazy(
            "medics:get-test-types-by-facility",
            kwargs={"facility_id": self.facility2.id},
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["status"], "success")
        self.assertEqual(len(response["data"]), 1)
        self.assertEqual(response["data"][0]["name"], "X-Ray")

    def test_get_test_types_by_facility_not_found(self):
        """
        Test retrieval of test types for non-existent facility.
        """
        url = reverse_lazy(
            "medics:get-test-types-by-facility", kwargs={"facility_id": 999}
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        response = response.json()
        self.assertEqual(response["status"], "error")
        self.assertIn("Facility with the given ID does not exist", response["detail"])

    def tearDown(self):
        Facility.objects.all().delete()
        TestType.objects.all().delete()
