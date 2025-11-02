from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from medics.models import Facility


class GetFacilitiesTestCase(BaseTestCase):
    """
    Test case for get facilities API endpoint.
    """

    def setUp(self):
        self.url = reverse_lazy("medics:get-facilities")

        # Create test facilities
        self.facility1 = Facility.objects.create(name="Lab A")
        self.facility2 = Facility.objects.create(name="Lab B")

    def test_get_facilities_success(self):
        """
        Test successful retrieval of facilities.
        """

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        response = response.json()
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["message"], "Facilities retrieved successfully")
        self.assertEqual(len(response["data"]), 2)
        # Check if the facilities are in the response
        facility_names = [f["name"] for f in response["data"]]
        self.assertIn("Lab A", facility_names)
        self.assertIn("Lab B", facility_names)

    def tearDown(self):
        Facility.objects.all().delete()
