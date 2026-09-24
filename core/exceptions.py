"""
Custom exceptions and exception handling for OYA.
"""
from django.http import JsonResponse


class OYAException(Exception):
    """Base exception for OYA."""
    pass


class ValidationError(OYAException):
    """Validation error."""
    pass


class PermissionDeniedError(OYAException):
    """Permission denied error."""
    pass


class AuthenticationError(OYAException):
    """Authentication error."""
    pass


class DuplicateRecordError(OYAException):
    """Duplicate record error."""
    pass


class DatabaseError(OYAException):
    """Database error."""
    pass


class FileUploadError(OYAException):
    """File upload error."""
    pass


def error_response(message, status_code=400):
    """Return a standardized error response."""
    return JsonResponse({
        "success": False,
        "message": message
    }, status=status_code)


def success_response(data=None, message="Success"):
    """Return a standardized success response."""
    response = {
        "success": True,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return JsonResponse(response)
