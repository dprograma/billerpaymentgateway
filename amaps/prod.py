from .base import *
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'new.sqlite3',
    }
}

CURRENT_SITE = "http://127.0.0.1:8000"

# BulkSMS otp settings
BULK_SMS_OTP_URL = "https://www.bulksmsnigeria.com/api/v1/sms/create"
BULK_SMS_API_TOKEN = "kK6ndC04gKIlNir9IyfSLoe6WtbBga1jwOjNlgQUI3oyXa0VNlVScJm0glwT"

# Termii otp settings
TERMII_OTP_TOKEN = "TTdkSJGmfTnHHNLedsfPdBaRQZbWeQWxZPsQkojHFgkiGNuHyZBcZXiigYrZVA"
TERMII_OTP_URL = "https://v3.api.termii.com/api/sms/send"

# ExchangeRate API
EXCHANGE_RATE_API_KEY = "a85a14d032c8cb7a72334650"


# [EMAIL]
# MAIL_PORT = os.environ.get('MAIL_PORT')
# MAIL_SERVER = os.environ.get('MAIL_SERVER')
# MAIL_USER = os.environ.get('MAIL_USER')
# MAIL_PASS = os.environ.get('MAIL_PASS')

# [EMAIL]
MAIL_PORT=587
EMAIL_USE_TLS = True
MAIL_SERVER='mail.ojapay.com'
MAIL_USER='reply@ojapay.com'
MAIL_PASS='36NlcwMpARUy'

# EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
# EMAIL_FILE_PATH = BASE_DIR / "emails"  # change this to a proper location
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "sandbox.smtp.mailtrap.io"
EMAIL_PORT = 2525
# EMAIL_HOST_USER = "12df3970b597f6"
EMAIL_HOST_USER = "e4ddb8cd5d0f6e"
# EMAIL_HOST_PASSWORD = "a663558518ce34"
EMAIL_HOST_PASSWORD = "7c789e78d8ef2a"
EMAIL_USE_TLS = True



CORALPAY_INVOKEPAYMENT_URL = "https://testdev.coralpay.com:5000/GwApi/api/v1/InvokePayment/"
CORALPAY_TRANSACTIONQUERY_URL = "https://testdev.coralpay.com:5000/GwApi/api/v1/TransactionQuery/"
CORALPAY_INVOKE_USSD_URL = "https://testdev.coralpay.com/cgateproxy/api/invokereference"

# CORALPAY_RETURN_URL = "https://google.com"
CORALPAY_RETURN_URL = "http://127.0.0.1:8000/gateway/api/v0/payment-status/"
CORALPAY_CALLBACKURL_SUCCESS = "http://127.0.0.1:8000/gateway/api/v0/success/"
CORALPAY_WEBSOCKETURL_SUCCESS = "http://127.0.0.1:8000/ws/success/"
CORALPAY_CALLBACKURL_FAILURE = "http://127.0.0.1:8000/gateway/api/v0/failure/"
CORALPAY_WEBSOCKETURL_FAILURE = "http://127.0.0.1:8000/ws/failure/"
CORALPAY_TRACEID = "9900990285"
CORALPAY_TERMINALID = "40016857947"
CORALPAY_PRODUCTID = "aa12443d"
CORALPAY_MERCHANT_USERNAME = "ojapaXIgaPqMJdRVh%I*NXppJGV)*mo"
CORALPAY_MERCHANT_PASSWORD = "83Y36$47@P^0TTME@NV?*5MFY8H5I?E8N95#I940"
CORALPAY_MERCHANTID = "4001686OJGUHK01"
CORALPAY_KEY = "59d7b52c-758e-4060-8bc3-cdffd780fb2f"
CORALPAY_TOKEN = "eyJhbGciOiJodHRwOi8vd3d3LnczLm9yZy8yMDAxLzA0L3htbGRzaWctbW9yZSNobWFjLXNoYTUxMiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI2YWNhY2EzYS04YzlmLTQyYTgtYjYzNy01NThkODQyZWU2M2YiLCJNZXJjaGFudElkIjoiNDAwMTY4Nk9KR1VISzAxIiwiZXhwIjoxNzI2MzMwNzQ3LCJpc3MiOiJodHRwczovL2NvcmFscGF5LmNvbSIsImF1ZCI6Imh0dHBzOi8vY29yYWxwYXkuY29tIn0.xrAqFg18m9u_j5TMrHEfOA0djU8Wnndh6ojOCHv3mmjdQOI6yuM0gYsyjaLQeQZbCpe5CMNmMTo7uQR249udFw"

# PAY WITH CARD DETAILS
CORALPAY_REQUESTPAYMENTWITHCARD_URL = "https://cnptest.coralpay.com:9443/octoweb/cnp/requestPayment/"
CORALPAY_CARD_MERCHANTID = "3051OJP10000001"
CORALPAY_PAYWITHCARD_TOKEN = "KHR0IyNtQDAkQG1hdm0lKCUxJSRAMCo1ZiU0dihqM25AOmFlMjEzYjNmOThkYTE5YjdlN2VlNzkwNjZlYTczODc3MGY0NDQ5MzgzOGE4NTc2OTJhZjYzNDU4MjY0MjEzNzVkMmVmMjM0NTAwNjBlOWM3YWZlZjVhN2RkZjYzOWZlY2EyZmU3MjdkM2IwZjRiNTYwNDgxOTU4NjM3NmVmM2NjMjcxMTAzNDI5N2Q1ZjNlZGJkMWY1ZjM4ZGIwY2Q3MzY5MDNjNmYwOGViNjM1YTQ5Njc2NzAwNmI="

# PAY WITH DYNAMIC BANK TRANSFER
CORALPAY_CLIENTID = "4001459DHEKNS17"
CORALPAY_DYNAMIC_PAYWITHTRANSFER_URL = "http://sandbox1.coralpay.com:8080/paywithtransfer/moneytransfer/apis/dynamicAccount/"
CORALPAY_DPWT_USERNAME = "Ojaypay_User"

# PAY WITH STATIC BANK TRANSFER
CORALPAY_STATIC_PAYWITHTRANSFER_URL = "http://sandbox1.coralpay.com:8080/paywithtransfer/moneytransfer/apis/staticAccount/"

# PAY WITH TRANSFER REQUERY
CORALPAY_PAYWITHTRANSFER_REQUERY_URL = "http://sandbox1.coralpay.com:8080/paywithtransfer/moneytransfer/apis/getTransactionDetails/"
CORALPAY_CLIENT_PASSWORD = "77LO!T38TY8I##@M09G$&TKKBX?JV"

# FETCH ACCOUNT TRANSACTIONS
CORALPAY_FETCH_ACCOUNT_TRANSACTIONS_URL = "http://sandbox1.coralpay.com:8080/paywithtransfer/moneytransfer/apis/partners/getAccountTransactions/"

# FETCH PARTNER TRANSACTIONS
CORALPAY_FETCH_PARTNER_TRANSACTIONS_URL = "http://sandbox1.coralpay.com:8080/paywithtransfer/moneytransfer/apis/partners/fetch-partner-transactions"


# TRANSACTION PAYMENT NOTIFICATION
CORALPAY_MERCHANT_ACCOUNT_NUMBER = "7003268673"
CORALPAY_MERCHANT_PAYMENT_NOTIFICATION_URL = "http://sandbox1.coralpay.com:8080/paywithtransfer/moneytransfer/apis/testPartnerRequest/"

# GET BANK LIST 
CORALPAY_GET_BANK_LIST_URL = "http://sandbox1.coralpay.com:8080/paywithtransfer/moneytransfer/apis/listOfBanks/"

# PAY DIRECT URL
CORALPAY_PAYDIRECT_URL = "http://sandbox1.coralpay.com:8080/paywithtransfer/v1/directpaywithaccount/apis/onetimepayment/"

# PAY WITH DYNAMIC BANK TRANSFER
CORALPAY_CLIENTID = "4001459DHEKNS17"
CORALPAY_BANKLINK_API_INIT_URL = "https://testdev.coralpay.com:5000/BankLinkService/api/Auth/"
CORALPAY_BANKLINK_API_BASEURL = "https://testdev.coralpay.com:5000/BankLink/api/"
CORALPAY_DPWT_USERNAME = "Ojaypay_User"
CORALPAY_CLIENT_PASSWORD = "77LO!T38TY8I##@M09G$&TKKBX?JV"
CORALPAY_MERCHANT_ACCOUNT_NUMBER = "7003268673"

# CORALPAY USSD API 
CORALPAY_USSD_AUTHENTICATION_URL = "https://testdev.coralpay.com/cgateproxy/api/v2/authentication/"
CORALPAY_USSD_USERNAME = "Ojapay"
CORALPAY_USSD_PASSWORD = "0350080220@005#0"
CORALPAY_INVOKEREFERENCE_URL = "https://testdev.coralpay.com/cgateproxy/api/v2/invokereference/"
CORALPAY_INVOKEREFERENCE_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI0NzZlYzlkOC0zZTVlLTQyZTUtYmYzMS1mOTFmNTc4ZjgzZWYiLCJNZXJjaGFudElkIjoiMTA1N0pKMDEwMDAwMDAxIiwiVXNlcm5hbWUiOiJPamFwYXkiLCJQYXNzd29yZCI6IjAzNTAwODAyMjBAMDA1IzAiLCJleHAiOjE3NDU5Mjg2MzgsImlzcyI6Imh0dHBzOi8vY29yYWxwYXkuY29tIiwiYXVkIjoiaHR0cHM6Ly9jb3JhbHBheS5jb20ifQ.TWVy4T55itdVPORldkcodUInw7o006PvaLQiudfEUG0"
CORALPAY_INVOKEREFERENCE_MERCHANTID = "1057JJ010000001"
CORALPAY_INVOKEREFERENCE_TERMINALID = "1057JJ01"
CORALPAY_INVOKEREFERENCE_KEY = "a4243592-9b95-4269-9684-28fc897fb601"
CORALPAY_USSD_REFUND_URL = "https://testdev.coralpay.com:5000/cgateproxy/api/v2/refund/"
CORALPAY_TRANSACTIONSTATUS_URL = "https://testdev.coralpay.com/cgateproxy/api/v2/statusquery/"
CORALPAY_GETBANKLIST_URL = "https://testdev.coralpay.com/cgateproxy/api/v2/getbanks/"

