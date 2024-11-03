from django.urls import re_path as url

from .auth import (
    GetCurrentUser,
    Login,
    SignUp,
    UpdatePassword,
    UpdateWalletPin,
    UserProfile,
    VerifyOTP,
    WalletPin,
)
from .wallets import FundWallet, UserWallet, WalletToBankTransfer, WalletTransfer, WalletToBankOTPValidation, WalletTransferValidation, FundWalletValidation

urlpatterns = [
    url(r"^user$", UserProfile.as_view(), name="profile"),
    url(r"^auth/signup/$", SignUp.as_view(), name="signup"),
    url(r"^auth/verify-otp/$", VerifyOTP.as_view(), name="verify_otp"),
    url(r"^auth/login/$", Login.as_view(), name="login"),
    url(r"^user/update-password/$", UpdatePassword.as_view(), name="change_password"),
    url(r"^user/set-pin/$", WalletPin.as_view(), name="set_pin"),
    url(r"^user/update-pin/$", UpdateWalletPin.as_view(), name="set_pin"),
    url(r"^user/wallets/$", UserWallet.as_view(), name="wallets"),
    url(r"^user/wallet/fund/$", FundWallet.as_view(), name="fund_wallet"),
    url(r"^user/wallet/fund/validation/$", FundWalletValidation.as_view(), name="fund_wallet"),
    url(
        r"^user/wallet/verify-deposit/(?P<reference>[\w-]+)/(?P<currency>[\w-]+)/$",
        FundWallet.as_view(),
        name="fund_wallet_verify",
    ),
    url(r"^user/wallet/transfer/$", WalletTransfer.as_view(), name="wallet_transfer"),
    url(r"^user/wallet/transfer/validation$", WalletTransferValidation.as_view(), name="wallet_transfer_validation"),
    url(
        r"^user/wallet/fetch-banks/$",
        WalletToBankTransfer.as_view(),
        name="wallet_fetch_banks",
    ),
    url(
        r"^user/wallet/bank-transfer/$",
        WalletToBankTransfer.as_view(),
        name="wallet_bank_transfer",
    ),
    url(
        r"^user/wallet/bank-otp-validation/$",
        WalletToBankOTPValidation.as_view(),
        name="wallet_bank_otp_validation",
    ),
    url(r"^user/getuser/$", GetCurrentUser.as_view(), name="get_user")
]
