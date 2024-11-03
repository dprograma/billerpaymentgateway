"""
Transaction Models
"""

import logging
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

# from walletservice.models import Wallet

# logger = logging.getLogger("transaction")


STATUS_CHOICES = [
    ("PAID", "Paid"),
    ("FAILED", "Failed"),
]


class Transaction(models.Model):
    """
    Represents a transaction between two Wallets.

    This model stores transaction entity between two wallets:
    - sender - wallet id
    - receiver - wallet id
    - transfer_amount - the amount of money that the "sender" sends to the "receiver". Example - 5.00
    - commission - 0.00 if no commission; otherwise, transfer_amount * 0.10
    - status - PAID if no problems; otherwise, FAILED
    - timestamp - datetime when the transaction was created
    """
    user = models.ForeignKey("userservice.Users", on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(
        decimal_places=2, 
        max_digits=20, 
        default=0.00, 
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    fee = models.DecimalField(
        decimal_places=2, 
        max_digits=20, 
        default=0.00, 
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    balance_before = models.DecimalField(
        decimal_places=2, 
        max_digits=20, 
        default=0.00, 
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    balance_after = models.DecimalField(
        decimal_places=2, 
        max_digits=20, 
        default=0.00, 
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    order = models.CharField(max_length=100, default='', blank=True)
    reference = models.CharField(max_length=100, default='', blank=True)
    note = models.TextField(default='', blank=True)
    gateway = models.CharField(max_length=50, default='', blank=True)
    transaction_type = models.CharField(max_length=40, default='debit', blank=True)
    payment_type = models.CharField(max_length=40, default='debit', blank=True)
    status = models.CharField(max_length=40, default='success', blank=True)
    date = models.DateTimeField(auto_now_add=True, blank=True)


class WalletTransaction(models.Model):
    sender_wallet = models.ForeignKey("walletservice.Wallet", related_name='sent_transactions', on_delete=models.SET_NULL, null=True, blank=True)
    recipient_wallet = models.ForeignKey("walletservice.Wallet", related_name='received_transactions', on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(
        decimal_places=2, 
        max_digits=12, 
        default=0.00, 
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    fee = models.DecimalField(
        decimal_places=2, 
        max_digits=12, 
        default=0.00, 
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    balance_before = models.DecimalField(
        decimal_places=2,
        max_digits=12, 
        default=0.00, 
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    balance_after = models.DecimalField(
        decimal_places=2, 
        max_digits=12, 
        default=0.00, 
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    order = models.CharField(max_length=100, default='', blank=True)
    reference = models.CharField(max_length=100, default='', blank=True)
    note = models.TextField(default='', blank=True)
    gateway = models.CharField(max_length=50, default='', blank=True)
    transaction_type = models.CharField(max_length=40, default='transfer', blank=True)
    payment_type = models.CharField(max_length=40, default='wallet', blank=True)
    status = models.CharField(max_length=40, default='success', blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction {self.reference} - {self.sender_wallet.user.username if self.sender_wallet else 'Unknown'} to {self.recipient_wallet.user.username if self.recipient_wallet else 'Unknown'} - {self.amount}"


class Deposit(models.Model):
    user = models.ForeignKey("userservice.Users", on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    fee = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    balance_before = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    balance_after = models.DecimalField(decimal_places=2, max_digits=12, default=0.00)
    order = models.CharField(max_length=100, default='', blank=True)
    reference = models.CharField(max_length=100, default='', blank=True)
    note = models.TextField(default='', blank=True)
    gateway = models.CharField(max_length=50, default='', blank=True)
    transaction_type = models.CharField(max_length=40, default='credit', blank=True)
    payment_type = models.CharField(max_length=40, default='credit', blank=True)
    status = models.CharField(max_length=40, default='success', blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.reference} - {self.amount}"