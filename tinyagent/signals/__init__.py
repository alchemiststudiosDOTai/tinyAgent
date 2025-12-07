"""
tinyagent.signals
LLM communication primitives for uncertainty and exploration.

Public surface
--------------
uncertain        – function
explore          – function
commit           – function
set_signal_logger – function
"""

from .primitives import commit, explore, set_signal_logger, uncertain

__all__ = ["uncertain", "explore", "commit", "set_signal_logger"]
