from django.urls import re_path as path

from transactions.views import DepositWallet, CombinedTransactionView, AllTransactionView

# from transactions.views import TransactionDetail, TransactionList, TransactionWalletList

urlpatterns = [
    path(r"^deposit/$", DepositWallet.as_view(), name="deposit-wallet"),
    path(r"^deposit/(?P<ref>[\w-]+)/$", DepositWallet.as_view(), name="deposit-wallet"),
    path(r"^transactions/$", CombinedTransactionView.as_view(), name="transactions"),
    path(r"^transactions/(?P<ref>[\w-]+)/$", CombinedTransactionView.as_view(), name="user-transactions"),
    path(r"^all-transactions/$", AllTransactionView.as_view(), name="all-transactions"),
    # AllTransactionView
    # path("", TransactionList.as_view(), name="transaction-list"),
    # path(
    #     "<int:id>",
    #     TransactionDetail.as_view(),
    #     name="transaction-detail",
    # ),
    # path(
    #     "<str:name>",
    #     TransactionWalletList.as_view(),
    #     name="transaction-wallets",
    # ),
]
