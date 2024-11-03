from django.urls import path

from . import views

urlpatterns = [
    path("update-kyc/", views.UpdateMerchantKyc.as_view(), name="update_kyc"),
    path("get-kyc/", views.RetrieveMerchantKyc.as_view(), name="get_kyc"),
]
