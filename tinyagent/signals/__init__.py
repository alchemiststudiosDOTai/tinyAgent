"""
tinyagent.signals
LLM communication primitives for uncertainty and exploration.

Public surface
--------------
uncertain  – function
explore    – function
commit     – function
"""

from .primitives import commit, explore, uncertain

__all__ = ["uncertain", "explore", "commit"]
