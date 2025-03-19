# tinyAgent Test Suite Documentation

## Overview

This document outlines the testing strategy, structure, and procedures for the tinyAgent framework. The test suite is designed to ensure the reliability, functionality, and performance of the core components, with special attention to the decorator-based tool factory system and configurable LLM call limits.

## Test Organization

The tests are organized by component and functionality:

- **Tool Framework Tests**: Tests for the basic tooling functionality, including the decorator system
- **Rate Limiting Tests**: Tests for the configurable LLM call limits and rate limiting features
- **Orchestration Tests**: Tests for the orchestrator and planning phase functionality

## Running Tests

### Running the Full Test Suite

```bash
# From the project root directory
python -m pytest

# With coverage reporting
python -m pytest --cov=core
```

### Running Specific Test Categories

```bash
# Run only tool framework tests
python -m pytest tests/test_tool_decorator.py

# Run only rate limiting tests
python -m pytest tests/test_rate_limiting.py

# Run only orchestration tests
python -m pytest tests/test_orchestrator_planning.py
```

## Test Components

### 1. Tool Decorator Tests (`test_tool_decorator.py`)

These tests focus on the decorator-based tool creation system, verifying:

- Basic tool creation from Python functions
- Parameter type inference and validation
- Custom tool naming and description
- Tool execution and result handling

**Key Test Scenarios:**
- Creating a simple tool with the `@tool` decorator
- Customizing tool name and description
- Verifying parameter types are correctly inferred
- Executing tools and validating results

### 2. Rate Limiting Tests (`test_rate_limiting.py`)

These tests verify the configurable LLM call limits and rate limiting functionality:

- Global rate limiting across all tools
- Tool-specific rate limits that override global settings
- Unlimited tools (rate limit = -1)
- Rate limit reset behavior

**Key Test Scenarios:**
- Testing tools against the global rate limit
- Testing tools with specific rate limits
- Verifying unlimited tools function without restrictions
- Testing rate limit reset after specified timeframes

### 3. Orchestrator and Planning Tests (`test_orchestrator_planning.py`)

These tests focus on the orchestration system and the planning phase functionality:

- Task creation and delegation
- Agent coordination and communication
- ElderBrain's three-phase processing approach
- Task status tracking throughout the workflow

**Key Test Scenarios:**
- Testing the ElderBrain's research, planning, and execution phases
- Testing task delegation to appropriate specialized agents
- Verifying task status tracking throughout the workflow

## Mock Strategy

The test suite uses strategic mocking to isolate components and avoid external dependencies:

- **LLM API Calls**: All LLM API calls are mocked to avoid actual API usage during testing
- **External Services**: All external service calls are mocked
- **Time-Dependent Functions**: Time-based functions are mocked to ensure consistent test behavior

## Adding New Tests

When adding new tests, follow these guidelines:

1. **Test Organization**: Place tests in the appropriate file based on functionality
2. **Test Independence**: Each test should be independent and not rely on other tests
3. **Use Mocks**: Avoid external dependencies by mocking services
4. **Clear Naming**: Use descriptive names for test methods
5. **Documentation**: Update this document when adding new test categories

## Continuous Integration

The test suite is integrated with CI/CD pipelines to ensure code quality:

- Tests run automatically on each pull request
- Coverage reports are generated to identify untested code
- Test failures block merging to protected branches

## Troubleshooting Tests

If tests are failing, consider these common issues:

- **Environment Issues**: Ensure all dependencies are installed
- **Configuration**: Check that test configuration matches expected environment
- **Mock Objects**: Verify that mock objects are correctly configured
- **API Changes**: If the API has changed, tests may need updating

Run failing tests in verbose mode for detailed output:

```bash
python -m pytest tests/failing_test.py -v
```
