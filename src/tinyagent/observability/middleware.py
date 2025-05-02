"""
Request/response tracing middleware for TinyAgent.

This module provides middleware components for automatically creating
and managing spans for incoming and outgoing requests.
"""

import logging
import time
import asyncio
from typing import Optional, Dict, Any, Callable
from functools import wraps

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from opentelemetry.semconv.trace import SpanAttributes

from .tracer import get_tracer
from .context import inject_context, extract_context, set_correlation_id

logger = logging.getLogger(__name__)

def trace_request(
    operation_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
) -> Callable:
    """
    Decorator for tracing function calls as requests.
    
    Args:
        operation_name: Optional name for the span. Defaults to function name.
        attributes: Optional attributes to add to the span.
        
    Returns:
        Decorator function that adds tracing.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            span_name = operation_name or func.__name__
            tracer = get_tracer()
            
            with tracer.start_as_current_span(
                span_name,
                kind=trace.SpanKind.SERVER,
                attributes=attributes
            ) as span:
                try:
                    # Set correlation ID for logging
                    set_correlation_id(span)
                    
                    # Record start time for duration
                    start_time = time.time()
                    
                    # Execute the wrapped function
                    result = await func(*args, **kwargs)
                    
                    # Record duration
                    duration = time.time() - start_time
                    span.set_attribute(SpanAttributes.DURATION, duration)
                    
                    # Mark as successful
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                    
                except Exception as e:
                    # Record error details
                    span.set_status(
                        Status(StatusCode.ERROR, str(e))
                    )
                    span.record_exception(e)
                    raise
                    
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            span_name = operation_name or func.__name__
            tracer = get_tracer()
            
            with tracer.start_as_current_span(
                span_name,
                kind=trace.SpanKind.SERVER,
                attributes=attributes
            ) as span:
                try:
                    # Set correlation ID for logging
                    set_correlation_id(span)
                    
                    # Record start time for duration
                    start_time = time.time()
                    
                    # Execute the wrapped function
                    result = func(*args, **kwargs)
                    
                    # Record duration
                    duration = time.time() - start_time
                    span.set_attribute(SpanAttributes.DURATION, duration)
                    
                    # Mark as successful
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                    
                except Exception as e:
                    # Record error details
                    span.set_status(
                        Status(StatusCode.ERROR, str(e))
                    )
                    span.record_exception(e)
                    raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def trace_client_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    attributes: Optional[Dict[str, Any]] = None
) -> trace.Span:
    """
    Start a client span for outgoing requests.
    
    Args:
        method: HTTP method
        url: Request URL
        headers: Optional request headers to inject context into
        attributes: Optional additional span attributes
        
    Returns:
        The created span
    """
    tracer = get_tracer()
    
    # Prepare span attributes
    span_attributes = {
        SpanAttributes.HTTP_METHOD: method,
        SpanAttributes.HTTP_URL: url,
        **(attributes or {})
    }
    
    # Create client span
    span = tracer.start_span(
        f"{method} {url}",
        kind=trace.SpanKind.CLIENT,
        attributes=span_attributes
    )
    
    # Inject context into headers if provided
    if headers is not None:
        inject_context(headers)
    
    return span 