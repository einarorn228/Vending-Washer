"""Provider contract for entitlement lookup/authorization/usage commit."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ProviderLookupResult:
    success: bool
    message: str
    entitlement: Optional[Any] = None


@dataclass
class ProviderAuthorizationResult:
    authorized: bool
    message: str
    entitlement: Optional[Any] = None


@dataclass
class ProviderCommitResult:
    success: bool
    message: str
    uses_left: Optional[int] = None
    retryable: bool = False


@dataclass
class ProviderCompletionResult:
    success: bool
    message: str


class BaseProvider(ABC):
    """Minimal provider interface used by the start orchestrator."""

    @abstractmethod
    def lookup(self, identifier: str, mode: str = "local_code") -> ProviderLookupResult:
        """Resolve an input identifier into an entitlement context."""

    @abstractmethod
    def authorize(self, entitlement: Any, machine_id: Optional[str] = None) -> ProviderAuthorizationResult:
        """Validate whether the entitlement can be used for a start attempt."""

    @abstractmethod
    def commit_start(self, entitlement: Any, quantity: int = 1) -> ProviderCommitResult:
        """Commit usage after telemetry confirms a machine start."""

    @abstractmethod
    def mark_completion(self, entitlement: Any, machine_id: Optional[str] = None) -> ProviderCompletionResult:
        """Mark completion for the provider if needed."""
