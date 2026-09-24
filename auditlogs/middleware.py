"""
Middleware for OYA audit logging.
"""
from .services import log_action, get_client_ip


class AuditLogMiddleware:
    """Middleware to auto-log authentication events."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        pass