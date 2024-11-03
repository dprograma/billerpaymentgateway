from django.db import models
from django.utils import timezone

from userservice.models import Users


class Wallet(models.Model):
    user = models.OneToOneField(Users, related_name="wallet", on_delete=models.CASCADE, unique=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    earning = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user}'s Wallet"


class Transactions(models.Model):
    TRANSACTION_STATUS = [
        (-1, "Debit"),
        (0, "Pending"),
        (1, "Credited"),
        (2, "Cancel or Fail"),
    ]

    TRANSACTION_METHOD = [("cash", "Cash"), ("wallet", "Wallet")]

    user = models.ForeignKey(Users, related_name="transactions", on_delete=models.CASCADE)
    title = models.CharField(max_length=128)
    body = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.IntegerField(choices=TRANSACTION_STATUS)
    method = models.CharField(max_length=10, choices=TRANSACTION_METHOD)
    avatar = models.ImageField(upload_to="transaction_avatars/", null=True, blank=True)
    trans_response = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
