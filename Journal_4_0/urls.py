from django.conf.urls.static import static
from django.contrib import admin
from django.core.asgi import get_asgi_application
from django.urls import path, include
from erp_main.views import custom_login, index
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import erp_main.routing


urlpatterns = [
    path('', index, name='index'),
    path('admin/', admin.site.urls),
    path('erp_main/', include('erp_main.urls')),
    path('custom-login/', custom_login, name='custom_login'),
    path('calculation/', include('calculation.urls')),
    path('api/erp/', include('erp_main.urls_api')),
    path('api/calculation/', include('calculation.urls_api')),
    path('api/auth/', include('rest_framework.urls')),
]

# WebSocket routing
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            erp_main.routing.websocket_urlpatterns
        )
    ),
})