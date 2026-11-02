""" """

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.common.io import dashlist
from conda.exceptions import CondaError, CondaValueError

if TYPE_CHECKING:
    from pathlib import Path

    from pydantic import ValidationError


class LockfileFormatNotSupported(CondaError):
    def __init__(self, path: str):
        message = f"The specified file {path} is not supported."
        super().__init__(message)


class ExportLockfileFormatNotSupported(CondaError):
    def __init__(self, lockfile_format: str):
        message = f"Exporting to lockfile format {lockfile_format} is not supported."
        super().__init__(message)


class EnvironmentExportNotSupported(CondaError):
    def __init__(self, lockfile_format: str, addendum: str | None = None):
        message = (
            "The specified environment cannot be exporting "
            f"to lockfile format {lockfile_format}."
        )
        addendum = f" {addendum.strip()}" if addendum else ""
        super().__init__(message + addendum)


class CondaLockfilesValidationError(CondaValueError):
    """Exception raised when pydantic validation of a lockfile fails."""

    def __init__(self, e: ValidationError, file_path: Path):
        """
        Format Pydantic validation errors into user-friendly messages.

        :param e: ValidationError from pydantic
        :param file_path: Path to the file being validated
        """

        def format_location(loc: tuple) -> str:
            """Convert Pydantic location tuple to readable field path."""
            return ".".join(str(item) for item in loc)

        errors = e.errors()
        error_messages = []
        for error in errors:
            loc = error.get("loc", ())
            msg = error.get("msg", "validation failed")
            error_type = error.get("type", "")

            # Create concise error description based on error type
            if loc:
                field_path = format_location(loc)
                if error_type == "missing":
                    description = f"missing required field '{field_path}'"
                elif "value_error" in error_type or "assertion_error" in error_type:
                    # Custom validator errors - use the message directly
                    description = msg
                else:
                    description = f"field '{field_path}': {msg}"
            else:
                description = msg

            error_messages.append(description)

        # Format the final message
        if len(error_messages) == 1:
            message = error_messages[0]
        else:
            formatted_list = dashlist(error_messages)
            message = f"File {file_path} has validation errors:\n{formatted_list}"

        super().__init__(message)


class CondaLockfilesParserError(CondaError):
    """
    Exception raised when a parsing error (e.g. `json` or `yaml`) has been encountered.

    We use this as a wrapper to ensure dependency specific errors (e.g. `ruamel.yaml`)
    are rendered correctly as a ``CondaError`` subclass.
    """

    def __init__(self, e: Exception, path: str):
        message = f"Unable to parse the content at '{path}': {e}"
        super().__init__(message)
