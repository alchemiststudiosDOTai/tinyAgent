"""
Tests for the observability package.
"""

import unittest
from unittest.mock import patch, MagicMock
import asyncio

from tinyagent.observability import get_tracer, configure_tracing
from tinyagent.observability.middleware import trace_request, trace_client_request
from tinyagent.observability.context import (
    extract_context,
    inject_context,
    get_correlation_id,
    set_correlation_id
)

class TestTracing(unittest.TestCase):
    """Test cases for OpenTelemetry tracing setup and utilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock config for testing
        self.test_config = {
            'observability': {
                'tracing': {
                    'enabled': True,
                    'service_name': 'test-service',
                    'sampling_rate': 1.0,
                    'exporter': {
                        'type': 'otlp',
                        'endpoint': 'http://localhost:4317'
                    }
                }
            }
        }
        
    def test_configure_tracing(self):
        """Test TracerProvider configuration."""
        with patch('tinyagent.observability.tracer.OTLPSpanExporter') as mock_exporter:
            configure_tracing(self.test_config)
            mock_exporter.assert_called_once_with(
                endpoint='http://localhost:4317',
                headers={}
            )
    
    def test_get_tracer(self):
        """Test tracer retrieval."""
        with patch('tinyagent.observability.tracer.configure_tracing'):
            tracer = get_tracer('test-module')
            self.assertIsNotNone(tracer)
    
    @patch('tinyagent.observability.middleware.get_tracer')
    def test_trace_request_sync(self, mock_get_tracer):
        """Test request tracing decorator for sync functions."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        @trace_request(operation_name='test_op')
        def test_func():
            return "success"
            
        result = test_func()
        self.assertEqual(result, "success")
        mock_span.set_status.assert_called_once()
    
    @patch('tinyagent.observability.middleware.get_tracer')
    def test_trace_request_async(self, mock_get_tracer):
        """Test request tracing decorator for async functions."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span
        mock_get_tracer.return_value = mock_tracer
        
        @trace_request(operation_name='test_op')
        async def test_func():
            return "success"
            
        result = asyncio.run(test_func())
        self.assertEqual(result, "success")
        mock_span.set_status.assert_called_once()
    
    def test_context_propagation(self):
        """Test trace context propagation utilities."""
        # Test context injection
        headers = {}
        updated_headers = inject_context(headers)
        self.assertIsInstance(updated_headers, dict)
        
        # Test context extraction
        context = extract_context(updated_headers)
        self.assertIsNotNone(context)
    
    @patch('tinyagent.observability.context.trace.get_current_span')
    def test_correlation_id(self, mock_get_span):
        """Test correlation ID management."""
        mock_span = MagicMock()
        mock_span.get_span_context.return_value.trace_id = 123
        mock_span.get_span_context.return_value.span_id = 456
        mock_span.is_recording.return_value = True
        mock_get_span.return_value = mock_span
        
        set_correlation_id()
        correlation_id = get_correlation_id()
        self.assertTrue(correlation_id.startswith('0000000000000'))

if __name__ == '__main__':
    unittest.main() 