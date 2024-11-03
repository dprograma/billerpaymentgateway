import os
from datetime import timedelta

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'userservice.settings')
django.setup()

import pytest
from django.test import TestCase
from django.utils import timezone
import datetime


from userservice.models import LoginAttempt, Users, OTPVerification


@pytest.mark.django_db
class TestUsersModel(TestCase):
    def test_users_model(self):
        # Create a sample user
        user = Users.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword",
            address="Test Address",
            phone_number="1234567890",
        )

        # Test the fields and methods of the user model
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpassword"))
        self.assertEqual(user.address, "Test Address")
        self.assertEqual(user.phone_number, "1234567890")
        self.assertEqual(str(user), "testuser")

        # Test the UserManager's create_superuser method
        admin_user = Users.objects.create_superuser(
            username="adminuser",
            email="admin@example.com",
            password="adminpassword",
            address="Admin Address",
            phone_number="0987654321",
        )

        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertEqual(admin_user.username, "adminuser")
        self.assertEqual(admin_user.email, "admin@example.com")
        self.assertTrue(admin_user.check_password("adminpassword"))
        self.assertEqual(admin_user.address, "Admin Address")
        self.assertEqual(admin_user.phone_number, "0987654321")
        self.assertEqual(str(admin_user), "adminuser")




@pytest.mark.django_db
class TestLoginAttempt:
    TEST_IP_ADDRESS = '123.123.123.123'
    MAX_LOGIN_ATTEMPTS = 3
    @pytest.fixture(autouse=True)
    def setup_class(self, db):
        self.user = Users.objects.create(first_name="John", last_name="Doe", email="john@example.com", last_login_ip=self.TEST_IP_ADDRESS)
        self.login_attempt = LoginAttempt.objects.create(ip_address=self.TEST_IP_ADDRESS, user=self.user)

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

    def test_lock_user(self):
        # Lock the user
        LoginAttempt.lock_user(self.TEST_IP_ADDRESS)

        # Retrieve the user associated with the IP
        user = Users.objects.get(last_login_ip=self.TEST_IP_ADDRESS)

        # Check that the user is locked
        assert user.is_locked
        


@pytest.mark.django_db
class TestOTPVerification:
    
    @pytest.fixture(autouse=True)
    def setup_method(self, db):
        self.user = Users.objects.create(
            username="testuser",
            email="testuser@example.com",
            password="testpassword123",
            is_active=False,
        )

        # Create an OTPVerification instance for the test user
        self.otp_verification = OTPVerification.objects.create(
            user=self.user,
            phone_otp="123456",
            email_otp="654321",
            # Other fields if necessary...
        )

    def test_is_expired(self):
        # Check if the OTP is not expired right after creation
        assert not self.otp_verification.is_expired()

        # Simulate the OTP being past its expiry time
        self.otp_verification.phone_otp_created_at = timezone.now() - datetime.timedelta(minutes=5)
        self.otp_verification.email_otp_created_at = timezone.now() - datetime.timedelta(minutes=5)
        assert self.otp_verification.is_expired()

    def test_set_user_is_active(self):
        # Initially, the user should not be active
        assert not self.user.is_active

        # Activate the user
        self.otp_verification.set_user_is_active(self.user.id)

        # Reload user data from the database
        self.user.refresh_from_db()

        # Now, the user should be active
        assert self.user.is_active
