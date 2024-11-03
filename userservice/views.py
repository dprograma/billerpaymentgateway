import json
import os

import geoip2
import pyotp
import requests
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.contrib.auth.tokens import default_token_generator
from django.contrib.gis.geoip2 import GeoIP2
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_exempt
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from amaps.sendmail import SendMail

# import custom modules
from . import constants
from .models import LoginAttempt, OTPVerification, Users
from .serializers import (
    OTPVerificationSerializer,
    RetrieveUserSerializer,
    UsersSerializer,
)


@method_decorator(csrf_exempt, name="dispatch")
class SignupView(generics.CreateAPIView):
    """View class to process user signup"""

    authentication_classes = []
    permission_classes = []
    serializer_class = UsersSerializer
    success_url = "userservice/activation_sent.html"

    def post(self, request) -> Response:
        """Create a user account and send out an activation email to user email"""
        password = request.data.get("password")
        email = request.data.get("email")
        # Check if user already exist
        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            user = None
        # If user does not exist, create user
        if user is None:
            serializer = self.get_serializer(data=request.data)

            if serializer.is_valid():
                serializer.save(is_active=False, password=make_password(password))
                user = Users.objects.get(email=email)
                return Response(
                    {
                        "status": "success",
                        "response": f"User created successfully. Please verify your account on {email}",
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"status": "error", "response": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {
                    "status": "error",
                    "response": f"This email {email} is already registered.",
                },
                status=status.HTTP_200_OK,
            )


@method_decorator(csrf_exempt, name="dispatch")
class SendEmailOTPView(generics.CreateAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OTPVerificationSerializer

    def post(self, request, *args, **kwargs) -> Response:
        email = request.data.get("email")
        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            user = None
        # Generate email OTPs
        email_otp = pyotp.TOTP(pyotp.random_base32()).now()

        if user is not None:
            # Save or update email otp and attempts to database
            data = {
                "user": user.id,
                "email_otp": email_otp,
                "attempts": 0,
                "email_otp_created_at": timezone.now(),
            }

            # Check if an OTP record already exists for the user
            otp_record = OTPVerification.objects.filter(user=user).first()
            if otp_record:
                # If record exists, update it
                serializer = self.get_serializer(otp_record, data=data)
            else:
                # If no record, create a new one
                serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                serializer.save()
            # Send OTP to email
            firstname = user.first_name
            mail_subject = "Activate your Email Address"
            message = render_to_string(
                "userservice/activation_email.html",
                {
                    "user": firstname,
                    "otp": email_otp,
                },
            )

            SendMail(mail_subject, message, email)

            return Response(
                {"status": "success", "response": f"OTP sent to email {email}."},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "error", "response": "Incorrect email address provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )


@method_decorator(csrf_exempt, name="dispatch")
class SendPhoneOTPView(generics.CreateAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OTPVerificationSerializer

    def post(self, request, *args, **kwargs) -> Response:
        phone_number = request.data.get("phone_number")
        try:
            user = Users.objects.get(phone_number=phone_number)
        except Users.DoesNotExist:
            user = None
        # generate phone OTP
        phone_otp = pyotp.TOTP(pyotp.random_base32()).now()
        if user is not None:
            # Save or update email otp and attempts to database
            data = {
                "user": user.id,
                "phone_otp": phone_otp,
                "attempts": 0,
                "phone_otp_created_at": timezone.now(),
            }
            # Check if an OTP record already exists for the user
            otp_record = OTPVerification.objects.filter(user=user).first()
            if otp_record:
                # If record exists, update it
                serializer = self.get_serializer(otp_record, data=data)
            else:
                # If no record, create a new one
                serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                serializer.save()
            # Send OTP to phone number using BulkSMS
            url = settings.BULK_SMS_OTP_URL
            api_token = settings.BULK_SMS_API_TOKEN
            body = f"Hi {user.first_name} your verification code is {phone_otp}."

            try:
                response = requests.get(
                    f"{url}?api_token={api_token}&from=OjapayIBP&to={phone_number}&body={body}",
                    timeout=30,
                )
                if response.status_code == 200:
                    return Response(
                        {"status": "success", "response": response.json()},
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"status": "error", "response": "Error retrieving OTP."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except requests.exceptions.RequestException:
                return Response(
                    {"status": "error", "response": "Incorrect Phone number provided."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"status": "error", "response": "Incorrect Phone number provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class VerifyOTPView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs) -> Response:
        email = request.data.get("email")
        phone_otp = request.data.get("phone_otp")
        email_otp = request.data.get("email_otp")

        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            user = None

        if user is not None:
            try:
                otp_record = OTPVerification.objects.get(user=user)
                # Check for expiry
                if otp_record.is_expired():
                    return Response({"status": "error", "response": "OTP expired"})

                # Implement rate limiting
                if otp_record.attempts >= 3:  # Allow up to 3 attempts
                    return Response(
                        {
                            "status": "error",
                            "response": "Maximum attempt limit reached",
                        }
                    )

                # Verify OTPs
                if (
                    phone_otp == otp_record.phone_otp
                    and email_otp == otp_record.email_otp
                ):
                    # activate user
                    otp_record.set_user_is_active(id=otp_record.user_id)
                    return Response(
                        {
                            "status": "success",
                            "response": "Phone and Email verified successfully",
                        },
                        status=status.HTTP_202_ACCEPTED,
                    )
                else:
                    otp_record.attempts += 1
                    otp_record.save()
                    return Response(
                        {"status": "error", "response": "Invalid OTP"},
                    )

            except OTPVerification.DoesNotExist:
                return Response(
                    {"status": "error", "response": "OTP record not found"},
                )
        else:
            return Response({"status": "error", "response": "User not found"})


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(generics.CreateAPIView):
    """View class to process user login"""

    authentication_classes = []
    permission_classes = []
    serializer_class = RetrieveUserSerializer
    max_login_attempts = constants.MAX_LOGIN_ATTEMPTS
    lockout_duration = 900  # 15 minutes in seconds

    def post(self, request) -> Response:
        email = request.data.get("email", "")
        password = request.data.get("password", "")

        try:
            user = authenticate(email=email, password=password)
        except Users.DoesNotExist:
            user = None
        # Check if the IP is locked
        remote_address = request.META.get("HTTP_X_FORWARDED_FOR")
        if remote_address:
            ip_address = remote_address.split(",")[-1].strip()
        else:
            ip_address = request.META.get("REMOTE_ADDR")
        geopath = os.path.join(
            settings.BASE_DIR, "staticfiles/geoip/GeoLite2-Country.mmdb"
        )
        try:
            g = GeoIP2(path=geopath)
            countrycode = g.country_code(ip_address)
        except geoip2.errors.AddressNotFoundError:
            countrycode = "NG"
        # Get the country name and code
        with open(
            os.path.join(settings.BASE_DIR, "staticfiles/json/countries.json"),
            encoding="utf8",
        ) as f:
            data = json.load(f)
            for keyval in data:
                if countrycode == keyval["isoAlpha2"]:
                    code = keyval["currency"]["code"]
                    location = keyval["name"]

        # Get the user agent values
        browser = f"{request.user_agent.browser.family} {request.user_agent.browser.version_string}"
        OS = f"{request.user_agent.os.family} {request.user_agent.os.version_string}"

        if LoginAttempt.is_ip_locked(ip_address):
            return Response(
                {
                    "status": "error",
                    "response": "Your IP address is locked. Please contact support.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user is not None:
            # Check if the user account is locked
            if user.is_locked:
                return Response(
                    {
                        "status": "error",
                        "response": "Your account is locked. Please contact support to resolve your account.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                # Create a new token for this user
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                serializer = self.get_serializer(user, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                LoginAttempt.reset_attempts(ip_address)

                # Check if the user logged in from a new device
                if user.last_login_ip != ip_address or OS != user.last_login_user_agent:
                    # Send email notification to the user

                    message = render_to_string(
                        "userservice/send_new_device_notification.html",
                        {
                            "user": user.first_name,
                            "ip_address": ip_address,
                            "location": location,
                            "device": OS,
                            "browser": browser,
                            "datetime": timezone.now(),
                            "site_name": settings.CURRENT_SITE,
                        },
                    )
                    mail_subject = "New Device Login Notification"
                    SendMail(mail_subject, message, email)
                # Update the user ip address and device
                serializer.save(last_login_ip=ip_address, last_login_user_agent=OS)

                # Return response to client
                current_user = serializer.data
                return Response(
                    {
                        "status": "success",
                        "response": {
                            "user": current_user,
                            "access_token": access_token,
                            "refresh_token": str(refresh),
                        },
                    },
                    status=status.HTTP_200_OK,
                )

        else:
            # Login failed, increase login attempts
            LoginAttempt.add_attempt(ip_address)
            remaining_attempts = self.max_login_attempts - LoginAttempt.get_attempts(
                ip_address
            )

            if remaining_attempts > 0:
                return Response(
                    {
                        "status": "error",
                        "response": f"Invalid login credentials. You have {remaining_attempts} attempts remaining.",
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            else:
                # Lock the user's account for 15 minutes
                LoginAttempt.lock_user(ip_address)
                return Response(
                    {
                        "status": "error",
                        "response": f"Invalid login credentials. Your IP address has been locked for 15 minutes.",
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )


class ForgotPasswordView(APIView):
    """View class to process user forgotten password"""

    permission_classes = []

    def post(self, request):
        email = request.data.get("email", "")
        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            user = None

        if user is not None:
            current_site = settings.CLIENT_SITE
            mail_subject = "Reset your password"
            uid = urlsafe_base64_encode(force_bytes(user.id))
            token = default_token_generator.make_token(user)
            message = render_to_string(
                "userservice/password_reset_email.html",
                {
                    "user": user.first_name,
                    "domain": current_site,
                    "uid": uid,
                    "token": token,
                },
            )
            data = {
                "message": "You will receive an email to reset your password",
                "uid": uid,
                "token": token,
            }
            SendMail(mail_subject, message, email)
            return Response(
                {"status": "success", "response": data}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"status": "error", "response": "Incorrect email supplied."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PasswordResetView(generics.GenericAPIView):
    permission_classes = []
    serializer_class = RetrieveUserSerializer
    queryset = Users.objects.all()

    def post(self, request):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")

        if not uidb64:
            return Response(
                {
                    "status": "error",
                    "response": "UID is missing.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not token:
            return Response(
                {
                    "status": "error",
                    "response": "Token is missing.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = Users.objects.get(id=uid)
        except (TypeError, ValueError, OverflowError, Users.DoesNotExist):
            user = None

        data = {"password": request.data.get("password")}
        if user is not None and default_token_generator.check_token(user, token):
            serializer = self.get_serializer(user, data=data, partial=True)
            if serializer.is_valid():
                self.perform_update(serializer)
                return Response(
                    {
                        "status": "success",
                        "response": "Password reset was successful",
                    },
                    status=status.HTTP_200_OK,
                )
        else:
            return Response(
                {
                    "status": "error",
                    "response": "Invalid activation link",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class UpdateUserView(generics.RetrieveUpdateAPIView):
    """View class to update user profile"""

    serializer_class = UsersSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Users.objects.filter(id=self.request.user.id)

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs) -> Response:
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(
                {"status": "success", "response": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "error", "response": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )


class LogoutView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        try:
            # Find all refresh tokens for the user
            tokens = OutstandingToken.objects.filter(
                user_id=request.user.id, token__isnull=False
            )
            for token in tokens:
                # Blacklist each token
                BlacklistedToken.objects.get_or_create(token=token)
                # Optionally, delete the outstanding token if you want to clean up
                token.delete()

            return Response(
                {"status": "success", "response": "Successfully logged out"},
                status=status.HTTP_200_OK,
            )
        except (
            TokenError,
            OutstandingToken.DoesNotExist,
            BlacklistedToken.DoesNotExist,
        ):
            return Response(
                {"status": "error", "response": "Invalid token"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DeleteAccountView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        try:
            # Delete all outstanding tokens
            tokens = OutstandingToken.objects.filter(user_id=request.user.id)
            for token in tokens:
                token.blacklist()
        except TokenError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Delete user
        request.user.delete()

        return Response(
            {"status": "success", "response": "User account has been deleted"},
            status=status.HTTP_200_OK,
        )
