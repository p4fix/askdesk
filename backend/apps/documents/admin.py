from django.contrib import admin
from .models import Document, DocumentChunk

class DocumentChunkInline(admin.TabularInline):
    model = DocumentChunk
    extra = 0
    fields = ('chunk_index', 'token_count', 'content', 'created_at')
    readonly_fields = ('chunk_index', 'token_count', 'content', 'created_at')
    can_delete = False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'file_type', 'status', 'organization', 'file_size_bytes', 'uploaded_by', 'created_at')
    list_filter = ('status', 'file_type', 'organization')
    search_fields = ('title', 'error_message')
    readonly_fields = ('id', 'file_size_bytes', 'created_at', 'updated_at')
    inlines = [DocumentChunkInline]
    ordering = ('-created_at',)


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ('document', 'chunk_index', 'token_count', 'organization', 'created_at')
    list_filter = ('organization',)
    search_fields = ('content', 'document__title')
    readonly_fields = ('id', 'created_at')
    ordering = ('document', 'chunk_index')

