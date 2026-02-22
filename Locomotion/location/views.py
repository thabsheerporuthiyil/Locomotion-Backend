from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from .models import District, Taluk, Panchayath
from .serializers import (
    DistrictSerializer,
    TalukSerializer,
    PanchayathSerializer
)


class DistrictListView(ListAPIView):
    queryset = District.objects.all()
    serializer_class = DistrictSerializer


class TalukListView(ListAPIView):
    serializer_class = TalukSerializer

    def get_queryset(self):
        district = self.request.query_params.get("district")
        return Taluk.objects.filter(district_id=district)


class PanchayathListView(ListAPIView):
    serializer_class = PanchayathSerializer

    def get_queryset(self):
        taluk = self.request.query_params.get("taluk")
        return Panchayath.objects.filter(taluk_id=taluk)