from decimal import Decimal
from django.utils import timezone
import uuid
from django.conf import settings
import pyotp
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication  # type: ignore
from django.db import transaction
from rest_framework import permissions
from amaps.sendmail import PlainEmail, SendMail
from transactions.models import Deposit, Transaction, WalletTransaction
from userservice.models import Users
from django.contrib.auth.hashers import check_password
from utils.api import CoralPay, Paystack
from django.template.loader import render_to_string
from utils.helpers import get_random_string
from walletservice.models import Wallet
from walletservice.serializers import WalletSerializer


class UserWallet(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        user = request.user
        wallets = Wallet.objects.filter(user=user)
        serializer = WalletSerializer(wallets, many=True)
        return Response(
            {
                "status": "success",
                "response": "Wallet fetched",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        user = request.user
        name = request.data.get("name")
        currency = request.data.get("currency")
        check_wallet = Wallet.objects.filter(
            user=user, currency=currency.upper()
        ).exists()
        if check_wallet:
            return Response(
                {
                    "status": "error",
                    "response": f"{currency.upper()} Wallet already exists",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        obj = Wallet(user=user, name=name, currency=currency.upper())
        obj.save()
        return Response(
            {
                "status": "success",
                "response": f"{currency.upper()} Wallet created successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class FundWalletValidation(APIView):
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        user = request.user
        print(
            "EMAIL: ",
            user.email,
            "FIRSTNAME: ",
            user.first_name,
            "LASTNAME: ",
            user.last_name,
        )
        amount = request.data.get("amount")
        currency = request.data.get("currency")
        print("AMOUNT: ", amount, "CURRENCY: ", currency)
        return_url = request.data.get("return_url")
        print("Return URL: ", return_url)

        try:
            wallet = Wallet.objects.filter(
                user=request.user, currency=currency.upper()
            ).first()

        except Wallet.DoesNotExist:
            return Response(
                {"status": "error", "response": "Wallet does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        amount = Decimal(amount)
        coralpay = CoralPay()
        customer_name = f"{user.first_name} {user.last_name}"
        title = f"NGN Wallet funding"
        description = f"Funding {customer_name}'s NGN Wallet"
        trace_id = get_random_string(10)
        product_id = get_random_string(8)
        init_payment = coralpay.invoke_payment(
            user.email,
            customer_name,
            user.phone_number,
            user.unique_uid,
            title,
            description,
            trace_id,
            product_id,
            amount,
            currency,
            return_url,
        )
        print("INIT PAYMENT: ", init_payment)
        obj = Deposit(
            order=product_id,
            status="pending",
            reference=trace_id,
            amount=Decimal(amount),
            user=user,
            balance_before=wallet.balance,
            balance_after=wallet.balance,
            gateway="CoralPay",
            note=f"Wallet Funding using Card Payment",
            transaction_type="Deposit",
            payment_type="Wallet Funding",
        )
        obj.save()
        data = {
            "link": init_payment["payPageLink"],
            "reference": init_payment["traceId"],
            "transaction_id": init_payment["transactionId"],
        }

        otp = pyotp.TOTP(pyotp.random_base32()).now()
        wallet.otp_code = otp
        wallet.otp_expiry = timezone.now() + timezone.timedelta(minutes=5)
        wallet.save()

        # Send OTP email
        msg = f"Hi {user.first_name}, your OTP code is {otp} and is only valid till the next 5 minutes."
        PlainEmail(msg, user.email.lower(), "OjaPay: Your OTP has arrived.")

        return Response(
            {
                "status": "success",
                "response": init_payment["responseHeader"]["responseMessage"],
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


class FundWallet(APIView):
    authentication_classes = [JWTAuthentication]

    def post(self, request):
        user = request.user
        print(
            "EMAIL: ",
            user.email,
            "FIRSTNAME: ",
            user.first_name,
            "LASTNAME: ",
            user.last_name,
        )
        amount = request.data.get("amount")
        currency = request.data.get("currency")
        print("AMOUNT: ", amount, "CURRENCY: ", currency)
        return_url = request.data.get("return_url")
        print("Return URL: ", return_url)
        otp = request.data.get("otp")
        print("OTP: ", otp)

        wallet = Wallet.objects.filter(
            user=request.user, currency=currency.upper()
        ).first()

        if not wallet:
            return Response(
                {"status": "error", "response": "Wallet does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if timezone.now() > wallet.otp_expiry:
            return Response(
                {"status": "error", "response": "OTP expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp != str(wallet.otp_code):
            return Response(
                {"status": "error", "response": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        obj = Deposit(status="success")
        obj.save()
        return Response(
            {
                "status": "success",
                "response": "OTP sent. Please verify.",
                "data": {"amount": f"{currency.upper()} {float(amount):,.2f}"},
            }
        )

    def get(self, request, reference=None, currency=None):
        if not reference:
            return Response(
                {
                    "status": "error",
                    "response": "Invalid or no reference code provided.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        coralpay = CoralPay()
        verify = coralpay.verify_payment(reference)
        print("PAYMENT VERIFICATION: ", verify)
        obj = Deposit.objects.filter(reference=reference).last()
        if not obj:
            return Response(
                {"status": "error", "response": "Error in transaction."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if obj.status == "success":
            return Response(
                {"status": "error", "response": "Payment already checked."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = Users.objects.get(email=obj.user.email)
        wallet = Wallet.objects.get(currency=currency, user=user)
        if verify["responseMessage"] == "Successful":
            obj.balance_after = Decimal(verify["amount"]) + wallet.balance
            obj.payment_type = verify["channel"]
            obj.status = "success"
            obj.save()
            wallet.balance += obj.amount
            wallet.save()
            message = render_to_string(
                "userservice/wallet_topup_notification.html",
                {
                    "user": user.first_name,
                    "amount": f"{currency.upper()} {verify["amount"]:,.2f}",
                    "transaction_id": verify["transactionId"],
                    "payment_method": verify["channel"] + " payment method",
                    "datetime": timezone.now(),
                    "site_name": settings.CURRENT_SITE,
                },
            )
            mail_subject = "Wallet Funding Notification"
            SendMail(mail_subject, message, user.email)
            return Response(
                {
                    "status": "success",
                    "response": "Fund deposited successfully",
                    "data": verify,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "status": "error",
                    "response": "Error depositing fund!",
                    "data": verify,
                },
                status=status.HTTP_200_OK,
            )


class WalletTransfer(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        print("REQUEST DATA: ", request.data)
        recipient_username = request.data.get("ojapay_tag", "")
        print("RECIPIENT USERNAME: ", recipient_username)
        amount = request.data.get("amount", "")
        print("AMOUNT: ", amount)
        note = request.data.get("note", "")
        print("DESCRIPTION: ", note)
        wallet_pin = request.data.get("wallet_pin", "")
        print("WALLET PIN: ", wallet_pin)
        donor_currency = request.data.get("donor_currency", "")
        print("DONOR CURRENCY: ", donor_currency)
        recipient_currency = request.data.get("recipient_currency", "")
        print("RECIPIENT CURRENCY: ", recipient_currency)
        donor_wallet = Wallet.objects.get(user=user, currency=donor_currency)
        recipient = Users.objects.get(username=recipient_username)

        try:
            if recipient_currency:
                recipient_wallet = Wallet.objects.get(
                    user=recipient, currency=recipient_currency
                )
            else:
                recipient_wallet = Wallet.objects.get(
                    user=recipient, currency=donor_currency
                )
        except Wallet.DoesNotExist:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={
                    "status": "error",
                    "response": f"Recipient does not have a {donor_currency} wallet.",
                },
            )

        amount = Decimal(amount)
        recipient_amount = Decimal(recipient_wallet.balance)

        if not check_password(wallet_pin, user.wallet_pin):
            return Response(
                {"status": "error", "response": "Incorrect pin entered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if donor_wallet.balance - amount < 0:
            return Response(
                {"status": "error", "response": "Insufficient funds"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if recipient.username == user.username:
            return Response(
                {"status": "error", "response": "You cannot do that."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp = pyotp.TOTP(pyotp.random_base32()).now()
        donor_wallet.otp_code = otp
        donor_wallet.otp_expiry = timezone.now() + timezone.timedelta(minutes=5)
        donor_wallet.save()

        # Send OTP email
        msg = f"Hi {user.first_name}, your OTP code is {otp} and is only valid till the next 5 minutes."
        PlainEmail(msg, user.email.lower(), "OjaPay: Your OTP has arrived.")

        return Response(
            {
                "status": "success",
                "response": "OTP sent. Please verify.",
                "data": {
                    "donor": f"{user.first_name} {user.last_name}",
                    "recipient": f"{recipient.first_name} {recipient.last_name}",
                    "amount": f"{donor_currency.upper()} {recipient_amount:,.2f}",
                    "description": note,
                },
            }
        )


class WalletTransferValidation(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        print("REQUEST DATA: ", request.data)
        recipient_username = request.data.get("ojapay_tag")
        amount = request.data.get("amount")
        otp = request.data.get("otp")
        note = request.data.get("note", "")
        wallet_pin = request.data.get("wallet_pin", "")
        donor_currency = request.data.get("donor_currency", "")
        recipient_currency = request.data.get("recipient_currency", "")
        donor_wallet = Wallet.objects.get(user=user, currency=donor_currency)
        recipient = Users.objects.get(username=recipient_username)

        try:
            if recipient_currency:
                recipient_wallet = Wallet.objects.get(
                    user=recipient, currency=recipient_currency
                )
            else:
                recipient_wallet = Wallet.objects.get(
                    user=recipient, currency=donor_currency
                )
        except Wallet.DoesNotExist:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={
                    "status": "error",
                    "response": f"Recipient does not have a {donor_currency} wallet.",
                },
            )

        if timezone.now() > donor_wallet.otp_expiry:
            return Response(
                {"status": "error", "response": "OTP expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp != str(donor_wallet.otp_code):
            return Response(
                {"status": "error", "response": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        amount = Decimal(amount)

        if check_password(wallet_pin, user.wallet_pin) == False:
            return Response(
                {"status": "error", "response": "Incorrect pin entered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if recipient.username == donor_wallet.user.username:
                return Response(
                    {"status": "error", "response": "You cannot do that."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if donor_wallet.balance >= amount:
                # Generate order and reference
                order = str(uuid.uuid4())
                reference = str(uuid.uuid4())

                with transaction.atomic():
                    # Create transaction for sender
                    WalletTransaction.objects.create(
                        sender_wallet=donor_wallet,
                        recipient_wallet=recipient_wallet,
                        amount=amount,
                        fee=Decimal("0.00"),  # Assuming no fee for this example
                        balance_before=donor_wallet.balance,
                        balance_after=donor_wallet.balance - amount,
                        order=order,
                        reference=reference,
                        note=note,
                        gateway="internal",
                        transaction_type="Wallet Transfer",
                        payment_type="wallet",
                        status="success",
                    )

                    # Create transaction for recipient
                    WalletTransaction.objects.create(
                        sender_wallet=donor_wallet,
                        recipient_wallet=recipient_wallet,
                        amount=amount,
                        fee=Decimal("0.00"),
                        balance_before=recipient_wallet.balance,
                        balance_after=recipient_wallet.balance + amount,
                        order=order,
                        reference=reference,
                        note=note,
                        gateway="internal",
                        transaction_type="Wallet Transfer",
                        payment_type="wallet",
                        status="success",
                    )

                    # Update wallet balances
                    donor_wallet.balance -= amount
                    recipient_wallet.balance += amount
                    donor_wallet.save()
                    recipient_wallet.save()
                if recipient.user_type == "Merchant":
                    tag = recipient.business_name
                else:
                    tag = recipient.username
                message = render_to_string(
                    "userservice/wallet_withdrawal_notification.html",
                    {
                        "user": user.first_name,
                        "transaction_type": "Wallet payment to " + tag,
                        "amount": f"{donor_currency} {amount:,.2f}",
                        "withdrawal_method ": "Wallet",
                        "transfer_to  ": tag,
                        "datetime": timezone.now(),
                        "site_name": settings.CURRENT_SITE,
                    },
                )
                mail_subject = "Payment Notification"
                SendMail(mail_subject, message, user.email)

                message = render_to_string(
                    "userservice/wallet_topup_notification.html",
                    {
                        "user": recipient.first_name,
                        "amount": f"{donor_currency} {amount:,.2f}",
                        "transaction_id": reference,
                        "payment_method": "Internal",
                        "datetime": timezone.now(),
                        "site_name": settings.CURRENT_SITE,
                    },
                )
                mail_subject = "Payment Received Notification"
                SendMail(mail_subject, message, recipient.email)

                return Response(
                    {"status": "success", "response": "Transfer successful!"},
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"status": "error", "response": "Insufficient balance"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Users.DoesNotExist:
            return Response(
                {"status": "error", "response": "Recipient not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Wallet.DoesNotExist:
            return Response(
                {"status": "error", "response": "Wallet not found"},
                status=status.HTTP_404_NOT_FOUND,
            )


class WalletToBankTransfer(APIView):
    def post(self, request):
        user = request.user
        wallet_pin = request.data.get("wallet_pin")
        amount = request.data.get("amount")
        bank_code = request.data.get("bank_code")
        account_number = request.data.get("account_number")
        currency = request.data.get("currency")
        wallet = Wallet.objects.get(user=user, currency=currency)
        bank_name = request.data.get("bank_name")

        if not check_password(wallet_pin, user.wallet_pin):
            return Response(
                {"status": "error", "response": "Incorrect pin entered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if wallet.balance - Decimal(amount) < 0:
            return Response(
                {"status": "error", "response": "Insufficient funds"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp = pyotp.TOTP(pyotp.random_base32()).now()
        wallet.otp_code = otp
        wallet.otp_expiry = timezone.now() + timezone.timedelta(minutes=5)
        wallet.save()

        # Send OTP email
        msg = f"Hi {user.first_name}, your OTP code is {otp} and is only valid till the next 5 minutes."
        PlainEmail(msg, user.email.lower(), "OjaPay: Your OTP has arrived.")

        return Response(
            {
                "status": "success",
                "response": "OTP sent. Please verify.",
                "data": {
                    "bank_code": bank_code,
                    "bank_name": bank_name,
                    "account_number": account_number,
                    "amount": f"{currency.upper()} {float(amount):,.2f}",
                },
            }
        )

    def get(self, request):
        user = request.user
        coral_pay = Paystack()
        banks = coral_pay.fetchBanks()
        return Response(
            {"status": "success", "response": "Banks returned", "data": banks["data"]},
            status=status.HTTP_200_OK,
        )


class WalletToBankOTPValidation(APIView):
    def post(self, request):
        print("REQUEST DATA: ", request.data)
        user = request.user
        bank_code = request.data.get("bank_code")
        bank_name = request.data.get("bank_name")
        account_number = request.data.get("account_number")
        amount = request.data.get("amount")
        wallet_pin = request.data.get("wallet_pin")
        currency = request.data.get("currency")
        wallet = Wallet.objects.get(user=user, currency=currency)
        print("WALLET OBJECT: ", wallet)
        otp = request.data.get("otp")

        if timezone.now() > wallet.otp_expiry:
            return Response(
                {"status": "error", "response": "OTP expired"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp != str(wallet.otp_code):
            return Response(
                {"status": "error", "response": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if check_password(wallet_pin, user.wallet_pin) == False:
            return Response(
                {"status": "error", "response": "Incorrect pin entered."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        validate = Paystack.resolveAccount(bank_code, account_number)
        print("VALIDATE PAYMENT: ", validate)
        account_name = validate["data"]["account_name"]
        print("ACCOUNT NAME: ", account_name)

        ref = get_random_string(8)
        if wallet.balance - Decimal(amount) < 0:
            return Response(
                {
                    "status": "error",
                    "response": "Insufficient fund. Please recharge and try again",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        amt = Decimal(amount) * 100
        full_name = f"{user.first_name} {user.last_name}"
        narration = f"{ref}/Bank Transfer by {full_name} from OjaPay."
        ps_transfer_id = Paystack.init_transfer_rec(
            account_name, account_number, bank_code
        )
        transfer_code = ps_transfer_id["data"]["recipient_code"]
        transfer = Paystack.init_transfer(transfer_code, str(amt), ref, narration)
        if transfer["status"] == False:
            return Response(
                {"status": "error", "response": transfer["message"]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        fee = 0
        ins = Transaction.objects.create(
            order=transfer["data"]["transfer_code"],
            status=transfer["data"]["status"],
            reference=ref,
            fee=fee,
            amount=Decimal(amount),
            user=user,
            balance_before=wallet.balance,
            balance_after=wallet.balance - Decimal(amount),
            gateway="OjaPay",
            note=f"Transfer to {account_number} {user.first_name} {user.last_name} - {bank_name}",
            transaction_type="Bank Transfer",
        )
        pay = Paystack.finalize_transfer(ins.order)

        amt = ins.amount
        wallet.balance -= Decimal(amount) + fee
        wallet.save()
        data = {
            "reference": ins.reference,
            "amount": f"{ins.amount:,.2f}",
            "reason": transfer["data"]["reason"],
            "status": transfer["data"]["status"],
            "recipient": {
                "account_name": account_name,
                "account_number": account_number,
                "bank_name": bank_name,
            },
            "createdAt": ins.date,
        }
        message = render_to_string(
            "userservice/wallet_withdrawal_notification.html",
            {
                "user": user.first_name,
                "service_name": "Wallet withdrawal",
                "amount": f"{ins.amount:,.2f}",
                "reference_number": ins.reference,
                "datetime": timezone.now(),
                "site_name": settings.CURRENT_SITE,
            },
        )
        mail_subject = "Fund Withdrawal Notification"
        SendMail(mail_subject, message, user.email)
        return Response(
            {"status": "success", "response": "Transfer in process", "data": data},
            status=status.HTTP_200_OK,
        )
