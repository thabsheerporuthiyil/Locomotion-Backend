from django.urls import path
from .views import (
    CreateRazorpayOrderView,
    VerifyPaymentView
)

urlpatterns = [
    path('order/<int:pk>/', CreateRazorpayOrderView.as_view(), name='create-razorpay-order'),
    path('verify/<int:pk>/', VerifyPaymentView.as_view(), name='verify-payment'),
]
