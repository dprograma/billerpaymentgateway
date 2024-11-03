from rest_framework import serializers

from walletservice.models import Wallet

from .models import (
    OTPVerification,
    Users,
    Recipient, 
    Donation
)  


# User Serializer
class UsersSerializer(serializers.ModelSerializer):
    address = serializers.CharField(required=False)

    class Meta:
        model = Users
        exclude = ["id", "password", "groups", "user_permissions"]
        # fields = "__all__"


# Retrieve user Serializer
class RetrieveUserSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(required=False)
    email = serializers.CharField(required=False)

    class Meta:
        model = Users
        exclude = ("password",)


# OTPVerification Serializer
class OTPVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTPVerification
        fields = "__all__"


class RecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipient
        fields = ['id', 'name', 'recipient_type']


class RecipientSerializer(serializers.ModelSerializer):
    recipient_type = serializers.CharField(source='get_recipient_type_display')  
    business_name = serializers.CharField(source='owner.business_name')  
    country = serializers.CharField(source='owner.country')  
    currency = serializers.SerializerMethodField() 
    wallet_tag = serializers.SerializerMethodField() 

    class Meta:
        model = Recipient
        fields = ['id', 'name', 'recipient_type', 'business_name', 'country', 'currency', 'wallet_tag']  

    def get_currency(self, obj):
        wallet = Wallet.objects.filter(user=obj.owner).first()
        return wallet.currency if wallet else None
    
    def get_wallet_tag(self, obj):
        user = Users.objects.filter(id=obj.owner.id).first()
        return user.username if user else None


# class DonationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Donation
#         fields = ['id', 'donor', 'recipient', 'amount', 'currency', 'description', 'reference']

class DonationSerializer(serializers.ModelSerializer):
    donor_id = serializers.PrimaryKeyRelatedField(queryset=Users.objects.all(), source='donor')
    recipient_id = serializers.PrimaryKeyRelatedField(queryset=Recipient.objects.all(), source='recipient')

    class Meta:
        model = Donation
        fields = ['donor_id', 'recipient_id', 'amount', 'currency', 'description']


