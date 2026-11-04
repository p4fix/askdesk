import uuid
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.authentication.models import Organization, User

class TicketStatus(models.TextChoices):
    OPEN = 'OPEN', _('Open')
    IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
    RESOLVED = 'RESOLVED', _('Resolved')
    CLOSED = 'CLOSED', _('Closed')


class TicketPriority(models.TextChoices):
    LOW = 'LOW', _('Low')
    MEDIUM = 'MEDIUM', _('Medium')
    HIGH = 'HIGH', _('High')
    URGENT = 'URGENT', _('Urgent')


class Ticket(models.Model):
    """
    Core support ticket entity scoped to an organization tenant.
    Maintains ticket state machine (status, priority) and agent assignment.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='tickets',
        db_index=True,
        help_text="Tenant organization that owns this ticket."
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tickets',
        help_text="Agent or user who submitted the ticket."
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        help_text="Support agent actively handling this ticket."
    )
    title = models.CharField(max_length=255, help_text="Summary of the customer issue.")
    description = models.TextField(help_text="Detailed problem description or customer message.")
    status = models.CharField(
        max_length=20,
        choices=TicketStatus.choices,
        default=TicketStatus.OPEN,
        db_index=True
    )
    priority = models.CharField(
        max_length=20,
        choices=TicketPriority.choices,
        default=TicketPriority.MEDIUM,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tickets'
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        # Security invariant: Assignee must belong to the exact same organization
        if self.assigned_to and self.assigned_to.organization_id != self.organization_id:
            raise ValidationError({
                'assigned_to': _('Assignee must belong to the same organization as the ticket.')
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.status}] {self.title}"


class TicketComment(models.Model):
    """
    Threaded conversation entry or internal private note on a ticket.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='comments',
        db_index=True
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ticket_comments'
    )
    body = models.TextField(help_text="Message content of the comment or note.")
    is_internal_note = models.BooleanField(
        default=False,
        help_text="If True, visible only to support agents and admins, not customers."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ticket_comments'
        ordering = ['created_at']

    def __str__(self):
        note_type = "Internal Note" if self.is_internal_note else "Reply"
        return f"{note_type} by {self.author.email} on {self.ticket_id}"

