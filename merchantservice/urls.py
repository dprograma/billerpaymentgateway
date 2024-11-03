from django.urls import path, re_path

from .views import (
    BankNameChoicesAPIView,
    BusinessVerificationView,
    CreateMerchantView,
    DeleteAccountView,
    ForgetPasswordView,
    IdTypeChoicesAPIView,
    LogoutView,
    MerchantLoginView,
    PasswordResetView,
    RetrieveAllMerchants,
    RetrieveMerchant,
    SendEmailOTPView,
    SendPhoneOTPView,
    UpdateMerchantBankDetails,
    UpdateMerchantView,
    VerifyOTPView,
    ProductListCreateView,
    GetAllProductlist,
    CategoryListCreateView,
    ProductUpdateDeleteView,
    MerchantCountriesView,
)

urlpatterns = [
    # This is the merchant-creation, merchant-login, email_otp_verification, phone_number_otp_verification and business_verification for JWT
    path("create-merchant/", CreateMerchantView.as_view(), name="create-merchant"),
    # http://127.0.0.1:8000/api/onboarding/create-merchant/
    path("merchant-login/", MerchantLoginView.as_view(), name="merchant_login"),
    # http://127.0.0.1:8000/api/onboarding/merchant-login/
    path("otp-phone-number/", SendPhoneOTPView.as_view(), name="otp-phone-number"),
    # http://127.0.0.1:8000/api/onboarding/otp-phone-number/
    path("otp-email/", SendEmailOTPView.as_view(), name="otp-email"),
    # http://127.0.0.1:8000/api/onboarding/otp-email/
    path(
        "business-verification/",
        BusinessVerificationView.as_view(),
        name="business-verification",
    ),
    # http://127.0.0.1:8000/api/onboarding/business-verification/
    path(
        "email-phone-verification/",
        VerifyOTPView.as_view(),
        name="email-phone-verification",
    ),
    # http://127.0.0.1:8000/api/onboarding/email-phone-verification/
    # path('reset-password/<str:uidb64>/<str:token>/', PasswordResetView.as_view(), name="reset_password"),
    # # http://127.0.0.1:8000/api/onboarding/reset-password/
    # path("reset/<str:pk>", Reset.as_view(), name="reset"),
    # # http://127.0.0.1:8000/api/onboarding/reset-password/
    # path("reset/", Reset.as_view(), name="reset_pass"),
    path(
        "reset-password/",
        PasswordResetView.as_view(),
        name="reset_password",
    ),
    # http://127.0.0.1:8000/api/onboarding/reset/
    path("logout/", LogoutView.as_view(), name="logout"),
    # http://127.0.0.1:8000/api/onboarding/logout/
    path("forgot-password/", ForgetPasswordView.as_view(), name="forgot_password"),
    # http://127.0.0.1:8000/api/onboarding/forget-password/
    path("delete-account/", DeleteAccountView.as_view(), name="delete_account"),
    # http://127.0.0.1:8000/api/onboarding/delete-account/
    path("update-profile/", UpdateMerchantView.as_view(), name="update_profile"),
    # http://127.0.0.1:8000/api/onboarding/update-profile/
    path("get-merchant/", RetrieveMerchant.as_view(), name="get_merchant"),
    # http://127.0.0.1:8000/api/onboarding/get-merchant/
    path("get-all-merchants/", RetrieveAllMerchants.as_view(), name="get_all_merchants"),
    path(
        "update-merchant-bank-details/",
        UpdateMerchantBankDetails.as_view(),
        name="update_merchant_bank_details",
    ),
    path("id-choices/", IdTypeChoicesAPIView.as_view(), name="id_choices"),
    path("bank-choices/", BankNameChoicesAPIView.as_view(), name="bank_choices"),
    path('products/', ProductListCreateView.as_view(), name='product-list-create'),
    path('products/<int:pk>', ProductUpdateDeleteView.as_view(), name='product-update-delete'),
    path('all-products/', GetAllProductlist.as_view(), name='get-all-product-list'),
    re_path(r"^all-products/(?P<category>[\w%\s\'-]+)/(?P<country>[\w%\s\'-]+)/$", GetAllProductlist.as_view(), name='get-all-product-category-list'),
    path('categories/', CategoryListCreateView.as_view(), name='category-list-create'),
    path('merchant-countries/', MerchantCountriesView.as_view(), name='merchant-countries'),
]
