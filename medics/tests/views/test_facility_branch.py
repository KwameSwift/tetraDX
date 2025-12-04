from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from authentication.models import UserType
from medics.models import BranchTechnician, Facility, FacilityBranch

User = get_user_model()


class FacilityBranchViewTestCase(BaseTestCase):
    """
    Test case for facility branch management API endpoints (add and deactivate).
    """

    def setUp(self):
        # Create facility admin user
        self.admin_user = User.objects.create_user(
            username="admin_user",
            full_name="Admin User",
            phone_number="1111111111",
            user_type=UserType.LAB_TECHNICIAN.value,
        )
        self.admin_user.set_password("AdminPass123!")
        self.admin_user.save()

        # Create regular technician user
        self.tech_user = User.objects.create_user(
            username="tech_user",
            full_name="Tech User",
            phone_number="2222222222",
            user_type=UserType.LAB_TECHNICIAN.value,
        )
        self.tech_user.set_password("TechPass123!")
        self.tech_user.save()

        # Create facility with admin
        self.facility = Facility.objects.create(name="Test Lab", admin=self.admin_user)
        self.branch = FacilityBranch.objects.create(
            facility=self.facility, name="Main Branch"
        )

        # Associate admin with branch
        BranchTechnician.objects.create(user=self.admin_user, branch=self.branch)

        # Associate tech with branch
        BranchTechnician.objects.create(user=self.tech_user, branch=self.branch)

        # Login as admin
        login_data = {"phone_number": "1111111111", "password": "AdminPass123!"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        self.admin_token = login_response.json()["data"]["access_token"]

        # Login as tech
        login_data = {"phone_number": "2222222222", "password": "TechPass123!"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        self.tech_token = login_response.json()["data"]["access_token"]

        self.add_branch_url = reverse_lazy("medics:add-branch")

    def test_add_branch_success(self):
        """
        Test successful addition of a new branch by facility admin.
        """

        branch_data = {
            "name": "New Branch",
        }

        response = self.client.post(
            self.add_branch_url,
            data=branch_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )

        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(response_data["message"], "Facility branch added successfully")
        self.assertIn("data", response_data)
        self.assertEqual(response_data["data"]["name"], "New Branch")

        # Verify branch was created in database
        self.assertTrue(
            FacilityBranch.objects.filter(
                name="New Branch", facility=self.facility
            ).exists()
        )

    def test_add_branch_duplicate_name(self):
        """
        Test adding a branch with a duplicate name.
        """

        branch_data = {
            "name": "Main Branch",  # Already exists
        }

        response = self.client.post(
            self.add_branch_url,
            data=branch_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("name", response_data["detail"])

    def test_add_branch_missing_name(self):
        """
        Test adding a branch without providing name.
        """

        branch_data = {}

        response = self.client.post(
            self.add_branch_url,
            data=branch_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )

        self.assertEqual(response.status_code, 400)

    def test_add_branch_unauthorized_non_admin(self):
        """
        Test that non-admin technicians cannot add branches.
        """

        branch_data = {
            "name": "Unauthorized Branch",
        }

        response = self.client.post(
            self.add_branch_url,
            data=branch_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.tech_token}",
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("Only facility admins can add branches", response_data["detail"])

    def test_add_branch_unauthenticated(self):
        """
        Test that unauthenticated users cannot add branches.
        """

        branch_data = {
            "name": "Unauthorized Branch",
        }

        response = self.client.post(
            self.add_branch_url,
            data=branch_data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_deactivate_branch_success(self):
        """
        Test successful deactivation of a branch by facility admin.
        """

        # Create another branch to deactivate
        branch_to_delete = FacilityBranch.objects.create(
            facility=self.facility, name="Branch to Delete"
        )

        url = reverse_lazy(
            "medics:get-branches", kwargs={"branch_id": branch_to_delete.id}
        )

        response = self.client.delete(
            url,
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(
            response_data["message"], "Facility branch deleted successfully"
        )

        # Verify branch was deactivated
        branch_to_delete.refresh_from_db()
        self.assertFalse(branch_to_delete.is_active)

    def test_deactivate_branch_invalid_id(self):
        """
        Test deactivating a branch with invalid ID.
        """

        url = reverse_lazy("medics:get-branches", kwargs={"branch_id": 99999})

        response = self.client.delete(
            url,
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("does not exist", response_data["detail"])

    def test_deactivate_branch_unauthorized_non_admin(self):
        """
        Test that non-admin technicians cannot deactivate branches.
        """

        url = reverse_lazy("medics:get-branches", kwargs={"branch_id": self.branch.id})

        response = self.client.delete(
            url,
            HTTP_AUTHORIZATION=f"Bearer {self.tech_token}",
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn(
            "Only facility admins can delete branches", response_data["detail"]
        )

    def test_deactivate_branch_unauthenticated(self):
        """
        Test that unauthenticated users cannot deactivate branches.
        """

        url = reverse_lazy("medics:get-branches", kwargs={"branch_id": self.branch.id})

        response = self.client.delete(url)

        self.assertEqual(response.status_code, 401)

    def tearDown(self):
        User.objects.all().delete()
        Facility.objects.all().delete()
        FacilityBranch.objects.all().delete()
        BranchTechnician.objects.all().delete()
