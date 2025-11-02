import copy
import uuid

from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from _tetradx import BaseTestCase

User = get_user_model()


class UserRegisterAPITestCase(BaseTestCase):
    """
    Test case for user registration API endpoint.
    """

    def setUp(self):
        self.url = reverse_lazy("auth:user-register")

        self.valid_data = {
            "full_name": self.generate_random_name(),
            "phone_number": self.generate_random_phone_number(),
        }

    def test_user_registration_success(self):
        """
        Test successful user registration.
        """

        response = self.client.post(
            self.url,
            data=self.valid_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("data", response.json())
        response = response.json()
        self.assertIn("id", response["data"])
        self.assertTrue(uuid.UUID(response["data"]["id"]))
        self.assertEqual(response["data"]["full_name"], self.valid_data["full_name"])
        self.assertEqual(
            response["data"]["phone_number"], self.valid_data["phone_number"]
        )

    def test_user_registration_missing_fields(self):
        """
        Test user registration with missing required fields.
        """

        invalid_data = copy.deepcopy(self.valid_data)
        invalid_data.pop("phone_number")  # Remove required field

        response = self.client.post(
            self.url,
            data=invalid_data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        response = response.json()
        self.assertEqual(
            response,
            {
                "status": "error",
                "code": "400",
                "detail": {"phone_number": ["This field is required."]},
            },
        )

    def test_user_registration_already_existing_phone_number(self):
        """
        Test user registration with an already existing phone number.
        """

        # First registration should succeed
        response1 = self.client.post(
            self.url,
            data=self.valid_data,
            content_type="application/json",
        )
        self.assertEqual(response1.status_code, 201)

        # Second registration with the same phone number should fail
        response2 = self.client.post(
            self.url,
            data=self.valid_data,
            content_type="application/json",
        )
        self.assertEqual(response2.status_code, 400)

        response2 = response2.json()
        self.assertEqual(
            response2,
            {
                "status": "error",
                "code": "400",
                "detail": {
                    "phone_number": ["A user with this phone number already exists."]
                },
            },
        )

    def tearDown(self):
        User.objects.all().delete()
