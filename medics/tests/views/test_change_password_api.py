from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from _tetradx import BaseTestCase

User = get_user_model()


class ChangePasswordTestCase(BaseTestCase):
    """
    Test case for change password API endpoint.
    """

    def setUp(self):
        self.url = reverse_lazy("medics:change-password")

        # Create a test user
        self.test_user = User.objects.create_user(
            username="test_user",
            full_name="Test User",
            phone_number="1234567890",
        )
        self.test_user.set_password("OldPass123!")
        self.test_user.save()

        # Login to get token
        login_data = {"phone_number": "1234567890", "password": "OldPass123!"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        self.access_token = login_response.json()["data"]["access_token"]

    def test_change_password_success(self):
        """
        Test successful password change.
        """

        password_data = {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!",
            "confirm_new_password": "NewPass456!",
        }

        response = self.client.post(
            self.url,
            data=password_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(response_data["message"], "Password changed successfully.")

        # Verify user can login with new password
        login_data = {"phone_number": "1234567890", "password": "NewPass456!"}
        login_response = self.client.post(
            reverse_lazy("auth:login"), data=login_data, content_type="application/json"
        )
        self.assertEqual(login_response.status_code, 200)

    def test_change_password_incorrect_current_password(self):
        """
        Test password change with incorrect current password.
        """

        password_data = {
            "current_password": "WrongPass123!",
            "new_password": "NewPass456!",
            "confirm_new_password": "NewPass456!",
        }

        response = self.client.post(
            self.url,
            data=password_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("current_password", response_data["detail"])

    def test_change_password_mismatch(self):
        """
        Test password change with mismatched new passwords.
        """

        password_data = {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!",
            "confirm_new_password": "DifferentPass789!",
        }

        response = self.client.post(
            self.url,
            data=password_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertIn("confirm_new_password", response_data["detail"])

    def test_change_password_missing_fields(self):
        """
        Test password change with missing required fields.
        """

        password_data = {
            "current_password": "OldPass123!",
            # Missing new_password and confirm_new_password
        }

        response = self.client.post(
            self.url,
            data=password_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 400)

    def test_change_password_weak_password(self):
        """
        Test password change with weak password.
        """

        password_data = {
            "current_password": "OldPass123!",
            "new_password": "weak",  # Too weak
            "confirm_new_password": "weak",
        }

        response = self.client.post(
            self.url,
            data=password_data,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )
        self.assertEqual(response.status_code, 400)

    def test_change_password_unauthenticated(self):
        """
        Test password change without authentication.
        """

        password_data = {
            "current_password": "OldPass123!",
            "new_password": "NewPass456!",
            "confirm_new_password": "NewPass456!",
        }

        response = self.client.post(
            self.url,
            data=password_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def tearDown(self):
        User.objects.all().delete()
