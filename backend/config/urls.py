from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.db import connection
from django.urls import path, include
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """
    Production healthcheck probe for Docker Compose, Kubernetes liveness/readiness,
    and load balancer health checks.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        health_status = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'version': '1.0.0',
            'services': {
                'database': {'status': 'unknown', 'vendor': connection.vendor},
            }
        }

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
            health_status['services']['database']['status'] = 'connected'
        except Exception as exc:
            health_status['status'] = 'unhealthy'
            health_status['services']['database']['status'] = 'error'
            health_status['services']['database']['error'] = str(exc)
            return Response(health_status, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(health_status, status=status.HTTP_200_OK)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', HealthCheckView.as_view(), name='health-check-root'),
    path('api/v1/health/', HealthCheckView.as_view(), name='health-check'),
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/v1/tickets/', include('apps.tickets.urls')),
    path('api/v1/documents/', include('apps.documents.urls')),
    path('api/v1/rag/', include('apps.rag.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
