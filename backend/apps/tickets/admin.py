from django.contrib import admin
from .models import Ticket, TicketComment

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'priority', 'organization', 'assigned_to', 'created_by', 'created_at')
    list_filter = ('status', 'priority', 'organization')
    search_fields = ('title', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'author', 'is_internal_note', 'created_at')
    list_filter = ('is_internal_note', 'created_at')
    search_fields = ('body', 'author__email')
    readonly_fields = ('id', 'created_at')
    ordering = ('created_at',)

