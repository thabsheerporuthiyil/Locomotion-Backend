from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import razorpay
from bookings.models import RideRequest

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
