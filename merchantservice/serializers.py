from rest_framework import serializers

from userservice.models import OTPVerification, Product, Users, Category, MerchantCountries


class CreateMerchantSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False)
    country = serializers.CharField(required=False)

    class Meta:
        model = Users
        fields = "__all__"


class LoginViewSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=False)
    username = serializers.CharField(required=False)
    country = serializers.CharField(required=False)

    class Meta:
        model = Users
        fields = "__all__"


class RetrieveMerchantSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(required=False)
    username = serializers.CharField(required=False)
    country = serializers.CharField(required=False)

    class Meta:
        model = Users
        exclude = ("password",)


# OTPVerification Serializer
class OTPVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTPVerification
        fields = "__all__"


class BusinessVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = "__all__"


# specify the fields i want to submit


class PasswordResetSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Users
        fields = ["password"]


class LogoutSerializer(serializers.Serializer):
    token = serializers.CharField(required=False)


class ForgetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class UpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Users
        fields = ["first_name", "last_name", "email", "password"]
        extra_kwargs = {"password": {"write_only": True}}


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']

class ProductSerializer(serializers.ModelSerializer):
    user = RetrieveMerchantSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), 
        source='category', 
        write_only=True
    )

    class Meta:
        model = Product
        fields = ['id', 'user', 'name', 'description', 'price', 'category', 'category_id', 'created_at', 'updated_at']
        read_only_fields = ['user']


class MerchantCountriesSerializer(serializers.ModelSerializer):
    africa = serializers.SerializerMethodField()
    world = serializers.SerializerMethodField()

    class Meta:
        model = MerchantCountries
        fields = ['africa', 'world']

    def get_africa(self, obj):
        africa_countries = [name for code, name in MerchantCountries.AFRICA_CHOICES]
        return africa_countries

    def get_world(self, obj):
        world_countries = [name for code, name in MerchantCountries.WORLD_CHOICES]
        return world_countries
