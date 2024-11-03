# import datetime
from datetime import timedelta, datetime
from decimal import Decimal
import uuid
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
from django.db.models import F
from django.utils import timezone
from django.contrib.auth.base_user import BaseUserManager
from django.core.validators import MinValueValidator
from walletservice.models import Wallet

from .constants import MAX_LOGIN_ATTEMPTS


class UserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create and save a User with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


class Users(AbstractUser):
    BANK_CHOICES = [
        ("UBA Bank", "UBA Bank"),
        ("First Bank", "First Bank"),
        ("WEMA Bank", "WEMA Bank"),
        ("Zenith Bank", "Zenith Bank"),
    ]

    ID_CHOICES = [
        ("International Passport", "International Passport"),
        ("Voters Card", "Voters Card"),
        ("Resident Permit", "Resident Permit"),
        ("Drivers License", "Drivers License"),
        ("National Identity Card", "National Identity Card"),
    ]

    USER_TYPE = (("Admin", "Admin"), ("Customer", "Customer"), ("Merchant", "Merchant"))
    
    BUSINESS_TYPES = [
        ('NGO', 'NGO'),
        ('Company', 'Company'),
        ('Individual', 'Individual'),
    ]

    # Common fields
    phone_number = models.CharField(max_length=20, unique=True)
    user_type = models.CharField(max_length=100, default="Admin", choices=USER_TYPE)
    address = models.CharField(max_length=255, null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(unique=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_user_agent = models.TextField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    is_activated = models.BooleanField(default=False)
    avatar = models.ImageField(
        upload_to="profile/", default="profile/avatar.png", null=True, blank=True
    )

    # Merchant-specific fields
    country = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to="business/profile_pictures/",
        null=True,
        blank=True,
        verbose_name="Profile Picture",
        help_text="Upload a profile picture with a maximum size of 500x500 pixels",
    )
    business_name = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Business Name"
    )
    business_certificate = models.FileField(
        upload_to="business/certificates/",
        null=True,
        blank=True,
        verbose_name="Business Certificate",
        help_text="Upload the business name certificate",
    )
    business_type = models.CharField(
        max_length=255, null=True, blank=True, choices=BUSINESS_TYPES, verbose_name="Business Type")
    rc_number = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="RC Number"
    )
    rc_certificate = models.FileField(
        upload_to="business/rc_certificates/",
        null=True,
        blank=True,
        verbose_name="RC Certificate",
        help_text="Upload the RC number certificate",
    )
    tax_id = models.CharField(
        max_length=50, null=True, blank=True, verbose_name="Tax ID"
    )
    tax_certificate = models.FileField(
        upload_to="business/tax_certificates/",
        null=True,
        blank=True,
        verbose_name="Tax Certificate",
        help_text="Upload the Tax ID certificate",
    )
    id_type = models.CharField(
        max_length=50, null=True, blank=True, choices=ID_CHOICES, verbose_name="ID Type"
    )
    upload_id = models.FileField(
        upload_to="verification/upload_ids/",
        null=True,
        blank=True,
        verbose_name="Upload ID",
    )
    bvn = models.CharField(max_length=11, null=True, blank=True, verbose_name="BVN")
    enter_bvn_number = models.CharField(
        max_length=11, null=True, blank=True, verbose_name="Enter BVN Number"
    )
    bank_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        choices=BANK_CHOICES,
        verbose_name="Bank Name",
    )
    account_number = models.CharField(
        max_length=20, null=True, blank=True, verbose_name="Account Number"
    )
    have_pin = models.BooleanField(default=False)
    wallet_pin = models.CharField(max_length=225, default="", blank=True)
    compliant = models.BooleanField(default=False)
    unique_uid = models.CharField(max_length=225, default=uuid.uuid4, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "phone_number"]

    class Meta:
        app_label = "userservice"

    def __str__(self):
        return self.email

    def is_compliant(self):
        """Check if the user is compliant based on business verification fields"""
        if (
            self.country
            and self.business_name
            and self.business_certificate
            and self.rc_number
            and self.rc_certificate
            and self.tax_id
            and self.tax_certificate
            and self.id_type
            and self.bvn
        ):
            self.compliant = True
        else:
            self.compliant = False
        self.save()
        # If compliant, create or update the recipient
        if self.compliant:
            self.create_or_update_recipient()
        return self.compliant
    
    def create_or_update_recipient(self):
        """Create or update the recipient for a compliant user"""
        _, _ = Recipient.objects.update_or_create(
            owner=self,  
            defaults={
                'name': f"{self.first_name} {self.last_name}",
                'recipient_type': self.business_type,  
                'is_verified': True, 
            }
        )

    def save(self, *args, **kwargs):
        if not self.unique_uid:
            self.unique_uid = str(uuid.uuid4())
        super().save(*args, **kwargs)


class LoginAttempt(models.Model):
    ip_address = models.CharField(max_length=45, unique=True)
    attempts = models.PositiveIntegerField(default=0)
    last_attempt_time = models.DateTimeField(auto_now=True, null=True, blank=True)
    lockout_duration = models.DurationField(default=timedelta(seconds=900))
    max_login_attempts = models.PositiveIntegerField(default=MAX_LOGIN_ATTEMPTS)

    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE,
        related_name="login_attempts",
        null=True,
        blank=True,
    )

    class Meta:
        app_label = "userservice"

    @classmethod
    def lock_user(cls, ip_address):
        Users.objects.filter(last_login_ip=ip_address).update(is_locked=True)

    @classmethod
    def add_attempt(cls, ip_address):
        """Add a login attempt for the given IP address."""
        user = Users.objects.filter(last_login_ip=ip_address).first()

        attempt, created = cls.objects.get_or_create(
            ip_address=ip_address,
            defaults={"user": user, "attempts": 1, "last_attempt_time": timezone.now()},
        )

        if not created:
            # If a record already exists, update it
            cls.objects.filter(ip_address=ip_address).update(
                user=user, attempts=F("attempts") + 1, last_attempt_time=timezone.now()
            )
            attempt.refresh_from_db()

    @classmethod
    def get_attempts(cls, ip_address):
        """Get the number of login attempts for the given IP address."""
        try:
            login_attempts = cls.objects.get(ip_address=ip_address)
        except LoginAttempt.DoesNotExist:
            return 0
        if login_attempts.attempts:
            return login_attempts.attempts
        return 0.0

    @classmethod
    def reset_attempts(cls, ip_address=None):
        """Reset the login attempts for the given IP address."""
        cls.objects.filter(ip_address=ip_address).update(
            attempts=0, last_attempt_time=timezone.now()
        )
        Users.objects.filter(last_login_ip=ip_address).update(is_locked=False)

    @classmethod
    def is_ip_locked(cls, ip_address=None):
        """
        Check if the IP address is locked due to too many login attempts.
        """
        try:
            login_attempts = cls.objects.get(ip_address=ip_address)
        except LoginAttempt.DoesNotExist:
            # If no record exists for this IP, we can assume it's not locked
            return False

        if login_attempts and login_attempts.attempts >= MAX_LOGIN_ATTEMPTS:
            time_difference = timezone.now() - login_attempts.last_attempt_time
            # result = time_difference <= login_attempts.lockout_duration
            return time_difference <= login_attempts.lockout_duration
        else:
            return False


class OTPVerification(models.Model):
    user = models.ForeignKey(Users, related_name="otp", on_delete=models.CASCADE)
    phone_otp = models.CharField(max_length=6, null=True, blank=True)
    email_otp = models.CharField(max_length=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    phone_otp_created_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    email_otp_created_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    attempts = models.IntegerField(default=0)

    class Meta:
        app_label = "userservice"

    def is_expired(self):
        # Set OTP expiry time (e.g., 5 minutes from creation)
        expiry_duration = timedelta(minutes=5)
        return (
            timezone.now() > self.phone_otp_created_at + expiry_duration
            or timezone.now() > self.email_otp_created_at + expiry_duration
        )

    def otp_is_due_for_retry(self):
        # Unlock OTP retry after 15 minutes
        lock_duration = timedelta(minutes=15)
        return (
            timezone.now() > self.phone_otp_created_at + lock_duration
            or timezone.now() > self.email_otp_created_at + lock_duration
        )

    def set_user_is_active(self, id):
        # grab the current user from Uses model user the user instance from OTPVerification model
        current_user = Users.objects.get(id=id)
        # set current user status to is_active
        current_user.is_active = True
        # save current user
        current_user.save()


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="products"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class PreviousPassword(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, default=None)
    password = models.CharField(max_length=200, default="")
    date = models.DateTimeField(default=datetime.now())

    def __str__(self):
        return f"{self.user.email}"


class SavedBeneficiary(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, default=None)
    bank_name = models.CharField(max_length=100, default="", blank=True)
    bank_slug = models.CharField(max_length=150, default="", blank=True)
    bank_code = models.CharField(max_length=100, default="", blank=True)
    account_name = models.CharField(max_length=100, default="", blank=True)
    account_number = models.CharField(max_length=100, default="", blank=True)
    beneficiary_name = models.CharField(max_length=100, default="", blank=True)

    def __str__(self):
        return f"{self.user.email}: {self.beneficiary_name} - {self.account_name} - {self.bank_name}"

    def save(self, *args, **kwargs):
        self.bank_slug = slugify(self.bank_name)
        self.beneficiary_name = (
            self.account_name if not self.beneficiary_name else self.beneficiary_name
        )
        super(SavedBeneficiary, self).save(*args, **kwargs)


class MerchantCountries(models.Model):
    AFRICA_CHOICES = [
        ("NGA", "Nigeria"),
        ("GHA", "Ghana"),
        ("KEN", "Kenya"),
        ("BEN", "Republique du Benin"),
        ("BFA", "Burkina Faso"),
        ("CMR", "Cameroun"),
        ("COG", "Congo Brazzaville"),
        ("COD", "Congo DRC"),
        ("CIV", "Cote d’lvoire"),
        ("GAB", "Gabon"),
        ("GHA", "Ghana"),
        ("GIN", "Guinea"),
        ("LBR", "Liberia"),
        ("MLI", "Mali"),
        ("MOZ", "Mozambique"),
        ("NGA", "Nigeria"),
        ("SEN", "Senegal"),
        ("SLE", "Sierra Leone"),
        ("TZA", "Tanzania"),
        ("TCD", "Tchad"),
        ("UGA", "Uganda "),
        ("ZMB", "Zambia"),
    ]

    WORLD_CHOICES = [
        ("USA", "United States"),
        ("FRA", "France"),
        ("GBR", "United Kingdom"),
        ("UAE", "United Arab Emirates"),
    ]

    africa = models.CharField(max_length=3, choices=AFRICA_CHOICES, blank=True)
    world = models.CharField(max_length=3, choices=WORLD_CHOICES, blank=True)

    def __str__(self):
        return f"Africa: {self.get_africa()}, World: {self.get_world()}"


class Recipient(models.Model):
    RECIPIENT_TYPES = [
        ('NGO', 'NGO'),
        ('Company', 'Company'),
        ('Individual', 'Individual'),
    ]

    name = models.CharField(max_length=255)
    recipient_type = models.CharField(max_length=10, choices=RECIPIENT_TYPES)
    owner = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="owned_recipients") 
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.get_recipient_type_display()})"

    
class Donation(models.Model):
    donor = models.ForeignKey(Users, on_delete=models.CASCADE, related_name="donations")
    recipient = models.ForeignKey(Recipient, on_delete=models.CASCADE, related_name="received_donations")
    amount = models.DecimalField(max_digits=20, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    currency = models.CharField(max_length=55, default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    reference = models.CharField(max_length=255, default="", blank=True)
    def __str__(self):
        return f"Donation from {self.donor.username} to {self.recipient.name} of {self.amount} {self.currency}"




