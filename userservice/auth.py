import json
import os
from datetime import datetime, date
import geoip2 # type: ignore
from django.conf import settings
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.gis.geoip2 import GeoIP2
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import status, generics, permissions, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken # type: ignore

from amaps.sendmail import PlainEmail, SendMail
from .serializers import RetrieveUserSerializer, UsersSerializer, RecipientSerializer, DonationSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication # type: ignore
from utils.api import Paystack
from utils.helpers import GenerateOTP, is_nigerian_phone_number, validate_password_strength
from walletservice.models import VirtualAccount, Wallet
from walletservice.serializers import WalletSerializer
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException

from . import constants
from .models import LoginAttempt, OTPVerification, PreviousPassword, Users, Recipient, Donation


class SignUp(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        password2 = request.data.get("confirm_password")
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        phone_number = request.data.get("phone_number")
        country = request.data.get("country")
        user_type = request.data.get("user_type")
        
        print("REQUEST DATA: ", request.data)

        # Validate required fields
        if (
            not password
            or not password2
            or not first_name
            or not last_name
            or not phone_number
            or not country
            or not email
        ):
            return Response(
                {"status": "error", "response": "All fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if email already exists
        check_email = Users.objects.filter(email=email.lower()).exists()
        if check_email:
            return Response(
                {"status": "error", "response": "Email already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if passwords match
        if password != password2:
            return Response(
                {"status": "error", "response": "Passwords do not match."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate password strength (assuming you have a validate_password_strength function)
        valid_email = validate_password_strength(password)
        if valid_email:
            return Response(
                {"status": "error", "response": valid_email}, status=status.HTTP_400_BAD_REQUEST
            )

        # Validate and format the phone number
        try:
            phone_obj = phonenumbers.parse(phone_number, None)  # None to auto-detect country code
            print(f"PHONE NUMBER: Country Code: {phone_obj.country_code}, National Number: {phone_obj.national_number}")
            # Check if the phone number is a possible number
            if not phonenumbers.is_possible_number(phone_obj):
                print("Phone number is not a possible number.")
                raise NumberParseException(1, "Invalid phone number")
            if not phonenumbers.is_valid_number(phone_obj):
                print("Phone number is not valid according to the country-specific rules.")
                raise NumberParseException(1, "Invalid phone number")
            mobile = phonenumbers.format_number(phone_obj, phonenumbers.PhoneNumberFormat.E164)
            print("VALID PHONE NUMBER: ", mobile)
        except NumberParseException:
            return Response(
                {"status": "error", "response": "Invalid phone number"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if phone number already exists
        check_phone = Users.objects.filter(phone_number=mobile).exists()
        if check_phone:
            return Response(
                {"status": "error", "response": "Phone number already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate OTP and determine user type
        otp = GenerateOTP(6)
        user_type = "Customer" if user_type.lower() == "customer" else "Merchant"

        # Create user
        username = email.split("@")[0].lower()
        obj = Users(
            email=email.lower(),
            password=make_password(password),
            first_name=first_name,
            last_name=last_name,
            phone_number=mobile,
            country=country,
            username=username,
            user_type=user_type,
        )
        obj.save()

        # Send OTP email
        msg = f"Hi {last_name}, your OTP code is {otp} and is only valid till the next 24 hours."
        PlainEmail(msg, email.lower(), "OjaPay: Your OTP has arrived.")

        # Handle OTP Verification
        check_otp = OTPVerification.objects.filter(user=obj)
        if check_otp.exists():
            check_otp.delete()
        OTPVerification.objects.create(user=obj, email_otp=make_password(otp))

        return Response(
            {
                "status": "success",
                "response": f"An OTP has been sent to {email.lower()}. Code will expire in 24 hours.",
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyOTP(APIView):
	permission_classes = [AllowAny]

	def post(self, request):
		# try:
		code = request.data.get("otp", None)
		email = request.data.get("email", None)
		currency = request.data.get("currency", None)
		country = request.data.get("country", None)
		print("code: ", code, "email: ", email, "currency: ", currency, "country: ", country)
		check_email = Users.objects.filter(email=email.lower()).exists()
		if check_email == False:
			return Response(
				{"status": "error", "response": "Invalid code/code has expired."},
				status=status.HTTP_400_BAD_REQUEST,
			)

		user = Users.objects.get(email=email.lower())
		check_otp = OTPVerification.objects.filter(user=user).exists()
		if check_otp == False:
			return Response(
				{"status": "error", "response": "Invalid code"},
				status=status.HTTP_400_BAD_REQUEST,
			)
		otp = OTPVerification.objects.get(user=user)
		if check_password(code, otp.email_otp) == False:
			return Response(
				{"status": "error", "response": "Invalid code or code has expired."},
				status=status.HTTP_400_BAD_REQUEST,
			)
		otp.delete()
		# Check if the user's currency exist in Currency model
		Wallet.objects.create(user=user, currency=currency, name=country)
		user.is_activated = True
		user.save()
		return Response(
			{"status": "success", "response": "Validated Successfully."},
			status=status.HTTP_200_OK,
		)


class Login(APIView):
	permission_classes = [AllowAny]
	serializer_class = RetrieveUserSerializer
	max_login_attempts = constants.MAX_LOGIN_ATTEMPTS
	lockout_duration = 900  # 15 minutes in seconds

	def post(self, request):
		email = request.data.get("email")
		password = request.data.get("password")

		if not password or not email:
			return Response(
				{"status": "error", "message": "All fields are required."},
				status=status.HTTP_400_BAD_REQUEST,
			)
		user = authenticate(username=email, password=password)
		remote_address = request.META.get("HTTP_X_FORWARDED_FOR")
		if remote_address:
			ip_address = remote_address.split(",")[-1].strip()
		else:
			ip_address = request.META.get("REMOTE_ADDR")
		geopath = os.path.join(settings.BASE_DIR, "staticfiles/geoip/GeoLite2-Country.mmdb")
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
				serializer = self.serializer_class(user, data=request.data)
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
				wallets = Wallet.objects.filter(user=user)
				if not wallets.exists():
					# Return a default wallet structure if no records are found
					default_wallet = {
						"id": user.id,
						"currency": "NGN",
						"balance": 0.0
        		}
					user_wallet = [default_wallet]
				else:
					wallet_serializer = WalletSerializer(wallets, many=True)
					user_wallet = wallet_serializer.data  
				
				print("USER WALLET: ", user_wallet)
				# Return response to client
				current_user = serializer.data
				return Response(
					{
						"status": "success",
						"response": "Login successful",
						"data": {
							"user": current_user,
							"wallet": user_wallet,
							"access_token": access_token,
							"refresh_token": str(refresh),
						},
					},
					status=status.HTTP_200_OK,
				)

		else:
			# Login failed, increase login attempts
			LoginAttempt.add_attempt(ip_address)
			remaining_attempts = self.max_login_attempts - LoginAttempt.get_attempts(ip_address)

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


class UpdatePassword(APIView):
	permission_classes = [JWTAuthentication]
	def post(self, request):
		try:
			user = request.user
			current_password = request.data.get("current_password", None)
			new_password = request.data.get("new_password", None)

			if check_password(current_password, user.password) == False:
				return Response({"status": False, "message": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
			check_user_pass = PreviousPassword.objects.filter(user=user).exists()
			if check_user_pass:
				user_pass = PreviousPassword.objects.filter(user=user)
				for i in user_pass:
					if check_password(new_password, i.password) == True:
						return Response({"status": False, "message": "You cannot use previous password. Use another password"}, status=status.HTTP_400_BAD_REQUEST)
			if check_password(new_password, current_password) == True:
				return Response({"status": False, "message": "You cannot use current password as new one. Use another password"}, status=status.HTTP_400_BAD_REQUEST)
			
			user.password = make_password(new_password)
			user.save()
			update_session_auth_hash(request, user)
			PreviousPassword.objects.create(user=user, password=make_password(new_password))
			title2 = f"Password Changed"
			note2 = f"Password changed occurred from your account recently."
			# CreateActivityNotification(user, "Notice", title2, note2)
			now = datetime.now()
			today = date.today()
			time = now.strftime("%H:%M:%S")
			title = f"Password Changed"
			note = f"Login Password has been changed successfully"
			# send_push = OneSignal.send_push(note2, request.user.device_token)
			# try:
			# 	UpdateEmail(request.user.email,request.user.first_name,title,note)
			# except:
			# 	print()
			return Response({"status": True, "message": "Password changed successfully."}, status=status.HTTP_200_OK)
		except:
			return Response({"status": False, "message": "An error occurred and we could not process your request."}, status=status.HTTP_400_BAD_REQUEST)

class WalletPin(APIView):
	# permission_classes = [JWTAuthentication]
	def post(self, request):
		try:
			print("request user: ", request.user)
			user = request.user
			wallet_pin = request.data.get("wallet_pin", None)
			if user.wallet_pin:
				return Response({"status": "error", "response": "Pin was set before. Kindly use the update pin button."}, status=status.HTTP_400_BAD_REQUEST)

			if len(wallet_pin) > 4 or len(wallet_pin) < 4:
				return Response({"status": "error", "response": "Wallet pin must not be more or less than 4 digits"}, status=status.HTTP_400_BAD_REQUEST)
			user.wallet_pin = make_password(wallet_pin)
			user.have_pin = True
			user.save()
			return Response({"status": "success", "response": "Wallet Pin has been set successfully."}, status=status.HTTP_200_OK)
		except:
			return Response({"status": "error", "response": "An error occurred and we could not process your request."}, status=status.HTTP_400_BAD_REQUEST)

class UpdateWalletPin(APIView):
	authentication_classes = [JWTAuthentication]

	def post(self, request):
		try:
			user = request.user
			wallet_pin = request.data.get("wallet_pin", None)
			code = request.data.get("otp", None)
			check_otp = OTPVerification.objects.filter(user=user).exists()
			if check_otp == False:
				return Response({"status": "error", "response": "Invalid code or code has expired."}, status=status.HTTP_400_BAD_REQUEST)
			otp = OTPVerification.objects.get(user=user)
			if check_password(code, otp.email_otp) == False:
				return Response({"status": "error", "response": "Invalid code or code has expired."}, status=status.HTTP_400_BAD_REQUEST)
			# if otp.expiry.replace(tzinfo=pytz.UTC) < datetime.now().replace(tzinfo=pytz.UTC):
			# 	return Response({"status": False, "message": "code has expired. Kindly request another."}, status=status.HTTP_400_BAD_REQUEST)

			if len(wallet_pin) > 4 or len(wallet_pin) < 4:
				return Response({"status": "error", "response": "Wallet pin must not be more or less than 4 digits"}, status=status.HTTP_400_BAD_REQUEST)
			user.wallet_pin = make_password(wallet_pin)
			user.save()
			otp.delete()
			title2 = f"Transaction Pin Changed"
			note2 = f"Transaction Pin changed occurred from your account recently."
			# CreateActivityNotification(user, "Notice", title2, note2)
			# send_push = OneSignal.send_push(note2, request.user.device_token)
			now = datetime.now()
			today = date.today()
			time = now.strftime("%H:%M:%S")
			title = f"Transaction Pin Changed"
			note = f"Wallet Transaction PIN Reset has been changed successfully"
			# try:
			# 	UpdateEmail(request.user.email,request.user.first_name,title,note)
			# except:
			# 	print()
			return Response({"status": "success", "response": "Wallet Pin has been updated successfully."}, status=status.HTTP_200_OK)
		except:
			return Response({"status": "error", "response": "An error occurred and we could not process your request."}, status=status.HTTP_400_BAD_REQUEST)
	
	# permission_classes = [IsUserActive]
	def get(self, request):
		user = request.user
		otp = GenerateOTP(4)
		check_otp = OTPVerification.objects.filter(user=user).last()
		check_otp.delete() if check_otp != None else ''
		save_otp = OTPVerification.objects.create(user=user,email_otp=make_password(otp))
		# Send OTP
		msg = f"Hi {user.last_name}, your OTP code for updating your wallet pin is {otp} and is only valid till the next 5 minutes."
		# try:
		# 	send_otp = Dojah.send_message(user.mobile,msg)
		# except:
		# 	print()
		# send_otp1 = Dojah.send_message(user.mobile,msg)
		PlainEmail(msg, user.email, "OjaPay: Your OTP has arrived.")
		return Response({"status": "success", "response": f"OTP has been sent to {user.email}"}, status=status.HTTP_200_OK)


class UserProfile(APIView):
	def get(self, request):
		serializer_class = UsersSerializer
		user = request.user
		serializer = serializer_class(user)
		wallet = Wallet.objects.get(user=user, currency="NGN")
		accounts = VirtualAccount.objects.filter(user=user)
		if wallet.customer_code == "" or wallet.customer_code == None:
			fetch_ps_customer = Paystack.fetch_customer(request.user.email)
			if fetch_ps_customer['status'] == False:
				customer = Paystack.create_customer(request.user.email,user.first_name,user.last_name,user.phone_number)
				wallet.customer_code = customer['data']['customer_code']
				wallet.save()
				# instance = Wallet.objects.filter(email=request.user.email).update(
				# 	customer_id=customer['data']['customer_code'],
				# )
			else:
				wallet.customer_code = fetch_ps_customer['data']['customer_code']
				wallet.save()
		if not len(accounts) > 0 and len(accounts) < 1:
			new_account = Paystack.virtual_account(wallet.customer_code, user.first_name, user.last_name, "test-bank")
			print(new_account)
			obj = VirtualAccount(
				user = user,
				bank_name = new_account['data']['bank']['name'],
				bank_slug = new_account['data']['bank']['slug'],
				wallet_code = new_account['data']['id'],
				account_name = new_account['data']['account_name'],
				account_number = new_account['data']['account_number'],
			)
			obj.save()
		account = VirtualAccount.objects.filter(user=user).last()
		virtual_account = {
			"account_name": account.account_name,
			"account_number": account.account_number,
			"bank_name": account.bank_name,
			"bank_slug": account.bank_slug,
		}
		data = {
			"profile": serializer.data,
			"virtual_nuban": virtual_account
		}
		return Response({"status": "success", "response": "Response from profile view", "data": data}, status=status.HTTP_200_OK)

class GetCurrentUser(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RetrieveUserSerializer
    def get(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(user)
        return Response({"status": "success", "response": "User successfully retrieved.", "data": serializer.data})
    
class RecipientViewSet(viewsets.ModelViewSet):
    queryset = Recipient.objects.filter(is_verified=True).select_related('owner')
    serializer_class = RecipientSerializer


class DonationViewSet(viewsets.ModelViewSet):
    queryset = Donation.objects.all()
    serializer_class = DonationSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print(serializer.errors)  
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)