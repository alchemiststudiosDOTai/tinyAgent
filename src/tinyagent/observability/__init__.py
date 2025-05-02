"""
TinyAgent Observability Package

This package provides observability features including distributed tracing,
metrics collection, and monitoring capabilities.
"""

from typing import Optional
from .tracer import get_tracer, configure_tracing

__all__ = ['get_tracer', 'configure_tracing'] 