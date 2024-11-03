import datetime
import os

import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "merchantonboardingservice.settings_dev")
django.setup()

import json
from unittest.mock import ANY, MagicMock, patch

import pytest
import requests_mock
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.tokens import default_token_generator
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from onboarding.models import Merchant, OTPVerification
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
class TestCreateMerchantView:
    def setup_method(self):
        self.client = APIClient()
        self.signup_url = reverse("create-merchant")

    def test_signup_success(self):
        """
        Test successful merchant signup.
        """
        data = {
            "email": "test@example.com",
            "password": "password123",
            "first_name": "test_merchant",
            "username": "testmerchant",
            "phone_number": "0818374950",
            "is_active": False,
        }
        response = self.client.post(self.signup_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "success"
        merchant = Merchant.objects.get(email=data["email"])
        assert merchant is not None
        assert not merchant.is_active  # Merchant are not active by default
        assert check_password(data["password"], merchant.password)

    def test_signup_merchant_exists(self):
        """
        Test signup with an email that's already registered.
        """
        Merchant.objects.create(email="existing@example.com", password="password123")
        data = {
            "email": "existing@example.com",
            "password": "newpassword123",
        }
        response = self.client.post(self.signup_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "error"

    def test_signup_invalid_data(self):
        """
        Test signup with invalid data.
        """
        data = {
            "email": "not-an-email",
            "password": "pwd",
        }
        response = self.client.post(self.signup_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"


@pytest.mark.django_db
class TestSendEmailOTPView:
    def setup_method(self):
        self.client = APIClient()
        self.send_email_otp_url = reverse("otp-email")

        self.merchant = Merchant.objects.create(
            first_name="Test",
            last_name="Merchant",
            email="testMerchant@example.com",
        )

    @patch("onboarding.views.SendMail")
    def test_send_email_otp_success(self, mock_send_mail):
        data = {
            "email": self.merchant.email,
        }
        response = self.client.post(self.send_email_otp_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert OTPVerification.objects.filter(merchant=self.merchant).exists()
        mock_send_mail.assert_called_once()  # Assert that SendMail was called

    @patch("onboarding.views.SendMail")
    def test_send_email_otp_invalid_email(self, mock_send_mail):
        data = {
            "email": "invalid@example.com",
        }
        response = self.client.post(self.send_email_otp_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"
        mock_send_mail.assert_not_called()  # Assert that SendMail was not called

    @patch("onboarding.views.SendMail")
    def test_update_existing_otp_record(self, mock_send_mail):
        OTPVerification.objects.create(merchant=self.merchant, email_otp="123456")
        data = {
            "email": self.merchant.email,
        }
        response = self.client.post(self.send_email_otp_url, data)
        assert response.status_code == status.HTTP_200_OK
        otp_record = OTPVerification.objects.get(merchant=self.merchant)
        assert otp_record.email_otp != "123456"
        mock_send_mail.assert_called_once()


@pytest.mark.django_db
class TestSendPhoneOTPView:
    def setup_method(self):
        self.client = APIClient()
        self.send_phone_otp_url = reverse("otp-phone-number")
        self.merchant = Merchant.objects.create(
            first_name="Test",
            last_name="Merchant",
            phone_number="1234567890",
        )

    def test_send_phone_otp_success(self, requests_mock):
        requests_mock.post(
            settings.TERMII_PHONE_OTP_URL, json={"message": "success"}, status_code=200
        )

        data = {
            "phone_number": self.merchant.phone_number,
        }
        response = self.client.post(self.send_phone_otp_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert OTPVerification.objects.filter(merchant=self.merchant).exists()

    def test_send_phone_otp_invalid_phone(self, requests_mock):
        requests_mock.post(
            settings.TERMII_PHONE_OTP_URL, json={"message": "error"}, status_code=400
        )

        data = {
            "phone_number": "invalid_phone",
        }
        response = self.client.post(self.send_phone_otp_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"


@pytest.mark.django_db
class TestVerifyOTPView:
    def setup_method(self):
        self.client = APIClient()
        self.verify_otp_url = reverse("email-phone-verification")

        self.merchant = Merchant.objects.create(
            first_name="Test",
            last_name="Merchant",
            email="testMerchant@example.com",
            phone_number="1234567890",
        )

        self.otp_verification = OTPVerification.objects.create(
            merchant=self.merchant,
            phone_otp="123456",
            email_otp="654321",
        )

    def test_verify_otp_success(self):
        """
        Test successful OTP verification.
        """
        data = {
            "email": self.merchant.email,
            "phone_otp": "123456",
            "email_otp": "654321",
        }
        response = self.client.post(self.verify_otp_url, data)
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["status"] == "success"

        # Refresh merchant from database
        self.merchant.refresh_from_db()
        assert self.merchant.is_active  # merchant should be active after successful verification

    def test_verify_otp_expired(self):
        # Simulate the OTP being past its expiry time
        self.otp_verification.phone_otp_created_at = timezone.now() - datetime.timedelta(minutes=5)
        self.otp_verification.email_otp_created_at = timezone.now() - datetime.timedelta(minutes=5)
        assert self.otp_verification.is_expired()


@pytest.mark.django_db
class TestLoginView:
    def setup_method(self):
        self.client = APIClient()
        self.login_url = reverse("merchant_login")
        self.merchant_password = "password123"
        self.merchant = Merchant.objects.create(
            email="merchant@example.com",
            password=make_password(self.merchant_password),
        )

    @patch("onboarding.views.SendMail")
    @patch("onboarding.views.GeoIP2")
    @patch("rest_framework.request.Request")
    def test_successful_login(self, mock_request, mock_geoip2, mock_send_mail):
        # Set up mock user_agent
        mock_request.user_agent = MagicMock()
        mock_request.user_agent.browser.family = "Test Browser"
        mock_request.user_agent.browser.version_string = "1.0"
        mock_request.user_agent.os.family = "Test OS"
        mock_request.user_agent.os.version_string = "1.0"

        # Mocking GeoIP2 and SendMail
        mock_geoip2.return_value.country_code.return_value = "NG"
        mock_send_mail.return_value = None

        data = {"email": self.merchant.email, "password": self.merchant_password}
        response = self.client.post(self.login_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert "access_token" in response.data["response"]

    @patch("onboarding.views.SendMail")
    @patch("onboarding.views.GeoIP2")
    @patch("rest_framework.request.Request")
    def test_failed_login(self, mock_request, mock_geoip2, mock_send_mail):
        # Set up mock user_agent
        mock_request.user_agent = MagicMock()
        mock_request.user_agent.browser.family = "Test Browser"
        mock_request.user_agent.browser.version_string = "1.0"
        mock_request.user_agent.os.family = "Test OS"
        mock_request.user_agent.os.version_string = "1.0"

        mock_geoip2.return_value.country_code.return_value = "NG"
        mock_send_mail.return_value = None

        data = {"email": self.merchant.email, "password": "wrongpassword"}
        response = self.client.post(self.login_url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["status"] == "error"


@pytest.mark.django_db
class TestForgotPasswordView:
    def setup_method(self):
        self.client = APIClient()
        self.forgot_password_url = reverse("forgot_password")
        self.merchant_password = "password123"
        self.merchant = Merchant.objects.create(
            email="merchant@example.com",
            password=make_password(self.merchant_password),
            first_name="Testmerchant",
        )

    @patch("onboarding.views.SendMail")
    def test_forgot_password_success(self, mock_send_mail):
        data = {"email": self.merchant.email}
        response = self.client.post(self.forgot_password_url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        mock_send_mail.assert_called_once_with("Reset your password", ANY, self.merchant.email)

    @patch("onboarding.views.SendMail")
    def test_forgot_password_invalid_email(self, mock_send_mail):
        data = {"email": "nonexistent@example.com"}
        response = self.client.post(self.forgot_password_url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"
        mock_send_mail.assert_not_called()


@pytest.mark.django_db
class TestPasswordResetView:
    def setup_method(self):
        self.client = APIClient()
        self.password_reset_url = reverse("reset_password")
        self.merchant = Merchant.objects.create_user(
            username="testmerchant", email="test@example.com", password="old_password"
        )
        self.uid = self.merchant.id
        self.token = default_token_generator.make_token(self.merchant)

        self.uid = urlsafe_base64_encode(force_bytes(self.merchant.id))
        self.token = default_token_generator.make_token(self.merchant)

    @patch(
        "django.contrib.auth.tokens.default_token_generator.check_token",
        return_value=True,
    )
    def test_password_reset_success(self, mock_check_token):
        data = {"uid": self.uid, "token": self.token, "password": "new_password"}
        response = self.client.post(self.password_reset_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"

    @patch(
        "django.contrib.auth.tokens.default_token_generator.check_token",
        return_value=False,
    )
    def test_password_reset_invalid_link(self, mock_check_token):
        data = {"uid": self.uid, "token": "invalid_token", "password": "new_password"}
        response = self.client.post(self.password_reset_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"


@pytest.mark.django_db
class TestUpdateMerchantView:
    def setup_method(self):
        self.client = APIClient()
        self.merchant = Merchant.objects.create_user(
            username="testmerchant",
            email="test@example.com",
            password="testpassword123",
            phone_number="123456789",
        )
        self.update_url = reverse("update_profile")
        self.client.force_authenticate(user=self.merchant)

    def test_update_merchant_success(self):
        updated_data = {
            "username": "updatedmerchant",
            "email": "updated@example.com",
            "phone_number": "123456789",
        }
        response = self.client.put(self.update_url, updated_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["response"]["email"] == updated_data["email"]

    def test_update_merchant_invalid_data(self):
        invalid_data = {
            "username": "updatedmerchant",
            "email": "updated@example.com",
            "first_name": "",  # Invalid data
        }
        response = self.client.put(self.update_url, invalid_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"


@pytest.mark.django_db
class TestLogoutView:
    def setup_method(self):
        self.client = APIClient()
        self.merchant = Merchant.objects.create_user(
            username="testmerchant",
            email="test@example.com",
            password="testpassword123",
        )
        self.logout_url = reverse("logout")
        self.refresh = RefreshToken.for_user(self.merchant)

        # Calculate an expiration date for the token
        expires_at = timezone.now() + datetime.timedelta(days=7)

        OutstandingToken.objects.filter(jti=self.refresh["jti"]).delete()
        OutstandingToken.objects.create(
            user=self.merchant,
            token=str(self.refresh),
            jti=self.refresh["jti"],
            expires_at=expires_at,
        )
        self.client.force_authenticate(user=self.merchant)

    def test_logout_success(self):
        response = self.client.delete(self.logout_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert not OutstandingToken.objects.filter(user=self.merchant).exists()


@pytest.mark.django_db
class TestDeleteAccountView:
    def setup_method(self):
        self.client = APIClient()
        self.merchant = Merchant.objects.create_user(
            username="testmerchant",
            email="test@example.com",
            password="testpassword123",
        )
        self.delete_account_url = reverse("delete_account")
        self.refresh = RefreshToken.for_user(self.merchant)

        # Calculate an expiration date for the token
        expires_at = timezone.now() + datetime.timedelta(days=7)

        OutstandingToken.objects.filter(jti=self.refresh["jti"]).delete()
        OutstandingToken.objects.create(
            user=self.merchant,
            token=str(self.refresh),
            jti=self.refresh["jti"],
            expires_at=expires_at,
        )
        self.client.force_authenticate(user=self.merchant)

    def test_delete_account_success(self):
        response = self.client.delete(self.delete_account_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
        assert not Merchant.objects.filter(id=self.merchant.id).exists()


@pytest.mark.django_db
class TestBusinessVerificationView:
    def setup_method(self):
        self.client = APIClient()
        self.merchant = Merchant.objects.create_user(
            username="testmerchant",
            email="test@example.com",
            password="testpassword123",
            phone_number="123456789",
        )
        self.update_url = reverse("business-verification")  # Replace with your actual URL name
        self.client.force_authenticate(user=self.merchant)

    def test_update_business_verification_success(self):
        # Create mock file objects
        mock_business_certificate = SimpleUploadedFile(
            "certificate.pdf", b"file_content", content_type="application/pdf"
        )
        mock_rc_certificate = SimpleUploadedFile(
            "rc_certificate.pdf", b"file_content", content_type="application/pdf"
        )
        mock_tax_certificate = SimpleUploadedFile(
            "tax_certificate.pdf", b"file_content", content_type="application/pdf"
        )

        updated_data = {
            "email": "test@example.com",
            "business_certificate": mock_business_certificate,
            "rc_certificate": mock_rc_certificate,
            "tax_certificate": mock_tax_certificate,
        }

        response = self.client.put(self.update_url, updated_data, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "success"

    def test_update_business_verification_invalid_merchant(self):
        updated_data = {
            "email": "nonexistent@example.com",
            "profile_picture": "",
            "business_certificate": "",
            "rc_certificate": "",
            "tax_certificate": "",
        }

        response = self.client.put(self.update_url, updated_data, format="multipart")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"


@pytest.mark.django_db
class TestUpdateMerchantBankDetails:
    def setup_method(self):
        self.client = APIClient()
        self.merchant = Merchant.objects.create_user(
            username="testmerchant",
            email="test@example.com",
            password="testpassword123",
            phone_number="123456789",
        )
        self.update_url = reverse("update_merchant_bank_details")
        self.client.force_authenticate(user=self.merchant)

    def test_update_merchant_bank_details_success(self):
        updated_data = {
            "email": "test@example.com",
            "bvn": "12345678901",
            "bank_name": "bank1",
            "account_number": "1234567890",
        }
        response = self.client.put(self.update_url, updated_data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "success"
        # Additional assertions to verify the updated data can be added here

    def test_update_merchant_bank_details_invalid_merchant(self):
        updated_data = {
            "email": "nonexistent@example.com",
            "bvn": "12345678901",
            "bank_name": "Test Bank",
            "account_number": "1234567890",
        }
        response = self.client.put(self.update_url, updated_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"


@pytest.mark.django_db
class TestRetrieveMerchant:
    def setup_method(self):
        self.client = APIClient()
        # Create and authenticate the merchant
        self.merchant = Merchant.objects.create_user(
            username="testmerchant",
            email="test@example.com",
            password="testpassword123",
            phone_number="123456789",
        )
        self.client.force_authenticate(user=self.merchant)
        self.retrieve_url = reverse("get_merchant")

    def test_retrieve_merchant_success(self):
        response = self.client.get(self.retrieve_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"

    def test_retrieve_merchant_not_found(self):
        # Force authenticate with a non-existent merchant
        non_existent_merchant = Merchant(
            id=999,  # ID that does not exist in the database
            email="nonexistent@example.com",
            password="password123",
            phone_number="987654321",
        )
        self.client.force_authenticate(user=non_existent_merchant)

        response = self.client.get(self.retrieve_url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["status"] == "error"


@pytest.mark.django_db
class TestRetrieveAllMerchants:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("get_all_merchants")

        # Creating multiple merchants
        Merchant.objects.create_user(
            username="merchant1", email="merchant1@example.com", password="password123"
        )
        Merchant.objects.create_user(
            username="merchant2", email="merchant2@example.com", password="password123"
        )

        # Create and authenticate an admin or a user who has the right to view all merchants
        self.admin_user = Merchant.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpassword"
        )
        self.client.force_authenticate(user=self.admin_user)

    def test_retrieve_all_merchants(self):
        response = self.client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "success"
