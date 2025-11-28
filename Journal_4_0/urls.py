from django.conf.urls.static import static
from django.contrib import admin
from django.core.asgi import get_asgi_application
from django.conf import settings
from django.urls import path, include
from erp_main.views import custom_login, index



urlpatterns = [
    path('', index, name='index'),
    path('admin/', admin.site.urls),
    path('erp_main/', include('erp_main.urls')),
    path('login/', custom_login, name='custom_login'),
    path('calculation/', include('calculation.urls')),
    # path('api/erp/', include('erp_main.urls_api')),
    # path('api/calculation/', include('calculation.urls_api')),
    # path('api/auth/', include('rest_framework.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

