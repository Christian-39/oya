"""
Custom middleware for OYA.
"""
import logging
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin
from .exceptions import (
    OYAException, ValidationError, PermissionDeniedError,
    AuthenticationError, DuplicateRecordError, DatabaseError, FileUploadError
)

logger = logging.getLogger("oya")


class AuditLogMiddleware(MiddlewareMixin):
    """Middleware to capture request data for audit logging."""

    def process_request(self, request):
        """Attach client IP to request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            request.client_ip = x_forwarded_for.split(",")[0].strip()
        else:
            request.client_ip = request.META.get("REMOTE_ADDR", "")
        return None


class ExceptionHandlerMiddleware(MiddlewareMixin):
    """
    Global exception handler middleware.

    Ensures no raw Python traceback or bare error message ever reaches the
    user: API/AJAX requests get a structured JSON error, ordinary page
    requests get the matching branded error template (400/403/404/500),
    while the full exception is always logged server-side either way.
    """

    def process_exception(self, request, exception):
        """Handle custom exceptions and return standardized responses."""
        if isinstance(exception, ValidationError):
            return self._error_response(request, exception, str(exception), 400)
        elif isinstance(exception, PermissionDeniedError):
            return self._error_response(request, exception, str(exception), 403)
        elif isinstance(exception, AuthenticationError):
            return self._error_response(request, exception, str(exception), 401)
        elif isinstance(exception, DuplicateRecordError):
            return self._error_response(request, exception, str(exception), 409)
        elif isinstance(exception, DatabaseError):
            return self._error_response(request, exception, str(exception), 500)
        elif isinstance(exception, FileUploadError):
            return self._error_response(request, exception, str(exception), 400)
        elif isinstance(exception, OYAException):
            return self._error_response(request, exception, str(exception), 400)

        # Anything else is an unexpected/unhandled exception — log it in
        # full for debugging, then let Django's own 500 handling take over
        # (which renders templates/500.html when DEBUG=False). Returning
        # None here is intentional: it hands off to Django rather than
        # duplicating that handling.
        logger.error(f"Unhandled exception: {exception}", exc_info=True)
        return None

    def _error_response(self, request, exception, message, status_code):
        logger.warning(
            f"Handled exception ({status_code}): {message}", exc_info=True
        )
        if self._is_api_request(request):
            return JsonResponse({
                "success": False,
                "message": message
            }, status=status_code)

        template_map = {
            400: "400.html",
            401: "403.html",
            403: "403.html",
            404: "404.html",
            409: "400.html",
        }
        template_name = template_map.get(status_code, "500.html")
        try:
            return render(request, template_name, {"error_message": message}, status=status_code)
        except Exception:
            # If even the error template fails to render, fall back to a
            # bare-minimum response rather than propagating a second,
            # more confusing exception.
            logger.exception("Failed to render error template %s", template_name)
            return JsonResponse({"success": False, "message": message}, status=status_code)

    def _is_api_request(self, request):
        """
        True for AJAX/fetch calls and JSON API endpoints — these should
        get a structured JSON error, not an HTML page.
        """
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return True
        accepts = request.headers.get("Accept", "")
        if "application/json" in accepts and "text/html" not in accepts:
            return True
        if request.path.startswith("/api/") or "/api/" in request.path:
            return True
        return False
