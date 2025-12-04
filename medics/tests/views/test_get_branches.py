from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from medics.models import Facility, FacilityBranch


class GetBranchTestCase(BaseTestCase):
    """
    Test case for get branches by facility API endpoint.
    """

    def setUp(self):
        # Create facilities and branches
        self.facility1 = Facility.objects.create(name="Test Lab")
        self.facility2 = Facility.objects.create(name="City Hospital")

        self.branch1 = FacilityBranch.objects.create(
            facility=self.facility1, name="Main Branch"
        )
        self.branch2 = FacilityBranch.objects.create(
            facility=self.facility1, name="East Branch"
        )
        self.branch3 = FacilityBranch.objects.create(
            facility=self.facility2, name="West Branch"
        )

    def test_get_branches_success(self):
        """
        Test successful retrieval of branches for a facility.
        """

        url = reverse_lazy(
            "medics:get-branches-by-facility", kwargs={"facility_id": self.facility1.id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(response_data["message"], "Branches retrieved successfully")
        self.assertEqual(len(response_data["data"]), 2)

        # Verify branch data
        branch_names = [branch["name"] for branch in response_data["data"]]
        self.assertIn("Main Branch", branch_names)
        self.assertIn("East Branch", branch_names)

    def test_get_branches_different_facility(self):
        """
        Test retrieval of branches for a different facility.
        """

        url = reverse_lazy(
            "medics:get-branches-by-facility", kwargs={"facility_id": self.facility2.id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["data"]), 1)
        self.assertEqual(response_data["data"][0]["name"], "West Branch")

    def test_get_branches_no_branches(self):
        """
        Test retrieval of branches for facility with no branches.
        """

        facility3 = Facility.objects.create(name="Empty Lab")
        url = reverse_lazy(
            "medics:get-branches-by-facility", kwargs={"facility_id": facility3.id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["data"]), 0)

    def test_get_branches_invalid_facility_id(self):
        """
        Test retrieval with non-existent facility ID.
        """

        url = reverse_lazy(
            "medics:get-branches-by-facility", kwargs={"facility_id": 99999}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["data"]), 0)

    def tearDown(self):
        Facility.objects.all().delete()
        FacilityBranch.objects.all().delete()
