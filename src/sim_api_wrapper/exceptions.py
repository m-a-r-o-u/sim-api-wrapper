"""Custom exceptions raised by the SIM API client."""

from __future__ import annotations


class SimApiError(RuntimeError):
    """Raised when a non-successful response is returned from the API."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code

    def __str__(self) -> str:  # pragma: no cover - trivial wrapper
        if self.status_code is not None:
            return f"{self.status_code}: {super().__str__()}"
        return super().__str__()
