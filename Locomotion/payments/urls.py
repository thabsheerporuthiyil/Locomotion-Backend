from django.urls import path
from .views import (
    CreateRazorpayOrderView,
    VerifyPaymentView,
    CreateWalletRechargeOrderView,
    VerifyWalletRechargeView
)

urlpatterns = [
    path('order/<int:pk>/', CreateRazorpayOrderView.as_view(), name='create-razorpay-order'),
    path('verify/<int:pk>/', VerifyPaymentView.as_view(), name='verify-payment'),
    path('wallet/recharge/', CreateWalletRechargeOrderView.as_view(), name='create-wallet-recharge'),
    path('wallet/verify/', VerifyWalletRechargeView.as_view(), name='verify-wallet-recharge'),
]
