"""
Urls for Wallet app
"""

from django.urls import path

from .views import (
    FundWalletView,
    WalletDetail,
    WalletList,
    CurrencyListView,
    ExchangeRateView,
    WalletUpdateView,
)

urlpatterns = [
    path("wallet-list-create", WalletList.as_view(), name="wallet-list-create"),
    path("wallet-detail/<str:name>", WalletDetail.as_view(), name="wallet-detail"),
    path("wallets/<int:pk>/fund/", FundWalletView.as_view(), name="fund-wallet"),
    path("currency-list/", CurrencyListView.as_view(), name="currency-list"),
    path("exchange-rate/", ExchangeRateView.as_view(), name="get-exchange-rate"),
    path(
        "wallet-update/<int:user_id>/wallet/",
        WalletUpdateView.as_view(),
        name="wallet-update",
    ),
]
