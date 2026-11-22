import json
import logging
import queue
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TenantEventBroadcaster:
    """
    Thread-safe in-memory pub/sub event broadcaster for Server-Sent Events (SSE).
    Subscribers are partitioned strictly by organization tenant ID, guaranteeing zero
    cross-tenant event leakage.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Mapping from org_id (str) to list of subscriber queues
        self._subscribers: Dict[str, List[queue.Queue]] = {}

    def subscribe(self, organization_id: str) -> queue.Queue:
        """Registers a new subscriber queue for an organization tenant."""
        q = queue.Queue(maxsize=100)
        org_id_str = str(organization_id)
        with self._lock:
            if org_id_str not in self._subscribers:
                self._subscribers[org_id_str] = []
            self._subscribers[org_id_str].append(q)
        return q

    def unsubscribe(self, organization_id: str, q: queue.Queue) -> None:
        """Removes a subscriber queue when an SSE client disconnects."""
        org_id_str = str(organization_id)
        with self._lock:
            if org_id_str in self._subscribers:
                try:
                    self._subscribers[org_id_str].remove(q)
                except ValueError:
                    pass
                if not self._subscribers[org_id_str]:
                    del self._subscribers[org_id_str]

    def broadcast(self, organization_id: str, event_type: str, data: Dict[str, Any]) -> int:
        """
        Dispatches an event payload exclusively to active subscribers
        belonging to the specified organization tenant.
        Returns the number of subscribers notified.
        """
        org_id_str = str(organization_id)
        payload = {
            'type': event_type,
            'data': data,
        }
        notified = 0
        with self._lock:
            queues = list(self._subscribers.get(org_id_str, []))

        for q in queues:
            try:
                q.put_nowait(payload)
                notified += 1
            except queue.Full:
                logger.warning(
                    "Subscriber queue full for org %s; dropping event %s",
                    org_id_str,
                    event_type,
                )

        return notified

    def active_subscribers_count(self, organization_id: Optional[str] = None) -> int:
        """Returns the number of active subscriber connections."""
        with self._lock:
            if organization_id:
                return len(self._subscribers.get(str(organization_id), []))
            return sum(len(q_list) for q_list in self._subscribers.values())


# Singleton instance shared across the Django application process
event_broadcaster = TenantEventBroadcaster()
