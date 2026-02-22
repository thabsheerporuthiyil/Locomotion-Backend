from rest_framework import serializers
from .models import RideRequest
from drivers.serializers import DriverListSerializer

class RideRequestSerializer(serializers.ModelSerializer):
    rider_name = serializers.CharField(source="rider.name", read_only=True)
    rider_phone = serializers.CharField(source="rider.phone_number", read_only=True) # Assuming User has phone_number or similar
    
    driver_name = serializers.CharField(source="driver.user.name", read_only=True)
    driver_phone = serializers.SerializerMethodField()
    
    class Meta:
        model = RideRequest
        fields = [
            "id",
            "rider",
            "rider_name",
            "rider_phone",
            "driver",
            "driver_name",
            "driver_phone",
            "source_location",
            "source_lat",
            "source_lng",
            "destination_location",
            "destination_lat",
            "destination_lng",
            "vehicle_details",
            "distance_km",
            "estimated_fare",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "rider", "status", "created_at", "updated_at"]

    def get_driver_phone(self, obj):
        # Only reveal phone number if status is accepted
        if obj.status == "accepted":
            return obj.driver.phone_number
        return None

class RideRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideRequest
        fields = [
            "driver",
            "source_location",
            "source_lat",
            "source_lng",
            "destination_location",
            "destination_lat",
            "destination_lng",
            "vehicle_details",
            "distance_km",
            "estimated_fare",
        ]

    def validate(self, data):
        required_fields = {
            'source_lat': 'Pickup location',
            'source_lng': 'Pickup location',
            'destination_lat': 'Drop-off location',
            'destination_lng': 'Drop-off location',
            'distance_km': 'Calculated distance',
            'estimated_fare': 'Estimated fare',
        }
        
        for field, name in required_fields.items():
            if data.get(field) is None:
                raise serializers.ValidationError({"error": f"Please calculate the fare before confirming. {name} is missing."})
        
        if data.get('estimated_fare', 0) <= 0:
            raise serializers.ValidationError({"error": "Invalid estimated fare."})
            
        return data


