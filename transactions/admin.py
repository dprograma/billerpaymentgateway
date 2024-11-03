from django.contrib import admin

from .models import WalletTransaction, Deposit

# Register your models here.


admin.site.register(WalletTransaction)
admin.site.register(Deposit)
