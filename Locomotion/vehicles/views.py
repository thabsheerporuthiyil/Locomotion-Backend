from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import VehicleCategory,VehicleBrand,VehicleModel
from .serializers import VehicleCategorySerializer,VehicleBrandSerializer,VehicleModelSerializer


class VehicleCategoryListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = VehicleCategory.objects.all()
        serializer = VehicleCategorySerializer(categories, many=True)
        return Response(serializer.data)
    
class VehicleBrandListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        category_id = request.query_params.get("category")
        brands = VehicleBrand.objects.all()

        if category_id:
            brands = brands.filter(category_id=category_id)

        serializer = VehicleBrandSerializer(brands, many=True)
        return Response(serializer.data)
    

class VehicleModelListAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        brand_id = request.query_params.get("brand")
        models = VehicleModel.objects.all()

        if brand_id:
            models = models.filter(brand_id=brand_id)

        serializer = VehicleModelSerializer(models, many=True)
        return Response(serializer.data)