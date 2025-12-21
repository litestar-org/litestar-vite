"""Tests for Precognition support (real-time form validation)."""

from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from litestar import Request
from litestar.exceptions import ValidationException
from litestar.status_codes import HTTP_204_NO_CONTENT, HTTP_422_UNPROCESSABLE_ENTITY
from litestar.types import HTTPScope

from litestar_vite.inertia import InertiaHeaders
from litestar_vite.inertia.precognition import (
    PrecognitionResponse,
    create_precognition_exception_handler,
    normalize_validation_errors,
    precognition,
)
from litestar_vite.inertia.request import InertiaDetails, InertiaRequest

# =====================================================
# normalize_validation_errors() Tests
# =====================================================


def test_normalize_validation_errors_list_format() -> None:
    """Test normalizing Litestar's list-based error format."""
    exc = ValidationException(
        detail=[
            {"key": "email", "message": "Email is required.", "source": "body"},
            {"key": "password", "message": "Password must be at least 8 characters.", "source": "body"},
        ]  # type: ignore[arg-type]
    )

    result = normalize_validation_errors(exc)

    assert result["message"] == "The given data was invalid."
    assert "email" in result["errors"]
    assert result["errors"]["email"] == ["Email is required."]
    assert "password" in result["errors"]
    assert result["errors"]["password"] == ["Password must be at least 8 characters."]


def test_normalize_validation_errors_string_format() -> None:
    """Test normalizing string error detail."""
    exc = ValidationException(detail="Something went wrong.")

    result = normalize_validation_errors(exc)

    assert result["message"] == "The given data was invalid."
    assert "_root" in result["errors"]
    assert result["errors"]["_root"] == ["Something went wrong."]


def test_normalize_validation_errors_multiple_errors_same_field() -> None:
    """Test multiple errors for the same field are grouped."""
    exc = ValidationException(
        detail=[
            {"key": "password", "message": "Password is required.", "source": "body"},
            {"key": "password", "message": "Password must be at least 8 characters.", "source": "body"},
        ]  # type: ignore[arg-type]
    )

    result = normalize_validation_errors(exc)

    assert len(result["errors"]["password"]) == 2
    assert "Password is required." in result["errors"]["password"]
    assert "Password must be at least 8 characters." in result["errors"]["password"]


def test_normalize_validation_errors_with_source_prefix() -> None:
    """Test errors from non-body sources get source prefix."""
    exc = ValidationException(
        detail=[
            {"key": "id", "message": "ID must be a number.", "source": "path"},
            {"key": "page", "message": "Page must be positive.", "source": "query"},
        ]  # type: ignore[arg-type]
    )

    result = normalize_validation_errors(exc)

    # Non-body sources get prefixed
    assert "path.id" in result["errors"]
    assert "query.page" in result["errors"]


def test_normalize_validation_errors_validate_only_filter() -> None:
    """Test validate_only filters errors to specified fields."""
    exc = ValidationException(
        detail=[
            {"key": "email", "message": "Email is required.", "source": "body"},
            {"key": "password", "message": "Password is required.", "source": "body"},
            {"key": "name", "message": "Name is required.", "source": "body"},
        ]  # type: ignore[arg-type]
    )

    result = normalize_validation_errors(exc, validate_only={"email", "name"})

    # Only specified fields should be included
    assert "email" in result["errors"]
    assert "name" in result["errors"]
    assert "password" not in result["errors"]


def test_normalize_validation_errors_empty_list_detail() -> None:
    """Test handling empty list error detail (uses fallback)."""
    exc = ValidationException(detail=[])  # type: ignore[arg-type]

    result = normalize_validation_errors(exc)

    # Empty list detail doesn't match string check, so errors dict stays empty
    # Note: ValidationException may have a default detail message
    assert "errors" in result
    assert isinstance(result["errors"], dict)


def test_normalize_validation_errors_missing_key() -> None:
    """Test handling error dict without key."""
    exc = ValidationException(
        detail=[{"message": "Something went wrong.", "source": "body"}]  # type: ignore[arg-type]
    )

    result = normalize_validation_errors(exc)

    # Should use _root as fallback
    assert "_root" in result["errors"]


# =====================================================
# PrecognitionResponse Tests
# =====================================================


def test_precognition_response_status_code() -> None:
    """Test PrecognitionResponse returns 204 No Content."""
    response = PrecognitionResponse()
    assert response.status_code == HTTP_204_NO_CONTENT


def test_precognition_response_success_header() -> None:
    """Test PrecognitionResponse includes Precognition-Success header."""
    response = PrecognitionResponse()
    assert response.headers.get("Precognition-Success") == "true"


def test_precognition_response_no_content() -> None:
    """Test PrecognitionResponse has no content."""
    response = PrecognitionResponse()
    # 204 responses have no body by design
    assert response.status_code == HTTP_204_NO_CONTENT


# =====================================================
# create_precognition_exception_handler() Tests
# =====================================================


def test_exception_handler_precognition_request() -> None:
    """Test handler returns Laravel-format errors for Precognition requests."""
    handler = create_precognition_exception_handler()

    # Create mock request with Precognition header
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"precognition": "true"}

    exc = ValidationException(
        detail=[{"key": "email", "message": "Email is required.", "source": "body"}]  # type: ignore[arg-type]
    )

    response = handler(mock_request, exc)

    assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY
    # Check the response has Precognition header
    assert response.headers.get("Precognition") == "true"


def test_exception_handler_non_precognition_request() -> None:
    """Test handler returns default format for non-Precognition requests."""
    handler = create_precognition_exception_handler()

    # Create mock request without Precognition header
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {}

    exc = ValidationException(detail="Validation failed")

    response = handler(mock_request, exc)

    assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY
    # Should not have Precognition header
    assert response.headers.get("Precognition") is None


def test_exception_handler_validate_only_filtering() -> None:
    """Test handler respects Precognition-Validate-Only header."""
    handler = create_precognition_exception_handler()

    # Create mock request with Precognition and Validate-Only headers
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"precognition": "true", "precognition-validate-only": "email,name"}

    exc = ValidationException(
        detail=[
            {"key": "email", "message": "Email is required.", "source": "body"},
            {"key": "password", "message": "Password is required.", "source": "body"},
            {"key": "name", "message": "Name is required.", "source": "body"},
        ]  # type: ignore[arg-type]
    )

    response = handler(mock_request, exc)

    # Response should only contain email and name errors
    # (We can't easily check the body content due to Response encoding)
    assert response.status_code == HTTP_422_UNPROCESSABLE_ENTITY


def test_exception_handler_with_fallback() -> None:
    """Test handler uses fallback for non-Precognition requests."""
    fallback_called = {"called": False}

    def fallback_handler(request: Request[Any, Any, Any], exc: ValidationException) -> Any:
        fallback_called["called"] = True
        return MagicMock(status_code=400)

    handler = create_precognition_exception_handler(fallback_handler=fallback_handler)  # pyright: ignore[reportArgumentType]

    mock_request = MagicMock(spec=Request)
    mock_request.headers = {}

    exc = ValidationException(detail="Validation failed")

    handler(mock_request, exc)

    assert fallback_called["called"] is True


# =====================================================
# @precognition Decorator Tests
# =====================================================


def test_precognition_decorator_sync_handler() -> None:
    """Test @precognition decorator with sync handler."""

    @precognition
    def my_handler(request: Request[Any, Any, Any]) -> dict[str, str]:
        return {"result": "executed"}

    # Create mock request with Precognition header
    mock_request = MagicMock(spec=Request)
    mock_request.headers = MagicMock()
    mock_request.headers.get = MagicMock(return_value="true")

    result = my_handler(mock_request)

    assert isinstance(result, PrecognitionResponse)


def test_precognition_decorator_sync_handler_normal_request() -> None:
    """Test @precognition decorator passes through non-Precognition requests."""

    @precognition
    def my_handler(request: Request[Any, Any, Any]) -> dict[str, str]:
        return {"result": "executed"}

    # Create mock request without Precognition header
    mock_request = MagicMock(spec=Request)
    mock_request.headers = MagicMock()
    mock_request.headers.get = MagicMock(return_value=None)

    result = my_handler(mock_request)

    assert result == {"result": "executed"}


@pytest.mark.anyio
async def test_precognition_decorator_async_handler() -> None:
    """Test @precognition decorator with async handler."""

    @precognition
    async def my_handler(request: Request[Any, Any, Any]) -> dict[str, str]:
        return {"result": "executed"}

    # Create mock request with Precognition header
    mock_request = MagicMock(spec=Request)
    mock_request.headers = MagicMock()
    mock_request.headers.get = MagicMock(return_value="true")

    result = await my_handler(mock_request)

    assert isinstance(result, PrecognitionResponse)


@pytest.mark.anyio
async def test_precognition_decorator_async_handler_normal_request() -> None:
    """Test @precognition decorator passes through non-Precognition async requests."""

    @precognition
    async def my_handler(request: Request[Any, Any, Any]) -> dict[str, str]:
        return {"result": "executed"}

    # Create mock request without Precognition header
    mock_request = MagicMock(spec=Request)
    mock_request.headers = MagicMock()
    mock_request.headers.get = MagicMock(return_value=None)

    result = await my_handler(mock_request)

    assert result == {"result": "executed"}


def test_precognition_decorator_request_in_kwargs() -> None:
    """Test @precognition decorator finds request in kwargs."""

    @precognition
    def my_handler(*, request: Request[Any, Any, Any]) -> dict[str, str]:
        return {"result": "executed"}

    # Create mock request with Precognition header
    mock_request = MagicMock(spec=Request)
    mock_request.headers = MagicMock()
    mock_request.headers.get = MagicMock(return_value="true")

    result = my_handler(request=mock_request)

    assert isinstance(result, PrecognitionResponse)


# =====================================================
# InertiaRequest Precognition Properties Tests
# =====================================================


def test_inertia_details_is_precognition_true() -> None:
    """Test InertiaDetails.is_precognition returns True when header present."""
    # Create a mock scope with Precognition header
    scope = cast(
        HTTPScope,
        {
            "type": "http",
            "method": "POST",
            "path": "/users",
            "headers": [(b"precognition", b"true")],
            "query_string": b"",
            "root_path": "",
            "app": MagicMock(),
            "state": {},
        },
    )

    request: Request[Any, Any, Any] = Request(scope=scope)
    details = InertiaDetails(request)

    assert details.is_precognition is True


def test_inertia_details_is_precognition_false() -> None:
    """Test InertiaDetails.is_precognition returns False when header missing."""
    scope = cast(
        HTTPScope,
        {
            "type": "http",
            "method": "POST",
            "path": "/users",
            "headers": [],
            "query_string": b"",
            "root_path": "",
            "app": MagicMock(),
            "state": {},
        },
    )

    request: Request[Any, Any, Any] = Request(scope=scope)
    details = InertiaDetails(request)

    assert details.is_precognition is False


def test_inertia_details_precognition_validate_only() -> None:
    """Test InertiaDetails.precognition_validate_only parses fields."""
    scope = cast(
        HTTPScope,
        {
            "type": "http",
            "method": "POST",
            "path": "/users",
            "headers": [(b"precognition", b"true"), (b"precognition-validate-only", b"email,password,name")],
            "query_string": b"",
            "root_path": "",
            "app": MagicMock(),
            "state": {},
        },
    )

    request: Request[Any, Any, Any] = Request(scope=scope)
    details = InertiaDetails(request)

    assert details.precognition_validate_only == ["email", "password", "name"]


def test_inertia_details_precognition_validate_only_empty() -> None:
    """Test InertiaDetails.precognition_validate_only returns empty list when not present."""
    scope = cast(
        HTTPScope,
        {
            "type": "http",
            "method": "POST",
            "path": "/users",
            "headers": [(b"precognition", b"true")],
            "query_string": b"",
            "root_path": "",
            "app": MagicMock(),
            "state": {},
        },
    )

    request: Request[Any, Any, Any] = Request(scope=scope)
    details = InertiaDetails(request)

    assert details.precognition_validate_only == []


def test_inertia_request_is_precognition() -> None:
    """Test InertiaRequest.is_precognition property."""
    scope = cast(
        HTTPScope,
        {
            "type": "http",
            "method": "POST",
            "path": "/users",
            "headers": [(b"precognition", b"true")],
            "query_string": b"",
            "root_path": "",
            "app": MagicMock(),
            "state": {},
        },
    )

    request: InertiaRequest[Any, Any, Any] = InertiaRequest(scope=scope)

    assert request.is_precognition is True


def test_inertia_request_precognition_validate_only() -> None:
    """Test InertiaRequest.precognition_validate_only property."""
    scope = cast(
        HTTPScope,
        {
            "type": "http",
            "method": "POST",
            "path": "/users",
            "headers": [(b"precognition", b"true"), (b"precognition-validate-only", b"email,password")],
            "query_string": b"",
            "root_path": "",
            "app": MagicMock(),
            "state": {},
        },
    )

    request: InertiaRequest[Any, Any, Any] = InertiaRequest(scope=scope)

    assert request.precognition_validate_only == {"email", "password"}


# =====================================================
# InertiaHeaders Tests
# =====================================================


def test_inertia_headers_precognition_values() -> None:
    """Test InertiaHeaders has correct Precognition header values."""
    assert InertiaHeaders.PRECOGNITION.value == "Precognition"
    assert InertiaHeaders.PRECOGNITION_SUCCESS.value == "Precognition-Success"
    assert InertiaHeaders.PRECOGNITION_VALIDATE_ONLY.value == "Precognition-Validate-Only"
