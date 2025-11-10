"""
Tests for tinyagent.tools.builtin.web_browse
"""

from unittest.mock import Mock, patch

from tinyagent.tools.builtin.web_browse import web_browse


class TestWebBrowse:
    """Test suite for web_browse tool."""

    def test_web_browse_successful_fetch_converts_to_markdown(self):
        """Test successful web page fetch and HTML to markdown conversion."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Welcome</h1>
                <p>This is a test paragraph.</p>
                <a href="https://example.com">Link</a>
            </body>
        </html>
        """

        with patch("requests.get", return_value=mock_response):
            result = web_browse("https://example.com")

        # Verify markdown conversion happened
        assert "# Welcome" in result
        assert "This is a test paragraph" in result
        assert "https://example.com" in result
        assert not result.startswith("Error:")

    def test_web_browse_404_returns_error_message(self):
        """Test that 404 status code returns descriptive error."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch("requests.get", return_value=mock_response):
            result = web_browse("https://example.com/nonexistent")

        assert result == "Error: Failed to fetch URL with status 404"

    def test_web_browse_500_returns_error_message(self):
        """Test that 500 status code returns descriptive error."""
        mock_response = Mock()
        mock_response.status_code = 500

        with patch("requests.get", return_value=mock_response):
            result = web_browse("https://example.com/error")

        assert result == "Error: Failed to fetch URL with status 500"

    def test_web_browse_with_custom_headers(self):
        """Test that custom headers are passed to requests."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Content</p></body></html>"

        custom_headers = {
            "User-Agent": "CustomBot/1.0",
            "Accept": "text/html",
        }

        with patch("requests.get", return_value=mock_response) as mock_get:
            web_browse("https://example.com", headers=custom_headers)

        # Verify custom headers were used
        call_args = mock_get.call_args
        assert call_args[1]["headers"]["User-Agent"] == "CustomBot/1.0"
        assert call_args[1]["headers"]["Accept"] == "text/html"

    def test_web_browse_without_headers_sets_default_user_agent(self):
        """Test that default User-Agent is set when no headers provided."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Content</p></body></html>"

        with patch("requests.get", return_value=mock_response) as mock_get:
            web_browse("https://example.com")

        # Verify default User-Agent was set
        call_args = mock_get.call_args
        assert call_args[1]["headers"]["User-Agent"] == "tinyAgent-WebBrowse/1.0"

    def test_web_browse_converts_html_to_markdown(self):
        """Test that HTML is converted to markdown format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>Test</title></head>
            <body>
                <h1>Content</h1>
                <p>Visible text</p>
                <ul>
                    <li>Item 1</li>
                    <li>Item 2</li>
                </ul>
            </body>
        </html>
        """

        with patch("requests.get", return_value=mock_response):
            result = web_browse("https://example.com")

        # Verify markdown conversion
        assert "# Content" in result
        assert "Visible text" in result
        assert "* Item 1" in result or "- Item 1" in result
        assert not result.startswith("Error:")

    def test_web_browse_empty_content_returns_error(self):
        """Test that empty page content returns error message."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><head></head><body></body></html>"

        with patch("requests.get", return_value=mock_response):
            result = web_browse("https://example.com")

        assert result == "Error: No content found on the page"

    def test_web_browse_timeout_error_returns_descriptive_message(self):
        """Test that request timeout returns error message."""
        import requests

        with patch("requests.get", side_effect=requests.Timeout("Connection timeout")):
            result = web_browse("https://example.com")

        assert result.startswith("Error: Request failed")
        assert "Connection timeout" in result

    def test_web_browse_connection_error_returns_descriptive_message(self):
        """Test that connection error returns error message."""
        import requests

        with patch("requests.get", side_effect=requests.ConnectionError("Failed to connect")):
            result = web_browse("https://unreachable.example.com")

        assert result.startswith("Error: Request failed")
        assert "Failed to connect" in result

    def test_web_browse_includes_timeout_parameter(self):
        """Test that requests are made with timeout parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><p>Test</p></body></html>"

        with patch("requests.get", return_value=mock_response) as mock_get:
            web_browse("https://example.com")

        # Verify timeout was set
        call_args = mock_get.call_args
        assert call_args[1]["timeout"] == 10


class TestWebBrowseContrastiveNegative:
    """Contrastive negative tests: good vs bad cases side by side."""

    def test_valid_html_vs_malformed_html(self):
        """Test valid HTML succeeds while malformed HTML still processes."""
        # GOOD: Valid, well-formed HTML
        mock_good = Mock()
        mock_good.status_code = 200
        mock_good.text = "<html><body><h1>Valid</h1><p>Content</p></body></html>"

        with patch("requests.get", return_value=mock_good):
            good_result = web_browse("https://example.com/valid")

        assert "# Valid" in good_result
        assert not good_result.startswith("Error:")

        # BAD: Malformed but still parseable HTML
        mock_bad = Mock()
        mock_bad.status_code = 200
        mock_bad.text = "<html><h1>Unclosed heading<p>Paragraph"

        with patch("requests.get", return_value=mock_bad):
            bad_result = web_browse("https://example.com/malformed")

        # Should still process (BeautifulSoup handles malformed HTML)
        assert "Unclosed heading" in bad_result
        assert not bad_result.startswith("Error:")

    def test_successful_request_vs_failed_request(self):
        """Test successful 200 response vs failed 404 response."""
        # GOOD: Successful fetch
        mock_success = Mock()
        mock_success.status_code = 200
        mock_success.text = "<html><body><p>Success</p></body></html>"

        with patch("requests.get", return_value=mock_success):
            success_result = web_browse("https://example.com/exists")

        assert "Success" in success_result
        assert not success_result.startswith("Error:")

        # BAD: Failed fetch
        mock_fail = Mock()
        mock_fail.status_code = 404

        with patch("requests.get", return_value=mock_fail):
            fail_result = web_browse("https://example.com/missing")

        assert fail_result.startswith("Error:")
        assert "404" in fail_result

    def test_content_with_headers_vs_content_without_headers(self):
        """Test content rendered with headers vs stripped content."""
        html_with_headers = """
        <html>
            <body>
                <h1>Title</h1>
                <h2>Subtitle</h2>
                <p>Paragraph</p>
            </body>
        </html>
        """

        html_without_headers = """
        <html>
            <body>
                <p>Just paragraph text without any headers.</p>
            </body>
        </html>
        """

        # GOOD: Content with headers
        mock_good = Mock()
        mock_good.status_code = 200
        mock_good.text = html_with_headers

        with patch("requests.get", return_value=mock_good):
            good_result = web_browse("https://example.com/with-headers")

        assert "# Title" in good_result
        assert "## Subtitle" in good_result

        # COMPARISON: Content without headers
        mock_comparison = Mock()
        mock_comparison.status_code = 200
        mock_comparison.text = html_without_headers

        with patch("requests.get", return_value=mock_comparison):
            comparison_result = web_browse("https://example.com/no-headers")

        assert "Just paragraph text" in comparison_result
        assert "#" not in comparison_result  # No header markers
