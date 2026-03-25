from fastapi import HTTPException, status


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        super().__init__(status_code=status_code, detail={"code": code, "message": message, "details": details or {}})


def unauthorized(message: str = "Authentication failed") -> ApiError:
    return ApiError(status_code=status.HTTP_401_UNAUTHORIZED, code="AUTHENTICATION_FAILED", message=message)


def forbidden(message: str = "Forbidden") -> ApiError:
    return ApiError(status_code=status.HTTP_403_FORBIDDEN, code="FORBIDDEN", message=message)


def conflict(code: str, message: str, details: dict | None = None) -> ApiError:
    return ApiError(status_code=status.HTTP_409_CONFLICT, code=code, message=message, details=details)


def validation_error(message: str, details: dict | None = None) -> ApiError:
    return ApiError(status_code=status.HTTP_400_BAD_REQUEST, code="VALIDATION_ERROR", message=message, details=details)


def not_found(message: str = "Not found", details: dict | None = None) -> ApiError:
    return ApiError(status_code=status.HTTP_404_NOT_FOUND, code="NOT_FOUND", message=message, details=details)


def payload_too_large(message: str, details: dict | None = None) -> ApiError:
    return ApiError(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, code="PAYLOAD_TOO_LARGE", message=message, details=details)
