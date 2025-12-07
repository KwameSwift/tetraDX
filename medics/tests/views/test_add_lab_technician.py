from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from _tetradx import BaseTestCase
from authentication.models import UserType
from medics.models import BranchTechnician, Facility, FacilityBranch

User = get_user_model()


class AddLabTechnicianTestCase(BaseTestCase):
    """
    Test case for add lab technician API endpoint.
    """

    def setUp(self):
        self.url = reverse_lazy("medics:add-lab-technician")

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

    def test_add_lab_technician_success(self):
        """
        Test successful addition of a lab technician by facility admin.
        """

        tech_data = {
            "full_name": "New Technician",
            "phone_number": "3333333333",
            "branch_id": self.branch.id,
            "password": "NewTechPass123!",
        }

        response = self.client.post(
            self.url,
            data=tech_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )

        self.assertEqual(response.status_code, 201)
        response_data = response.json()
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(response_data["message"], "Lab technician added successfully")
        self.assertIn("data", response_data)
        self.assertEqual(response_data["data"]["full_name"], "New Technician")
        self.assertEqual(response_data["data"]["phone_number"], "3333333333")
        self.assertEqual(response_data["data"]["facility_name"], "Test Lab")
        self.assertEqual(response_data["data"]["facility_branch_name"], "Main Branch")

        # Verify user was created
        new_user = User.objects.get(phone_number="3333333333")
        self.assertEqual(new_user.full_name, "New Technician")
        self.assertEqual(new_user.user_type, UserType.LAB_TECHNICIAN.value)

        # Verify technician was associated with branch
        self.assertTrue(
            BranchTechnician.objects.filter(user=new_user, branch=self.branch).exists()
        )

    def test_add_lab_technician_duplicate_phone_number(self):
        """
        Test adding a lab technician with a duplicate phone number.
        """

        tech_data = {
            "full_name": "Duplicate Tech",
            "phone_number": "1111111111",  # Already exists
            "branch_id": self.branch.id,
            "password": "NewTechPass123!",
        }

        response = self.client.post(
            self.url,
            data=tech_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("phone_number", response_data["detail"])

    def test_add_lab_technician_invalid_branch(self):
        """
        Test adding a lab technician with invalid branch ID.
        """

        tech_data = {
            "full_name": "New Technician",
            "phone_number": "4444444444",
            "branch_id": 99999,  # Invalid branch
            "password": "NewTechPass123!",
        }

        response = self.client.post(
            self.url,
            data=tech_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("branch_id", response_data["detail"])

    def test_add_lab_technician_missing_required_fields(self):
        """
        Test adding a lab technician with missing required fields.
        """

        tech_data = {
            "full_name": "New Technician",
            # Missing phone_number, branch_id, and password
        }

        response = self.client.post(
            self.url,
            data=tech_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )

        self.assertEqual(response.status_code, 400)

    def test_add_lab_technician_weak_password(self):
        """
        Test adding a lab technician with weak password.
        """

        tech_data = {
            "full_name": "New Technician",
            "phone_number": "5555555555",
            "branch_id": self.branch.id,
            "password": "weak",  # Weak password
        }

        response = self.client.post(
            self.url,
            data=tech_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.admin_token}",
        )

        self.assertEqual(response.status_code, 400)

    def test_add_lab_technician_unauthorized_non_admin(self):
        """
        Test that non-admin technicians cannot add lab technicians.
        """

        tech_data = {
            "full_name": "Unauthorized Tech",
            "phone_number": "6666666666",
            "branch_id": self.branch.id,
            "password": "UnauthorizedPass123!",
        }

        response = self.client.post(
            self.url,
            data=tech_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.tech_token}",
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn(
            "Unauthorized: Only facility admins can add Lab Technicians.",
            response_data["detail"],
        )

    def test_add_lab_technician_unauthenticated(self):
        """
        Test that unauthenticated users cannot add lab technicians.
        """

        tech_data = {
            "full_name": "Unauthorized Tech",
            "phone_number": "7777777777",
            "branch_id": self.branch.id,
            "password": "UnauthorizedPass123!",
        }

        response = self.client.post(
            self.url,
            data=tech_data,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_add_lab_technician_user_not_associated_with_facility(self):
        """
        Test adding lab technician by user not associated with any facility.
        """

        # Create user without facility association
        orphan_user = User.objects.create_user(
            username="orphan_user",
            full_name="Orphan User",
            phone_number="8888888888",
            user_type=UserType.LAB_TECHNICIAN.value,
        )
        orphan_user.set_password("OrphanPass123!")
        orphan_user.save()

        login_data = {"phone_number": "8888888888", "password": "OrphanPass123!"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        orphan_token = login_response.json()["data"]["access_token"]

        tech_data = {
            "full_name": "New Technician",
            "phone_number": "9999999999",
            "branch_id": self.branch.id,
            "password": "NewTechPass123!",
        }

        response = self.client.post(
            self.url,
            data=tech_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {orphan_token}",
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn(
            "Unauthorized: Only facility admins can add Lab Technicians.",
            response_data["detail"],
        )

    def tearDown(self):
        User.objects.all().delete()
        Facility.objects.all().delete()
        FacilityBranch.objects.all().delete()
        BranchTechnician.objects.all().delete()
