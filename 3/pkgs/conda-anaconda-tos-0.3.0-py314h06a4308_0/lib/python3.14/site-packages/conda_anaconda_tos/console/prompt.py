# Copyright (C) 2024 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Custom rich.prompt.Prompt implementations for console prompting."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.prompt import InvalidResponse, Prompt

if TYPE_CHECKING:
    from typing import Self


class FuzzyPrompt(Prompt):
    """A prompt that fuzzy matches the choices."""

    @staticmethod
    def strip_braces(value: str) -> str:
        """Strip braces from value."""
        return value.replace("(", "").replace(")", "").strip()

    def check_choice(self: Self, value: str) -> str | None:
        """Check value is in the list of valid choices."""
        if not self.choices:
            return value
        value = self.strip_braces(value)
        value = value.lower()
        return next(
            (
                choice
                for choice in map(self.strip_braces, self.choices)
                if choice.lower().startswith(value)
            ),
            None,
        )

    def process_response(self: Self, value: str) -> str:
        """Process response from user, convert to prompt type."""
        try:
            return_value = self.response_type(value)
        except ValueError as exc:
            raise InvalidResponse(self.validate_error_message) from exc

        if not (return_value := self.check_choice(return_value)):
            raise InvalidResponse(self.illegal_choice_message)
        return return_value
