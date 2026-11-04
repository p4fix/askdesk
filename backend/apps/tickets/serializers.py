from rest_framework import serializers

from apps.authentication.models import User
from apps.tickets.models import Ticket, TicketComment, TicketPriority, TicketStatus

class TicketUserSummarySerializer(serializers.ModelSerializer):
    """Minimal representation of a user for ticket assignments and comment authorship."""
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'role']
        read_only_fields = fields


class TicketCommentSerializer(serializers.ModelSerializer):
    """Serializer for ticket comment / discussion thread entries."""
    author = TicketUserSummarySerializer(read_only=True)
    ticket = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = TicketComment
        fields = [
            'id',
            'ticket',
            'author',
            'body',
            'is_internal_note',
            'created_at',
        ]
        read_only_fields = ['id', 'ticket', 'author', 'created_at']

    def validate_body(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Comment body cannot be blank.")
        return stripped

    def create(self, validated_data):
        request = self.context['request']
        ticket = self.context['ticket']
        return TicketComment.objects.create(
            ticket=ticket,
            author=request.user,
            **validated_data
        )


class TicketListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for paginated ticket queues and search results."""
    created_by = TicketUserSummarySerializer(read_only=True)
    assigned_to = TicketUserSummarySerializer(read_only=True)
    comments_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Ticket
        fields = [
            'id',
            'title',
            'status',
            'priority',
            'created_by',
            'assigned_to',
            'comments_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class TicketDetailSerializer(serializers.ModelSerializer):
    """Full ticket representation including description and threaded conversation history."""
    created_by = TicketUserSummarySerializer(read_only=True)
    assigned_to = TicketUserSummarySerializer(read_only=True)
    comments = TicketCommentSerializer(many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            'id',
            'title',
            'description',
            'status',
            'priority',
            'created_by',
            'assigned_to',
            'comments',
            'comments_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_comments_count(self, obj):
        if hasattr(obj, 'comments_count'):
            return obj.comments_count
        return obj.comments.count()


class TicketCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating tickets with strict tenant boundary enforcement."""
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.none(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Ticket
        fields = [
            'id',
            'title',
            'description',
            'priority',
            'assigned_to',
            'status',
            'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically scope allowed assignees strictly to members of the requesting user's organization
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.organization:
            self.fields['assigned_to'].queryset = User.objects.filter(
                organization=request.user.organization,
                is_active=True
            )

    def validate_title(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Title cannot be empty.")
        return stripped

    def validate_description(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Description cannot be empty.")
        return stripped

    def validate_assigned_to(self, value):
        if value is None:
            return None
        request = self.context.get('request')
        if request and request.user.organization_id != value.organization_id:
            raise serializers.ValidationError("Cannot assign a ticket to an agent outside your organization.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        validated_data['organization'] = request.user.organization
        validated_data['created_by'] = request.user
        return super().create(validated_data)


class TicketUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating ticket status, priority, description, or assigned agent."""
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.none(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Ticket
        fields = [
            'title',
            'description',
            'status',
            'priority',
            'assigned_to',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.organization:
            self.fields['assigned_to'].queryset = User.objects.filter(
                organization=request.user.organization,
                is_active=True
            )

    def validate_assigned_to(self, value):
        if value is None:
            return None
        request = self.context.get('request')
        if request and request.user.organization_id != value.organization_id:
            raise serializers.ValidationError("Cannot assign a ticket to an agent outside your organization.")
        return value

