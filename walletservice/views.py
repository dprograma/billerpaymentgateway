from django.db import transaction as transaction_decorators
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
import requests
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView
from amaps.permissions import IsOwner
from paymentgatewayservice.views import PayWithStaticBankAccount
from userservice.models import Users
from utils.helpers import *
from django.conf import settings
from django.utils import timezone

from .models import CustomerBankAccount, Wallet
from .serializers import *
from .serializers import FundWalletSerializer, WalletSerializer


class FundWalletView(generics.UpdateAPIView):
    """
    Fund an existing Wallet.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    serializer_class = FundWalletSerializer
    queryset = Wallet.objects.all()

    def get_object(self):
        """
        Retrieve and return the wallet instance that needs to be funded.
        """
        wallet_id = self.kwargs["pk"]
        wallet = get_object_or_404(Wallet, id=wallet_id)
        self.check_object_permissions(self.request, wallet)
        return wallet

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        amount = serializer.validated_data["amount"]
        firstname = request.user.first_name
        lastname = request.user.last_name

        # Check if the customer already has a bank account
        try:
            customer_account = CustomerBankAccount.objects.get(user=user)
            bank_account_number = customer_account.bank_account_number
            reference_no = customer_account.reference_no
        except CustomerBankAccount.DoesNotExist:
            # Create a static bank account for the customer
            response = PayWithStaticBankAccount.create_static_bank_account(
                firstname, lastname
            )
            if response.status_code == 200:
                response_data = response.json()
                bank_account_number = response_data["accountNumber"]
                reference_no = response_data["responseDetails"]["referenceNumber"]

                # Save the bank account details in the database
                CustomerBankAccount.objects.create(
                    user=user,
                    bank_account_number=bank_account_number,
                    reference_no=reference_no,
                )
            else:
                return Response(
                    {
                        "status": "error",
                        "response": "An error occurred while creating static bank account.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Process the payment to the bank account
        response = PayWithStaticBankAccount.process_payment_direct(
            firstname, lastname, amount, reference_no
        )

        if response.status_code == 200:
            # Update the wallet balance upon successful payment
            instance.balance += amount
            instance.save()

            return Response(
                {"status": "success", "response": response.json()},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "error", "response": response.text},
                status=status.HTTP_400_BAD_REQUEST,
            )


class WalletList(generics.ListCreateAPIView):
    """
    List Existing Wallets or add new
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    serializer_class = WalletSerializer

    def get_queryset(self) -> QuerySet[Wallet]:
        """
        Only return those wallets, which belong to current user.
        """
        user = self.request.user
        return Wallet.objects.all().filter(user=user.id)

    def perform_create(self, serializer: WalletSerializer) -> None:
        """
        When creating a new wallet, set user field as current user.
        """
        serializer.save(user=self.request.user)
        return Response(
            {
                "status": "success",
                "response": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class WalletDetail(generics.RetrieveDestroyAPIView):
    """
    Detail of an individual Wallet.

    See info about wallet, update it or destroy the wallet.
    """

    authentication_classes = [JWTAuthentication]
    permission_classes = [
        permissions.IsAuthenticated,
        IsOwner,
    ]
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer

    def get_object(self) -> Wallet:
        """
        GET Wallet or 404 if it doesn't exist
        """
        name = self.kwargs["name"]
        try:
            wallet = generics.get_object_or_404(Wallet, name=name)
            self.check_object_permissions(self.request, wallet)
            return wallet
        except Wallet.DoesNotExist:
            raise ValidationError("Wallet does not exist.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance:
            self.perform_destroy(instance)
            return Response(
                {"detail": "Wallet is deleted."}, status=status.HTTP_204_NO_CONTENT
            )
        else:
            return Response(
                {"detail": "Wallet does not exist."}, status=status.HTTP_404_NOT_FOUND
            )


class CurrencyListView(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer


class ExchangeRateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from_currency_code = request.query_params.get("from")
        to_currency_code = request.query_params.get("to")

        if not from_currency_code or not to_currency_code:
            return Response(
                {
                    "status": "error",
                    "response": "Both 'from' and 'to' currency codes are required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from_currency = Currency.objects.get(code=from_currency_code)
            to_currency = Currency.objects.get(code=to_currency_code)
            exchange_rate = ExchangeRate.objects.get(
                from_currency=from_currency, to_currency=to_currency
            )
        except Currency.DoesNotExist:
            return Response(
                {"status": "error", "response": "Invalid currency code"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ExchangeRate.DoesNotExist:
            exchange_rate = ExchangeRate(
                from_currency=from_currency, to_currency=to_currency
            )

        serializer = ExchangeRateSerializer(exchange_rate)
        return Response(
            {
                "status": "success",
                "response": "Exchange rate retrieved successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class WalletUpdateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id, *args, **kwargs):
        user = Users.objects.get(id=user_id)
        wallet = Wallet.objects.get(user=user)

        new_currency_code = request.data.get("currency")
        new_balance = request.data.get("balance")

        if not new_currency_code or not new_balance:
            return Response(
                {
                    "status": "error",
                    "response": "Both 'currency' and 'balance' are required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the Currency instance by code
        new_currency = Currency.objects.get(code=new_currency_code)

        # Assign the currency code to the wallet's currency field
        wallet.currency = new_currency.code
        wallet.balance = new_balance
        wallet.save()

        serializer = WalletSerializer(wallet)
        return Response(serializer.data)
