import datetime
import os

import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'userservice.settings')
django.setup()

import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.hashers import check_password
from userservice.models import Users, OTPVerification
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from unittest.mock import ANY, MagicMock, patch
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.test import TestCase
import requests_mock
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
import json



@pytest.mark.django_db
class TestSignupView:

    def setup_method(self):
        self.client = APIClient()
        self.signup_url = reverse('signup')  

    def test_signup_success(self):
        """
        Test successful user signup.
        """
        data = {
            "email": "test@example.com",
            "password": "password123",
            "username": "testuser",
            "phone_number": "0818374950",
            "is_active": False
        }
        response = self.client.post(self.signup_url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'success'
        user = Users.objects.get(email=data['email'])
        assert user is not None
        assert not user.is_active  # Assuming users are not active by default
        assert check_password(data['password'], user.password)

    def test_signup_user_exists(self):
        """
        Test signup with an email that's already registered.
        """
        Users.objects.create(email="existing@example.com", password="password123")
        data = {
            "email": "existing@example.com",
            "password": "newpassword123",
        }
        response = self.client.post(self.signup_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'error'

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
        assert response.data['status'] == 'error'



@pytest.mark.django_db
class TestSendEmailOTPView:

    def setup_method(self):
        self.client = APIClient()
        self.send_email_otp_url = reverse('send_email_otp')  

        self.user = Users.objects.create(
            first_name="Test",
            last_name="User",
            email="testuser@example.com",
        )

    @patch('userservice.views.SendMail')
    def test_send_email_otp_success(self, mock_send_mail):
        data = {
            "email": self.user.email,
        }
        response = self.client.post(self.send_email_otp_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert OTPVerification.objects.filter(user=self.user).exists()
        mock_send_mail.assert_called_once()  # Assert that SendMail was called

    @patch('userservice.views.SendMail')
    def test_send_email_otp_invalid_email(self, mock_send_mail):
        data = {
            "email": "invalid@example.com",
        }
        response = self.client.post(self.send_email_otp_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['status'] == 'error'
        mock_send_mail.assert_not_called()  # Assert that SendMail was not called

    @patch('userservice.views.SendMail')
    def test_update_existing_otp_record(self, mock_send_mail):
        OTPVerification.objects.create(user=self.user, email_otp="123456")
        data = {
            "email": self.user.email,
        }
        response = self.client.post(self.send_email_otp_url, data)
        assert response.status_code == status.HTTP_200_OK
        otp_record = OTPVerification.objects.get(user=self.user)
        assert otp_record.email_otp != "123456"
        mock_send_mail.assert_called_once()
        

@pytest.mark.django_db
class TestSendPhoneOTPView:

    def setup_method(self):
        self.client = APIClient()
        self.send_phone_otp_url = reverse('send_phone_otp')  

        self.user = Users.objects.create(
            first_name="Test",
            last_name="User",
            phone_number="1234567890",
        )

    @patch('userservice.views.SendMail')
    def test_send_phone_otp_success(self, mock_send_mail):
        data = {
            "phone_number": self.user.phone_number,
        }
        response = self.client.post(self.send_phone_otp_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert OTPVerification.objects.filter(user=self.user).exists()
        mock_send_mail.assert_called_once()  # Assert that SendMail was called
        
    @patch('userservice.views.SendMail')
    def test_send_phone_otp_invalid_phone(self, mock_send_mail):
        data = {
            "phone_number": "invalid_phone",
        }
        response = self.client.post(self.send_phone_otp_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['status'] == 'error'
        mock_send_mail.assert_not_called()  # Assert that SendMail was not called
        


@pytest.mark.django_db
class TestSendPhoneOTPView:

    def setup_method(self):
        self.client = APIClient()
        self.send_phone_otp_url = reverse('send_phone_otp')  
        self.user = Users.objects.create(
            first_name="Test",
            last_name="User",
            phone_number="1234567890",
        )

    def test_send_phone_otp_success(self, requests_mock):
        requests_mock.post(settings.TERMII_PHONE_OTP_URL, json={"message": "success"}, status_code=200)

        data = {
            "phone_number": self.user.phone_number,
        }
        response = self.client.post(self.send_phone_otp_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert OTPVerification.objects.filter(user=self.user).exists()

    def test_send_phone_otp_invalid_phone(self, requests_mock):
        requests_mock.post(settings.TERMII_PHONE_OTP_URL, json={"message": "error"}, status_code=400)

        data = {
            "phone_number": "invalid_phone",
        }
        response = self.client.post(self.send_phone_otp_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['status'] == 'error'



@pytest.mark.django_db
class TestVerifyOTPView:

    def setup_method(self):
        self.client = APIClient()
        self.verify_otp_url = reverse('verify_otp')  

        self.user = Users.objects.create(
            first_name="Test",
            last_name="User",
            email="testuser@example.com",
            phone_number="1234567890",
        )

        self.otp_verification = OTPVerification.objects.create(
            user=self.user,
            phone_otp="123456",
            email_otp="654321",
        )

    def test_verify_otp_success(self):
        """
        Test successful OTP verification.
        """
        data = {
            "email": self.user.email,
            "phone_otp": "123456",
            "email_otp": "654321",
        }
        response = self.client.post(self.verify_otp_url, data)
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data['status'] == 'success'
        
        # Refresh user from database
        self.user.refresh_from_db()
        assert self.user.is_active  # User should be active after successful verification

        
    def test_verify_otp_expired(self):
        # Simulate the OTP being past its expiry time
        self.otp_verification.phone_otp_created_at = timezone.now() - datetime.timedelta(minutes=5)
        self.otp_verification.email_otp_created_at = timezone.now() - datetime.timedelta(minutes=5)
        assert self.otp_verification.is_expired()


  
@pytest.mark.django_db
class TestLoginView:
    def setup_method(self):
        self.client = APIClient()
        self.login_url = reverse('login') 
        self.user_password = 'password123'
        self.user = Users.objects.create(
            email="user@example.com",
            password=make_password(self.user_password),
        )

    @patch('userservice.views.SendMail')
    @patch('userservice.views.GeoIP2')
    @patch('rest_framework.request.Request')
    def test_successful_login(self, mock_request, mock_geoip2, mock_send_mail):
        # Set up mock user_agent
        mock_request.user_agent = MagicMock()
        mock_request.user_agent.browser.family = "Test Browser"
        mock_request.user_agent.browser.version_string = "1.0"
        mock_request.user_agent.os.family = "Test OS"
        mock_request.user_agent.os.version_string = "1.0"

        # Mocking GeoIP2 and SendMail
        mock_geoip2.return_value.country_code.return_value = 'NG'
        mock_send_mail.return_value = None

        data = {
            "email": self.user.email,
            "password": self.user_password
        }
        response = self.client.post(self.login_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert 'access_token' in response.data['response']


    @patch('userservice.views.SendMail')
    @patch('userservice.views.GeoIP2')
    @patch('rest_framework.request.Request')
    def test_failed_login(self, mock_request, mock_geoip2, mock_send_mail):
         # Set up mock user_agent
        mock_request.user_agent = MagicMock()
        mock_request.user_agent.browser.family = "Test Browser"
        mock_request.user_agent.browser.version_string = "1.0"
        mock_request.user_agent.os.family = "Test OS"
        mock_request.user_agent.os.version_string = "1.0"
        
        mock_geoip2.return_value.country_code.return_value = 'NG'
        mock_send_mail.return_value = None

        data = {
            "email": self.user.email,
            "password": "wrongpassword"
        }
        response = self.client.post(self.login_url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data['status'] == 'error'


@pytest.mark.django_db
class TestForgotPasswordView:

    def setup_method(self):
        self.client = APIClient()
        self.forgot_password_url = reverse('forgot_password')  
        self.user_password = 'password123'
        self.user = Users.objects.create(
            email="user@example.com",
            password=make_password(self.user_password),
            first_name="TestUser",
            # Other necessary fields...
        )

    @patch('userservice.views.SendMail')
    def test_forgot_password_success(self, mock_send_mail):
        data = {"email": self.user.email}
        response = self.client.post(self.forgot_password_url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        mock_send_mail.assert_called_once_with(
            "Reset your password",
            ANY,  # For the message, since it's a rendered string
            self.user.email
        )

    @patch('userservice.views.SendMail')
    def test_forgot_password_invalid_email(self, mock_send_mail):
        data = {"email": "nonexistent@example.com"}
        response = self.client.post(self.forgot_password_url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['status'] == 'error'
        mock_send_mail.assert_not_called()


@pytest.mark.django_db
class TestPasswordResetView:

    def setup_method(self):
        self.client = APIClient()
        self.password_reset_url = reverse('reset_password')  
        self.user = Users.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='old_password'
        )
        self.uid = self.user.id  
        self.token = default_token_generator.make_token(self.user)
        
        self.uid = urlsafe_base64_encode(force_bytes(self.user.id))
        self.token = default_token_generator.make_token(self.user)

    @patch('django.contrib.auth.tokens.default_token_generator.check_token', return_value=True)
    def test_password_reset_success(self, mock_check_token):
        data = {
            'uid': self.uid,
            'token': self.token,
            'password': 'new_password'
        }
        response = self.client.post(self.password_reset_url, data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'

    @patch('django.contrib.auth.tokens.default_token_generator.check_token', return_value=False)
    def test_password_reset_invalid_link(self, mock_check_token):
        data = {
            'uid': self.uid,
            'token': 'invalid_token',
            'password': 'new_password'
        }
        response = self.client.post(self.password_reset_url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['status'] == 'error'
        
        
@pytest.mark.django_db
class TestUpdateUserView:

    def setup_method(self):
        self.client = APIClient()
        self.user = Users.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123',
            phone_number='123456789'
        )
        self.update_url = reverse('update_user')  
        self.client.force_authenticate(user=self.user)

    def test_update_user_success(self):
        updated_data = {
            'username': 'updateduser',
            'email': 'updated@example.com',
            'phone_number': '123456789'
        }
        response = self.client.put(self.update_url, updated_data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['response']['username'] == updated_data['username']
        assert response.data['response']['email'] == updated_data['email']

    def test_update_user_invalid_data(self):
        invalid_data = {
            'username': 'updateduser',  
            'email': 'updated@example.com',
            'phone_number': ''  # Invalid data
        }
        response = self.client.put(self.update_url, invalid_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['status'] == 'error'
        

@pytest.mark.django_db
class TestLogoutView:
        
    def setup_method(self):
        self.client = APIClient()
        self.user = Users.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        self.logout_url = reverse('logout')
        self.refresh = RefreshToken.for_user(self.user)

        # Calculate an expiration date for the token
        expires_at = timezone.now() + datetime.timedelta(days=7) 
        
        OutstandingToken.objects.filter(jti=self.refresh['jti']).delete()
        OutstandingToken.objects.create(
            user=self.user, token=str(self.refresh), jti=self.refresh['jti'], expires_at=expires_at
        )
        self.client.force_authenticate(user=self.user)

    def test_logout_success(self):
        response = self.client.delete(self.logout_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert not OutstandingToken.objects.filter(user=self.user).exists()



@pytest.mark.django_db
class TestDeleteAccountView:

    def setup_method(self):
        self.client = APIClient()
        self.user = Users.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword123'
        )
        self.delete_account_url = reverse('delete_account')  
        self.refresh = RefreshToken.for_user(self.user)
        
        # Calculate an expiration date for the token
        expires_at = timezone.now() + datetime.timedelta(days=7) 
        
        OutstandingToken.objects.filter(jti=self.refresh['jti']).delete()
        OutstandingToken.objects.create(
            user=self.user, token=str(self.refresh), jti=self.refresh['jti'], expires_at=expires_at
        )
        self.client.force_authenticate(user=self.user)

    def test_delete_account_success(self):
        response = self.client.delete(self.delete_account_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'
        assert not Users.objects.filter(id=self.user.id).exists()

 
