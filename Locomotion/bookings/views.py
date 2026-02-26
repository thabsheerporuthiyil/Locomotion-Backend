import requests
from django.conf import settings
import random
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import RideRequest
from .serializers import RideRequestSerializer, RideRequestCreateSerializer, RideRatingSerializer
from rest_framework.permissions import IsAuthenticated
from drivers.permissions import IsActiveDriver
from django.db.models import Avg, Count
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class CalculateFareView(APIView):
    @swagger_auto_schema(
        operation_description="Calculate estimated fare for a ride",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'pickup_lat': openapi.Schema(type=openapi.TYPE_NUMBER),
                'pickup_lon': openapi.Schema(type=openapi.TYPE_NUMBER),
                'dropoff_lat': openapi.Schema(type=openapi.TYPE_NUMBER),
                'dropoff_lon': openapi.Schema(type=openapi.TYPE_NUMBER),
                'vehicle_category': openapi.Schema(type=openapi.TYPE_STRING),
            }
        ),
        responses={200: "Estimated fare details", 400: "Bad Request"}
    )
    def post(self, request):
        try:
            pickup_lat = request.data.get('pickup_lat')
            pickup_lon = request.data.get('pickup_lon')
            dropoff_lat = request.data.get('dropoff_lat')
            dropoff_lon = request.data.get('dropoff_lon')

            if not all([pickup_lat, pickup_lon, dropoff_lat, dropoff_lon]):
                return Response({'error': 'Missing coordinates'}, status=status.HTTP_400_BAD_REQUEST)

            vehicle_category = request.data.get('vehicle_category', '').lower()
            is_two_wheeler = any(word in vehicle_category for word in ['two', '2', 'bike', 'scooter', 'motorcycle'])
            
            if is_two_wheeler:
                BASE_FARE = 25.0
                PER_KM_RATE = 8.0
                PER_MIN_RATE = 1.0
            else:
                BASE_FARE = 50.0
                PER_KM_RATE = 15.0
                PER_MIN_RATE = 2.0
            
            ORS_API_KEY = getattr(settings, 'ORS_API_KEY', None)
            if not ORS_API_KEY:
                return Response({'error': 'Please set the ORS_API_KEY in settings.py to calculate fares.'}, status=status.HTTP_400_BAD_REQUEST)
            
            headers = {
                'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
                'Authorization': ORS_API_KEY,
                'Content-Type': 'application/json; charset=utf-8'
            }
            body = {
                "coordinates": [
                    [float(pickup_lon), float(pickup_lat)],
                    [float(dropoff_lon), float(dropoff_lat)]
                ],
                "options": {
                    "avoid_features": ["ferries", "tollways"],
                }
            }
            url = 'https://api.openrouteservice.org/v2/directions/driving-car'
            
            response = requests.post(url, json=body, headers=headers)
            
            print(f"ORS API STATUS: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if 'routes' in data and len(data['routes']) > 0:
                    summary = data['routes'][0]['summary']
                    distance_m = summary['distance']
                    duration_s = summary['duration']
                    
                    distance_km = distance_m / 1000.0

                    TRAFFIC_MULTIPLIER = 1.75
                    duration_min = (duration_s / 60.0) * TRAFFIC_MULTIPLIER
                    
                    ride_fare = BASE_FARE + (distance_km * PER_KM_RATE) + (duration_min * PER_MIN_RATE)
                    
                    if distance_km <= 5.0:
                        SERVICE_CHARGE = 10.0
                    elif distance_km <= 10.0:
                        SERVICE_CHARGE = 15.0
                    elif distance_km <= 20.0:
                        SERVICE_CHARGE = 25.0
                    else:
                        SERVICE_CHARGE = 35.0
                    
                    total_estimated_fare = ride_fare + SERVICE_CHARGE
                    
                    return Response({
                        'distance_km': round(distance_km, 2),
                        'duration_min': round(duration_min, 0),
                        'ride_fare': round(ride_fare, 2),
                        'service_charge': round(SERVICE_CHARGE, 2),
                        'estimated_fare': round(total_estimated_fare, 2)
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({'error': 'No route found'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                print(f"ORS ERROR DETAILS: {response.text}")
                return Response({'error': 'Failed to fetch route details', 'details': response.text}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateRideRequestView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Create a new ride request",
        request_body=RideRequestCreateSerializer,
        responses={201: RideRequestCreateSerializer, 400: "Bad Request"}
    )
    def post(self, request):
        user = request.user
        
        provided_phone = request.data.get('rider_phone_number')
        if not user.phone_number and not provided_phone:
            return Response(
                {"error": "A valid mobile number is required to book a ride."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = RideRequestCreateSerializer(data=request.data)
        if serializer.is_valid():

            if not user.phone_number and provided_phone:
                user.phone_number = provided_phone
                user.save()

            distance_km = serializer.validated_data.get('distance_km', 0)
            
            # --- Service Charge Logic ---
            if distance_km <= 5.0:
                service_charge = 10.0
            elif distance_km <= 10.0:
                service_charge = 15.0
            elif distance_km <= 20.0:
                service_charge = 25.0
            else:
                service_charge = 35.0

            ride_otp = str(random.randint(1000, 9999))
            serializer.save(rider=user, ride_otp=ride_otp, service_charge=service_charge)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# List ride requests for drivers
class DriverRideRequestListView(APIView):
    permission_classes = [IsActiveDriver]

    @swagger_auto_schema(
        operation_description="List available ride requests for the driver",
        responses={200: RideRequestSerializer(many=True)}
    )
    def get(self, request):
        driver_profile = request.user.driver_profile
        
        # Block drivers with a wallet balance below -100
        if driver_profile.wallet_balance <= -100.00:
             return Response([])
             
        queryset = RideRequest.objects.filter(
            driver=driver_profile,
            status__in=['pending', 'accepted', 'arrived', 'in_progress']
        ).order_by('-created_at')
        
        serializer = RideRequestSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


# List of all rides for riders "My Rides"
class RiderRideRequestListView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List all past and current ride requests for the rider",
        responses={200: RideRequestSerializer(many=True)}
    )
    def get(self, request):
        queryset = RideRequest.objects.filter(rider=request.user).order_by('-created_at')
        serializer = RideRequestSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

# Not used yet
class RideRequestDetailView(APIView):    
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Get details of a specific ride request",
        responses={200: RideRequestSerializer, 403: "Forbidden", 404: "Not Found"}
    )
    def get(self, request, pk):
        try:
            ride_request = RideRequest.objects.get(pk=pk)
            is_rider = request.user == ride_request.rider
            is_driver = hasattr(request.user, "driver_profile") and request.user.driver_profile == ride_request.driver
            
            if not (is_rider or is_driver):
                return Response({'error': 'Not authorized to view this ride.'}, status=status.HTTP_403_FORBIDDEN)
                
            serializer = RideRequestSerializer(ride_request, context={'request': request})
            return Response(serializer.data)
        except RideRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Update a specific ride request",
        request_body=RideRequestSerializer,
        responses={200: RideRequestSerializer, 400: "Bad Request", 404: "Not Found"}
    )
    def put(self, request, pk):
        try:
            ride_request = RideRequest.objects.get(pk=pk)
            serializer = RideRequestSerializer(ride_request, data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except RideRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    @swagger_auto_schema(
        operation_description="Delete a specific ride request",
        responses={204: "No Content", 404: "Not Found"}
    )
    def delete(self, request, pk):
        try:
            ride_request = RideRequest.objects.get(pk=pk)
            ride_request.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except RideRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

# Actions like accept and reject
class RideRequestActionView(APIView):
    permission_classes = [IsActiveDriver]

    @swagger_auto_schema(
        operation_description="Perform an action on a ride request (accept, reject, arrive, start_trip, complete, cancel)",
        manual_parameters=[
            openapi.Parameter('action', openapi.IN_PATH, description="Action to perform", type=openapi.TYPE_STRING)
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'otp': openapi.Schema(type=openapi.TYPE_STRING, description="Required only for start_trip action")
            }
        ),
        responses={200: "Success", 400: "Bad Request", 404: "Not Found"}
    )
    def post(self, request, pk, action):
        try:
            ride_request = RideRequest.objects.get(pk=pk, driver=request.user.driver_profile)
        except RideRequest.DoesNotExist:
            return Response({'error': 'Ride request not found or you are not the assigned driver.'}, status=status.HTTP_404_NOT_FOUND)
        
        valid_actions = ['accept', 'reject', 'arrive', 'start_trip', 'complete', 'cancel']
        if action not in valid_actions:
            return Response({'error': f'Invalid action. Valid actions are: {", ".join(valid_actions)}'}, status=status.HTTP_400_BAD_REQUEST)

        if action in ['accept', 'reject'] and ride_request.status != 'pending':
            return Response({'error': f'Cannot {action} a ride that is currently {ride_request.status}.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if action == 'arrive' and ride_request.status != 'accepted':
            return Response({'error': 'Cannot arrive for a ride that has not been accepted.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if action == 'start_trip' and ride_request.status != 'arrived':
            return Response({'error': 'Cannot start a trip before arriving.'}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'complete' and ride_request.status != 'in_progress':
            return Response({'error': 'Cannot complete a ride that has not started.'}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'accept':
            ride_request.status = 'accepted'
        elif action == 'reject':
            ride_request.status = 'rejected'
        elif action == 'arrive':
            ride_request.status = 'arrived'
        elif action == 'start_trip':
            provided_otp = request.data.get('otp')
            if not provided_otp or provided_otp != ride_request.ride_otp:
                return Response({'error': 'Invalid OTP.'}, status=status.HTTP_400_BAD_REQUEST)
            ride_request.status = 'in_progress'
        elif action == 'complete':
            ride_request.status = 'completed'
            
            # --- Prepaid Commission Wallet Deduction ---
            driver_profile = ride_request.driver
            if ride_request.service_charge:
                 driver_profile.wallet_balance -= ride_request.service_charge
                 driver_profile.save()
                 
        elif action == 'cancel':
            ride_request.status = 'cancelled'

        ride_request.save()

        serializer = RideRequestSerializer(ride_request, context={'request': request})
        return Response({
            'message': f'Ride request {action}ed successfully.',
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class RateRideView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Rate a completed ride",
        request_body=RideRatingSerializer,
        responses={200: "Rating submitted successfully.", 400: "Bad Request", 404: "Not Found"}
    )
    def post(self, request, pk):
        try:
            ride = RideRequest.objects.get(pk=pk, rider=request.user)
        except RideRequest.DoesNotExist:
            return Response({"error": "Ride not found or unauthorized."}, status=status.HTTP_404_NOT_FOUND)

        if ride.status != 'completed':
            return Response({"error": "Only completed rides can be rated."}, status=status.HTTP_400_BAD_REQUEST)

        if ride.rating is not None:
            return Response({"error": "This ride has already been rated."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RideRatingSerializer(data=request.data)
        if serializer.is_valid():
            ride.rating = serializer.validated_data['rating']
            ride.feedback = serializer.validated_data.get('feedback', '')
            ride.save()

            # Update Driver's Average Rating
            driver_profile = ride.driver
            # Recalculate average based on all completed, rated rides
            stats = RideRequest.objects.filter(
                driver=driver_profile, 
                rating__isnull=False
            ).aggregate(
                avg_rating=Avg('rating'), 
                count=Count('rating')
            )
            
            driver_profile.average_rating = round(stats['avg_rating'] or 0.0, 1)
            driver_profile.total_ratings = stats['count']
            driver_profile.save()

            return Response({"message": "Rating submitted successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
