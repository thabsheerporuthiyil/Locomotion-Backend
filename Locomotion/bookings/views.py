import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from .models import RideRequest
from .serializers import RideRequestSerializer, RideRequestCreateSerializer


class CalculateFareView(APIView):
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
                        'duration_min': round(duration_min, 0), # Round to nearest whole minute for realism
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

# View stubs to prevent Django ImportErrors from missing views.py during previous interrupted feature
class CreateRideRequestView(APIView):
    from rest_framework.permissions import IsAuthenticated
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        
        # Validate that a phone number exists
        provided_phone = request.data.get('rider_phone_number')
        if not user.phone_number and not provided_phone:
            return Response(
                {"error": "A valid mobile number is required to book a ride."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = RideRequestCreateSerializer(data=request.data)
        if serializer.is_valid():
            # If the user doesn't have a phone number, extract it from the ride payload and save it permanently
            if not user.phone_number and provided_phone:
                user.phone_number = provided_phone
                user.save()

            serializer.save(rider=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DriverRideRequestListView(APIView):
    def get(self, request):
        queryset = RideRequest.objects.none()
        serializer = RideRequestSerializer(queryset, many=True)
        return Response(serializer.data)

class RiderRideRequestListView(APIView):
    def get(self, request):
        queryset = RideRequest.objects.none()
        serializer = RideRequestSerializer(queryset, many=True)
        return Response(serializer.data)

class RideRequestDetailView(APIView):
    def get(self, request, pk):
        try:
            ride_request = RideRequest.objects.get(pk=pk)
            serializer = RideRequestSerializer(ride_request)
            return Response(serializer.data)
        except RideRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        try:
            ride_request = RideRequest.objects.get(pk=pk)
            serializer = RideRequestSerializer(ride_request, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except RideRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        try:
            ride_request = RideRequest.objects.get(pk=pk)
            ride_request.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except RideRequest.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

class RideRequestActionView(APIView):
    def post(self, request, pk, action):
        return Response({'status': 'Dummy action response'}, status=status.HTTP_200_OK)
