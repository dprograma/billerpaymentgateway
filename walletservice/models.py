# from __future__ import unicode_literals

import datetime
from django.utils.html import mark_safe
from cloudinary.models import CloudinaryField  # type: ignore
import secrets
from decimal import Decimal
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from datetime import timedelta

# Create your models here.
# class QRCode(models.Model):
# 	user = models.OneToOneField("userservice.User", on_delete=models.CASCADE, default=None)
# 	qr_code = CloudinaryField('QR Code', folder="qr_code", null=True, blank=True)
# 	payment_link = models.CharField(max_length=100, default='', blank=True)

# 	def __str__(self):
# 		return f"{self.user.user_id}"

# 	def qr_image(self):
# 		return mark_safe(f'<img src="{self.qr_code}" width="100" height="100" />')
# 	qr_image.allow_tags = False


def generate_wallet_name(prefix):
    # Generate a random 10-digit number
    random_number = "".join(secrets.choice("0123456789"))
    return f"{prefix}{random_number}"


class Wallet(models.Model):
    WALLET_CHOICES = [
            ("NGN", "NGN"),
            ("GHS", "GHS"),
            ("KES", "KES"),
            ("XOF", "XOF"),
            ("XAF", "XAF"),
            ("CDF", "CDF"),
            ("GNF", "GNF"),
            ("LRD", "LRD"),
            ("MZN", "MZN"),
            ("SLL", "SLL"),
            ("TZS", "TZS"),
            ("UGX", "UGX"),
            ("ZMW", "ZMW"),
            ("USD", "USD"),
            ("EUR", "EUR"),
            ("GBP", "GBP"),
            ("AED", "AED"),
        ]

    user = models.ForeignKey(
        "userservice.Users",
        on_delete=models.CASCADE,
        default=None,
        related_name="wallets",
    )
    currency = models.CharField(choices=WALLET_CHOICES, default="NGN", max_length=50)
    name = models.CharField(max_length=11, default="Naira")
    customer_code = models.CharField(max_length=55, default="", blank=True)
    transfer_code = models.CharField(max_length=55, default="", blank=True)
    balance = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal("0"))],
        editable=False,
        null=False,
    )
    bank_name = models.CharField(max_length=100, default="", blank=True)
    bank_slug = models.CharField(max_length=150, default="", blank=True)
    bank_code = models.CharField(max_length=100, default="", blank=True)
    account_name = models.CharField(max_length=100, default="", blank=True)
    account_number = models.CharField(max_length=100, default="", blank=True)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_expiry = models.DateTimeField(null=True, blank=True)
    suspend = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True, null=False)
    modified_on = models.DateTimeField(auto_now=True, null=False)

    def __str__(self):
        return f"{self.user.username} - {self.balance:,} {self.currency} - {self.name}"


class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.code})"


class ExchangeRate(models.Model):
    from_currency = models.ForeignKey(
        Currency, related_name="from_rates", on_delete=models.CASCADE
    )
    to_currency = models.ForeignKey(
        Currency, related_name="to_rates", on_delete=models.CASCADE
    )
    rate = models.DecimalField(max_digits=10, decimal_places=4)
    last_updated = models.DateTimeField(auto_now=True)

    def is_stale(self):
        return timezone.now() > self.last_updated + timedelta(hours=24)

    def __str__(self):
        return f"1 {self.from_currency.code} = {self.rate} {self.to_currency.code}"


class CustomerBankAccount(models.Model):
    user = models.OneToOneField("userservice.Users", on_delete=models.CASCADE)
    bank_account_number = models.CharField(max_length=20)
    reference_no = models.CharField(max_length=50)


class VirtualAccount(models.Model):
    user = models.OneToOneField(
        "userservice.Users", on_delete=models.CASCADE, default=None
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    bank_name = models.CharField(max_length=100, default="", blank=True)
    bank_slug = models.CharField(max_length=150, default="", blank=True)
    wallet_code = models.CharField(max_length=100, default="", blank=True)
    account_name = models.CharField(max_length=100, default="", blank=True)
    account_number = models.CharField(max_length=100, default="", blank=True)
    suspend = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email}"

    def save(self, *args, **kwargs):
        self.bank_slug = slugify(self.bank_name)
        super(VirtualAccount, self).save(*args, **kwargs)
