from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from .models import VehicleCategory
from .serializers import VehicleCategorySerializer
from rest_framework.response import Response


class AdminVehicleCategoryAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        categories = VehicleCategory.objects.all()
        serializer = VehicleCategorySerializer(categories, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = VehicleCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def put(self, request, pk):
        category = get_object_or_404(VehicleCategory, pk=pk)
        serializer = VehicleCategorySerializer(category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        category = get_object_or_404(VehicleCategory, pk=pk)
        category.delete()
        return Response({"message": "Deleted"}, status=204)