from rest_framework import serializers

from transactions.models import Transaction
from userservice.serializers import UsersSerializer
from walletservice.models import Wallet


# Wallet Serializer
class WalletSerializer(serializers.ModelSerializer):
    user = UsersSerializer(read_only=True)

    class Meta:
        model = Wallet
        fields = "__all__"


# Transactions Serializer
class TransactionsSerializer(serializers.ModelSerializer):
    user = UsersSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = "__all__"
