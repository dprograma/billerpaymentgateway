from django.contrib import admin

from .models import LoginAttempt, OTPVerification, Users

# Register your models here.

admin.site.register(Users)
admin.site.register(LoginAttempt)
admin.site.register(OTPVerification)
