"""
Custom permissions for OYA.
"""
from django.core.exceptions import PermissionDenied


class RolePermissionMixin:
    """Mixin to check user roles."""

    def check_admin(self):
        """Check if user is admin."""
        if not self.request.user.has_admin_access():
            raise PermissionDenied("Admin access required.")

    def check_executive(self):
        """Check if user is executive or admin."""
        if not self.request.user.has_executive_access():
            raise PermissionDenied("Executive access required.")

    def check_floor_member(self):
        """Check if user is at least a floor member (any authenticated user)."""
        if not self.request.user.is_authenticated:
            raise PermissionDenied("Authentication required.")


class AdminRequiredMixin:
    """Mixin requiring admin role."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_admin_access():
            raise PermissionDenied("Admin access required.")
        return super().dispatch(request, *args, **kwargs)


class ExecutiveRequiredMixin:
    """Mixin requiring executive or admin role."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.has_executive_access():
            raise PermissionDenied("Executive access required.")
        return super().dispatch(request, *args, **kwargs)


class FloorMemberRequiredMixin:
    """Mixin requiring any authenticated user."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required.")
        return super().dispatch(request, *args, **kwargs)
