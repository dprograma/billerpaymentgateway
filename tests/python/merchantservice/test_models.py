import datetime
import os

import django
import pytest
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "merchantonboardingservice.settings_dev")
django.setup()

from django.test import TestCase
from onboarding.models import LoginAttempt, Merchant, OTPVerification


@pytest.mark.django_db
class TestMerchantModel(TestCase):
    def test_merchant_model(self):
        # Create a Merchant instance
        merchant = Merchant.objects.create(
            first_name="John",
            last_name="Doe",
            email="johndoe@example.com",
            username="johndoe",
            phone_number="1234567890",
            country="Country",
            # Add other required fields as necessary
        )

        # Fetch the created object from the database
        saved_merchant = Merchant.objects.get(pk=merchant.pk)

        # Assert that the saved object is correctly retrieved
        assert saved_merchant.first_name == "John"
        assert saved_merchant.email == "johndoe@example.com"
        # Add more assertions as necessary


@pytest.mark.django_db
class TestLoginAttempt:
    TEST_IP_ADDRESS = "123.123.123.123"
    MAX_LOGIN_ATTEMPTS = 3

    @pytest.fixture(autouse=True)
    def setup_class(self, db):
        self.merchant = Merchant.objects.create(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            last_login_ip=self.TEST_IP_ADDRESS,
        )
        self.login_attempt = LoginAttempt.objects.create(
            ip_address=self.TEST_IP_ADDRESS, merchant=self.merchant
        )

    def test_add_attempt(self):
        # Add a login attempt
        LoginAttempt.add_attempt(self.TEST_IP_ADDRESS)

        # Retrieve the updated login attempt record
        login_attempt = LoginAttempt.objects.get(ip_address=self.TEST_IP_ADDRESS)

        # Check that the number of attempts is incremented
        assert login_attempt.attempts == 1

    def test_get_attempts(self):
        # Check the number of attempts
        attempts = LoginAttempt.get_attempts(self.TEST_IP_ADDRESS)
        assert attempts == 0

        # Add an attempt and check again
        LoginAttempt.add_attempt(self.TEST_IP_ADDRESS)
        attempts = LoginAttempt.get_attempts(self.TEST_IP_ADDRESS)
        assert attempts == 1

    def test_reset_attempts(self):
        # Add a login attempt
        LoginAttempt.add_attempt(self.TEST_IP_ADDRESS)

        # Reset attempts
        LoginAttempt.reset_attempts(self.TEST_IP_ADDRESS)

        # Retrieve the updated login attempt record
        login_attempt = LoginAttempt.objects.get(ip_address=self.TEST_IP_ADDRESS)

        # Check that the number of attempts is reset
        assert login_attempt.attempts == 0

    def test_is_ip_locked(self):
        # Initially, IP should not be locked
        assert not LoginAttempt.is_ip_locked(self.TEST_IP_ADDRESS)

        # Exceed the maximum login attempts
        for _ in range(self.MAX_LOGIN_ATTEMPTS + 1):
            LoginAttempt.add_attempt(self.TEST_IP_ADDRESS)

        # Check if the IP is locked
        assert LoginAttempt.is_ip_locked(self.TEST_IP_ADDRESS)

    def test_lock_merchant(self):
        # Lock the merchant
        LoginAttempt.lock_merchant(self.TEST_IP_ADDRESS)

        # Retrieve the merchant associated with the IP
        merchant = Merchant.objects.get(last_login_ip=self.TEST_IP_ADDRESS)

        # Check that the merchant is locked
        assert merchant.is_locked


@pytest.mark.django_db
class TestOTPVerification:
    @pytest.fixture(autouse=True)
    def setup_method(self, db):
        self.merchant = Merchant.objects.create(
            username="testmerchant",
            email="testmerchant@example.com",
            password="testpassword123",
            is_active=False,
        )

        # Create an OTPVerification instance for the test merchant
        self.otp_verification = OTPVerification.objects.create(
            merchant=self.merchant,
            phone_otp="123456",
            email_otp="654321",
        )

    def test_is_expired(self):
        # Check if the OTP is not expired right after creation
        assert not self.otp_verification.is_expired()

        # Simulate the OTP being past its expiry time
        self.otp_verification.phone_otp_created_at = timezone.now() - datetime.timedelta(minutes=5)
        self.otp_verification.email_otp_created_at = timezone.now() - datetime.timedelta(minutes=5)
        assert self.otp_verification.is_expired()

    def test_set_merchant_is_active(self):
        # Initially, the merchant should not be active
        assert not self.merchant.is_active

        # Activate the merchant
        self.otp_verification.set_merchant_is_active(self.merchant.id)

        # Reload merchant data from the database
        self.merchant.refresh_from_db()

        # Now, the merchant should be active
        assert self.merchant.is_active
