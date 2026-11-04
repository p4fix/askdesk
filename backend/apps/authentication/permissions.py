from rest_framework import permissions
from .models import UserRole

class IsOrgMember(permissions.BasePermission):
    """
    Allows access only to authenticated users who belong to an active organization.
    """
    message = "You must be an authenticated member of an organization to access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.organization is not None
        )


class IsOrgAdmin(permissions.BasePermission):
    """
    Allows access only to Organization Admins or Superusers.
    Used for administrative actions such as uploading knowledge base documents
    and managing support agents.
    """
    message = "Only organization administrators can perform this action."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.is_superuser:
            return True
        return bool(
            request.user.organization is not None and
            request.user.role == UserRole.ADMIN
        )

