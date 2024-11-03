from django.urls import path, include

from .views import (
    DeleteAccountView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    PasswordResetView,
    SendEmailOTPView,
    SendPhoneOTPView,
    SignupView,
    UpdateUserView,
    VerifyOTPView,
)
from rest_framework.routers import DefaultRouter
from .auth import RecipientViewSet, DonationViewSet

router = DefaultRouter()
router.register(r'recipients', RecipientViewSet)
router.register(r'donations', DonationViewSet)

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    # http://127.0.0.1:8000/gateway/api/v1/signup
    path("login/", LoginView.as_view(), name="login"),
    path("send-email-otp/", SendEmailOTPView.as_view(), name="send_email_otp"),
    path("send-phone-otp/", SendPhoneOTPView.as_view(), name="send_phone_otp"),
    path("verify-otp/", VerifyOTPView.as_view(), name="verify_otp"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path(
        "reset-password/",
        PasswordResetView.as_view(),
        name="reset_password",
    ),
    path("update-user/", UpdateUserView.as_view(), name="update_user"),
    path("delete-account/", DeleteAccountView.as_view(), name="delete_account"),
    path('', include(router.urls)),
]

