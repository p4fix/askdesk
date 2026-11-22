import json
import logging
import queue
from django.http import HttpResponse, StreamingHttpResponse
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .events import event_broadcaster

logger = logging.getLogger(__name__)


def format_sse(data: str, event: str = None) -> str:
    """Formats string content according to the W3C Server-Sent Events specification."""
    msg = f"data: {data}\n\n"
    if event:
        msg = f"event: {event}\n{msg}"
    return msg


class TicketEventStreamView(APIView):
    """
    Real-Time Server-Sent Events (SSE) streaming endpoint for multi-tenant ticket queues.
    Streams ticket updates, customer comments, internal staff notes, and RAG draft events.

    Authentication:
    - Standard 'Authorization: Bearer <token>' header
    - Query parameter '?token=<token>' (supports native browser EventSource)
    """

    permission_classes = [permissions.AllowAny]

    def get_authenticated_user(self, request):
        auth_header = request.headers.get('Authorization', '')
        raw_token = None
        if auth_header.startswith('Bearer '):
            raw_token = auth_header.split(' ')[1].strip()
        elif 'token' in request.GET:
            raw_token = request.GET.get('token')

        if not raw_token:
            return None

        jwt_auth = JWTAuthentication()
        try:
            validated_token = jwt_auth.get_validated_token(raw_token)
            user = jwt_auth.get_user(validated_token)
            if user and user.is_active and user.organization:
                return user
        except (InvalidToken, TokenError, Exception) as exc:
            logger.debug("SSE authentication failed: %s", exc)
            return None
        return None

    def get(self, request, *args, **kwargs):
        user = self.get_authenticated_user(request)
        if not user:
            return HttpResponse(
                "Invalid or missing authentication credentials.",
                status=401,
                content_type="text/plain",
            )

        organization_id = str(user.organization.id)
        subscriber_queue = event_broadcaster.subscribe(organization_id)

        # Optional parameter for automated testing: auto-terminate after N events
        try:
            max_events = int(request.GET.get('limit', 0))
        except (ValueError, TypeError):
            max_events = 0

        # Heartbeat timeout in seconds (shortened for test runs when requested)
        try:
            timeout_sec = float(request.GET.get('timeout', 15.0))
        except (ValueError, TypeError):
            timeout_sec = 15.0

        def event_generator():
            delivered = 0
            try:
                # 1. Emit connection ready confirmation
                ready_payload = json.dumps({
                    'status': 'connected',
                    'organization_id': organization_id,
                    'user': user.email,
                })
                yield format_sse(ready_payload, event='connection.ready')
                delivered += 1
                if max_events > 0 and delivered >= max_events:
                    return

                # 2. Main event loop listening to tenant broadcaster queue
                while True:
                    try:
                        event = subscriber_queue.get(timeout=timeout_sec)
                        event_type = event.get('type', 'message')
                        event_data = json.dumps(event.get('data', {}))
                        yield format_sse(event_data, event=event_type)
                        delivered += 1
                        if max_events > 0 and delivered >= max_events:
                            break
                    except queue.Empty:
                        # 3. Emit keep-alive comment ping to keep socket alive
                        yield ": ping\n\n"
                        if max_events > 0 and delivered >= max_events:
                            break
            finally:
                event_broadcaster.unsubscribe(organization_id, subscriber_queue)

        response = StreamingHttpResponse(
            event_generator(),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache, no-transform'
        response['X-Accel-Buffering'] = 'no'
        return response
