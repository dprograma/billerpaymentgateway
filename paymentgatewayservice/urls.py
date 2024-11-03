from django.urls import path

from .views import (
    AuthenticationUSSD,
    CallBackUrlView,
    DirectPay,
    FailureUrl,
    FetchAccountTransactions,
    FetchPartnerTransactions,
    GetBankList,
    GetUSSDBankList,
    GetTransactionDetails,
    InvokePayment,
    InvokeReference,
    PaymentStatus,
    Refund,
    RequestPaymentWithCard,
    RequestPaymentWithTransfer,
    SuccessUrl,
    TransactionPaymentNotification,
    TransactionStatusQuery,
    BankLinkAuthentication,
)

urlpatterns = [
    path("invokepayment/", InvokePayment.as_view(), name="invoke_payment"),
    # http://127.0.0.1:8000/gateway/api/v0/invokepayment
    path("payment-status/", PaymentStatus.as_view(), name="payment_status"),
    # http://127.0.0.1:8000/gateway/api/v0/payment-status
    path("paywithcard/", RequestPaymentWithCard.as_view(), name="pay_with_card"),
    # http://127.0.0.1:8000/gateway/api/v0/paywithcard
    path("success/", SuccessUrl.as_view(), name="success"),
    path("failure/", FailureUrl.as_view(), name="failure"),
    path(
        "paywithtransfer",
        RequestPaymentWithTransfer.as_view(),
        name="dynamic_pay_with_transfer",
    ),
    # http://127.0.0.1:8000/gateway/api/v0/paywithtransfer
    path(
        "get-transaction-details/",
        GetTransactionDetails.as_view(),
        name="get_transaction_details",
    ),
    # http://127.0.0.1:8000/gateway/api/v0/get-transaction-details
    path(
        "fetch-account-transactions/",
        FetchAccountTransactions.as_view(),
        name="fetch_account_transaction",
    ),
    # http://127.0.0.1:8000/gateway/api/v0/fetch-account-transactions
    path(
        "fetch-partner-transactions/",
        FetchPartnerTransactions.as_view(),
        name="fetch_partner_transaction",
    ),
    # http://127.0.0.1:8000/gateway/api/v0/fetch-partner-transactions
    path(
        "merchant-transactions-notification/",
        TransactionPaymentNotification.as_view(),
        name="merchanttransactions_notification",
    ),
    # http://127.0.0.1:8000/gateway/api/v0/merchant-transactions-notification
    path("get-bank-list/", GetBankList.as_view(), name="get_bank_list"),
    # http://127.0.0.1:8000/gateway/api/v0/get-bank-list
    path("direct-pay/", DirectPay.as_view(), name="direct_pay"),
    # http://127.0.0.1:8000/gateway/api/v0/direct-pay
    path("ussd-authentication/", AuthenticationUSSD.as_view(), name="ussd_authentication"),
    # http://127.0.0.1:8000/gateway/api/v0/ussd-authentication/
    path("invoke-reference/", InvokeReference.as_view(), name="invoke_reference"),
    # http://127.0.0.1:8000/gateway/api/v0/invoke-reference/
    path(
        "transaction-status/",
        TransactionStatusQuery.as_view(),
        name="transaction_status",
    ),
    # http://127.0.0.1:8000/gateway/api/v0/transaction-status/
    path("ussd-callback/", CallBackUrlView.as_view(), name="ussd_callback"),
    # http://127.0.0.1:8000/gateway/api/v0/ussd-callbackurl/
    path("refund/", Refund.as_view(), name="refund"),
    # http://127.0.0.1:8000/gateway/api/v0/refund/
    path("get-ussd-bank-list/", GetUSSDBankList.as_view(), name="get_bank_list"),
    
    # CoralPay new BankLink API for Bank Transfers
    path("authentication/", BankLinkAuthentication.as_view(), name="bank_link_authentication")
]
