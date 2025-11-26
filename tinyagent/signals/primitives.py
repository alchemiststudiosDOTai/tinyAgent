"""
tinyagent.signals.primitives
Communication primitives for the LLM to signal uncertainty and progress.

These functions allow the LLM to express its cognitive state during execution,
providing visibility into its reasoning process.

Public surface
--------------
uncertain  – function (signal uncertainty)
explore    – function (signal exploration)
commit     – function (signal confidence)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

__all__ = ["uncertain", "explore", "commit", "Signal", "SignalType"]


class SignalType(Enum):
    """Types of cognitive signals the LLM can emit."""

    UNCERTAIN = auto()
    EXPLORE = auto()
    COMMIT = auto()


@dataclass(frozen=True)
class Signal:
    """
    A cognitive signal from the LLM.

    Parameters
    ----------
    signal_type : SignalType
        The type of signal
    message : str
        The message describing the signal
    """

    signal_type: SignalType
    message: str

    def __str__(self) -> str:
        prefix = {
            SignalType.UNCERTAIN: "[UNCERTAIN]",
            SignalType.EXPLORE: "[EXPLORE]",
            SignalType.COMMIT: "[COMMIT]",
        }
        return f"{prefix[self.signal_type]} {self.message}"


# Signal collector - will be set by the executor
_signal_collector: Callable[[Signal], None] | None = None


def set_signal_collector(collector: Callable[[Signal], None] | None) -> None:
    """
    Set the signal collector function.

    Parameters
    ----------
    collector : Callable[[Signal], None] | None
        Function to call when a signal is emitted, or None to clear
    """
    global _signal_collector
    _signal_collector = collector


def uncertain(message: str) -> Signal:
    """
    Signal uncertainty about something.

    Use this when you're not sure about:
    - The format of data you're working with
    - Whether an approach will work
    - The meaning of something you observed

    Parameters
    ----------
    message : str
        Description of the uncertainty

    Returns
    -------
    Signal
        The emitted signal

    Examples
    --------
    >>> uncertain("I'm not sure if this API returns a list or dict")
    """
    signal = Signal(SignalType.UNCERTAIN, message)
    if _signal_collector:
        _signal_collector(signal)
    print(str(signal))
    return signal


def explore(message: str) -> Signal:
    """
    Signal that you're exploring before committing.

    Use this when you're:
    - Investigating the structure of data
    - Testing assumptions
    - Gathering information before making a decision

    Parameters
    ----------
    message : str
        Description of what you're exploring

    Returns
    -------
    Signal
        The emitted signal

    Examples
    --------
    >>> explore("Let me check the structure first")
    """
    signal = Signal(SignalType.EXPLORE, message)
    if _signal_collector:
        _signal_collector(signal)
    print(str(signal))
    return signal


def commit(message: str) -> Signal:
    """
    Signal confidence and readiness to proceed.

    Use this when:
    - You've verified your assumptions
    - You understand the data format
    - You're ready to produce the final answer

    Parameters
    ----------
    message : str
        Description of what you're confident about

    Returns
    -------
    Signal
        The emitted signal

    Examples
    --------
    >>> commit("Now I know the format, proceeding with solution")
    """
    signal = Signal(SignalType.COMMIT, message)
    if _signal_collector:
        _signal_collector(signal)
    print(str(signal))
    return signal
