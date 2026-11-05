import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.authentication.models import Organization, User
from apps.documents.models import DocumentChunk
from apps.tickets.models import Ticket

class AIDraftStatus(models.TextChoices):
    DRAFT_GENERATED = 'DRAFT_GENERATED', _('Draft Generated')
    REVIEWED = 'REVIEWED', _('Reviewed')
    ACCEPTED = 'ACCEPTED', _('Accepted')
    REJECTED = 'REJECTED', _('Rejected')


class AIDraftResponse(models.Model):
    """
    AI-generated response draft for a customer support ticket.
    Maintains a strict human-in-the-loop lifecycle:
    Draft Generated -> Agent Review (Edit/Approve) -> Ticket Comment Dispatch.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='ai_drafts',
        db_index=True,
        help_text="Support ticket this draft was synthesized for."
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='ai_drafts',
        db_index=True,
        help_text="Tenant organization boundary."
    )
    suggested_reply = models.TextField(
        help_text="Grounded reply drafted by the RAG LLM engine."
    )
    model_name = models.CharField(
        max_length=100,
        default='gpt-4o-mini',
        help_text="Name and version of the LLM model that generated this draft."
    )
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Relevance/confidence score (0.0 - 1.0) based on top retrieved chunk similarity."
    )
    status = models.CharField(
        max_length=30,
        choices=AIDraftStatus.choices,
        default=AIDraftStatus.DRAFT_GENERATED,
        db_index=True,
        help_text="Current review status of this AI suggestion."
    )
    final_edited_reply = models.TextField(
        null=True,
        blank=True,
        help_text="Final text approved or edited by the human support agent."
    )
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_ai_drafts',
        help_text="Support agent who reviewed, edited, or approved this draft."
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ai_draft_responses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket', 'status']),
            models.Index(fields=['organization', '-created_at']),
        ]

    def __str__(self):
        return f"AI Draft [{self.status}] for Ticket #{self.ticket_id} ({self.model_name})"


class AIDraftCitation(models.Model):
    """
    Structured document source citation verifying factual grounding of an AI draft response.
    Enables support agents to trace exact document origin, page number, and text excerpt.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    draft_response = models.ForeignKey(
        AIDraftResponse,
        on_delete=models.CASCADE,
        related_name='citations',
        db_index=True
    )
    chunk = models.ForeignKey(
        DocumentChunk,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citations',
        help_text="Underlying vector chunk cited (if still present in knowledge base)."
    )
    relevance_score = models.FloatField(
        default=0.0,
        help_text="Cosine similarity score (0.0 to 1.0) between query and chunk."
    )
    cited_excerpt = models.TextField(
        help_text="Verbatim excerpt from the knowledge base chunk referenced by the draft."
    )
    source_title = models.CharField(
        max_length=255,
        help_text="Title of the source document at time of citation."
    )
    page_number = models.PositiveIntegerField(
        default=1,
        help_text="Source document page number."
    )

    class Meta:
        db_table = 'ai_draft_citations'
        ordering = ['-relevance_score']

    def __str__(self):
        return f"Citation from '{self.source_title}' (Page {self.page_number}, Score: {self.relevance_score:.2f})"
