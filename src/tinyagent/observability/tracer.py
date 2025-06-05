"""
OpenTelemetry tracer configuration and utilities for TinyAgent.

This module provides the core functionality for distributed tracing,
including TracerProvider configuration and utility functions for span creation.
"""

import inspect
import logging
import threading
from functools import lru_cache, wraps
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from ..agent import Agent

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
from opentelemetry.trace import Status, StatusCode

# Import the new exporter
from .sqlite_exporter import SQLiteSpanExporter


# Lazy import to avoid circular dependency if config uses logging
def _load_config():
    from ..config import load_config

    return load_config()


logger = logging.getLogger(__name__)

_tracer_provider: Optional[TracerProvider] = None
_config_lock = threading.Lock()  # Ensure thread-safe configuration


def configure_tracing(
    config: Optional[Dict[str, Any]] = None, force: bool = False
) -> None:
    """
    Configure OpenTelemetry tracing for the application idempotently.

    Loads configuration from config.yml if not provided.
    Sets up the global TracerProvider based on the configuration.

    Args:
        config: Optional configuration dictionary. If None, loads from config.yml.
        force: If True, reconfigure even if already configured.
    """
    global _tracer_provider

    with _config_lock:
        if _tracer_provider is not None and not force:
            logger.debug("Tracer provider already configured. Skipping.")
            return

        if config is None:
            try:
                config = _load_config()
            except Exception as e:
                logger.error(f"Failed to load configuration for tracing: {e}")
                return  # Cannot configure without config

        tracing_config = config.get("observability", {}).get("tracing", {})
        if not tracing_config.get("enabled", False):
            logger.info("Tracing is disabled in configuration.")
            _tracer_provider = None  # Ensure it's reset if disabled
            trace.set_tracer_provider(trace.NoOpTracerProvider())  # Use NoOp provider
            return

        service_name = tracing_config.get("service_name", "tinyagent")
        sampling_rate = float(tracing_config.get("sampling_rate", 1.0))

        # Create resource
        resource_attributes = {"service.name": service_name}
        resource_attributes.update(tracing_config.get("attributes", {}))

        # --- ADD DEFAULT MODEL TO RESOURCE ATTRIBUTES ---
        try:
            agent_config = config.get("model", {})
            default_model = agent_config.get("default", "not_configured")
            resource_attributes["agent.default_model"] = default_model
            logger.info(
                f"Adding agent.default_model={default_model} to resource attributes."
            )
        except Exception as e:
            logger.warning(
                f"Could not determine default model for resource attributes: {e}"
            )
        # --- END ADD ---

        resource = Resource.create(resource_attributes)

        # Create TracerProvider
        provider = TracerProvider(
            resource=resource, sampler=ParentBasedTraceIdRatio(sampling_rate)
        )

        # Configure exporter based on type
        exporter_config = tracing_config.get(
            "exporter", {"type": "console"}
        )  # Default to console
        exporter_type = exporter_config.get("type", "console").lower()

        if exporter_type == "otlp":
            try:
                exporter = OTLPSpanExporter(
                    endpoint=exporter_config.get("endpoint", "http://localhost:4317"),
                    headers=exporter_config.get("headers", {}),
                )
                # Use BatchSpanProcessor for OTLP for better performance
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info(f"Using OTLP exporter to {exporter_config.get('endpoint')}")
            except Exception as e:
                logger.error(
                    f"Failed to configure OTLP exporter: {e}. Falling back to console."
                )
                # Fallback to console exporter on error
                provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        elif exporter_type == "console":
            # Use SimpleSpanProcessor for console for immediate output
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
            logger.info("Using Console exporter for traces.")
        elif exporter_type == "sqlite":
            try:
                db_path = exporter_config.get("db_path", "traces.db")
                exporter = SQLiteSpanExporter(db_path=db_path)
                # Use SimpleSpanProcessor for SQLite to write spans as they end
                # BatchSpanProcessor could also be used for higher volume
                provider.add_span_processor(SimpleSpanProcessor(exporter))
                logger.info(f"Using SQLite exporter to {db_path}")
            except Exception as e:
                logger.error(
                    f"Failed to configure SQLite exporter: {e}. Falling back to console."
                )
                provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        else:
            logger.warning(
                f"Unsupported exporter type '{exporter_type}'. Using console exporter."
            )
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

        # Set as global TracerProvider
        trace.set_tracer_provider(provider)
        _tracer_provider = provider  # Store the configured provider
        logger.info(
            f"Configured tracing for service '{service_name}' with {exporter_type} exporter."
        )


@lru_cache
def get_tracer(name: Optional[str] = None) -> trace.Tracer:
    """
    Get a tracer instance based on the current global configuration.

    If tracing has not been explicitly configured via configure_tracing(),
    this will return a NoOpTracer.

    Args:
        name: Name for the tracer. Defaults to the calling module's name if possible.

    Returns:
        A Tracer instance (potentially NoOpTracer if disabled).
    """
    # Determine the tracer name
    if name is None:
        try:
            # Get caller module name dynamically
            frame = inspect.currentframe()
            caller_frame = inspect.getouterframes(frame, 2)[1]
            name = caller_frame.filename
        except Exception:
            name = "unknown_module"  # Fallback name

    return trace.get_tracer(name)


# --- ADDED AGENT RUN DECORATOR ---
# from ..agent import Agent # REMOVE direct import to break cycle


def trace_agent_run(func):  # RENAMED back
    """
    Decorator to automatically trace the execution of an Agent's run method.

    Starts a span named 'agent.run', sets relevant attributes, handles errors,
    and records the final response.
    """

    @wraps(func)
    def wrapper(self: "Agent", *args, **kwargs):  # Use string literal for type hint
        # REMOVED instance flag check. If this decorator is applied, tracing should proceed.

        # Class type check
        expected_class_names = {"Agent", "TracedAgent"}
        if (
            not hasattr(self, "__class__")
            or self.__class__.__name__ not in expected_class_names
        ):
            logger.warning(
                f"trace_agent_run decorator applied to an instance of unexpected class '{self.__class__.__name__}'. Skipping tracing."
            )
            return func(self, *args, **kwargs)

        tracer = get_tracer(__name__)  # Get tracer instance

        # Extract query safely from args or kwargs
        query = args[0] if args else kwargs.get("query", "Unknown Query")

        # Use the agent's configured model
        model_for_run = self.model

        span_name = "agent.run"
        with tracer.start_as_current_span(span_name) as span:
            # Set initial attributes
            span.set_attribute("agent.prompt", str(query))  # Ensure query is string
            span.set_attribute("agent.model_used", model_for_run)

            final_result = None
            try:
                # Call the original Agent.run method
                final_result = func(self, *args, **kwargs)
                # Assuming success if no exception
                span.set_status(Status(StatusCode.OK))
                return final_result
            except Exception as e:
                logger.error(f"Exception during traced agent run: {e}", exc_info=True)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, f"Agent run failed: {str(e)}"))
                # Store exception info or re-raise? Re-raising is usually better.
                raise  # Re-raise the original exception after recording it
            finally:
                # Record the final result (or error string) in the span
                # Convert result to string to ensure it's a valid attribute type
                final_response_str = (
                    str(final_result)
                    if final_result is not None
                    else "[No final result captured]"
                )
                span.set_attribute("agent.final_response", final_response_str)
                # Span context automatically ends here

    return wrapper


# --- END ADDED DECORATOR ---
