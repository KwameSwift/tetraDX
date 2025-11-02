import random
import string

from django.test import Client, TestCase


class BaseTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()

    def generate_random_email(self):
        domains = ["user.com", "example.com"]
        username = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        domain = random.choice(domains)
        return f"{username}@{domain}"

    def generate_random_bvn(self):
        return "".join(str(random.randint(0, 9)) for _ in range(11))

    def generate_random_name(self):
        name = "".join(random.choices(string.ascii_lowercase, k=6))
        return name.title()

    def generate_random_phone_number(self):
        return f"0701{''.join(random.choices(string.digits, k=10))}"

    def generate_random_amount(self):
        return random.randint(1000, 10000)
