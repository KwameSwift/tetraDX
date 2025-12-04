from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from _tetradx import BaseTestCase

User = get_user_model()


class UserLoginTestCase(BaseTestCase):
    """
    Test case for user login API endpoint.
    """

    def setUp(self):
        self.url = reverse_lazy("auth:login")

        # Create a test user
        self.test_user = User.objects.create_user(
            username="test_user",
            full_name="Test User",
            phone_number="1234567890",
        )
        self.test_user.set_password("TestPass123!")
        self.test_user.save()

    def test_user_login_success(self):
        """
        Test successful user login.
        """

        login_data = {
            "phone_number": "1234567890",
            "password": "TestPass123!",
        }

        response = self.client.post(
            self.url,
            data=login_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        response = response.json()
        usr_data = response["data"]["user_data"]
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["message"], "Login successful")
        self.assertEqual(usr_data["id"], str(self.test_user.id))
        self.assertEqual(usr_data["full_name"], self.test_user.full_name)
        self.assertEqual(usr_data["phone_number"], self.test_user.phone_number)

    def test_user_login_invalid_phone_number(self):
        """
        Test user login with invalid phone number.
        """

        login_data = {
            "phone_number": "0987654321",  # Non-existent phone number
            "password": "TestPass123!",
        }

        response = self.client.post(
            self.url, data=login_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        response = response.json()
        # DRF's raise_exception=True returns errors without wrapper
        self.assertIn("phone_number_and_password", response)
        self.assertEqual(
            response["phone_number_and_password"],
            ["Invalid phone number or password."],
        )

    def test_user_login_missing_phone_number(self):
        """
        Test user login with missing phone number.
        """

        login_data = {
            # "phone_number" and "password" are missing
        }

        response = self.client.post(
            self.url, data=login_data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        response = response.json()
        # DRF's raise_exception=True returns errors without wrapper
        self.assertIn("phone_number", response)
        self.assertIn("password", response)
        self.assertEqual(response["phone_number"], ["This field is required."])
        self.assertEqual(response["password"], ["This field is required."])

    def tearDown(self):
        User.objects.all().delete()
