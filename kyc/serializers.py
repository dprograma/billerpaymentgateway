from rest_framework import serializers

from .models import KYC


class KYCSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYC
        fields = "__all__"
