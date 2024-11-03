import json
import os
from urllib.parse import unquote

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
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException


from amaps.sendmail import SendMail
from userservice.models import (
    Category,
    LoginAttempt,
    OTPVerification,
    Users,
    Product,
    MerchantCountries,
    Recipient,
)
from walletservice.models import Currency, Wallet
from .serializers import CategorySerializer, ProductSerializer
from . import constants
from .serializers import (
    CreateMerchantSerializer,
    ForgetPasswordSerializer,
    OTPVerificationSerializer,
    PasswordResetSerializer,
    RetrieveMerchantSerializer,
    UpdateSerializer,
    MerchantCountriesSerializer,
)


@method_decorator(csrf_exempt, name="dispatch")
class CreateMerchantView(generics.CreateAPIView):
    """View class to process merchant signup"""

    authentication_classes = []
    permission_classes = []
    serializer_class = CreateMerchantSerializer

    def post(self, request, *args, **kwargs) -> Response:
        """Create a merchant account and send out an activation email to the user's email"""
        email = request.data.get("email")
        password = request.data.get("password")

        # Check if the user already exists
        try:
            merchant = Users.objects.get(email=email)
            return Response(
                {
                    "status": "error",
                    "response": f"This email {email} is already registered.",
                },
                status=status.HTTP_200_OK,
            )
        except Users.DoesNotExist:
            merchant = None

        # If the merchant does not exist, create the merchant
        if merchant is None:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save(is_active=False, password=make_password(password))
                return Response(
                    {
                        "status": "success",
                        "response": f"Users created successfully. Please verify your account on {email}",
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
                status=status.HTTP_400_BAD_REQUEST,
            )


@method_decorator(csrf_exempt, name="dispatch")
class SendEmailOTPView(generics.CreateAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OTPVerificationSerializer

    def post(self, request, *args, **kwargs) -> Response:
        print("REQUEST DATA: ", request.data)
        email = request.data.get("email")
        try:
            merchant = Users.objects.get(email=email)
        except Users.DoesNotExist:
            merchant = None
        # Generate email OTPs
        email_otp = pyotp.TOTP(pyotp.random_base32()).now()

        if merchant is not None:
            firstname = merchant.first_name
            # Save or update email otp and attempts to database
            data = {
                "user": merchant.id,
                "email_otp": email_otp,
                "email_otp_created_at": timezone.now(),
            }

            # Check if an OTP record already exists for the user
            otp_record = OTPVerification.objects.filter(user=merchant).first()
            if otp_record:
                # If record exists, update it
                serializer = self.get_serializer(otp_record, data=data, partial=True)
            else:
                # If no record, create a new one
                serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                serializer.save()
            # Send OTP to email
            mail_subject = "Activate your Email Address"
            message = render_to_string(
                "onboarding/email_activation.html",
                {
                    "merchant": firstname,
                    "otp": email_otp,
                },
            )

            SendMail(mail_subject, message, email)
            # SendMail(email, mail_subject, message, firstname)

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
        # Validate and format the phone number
        try:
            phone_obj = phonenumbers.parse(
                phone_number, None
            )  # None to auto-detect country code
            if not phonenumbers.is_valid_number(phone_obj):
                raise NumberParseException(1, "Invalid phone number")
            mobile = phonenumbers.format_number(
                phone_obj, phonenumbers.PhoneNumberFormat.E164
            )
            print("VALID PHONE NUMBER: ", mobile)
        except NumberParseException:
            return Response(
                {"status": "error", "response": "Invalid phone number"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            merchant = Users.objects.get(phone_number=mobile)
        except Users.DoesNotExist:
            merchant = None
        # generate phone OTP
        phone_otp = pyotp.TOTP(pyotp.random_base32()).now()

        if merchant is not None:
            # Save or update email otp and attempts to database
            data = {
                "user": merchant.id,
                "phone_otp": phone_otp,
                "phone_otp_created_at": timezone.now(),
            }
            print("MERCHANT ID: ", merchant.id)
            print("MERCHANT PHONE OTP: ", phone_otp)
            # Check if an OTP record already exists for the user
            otp_record = OTPVerification.objects.filter(user=merchant).first()
            print("OTP EXIST: ", otp_record)
            if otp_record:
                # If record exists, update it
                serializer = self.get_serializer(otp_record, data=data, partial=True)
            else:
                # If no record, create a new one
                serializer = self.get_serializer(data=data)

            if serializer.is_valid():
                serializer.save()
            print("SERIALIZER DATA: ", serializer.data)
            url = settings.TERMII_OTP_URL
            api_token = settings.TERMII_OTP_TOKEN
            body = f"Hi {merchant.first_name}, your verification code is {phone_otp}."
            # if mobile.startswith("0"):
            #     m = mobile.lstrip("0")
            # phone = "234" + m

            payload = {
                "to": mobile,
                "from": "Ojapay",
                "sms": body,
                "type": "plain",
                "channel": "generic",
                "api_key": api_token,
            }

            headers = {
                "Content-Type": "application/json",
            }
            # try:
            #     response = requests.post(url, headers=headers, json=payload)
            #     if response.status_code == 200:
            #         return Response(
            #             {"status": "success", "response": response.json()},
            #             status=status.HTTP_200_OK,
            #         )
            #     else:
            #         return Response(
            #             {"status": "error", "response": response.text},
            #             status=status.HTTP_400_BAD_REQUEST,
            #         )
            # except requests.exceptions.RequestException:
            #     return Response(
            #         {"status": "error", "response": "Incorrect Phone number provided."},
            #         status=status.HTTP_400_BAD_REQUEST,
            #     )
            # Send OTP to email
            mail_subject = "Verify your Phone number"

            message = (
                f"Hi {merchant.first_name}, Your phone OTP has arrived: {phone_otp}"
            )

            SendMail(mail_subject, message, merchant.email)
            # SendMail(email, mail_subject, message, firstname)
            return Response(
                {"status": "success", "response": f"Phone OTP sent to {mobile}"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "error", "response": "Incorrect Phone number provided222."},
                status=status.HTTP_400_BAD_REQUEST,
            )


@method_decorator(csrf_exempt, name="dispatch")
class VerifyOTPView(generics.CreateAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = OTPVerificationSerializer

    def post(self, request, *args, **kwargs) -> Response:
        email = request.data.get("email")
        phone_otp = request.data.get("phone_otp")
        email_otp = request.data.get("email_otp")
        currency = request.data.get("currency")
        print(
            "phone otp: ", phone_otp, "email otp: ", email_otp, "currency: ", currency
        )
        try:
            merchant = Users.objects.get(email=email)
        except Users.DoesNotExist:
            merchant = None
        if merchant is not None:
            try:
                otp_record = OTPVerification.objects.get(user=merchant)
                # Check for expiry
                if otp_record.is_expired():
                    return Response({"status": "error", "response": "OTP expired"})

                # Implement rate limiting
                if otp_record.attempts >= 3:  # Allow up to 3 attempts
                    if otp_record.otp_is_due_for_retry:  # Check if due for retry
                        otp_record.attempts = 0
                        otp_record.save()
                    else:
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
                    # Check if currency exists in the Currency model
                    try:
                        # Assuming your Currency model has a 'code' field for the currency code
                        selected_currency = Currency.objects.get(code=currency)
                    except Currency.DoesNotExist:
                        # If currency does not exist, default to "NGN"
                        selected_currency = Currency.objects.get(code="NGN")
                    print("SELECTED CURRENCY: ", selected_currency)
                    # activate user
                    otp_record.set_user_is_active(id=otp_record.user_id)
                    # create user wallet
                    Wallet.objects.create(
                        user=merchant, currency=selected_currency.code
                    )
                    merchant.is_activated = True
                    merchant.save()
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
            return Response(
                {"status": "error", "response": "Users not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


@method_decorator(csrf_exempt, name="dispatch")
class MerchantLoginView(generics.CreateAPIView):
    """View class to process merchant login"""

    authentication_classes = []
    permission_classes = []
    serializer_class = RetrieveMerchantSerializer
    max_login_attempts = constants.MAX_LOGIN_ATTEMPTS
    lockout_duration = 900  # 15 minutes in seconds

    def post(self, request, *args, **kwargs) -> Response:
        email = request.data.get("email", "")
        password = request.data.get("password", "")

        try:
            merchant = authenticate(email=email, password=password)
        except Users.DoesNotExist:
            merchant = None
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
                    location = keyval["name"]

        # Get the merchant agent values
        browser = f"{request.user_agent.browser.family} {request.user_agent.browser.version_string}"
        OS = f"{request.user_agent.os.family} {request.user_agent.os.version_string}"

        if merchant is not None:
            # Check if the merchant account is locked
            if merchant.is_locked:
                return Response(
                    {
                        "status": "error",
                        "response": "Your account is locked. Please contact support to resolve your account.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                # Create a new token for this merchant
                refresh = RefreshToken.for_user(merchant)
                access_token = str(refresh.access_token)
                serializer = self.get_serializer(merchant, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                LoginAttempt.reset_attempts(ip_address)
                # Check if the user logged in from a new device
                if (
                    merchant.last_login_ip != ip_address
                    or OS != merchant.last_login_user_agent
                ):
                    # Send email notification to the user

                    message = render_to_string(
                        "onboarding/send_new_device_notification.html",
                        {
                            "user": merchant.first_name,
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
                wallet = Wallet.objects.filter(user=merchant)
                print("MERCHANT WALLET: ", wallet)
                # Return response to client
                current_user = serializer.data
                return Response(
                    {
                        "status": "success",
                        "response": {
                            "user": current_user,
                            "wallet": wallet,
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
                LoginAttempt.lock_merchant(ip_address)
                return Response(
                    {
                        "status": "error",
                        "response": "Invalid login credentials. Your IP address has been locked for 15 minutes.",
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )


@method_decorator(csrf_exempt, name="dispatch")
class ForgetPasswordView(generics.CreateAPIView):
    serializer_class = ForgetPasswordSerializer
    permission_classes = []

    def post(self, request, *args, **kwargs):
        email = request.data.get("email", "")
        try:
            merchant = Users.objects.get(email=email)
        except Users.DoesNotExist:
            merchant = None

        if merchant is not None:
            current_site = settings.CURRENT_SITE
            mail_subject = "Reset your password"
            message = render_to_string(
                "onboarding/password_reset_email.html",
                {
                    "user": merchant.first_name,
                    "domain": current_site,
                    "uid": urlsafe_base64_encode(force_bytes(merchant.id)),
                    "token": default_token_generator.make_token(merchant),
                },
            )
            SendMail(mail_subject, message, email)
            return Response({"status": "success"}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"status": "error", "response": "Incorrect email supplied."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PasswordResetView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = []

    def post(self, request, *args, **kwargs):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = Users.objects.get(id=uid)
        except (TypeError, ValueError, OverflowError, Users.DoesNotExist):
            user = None

        data = {"password": request.data.get("password")}
        if user is not None and default_token_generator.check_token(user, token):
            serializer = self.get_serializer(user, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "status": "success",
                        "response": "Password reset was successful",
                    },
                    status=status.HTTP_200_OK,
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
                    "response": "Invalid activation link",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


@method_decorator(csrf_exempt, name="dispatch")
class UpdateMerchantView(generics.RetrieveUpdateAPIView):
    """View class to update merchant profile"""

    serializer_class = UpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Users.objects.filter(id=self.request.user.id)

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs) -> Response:
        merchant = self.get_object()
        serializer = self.get_serializer(merchant, data=request.data, partial=True)
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
    # permission_classes = [permissions.IsAuthenticated]

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


# @method_decorator(csrf_exempt, name="dispatch")
# class BusinessVerificationView(generics.GenericAPIView):
#     """View class to process user signup"""

#     authentication_classes = []
#     permission_classes = []
#     serializer_class = RetrieveMerchantSerializer

#     def put(self, request, *args, **kwargs):
#         """Update merchant details"""
#         email = request.data.get("email")
#         # Check if merchant already exists
#         try:
#             merchant = Users.objects.get(email=email)
#         except Users.DoesNotExist:
#             merchant = None

#         # If merchant does not exist, return an error response
#         if merchant is None:
#             return Response(
#                 {
#                     "status": "error",
#                     "response": "User does not exist.",
#                 },
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         # Otherwise, update the merchant's details
#         serializer = self.get_serializer(merchant, data=request.data, partial=True)
#         if serializer.is_valid():
#             self.perform_update(serializer)
#             # Check compliance after updating the user's details
#             merchant.is_compliant()
#             return Response(
#                 {
#                     "status": "success",
#                     "response": serializer.data,
#                 },
#                 status=status.HTTP_200_OK,
#             )
#         else:
#             return Response(
#                 {"status": "error", "response": serializer.errors},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#     def perform_update(self, serializer):
#         """Perform the update on the merchant object"""
#         serializer.save()


@method_decorator(csrf_exempt, name="dispatch")
class BusinessVerificationView(generics.GenericAPIView):
    """View class to process user business verification"""

    authentication_classes = []
    permission_classes = []
    serializer_class = RetrieveMerchantSerializer

    def put(self, request, *args, **kwargs):
        """Update merchant details based on verification process"""
        email = request.data.get("email")
        business_type = request.data.get("business_type")
        print("REQUEST DATA: ", request.data)

        try:
            merchant = Users.objects.get(email=email)
        except Users.DoesNotExist:
            return Response(
                {"status": "error", "response": "User does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update the user's business details
        serializer = self.get_serializer(merchant, data=request.data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)

            # Update or create Recipient for the merchant
            recipient, created = Recipient.objects.update_or_create(
                owner=merchant,
                defaults={
                    "name": f"{merchant.first_name} {merchant.last_name}",
                    "recipient_type": business_type,
                    "is_verified": False,  # You can change this based on logic
                },
            )

            # Optionally, create a Donation record if required
            # Donation.objects.create(
            #     recipient=recipient,
            #     amount=0,  # Initialize to 0, this can be updated later
            #     currency="USD",  # Example, change as needed
            #     description="Initial business verification",
            #     reference="VERIFICATION"
            # )

            # Trigger compliance checks and return success response
            compliant = merchant.is_compliant()
            if compliant:
                recipient.is_verified = True
            return Response(
                {"status": "success", "response": serializer.data},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"status": "error", "response": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def perform_update(self, serializer):
        """Perform the update on the merchant object"""
        serializer.save()


@method_decorator(csrf_exempt, name="dispatch")
class UpdateMerchantBankDetails(generics.GenericAPIView):
    """View class to merchant's bank details"""

    authentication_classes = []
    permission_classes = []
    serializer_class = RetrieveMerchantSerializer

    def update(self, request) -> Response:
        """Update a merchant bank account account details and BVN"""
        email = request.data.get("email")
        # Check if merchant already exist
        try:
            merchant = Users.objects.get(email=email)
        except Users.DoesNotExist:
            merchant = None
        # If merchant does not exist, create user
        if merchant is None:
            return Response(
                {
                    "status": "error",
                    "response": "Users does not exist.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            serializer = self.get_serializer(merchant, data=request.data, partial=True)
            if serializer.is_valid():
                self.perform_update(serializer)
                return Response(
                    {
                        "status": "success",
                        "response": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"status": "error", "response": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )


@method_decorator(csrf_exempt, name="dispatch")
class RetrieveMerchant(generics.ListAPIView):
    """View class to retrieve merchant profile"""

    serializer_class = RetrieveMerchantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            merchant = Users.objects.get(id=request.user.id)
        except Users.DoesNotExist:
            merchant = None

        if merchant is not None:
            serializer = self.get_serializer(merchant)
            return Response(
                {"status": "success", "response": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "error", "response": "Users not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )


@method_decorator(csrf_exempt, name="dispatch")
class RetrieveAllMerchants(generics.ListAPIView):
    """View class to retrieve all merchants profile"""

    serializer_class = RetrieveMerchantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        merchants = Users.objects.all()
        if merchants is not None:
            serializer = self.get_serializer(merchants)
            return Response(
                {"status": "success", "response": serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "error", "response": "Records not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class IdTypeChoicesAPIView(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        return Response({"idtypes": Users.ID_CHOICES})


class BankNameChoicesAPIView(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        return Response({"banknames": Users.BANK_CHOICES})


class ProductListCreateView(generics.ListCreateAPIView):
    """Retrieve products for a particular merchant or create products for merchant"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        merchant = Users.objects.get(id=self.request.user.id)
        return Product.objects.filter(user=merchant)

    def perform_create(self, serializer):
        merchant = Users.objects.get(id=self.request.user.id)
        serializer.save(user=merchant)

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            "status": "success",
            "response": "Products retrieved successfully",
            "data": serializer.data,
        }
        print("SERIALIZER: ", serializer.data)
        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        print("REQUEST DATA: ", request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            response_data = {
                "status": "success",
                "response": "Product created successfully",
                "data": serializer.data,
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            response_data = {
                "status": "error",
                "response": "Product creation failed",
                "errors": serializer.errors,
            }
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)


# class GetAllProductlist(generics.ListAPIView):
#     """Retrieve all products for all merchants"""
#     permission_classes = [permissions.IsAuthenticated]
#     serializer_class = ProductSerializer

#     def get(self, request, category=None, country=None, *args, **kwargs):
#         if country or category:
#             print("COUNTRY: ", country)
#             print("CATEGORY: ", category.lower())
#             # Decode the country name
#             category = unquote(category.lower())
#             country = unquote(country)
#             try:
#                 category = Category.objects.get(name=category)
#                 print("CATEGORY: ", category)
#                 products = Product.objects.filter(user__country=country, category=category)
#                 print("PRODUCTS QUERY: ", str(products.query))
#                 serializer = self.get_serializer(products, many=True)
#                 response_data = {
#                     'status': 'success',
#                     'response': 'Products retrieved successfully',
#                     'data': serializer.data
#                 }
#                 return Response(response_data, status=status.HTTP_200_OK)
#             except Exception as e:
#                 return Response({"status": "error", "response": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#         else:
#             country = "Nigeria"
#             try:
#                 products = Product.objects.filter(user__country=country)
#                 serializer = self.get_serializer(products, many=True)
#                 print("DATA: ", serializer.data)
#                 response_data = {
#                     'status': 'success',
#                     'response': 'Products retrieved successfully',
#                     'data': serializer.data
#                 }
#                 return Response(response_data, status=status.HTTP_200_OK)
#             except Exception as e:
#                 return Response({"status": "error", "response": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAllProductlist(generics.ListAPIView):
    """Retrieve all products for all merchants"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer

    def get(self, request, category=None, country=None, *args, **kwargs):
        if country or category:
            # Decode the URL-encoded parameters (spaces, special characters)
            category = unquote(category.lower())
            country = unquote(country)

            print("Decoded CATEGORY: ", category)
            print("Decoded COUNTRY: ", country)

            try:
                category = Category.objects.get(name=category)
                products = Product.objects.filter(
                    user__country=country, category=category
                )
                serializer = self.get_serializer(products, many=True)
                response_data = {
                    "status": "success",
                    "response": "Products retrieved successfully",
                    "data": serializer.data,
                }
                return Response(response_data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {"status": "error", "response": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            country = "Nigeria"
            try:
                products = Product.objects.filter(user__country=country)
                serializer = self.get_serializer(products, many=True)
                response_data = {
                    "status": "success",
                    "response": "Products retrieved successfully",
                    "data": serializer.data,
                }
                return Response(response_data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(
                    {"status": "error", "response": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )


class ProductUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a product by ID"""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        merchant = self.request.user
        return Product.objects.filter(user=merchant)

    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(data={"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class MerchantCountriesView(APIView):
    def get(self, request):
        country_choices = MerchantCountries.objects.all()
        serializer = MerchantCountriesSerializer(country_choices)
        print("MERCHANT COUNTRIES: ", serializer.data)
        return Response(serializer.data)
