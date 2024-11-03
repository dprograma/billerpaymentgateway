"""
Serializers of the Wallets app
"""

from decimal import Decimal
from typing import Any, Dict

from rest_framework import serializers

from .models import Wallet, Currency, ExchangeRate

MAX_NUMBER_OF_WALLETS = 5


class WalletSerializer(serializers.ModelSerializer):
    """
    Serializer for Wallet Model.

    Methods:
        create: Create an instance of Wallet.
        validate_max_wallets: Check that user does not have too many wallets.
    """

    user = serializers.PrimaryKeyRelatedField(read_only=True, source="user.username")
    name = serializers.CharField(required=False)

    class Meta:
        """
        Related Model and its fields
        """

        model = Wallet
        fields = [
            "id",
            "name",
            "currency",
            "balance",
            "user",
            "created_on",
            "modified_on",
        ]

        extra_kwargs = {
            "id": {"required": False},
            "currency": {"required": False, "default": "NGN"},
            "balance": {"required": False, "default": 0.00},
        }

    def create(self, validated_data: Dict[str, Any]) -> Wallet:
        """
        Validate Wallet fields before serializing.
        """
        self.validate_max_wallets(validated_data)
        # print(validated_data)
        return Wallet.objects.create(**validated_data)

    def validate_max_wallets(self, validated_data: Dict[str, Any]) -> None:
        """
        User cannot have too many wallets.
        """
        user = validated_data["user"]
        if Wallet.objects.filter(user=user).count() >= MAX_NUMBER_OF_WALLETS:
            raise serializers.ValidationError(
                f"Users can't create more than {MAX_NUMBER_OF_WALLETS} wallets."
            )


class FundWalletSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01")
    )

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "The funding amount must be greater than zero."
            )
        return value

    # def validate_bonus(self, validated_data: Dict[str, Any]) -> None:
    #     """
    #     Adding bonus based on currency.
    #     """
    #     currency = validated_data.get("currency")
    #     bonus = Wallet.BONUSES[currency]  # Sets appropriate bonus for Wallet currency
    #     validated_data["balance"] = bonus


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["code", "name"]


class ExchangeRateSerializer(serializers.ModelSerializer):
    from_currency = CurrencySerializer()
    to_currency = CurrencySerializer()

    class Meta:
        model = ExchangeRate
        fields = ["from_currency", "to_currency", "rate", "last_updated"]
