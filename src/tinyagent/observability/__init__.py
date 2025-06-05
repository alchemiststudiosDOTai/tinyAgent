"""
TinyAgent Observability Package

This package provides observability features including distributed tracing,
metrics collection, and monitoring capabilities.
"""

from .tracer import configure_tracing, get_tracer

__all__ = ["get_tracer", "configure_tracing"]
