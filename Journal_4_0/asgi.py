import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import erp_main.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Journal_4_0.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            erp_main.routing.websocket_urlpatterns  # ИЛИ chat.routing.websocket_urlpatterns
        )
    ),
})