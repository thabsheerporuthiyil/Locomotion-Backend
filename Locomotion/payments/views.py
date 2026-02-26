from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import razorpay
import random
from bookings.models import RideRequest
from decimal import Decimal

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class CreateRazorpayOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            ride = RideRequest.objects.get(pk=pk, rider=request.user)
            
            if ride.status != "completed":
                return Response({"error": "Ride is not completed yet."}, status=status.HTTP_400_BAD_REQUEST)
                
            if ride.payment_status == "completed" or ride.is_paid:
                return Response({"error": "Ride is already paid."}, status=status.HTTP_400_BAD_REQUEST)

            amount_in_paise = int(ride.estimated_fare * 100)
            
            # Create Razorpay Order
            razorpay_order = razorpay_client.order.create(dict(
                amount=amount_in_paise,
                currency="INR",
                receipt=f"ride_{ride.id}",
                notes={
                    "ride_id": ride.id,
                    "rider_name": ride.rider.name
                }
            ))

            ride.razorpay_order_id = razorpay_order["id"]
            ride.save()

            return Response({
                "order_id": razorpay_order["id"],
                "amount": razorpay_order["amount"],
                "currency": razorpay_order["currency"],
                "key_id": settings.RAZORPAY_KEY_ID,
                "ride_id": ride.id,
            }, status=status.HTTP_200_OK)

        except RideRequest.DoesNotExist:
            return Response({"error": "Ride not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return Response({"error": "Missing payment verification parameters."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ride = RideRequest.objects.get(pk=pk, razorpay_order_id=razorpay_order_id)
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            # Verify Signature
            razorpay_client.utility.verify_payment_signature(params_dict)
            
            # If successful, mark as paid
            ride.payment_status = "completed"
            ride.is_paid = True
            ride.razorpay_payment_id = razorpay_payment_id
            ride.save()
            
            return Response({"message": "Payment verified successfully."}, status=status.HTTP_200_OK)

        except RideRequest.DoesNotExist:
            return Response({"error": "Ride or Order not found."}, status=status.HTTP_404_NOT_FOUND)
        except razorpay.errors.SignatureVerificationError:
            return Response({"error": "Payment signature verification failed."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class CreateWalletRechargeOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            driver_profile = request.user.driver_profile
            
            # Allow user to specify amount, or default to the exact amount needed to reach 0
            requested_amount = request.data.get('amount')
            
            if requested_amount:
                amount_in_inr = float(requested_amount)
            else:
                if driver_profile.wallet_balance >= 0:
                    return Response({"error": "Wallet balance is already positive."}, status=status.HTTP_400_BAD_REQUEST)
                # Calculate absolute value needed to reach exactly 0
                amount_in_inr = float(abs(driver_profile.wallet_balance))

            amount_in_paise = int(amount_in_inr * 100)
            
            if amount_in_paise <= 0:
                return Response({"error": "Invalid recharge amount."}, status=status.HTTP_400_BAD_REQUEST)

            # Create Razorpay Order
            razorpay_order = razorpay_client.order.create(dict(
                amount=amount_in_paise,
                currency="INR",
                receipt=f"recharge_{driver_profile.id}_{random.randint(1000, 9999)}",
                notes={
                    "driver_id": str(driver_profile.id),
                    "type": "wallet_recharge"
                }
            ))

            return Response({
                "order_id": razorpay_order["id"],
                "amount": razorpay_order["amount"],
                "currency": razorpay_order["currency"],
                "key_id": settings.RAZORPAY_KEY_ID,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyWalletRechargeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return Response({"error": "Missing payment verification parameters."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            driver_profile = request.user.driver_profile
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            }
            
            # Verify Signature
            razorpay_client.utility.verify_payment_signature(params_dict)
            
            # Fetch the order details from Razorpay to know exactly how much was paid
            order = razorpay_client.order.fetch(razorpay_order_id)
            amount_paid_in_inr = order['amount'] / 100.0
            
            # Add the money back to the driver's wallet
            driver_profile.wallet_balance += Decimal(str(amount_paid_in_inr))
            driver_profile.save()
            
            return Response({
                "message": "Wallet recharged successfully.",
                "new_balance": driver_profile.wallet_balance
            }, status=status.HTTP_200_OK)

        except razorpay.errors.SignatureVerificationError:
            return Response({"error": "Payment signature verification failed."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
