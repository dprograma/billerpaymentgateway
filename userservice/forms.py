from django import forms
from django.contrib.auth.forms import (
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from .models import Users


class SignupForm(UserCreationForm):
    username = forms.CharField(label="Username", required=True)
    phone_number = forms.CharField(label="Mobile Phone", required=True)
    email = forms.EmailField(label="Email", required=True)
    password1 = forms.CharField(label="Password", required=True)

    class Meta:
        model = Users
        fields = ("username", "phone_number", "email", "password1", "password2")


class LoginForm(forms.Form):
    email = forms.EmailField(label="Email", required=True)
    password1 = forms.CharField(
        label="Password", widget=forms.PasswordInput, required=True
    )
    phone_number = forms.CharField(label="Mobile Phone", required=True)

    class Meta:
        model = Users
        fields = ("email", "phone_number", "password1")


class ForgotPasswordForm(PasswordResetForm):
    email = forms.EmailField(label="Email", max_length=254)

    class Meta:
        model = Users
        fields = ("email",)


class ResetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(label="New Password", widget=forms.PasswordInput)
    new_password2 = forms.CharField(
        label="Confirm New Password", widget=forms.PasswordInput
    )

    class Meta:
        model = Users
        fields = ("new_password1", "new_password2")
