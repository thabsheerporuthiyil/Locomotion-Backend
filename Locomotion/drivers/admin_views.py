from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from .models import DriverApplication,DriverProfile,DriverApplicationReview, DriverVehicle
from .serializers import DriverApplicationSerializer,DriverVehicleSerializer


class AdminDriverApplicationListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        applications = DriverApplication.objects.all().order_by("-submitted_at")
        serializer = DriverApplicationSerializer(
            applications,
            many=True,
            context={"request": request}
        )
        return Response(serializer.data)


class AdminDriverApplicationActionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            application = DriverApplication.objects.get(pk=pk)
        except DriverApplication.DoesNotExist:
            return Response({"error": "Application not found"}, status=404)

        action = request.data.get("action")

        if action not in ["approve", "reject"]:
            return Response({"error": "Invalid action"}, status=400)

        reason = request.data.get("reason")

        if action == "reject" and not reason:
            return Response(
                {"error": "Rejection reason required"},
                status=400
            )

        application.status = "approved" if action == "approve" else "rejected"
        application.save()

        DriverApplicationReview.objects.create(
            application=application,
            status=application.status,
            reason=reason if action == "reject" else None,
            reviewed_by=request.user
        )

        if action == "approve":
            driver_profile, created = DriverProfile.objects.get_or_create(
                user=application.user,
                defaults={
                    "phone_number": application.phone_number,
                    "experience_years": application.experience_years,
                    "service_type": application.service_type,
                    "vehicle_model": application.vehicle_model,
                    "vehicle_registration_number": application.vehicle_registration_number,
                    "panchayath": application.panchayath,
                    "profile_image":application.profile_image, 
                }
            )

            # Create DriverVehicle if applicable
            if application.service_type == "driver_with_vehicle":
                DriverVehicle.objects.create(
                    driver=driver_profile,
                    vehicle_category=application.vehicle_category,
                    vehicle_model=application.vehicle_model,
                    registration_number=application.vehicle_registration_number,
                    vehicle_image=application.vehicle_image,
                    rc_document=application.rc_document,
                    insurance_document=application.insurance_document,
                    status="approved",
                    is_primary=True,
                    is_active=True
                )

        return Response({"message": f"Application {application.status}"})



class AdminVehicleListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        vehicles = DriverVehicle.objects.all().order_by("-created_at")
        serializer = DriverVehicleSerializer(
            vehicles, 
            many=True, 
            context={"request": request}
        )
        return Response(serializer.data)



class AdminVehicleActionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            vehicle = DriverVehicle.objects.get(pk=pk)
        except DriverVehicle.DoesNotExist:
             return Response({"error": "Vehicle not found"}, status=404)
        
        action = request.data.get("action")
        if action not in ["approve", "reject"]:
             return Response({"error": "Invalid action"}, status=400)
        
        vehicle.status = "approved" if action == "approve" else "rejected"
        vehicle.is_active = True if action == "approve" else False
        
        if action == "approve":
            if vehicle.driver.service_type == "driver_only":
                vehicle.driver.service_type = "driver_with_vehicle"
                vehicle.driver.save()

            current_primary = DriverVehicle.objects.filter(driver=vehicle.driver, is_primary=True).exists()
            if not current_primary:
                vehicle.is_primary = True

        vehicle.save()
        
        return Response({"message": f"Vehicle {vehicle.status}"})