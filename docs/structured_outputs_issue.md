# OpenRouter Structured Outputs Issue

## Summary
When using OpenRouter with structured outputs enabled (`structured_outputs: true`), the API returns a 404 error when trying to use the `/chat/completions` endpoint with a JSON schema for response formatting.

## Error Details
- **Error Message**: `No endpoints found that can handle the requested parameters`
- **HTTP Status**: 404
- **Affected Models**: All models tested through OpenRouter
- **Configuration**: Occurs when `structured_outputs: true` is set in `config.yml`

## Root Cause
The issue appears to be related to how OpenRouter handles the `response_format` parameter when making direct API calls to their endpoint. The error suggests that the endpoint doesn't recognize or support the structured output format being sent.

## Workaround
1. Disable structured outputs in `config.yml`:
   ```yaml
   structured_outputs: false  # Disable structured outputs
   ```

2. Use models that work well with the standard response format, such as:
   - `openai/gpt-4o-mini-2024-07-18`
   - `nousresearch/deephermes-3-mistral-24b-preview:free`

## Current Status
- **Status**: Workaround in place
- **Impact**: Limited to using models that work well without structured outputs
- **Priority**: Medium

## Next Steps
1. Investigate if there's a different way to format the request that OpenRouter accepts
2. Check OpenRouter documentation for any specific requirements for structured outputs
3. Consider implementing a fallback mechanism that automatically disables structured outputs when a 404 is received

## Related Files
- `src/tinyagent/utils/openrouter_request.py` - Contains the API request logic
- `config.yml` - Configuration settings
- `tests/00_test_single_tool_sanity_test.py` - Test that verifies basic functionality

## Additional Notes
- The issue might be specific to how we're formatting the JSON schema in the request
- Some models might support structured outputs while others don't
- The workaround of disabling structured outputs might affect the reliability of the JSON parsing for some models
