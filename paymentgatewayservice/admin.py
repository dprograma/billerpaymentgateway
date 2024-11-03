from django.contrib import admin

from .models import Transactions, Wallet

admin.site.register(Wallet)
admin.site.register(Transactions)
