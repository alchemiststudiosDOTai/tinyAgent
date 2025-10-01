"""
tinyagent.tool
Registry + decorator for agent-callable tools.

Public surface
--------------
tool              – decorator
Tool              – dataclass wrapper
freeze_registry   – lock mutation
get_registry      – read-only mapping
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Callable, Dict, Iterator, Mapping, MutableMapping

__all__ = [
    "Tool",
    "tool",
    "freeze_registry",
    "get_registry",
]


# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Tool:
    """Wraps a callable with metadata."""

    fn: Callable[..., Any]
    name: str
    doc: str
    signature: inspect.Signature

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.fn(*args, **kwargs)

    def run(self, payload: Dict[str, Any]) -> str:
        bound = self.signature.bind(**payload)
        return str(self.fn(*bound.args, **bound.kwargs))


class ToolRegistry(MutableMapping[str, Tool]):
    """Dict-like registry with a handy `.register` decorator."""

    def __init__(self) -> None:
        self._data: Dict[str, Tool] = {}
        self._frozen: bool = False

    # Decorator ----------------------------------------------------------
    def register(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        if self._frozen:
            raise RuntimeError("Registry is frozen; cannot add new tools.")
        self._data[fn.__name__] = Tool(
            fn=fn,
            name=fn.__name__,
            doc=(fn.__doc__ or "").strip(),
            signature=inspect.signature(fn),
        )
        return fn

    # MutableMapping API -------------------------------------------------
    def __getitem__(self, key: str) -> Tool:  # noqa: Dunder
        return self._data[key]

    def __setitem__(self, key: str, value: Tool) -> None:  # noqa: Dunder
        if self._frozen:
            raise RuntimeError("Registry is frozen; cannot mutate.")
        self._data[key] = value

    def __delitem__(self, key: str) -> None:  # noqa: Dunder
        if self._frozen:
            raise RuntimeError("Registry is frozen; cannot mutate.")
        del self._data[key]

    def __iter__(self) -> Iterator[str]:  # noqa: Dunder
        return iter(self._data)

    def __len__(self) -> int:  # noqa: Dunder
        return len(self._data)

    # Helpers ------------------------------------------------------------
    def freeze(self) -> None:
        """Lock the registry against further changes."""
        self._frozen = True
        self._data = MappingProxyType(self._data)  # type: ignore[assignment]

    def view(self) -> Mapping[str, Tool]:
        """Immutable mapping view."""
        return MappingProxyType(self._data)


# Default registry instance + decorator alias
REGISTRY = ToolRegistry()
tool = REGISTRY.register


# Public helpers ---------------------------------------------------------
def freeze_registry() -> None:
    """Freeze the default registry."""
    REGISTRY.freeze()


def get_registry() -> Mapping[str, Tool]:
    """Return a read-only view of the default registry."""
    return REGISTRY.view()
