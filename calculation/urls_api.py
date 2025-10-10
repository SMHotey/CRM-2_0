from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import *

router = DefaultRouter()
router.register(r'standard-prices', StandardPriceViewSet)
router.register(r'personal-prices', PersonalPriceViewSet)
router.register(r'calculations', CalculationViewSet)
router.register(r'calculation-items', CalculationItemViewSet)
router.register(r'cp', CPViewSet)
router.register(r'cp-items', CPitemViewSet)

urlpatterns = [
    path('', include(router.urls)),
]