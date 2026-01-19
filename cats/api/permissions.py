from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Only allow owners of an object to view it. Admins can view all.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user == request.user