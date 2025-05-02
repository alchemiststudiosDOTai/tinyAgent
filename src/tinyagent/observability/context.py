"""
Trace context propagation utilities for TinyAgent.

This module provides utilities for propagating trace context between services
and correlating traces with logs.
"""

import logging
from typing import Optional, Dict, Any, Tuple
from contextvars import ContextVar

from opentelemetry import trace
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.context.context import Context
from opentelemetry.trace.span import TraceFlags

logger = logging.getLogger(__name__)

# Context propagator for W3C trace context
_propagator = TraceContextTextMapPropagator()

# Context variable for storing correlation IDs
correlation_id: ContextVar[str] = ContextVar('correlation_id', default='')

def extract_context(headers: Dict[str, str]) -> Context:
    """
    Extract trace context from request headers.
    
    Args:
        headers: Dictionary of request headers
        
    Returns:
        Context object containing the extracted trace context
    """
    return _propagator.extract(carrier=headers)

def inject_context(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Inject current trace context into request headers.
    
    Args:
        headers: Dictionary of request headers to inject context into
        
    Returns:
        Updated headers dictionary with trace context
    """
    _propagator.inject(carrier=headers)
    return headers

def get_correlation_id() -> str:
    """
    Get the current correlation ID from context.
    
    Returns:
        The current correlation ID or empty string if not set
    """
    return correlation_id.get()

def set_correlation_id(span: Optional[trace.Span] = None) -> None:
    """
    Set correlation ID from current span or generate new one.
    
    Args:
        span: Optional span to extract trace ID from. If None, uses current span.
    """
    if span is None:
        span = trace.get_current_span()
    
    if span.is_recording():
        trace_id = format(span.get_span_context().trace_id, '032x')
        span_id = format(span.get_span_context().span_id, '016x')
        correlation_id.set(f"{trace_id}.{span_id}")
    else:
        logger.debug("No active span found for correlation ID") 