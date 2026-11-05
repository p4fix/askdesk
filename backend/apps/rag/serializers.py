from rest_framework import serializers

from apps.rag.models import AIDraftCitation, AIDraftResponse, AIDraftStatus

class AIDraftCitationSerializer(serializers.ModelSerializer):
    chunk_id = serializers.UUIDField(source='chunk.id', read_only=True, allow_null=True)

    class Meta:
        model = AIDraftCitation
        fields = [
            'id',
            'chunk_id',
            'source_title',
            'page_number',
            'relevance_score',
            'cited_excerpt',
        ]
        read_only_fields = fields


class AIDraftResponseSerializer(serializers.ModelSerializer):
    citations = AIDraftCitationSerializer(many=True, read_only=True)
    ticket_id = serializers.UUIDField(read_only=True)
    organization_id = serializers.UUIDField(read_only=True)
    reviewed_by_email = serializers.EmailField(source='reviewed_by.email', read_only=True, allow_null=True)

    class Meta:
        model = AIDraftResponse
        fields = [
            'id',
            'ticket_id',
            'organization_id',
            'suggested_reply',
            'model_name',
            'confidence_score',
            'status',
            'final_edited_reply',
            'reviewed_by_email',
            'citations',
            'created_at',
            'reviewed_at',
        ]
        read_only_fields = fields


class AIDraftReviewSerializer(serializers.Serializer):
    """Payload for human agent review of an AI draft response."""
    action = serializers.ChoiceField(
        choices=['ACCEPT', 'REJECT'],
        help_text="Review decision: 'ACCEPT' dispatches response to ticket; 'REJECT' discards draft."
    )
    edited_reply = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional human edits. If omitted on ACCEPT, the original suggested_reply is accepted."
    )
    is_internal_note = serializers.BooleanField(
        default=False,
        help_text="If True, post the accepted response as an internal private staff note instead of public reply."
    )


class SemanticSearchQuerySerializer(serializers.Serializer):
    """Validation for direct vector retrieval query parameters."""
    query = serializers.CharField(required=True, min_length=1, max_length=500)
    top_k = serializers.IntegerField(required=False, default=3, min_value=1, max_value=20)
    min_similarity = serializers.FloatField(required=False, default=0.0, min_value=0.0, max_value=1.0)


class SemanticSearchResultSerializer(serializers.Serializer):
    """Serialized match result from vector similarity search."""
    chunk_id = serializers.UUIDField(source='chunk.id')
    document_title = serializers.CharField()
    page_number = serializers.IntegerField()
    similarity = serializers.FloatField()
    content = serializers.CharField()
