# Character Test Usage

## Make Targets

The character tests can be run using convenient make targets that automatically handle environment variables.

### Basic Usage

```bash
# Run basic character tests only (recommended for quick testing)
make test-char-basic

# Run all character tests
make test-char

# Run character tests in fast mode (stop on first failure)
make test-char-fast
```

### Environment Variable Handling

The make targets automatically handle the `OPENROUTER_API_KEY` environment variable:

1. **If `OPENROUTER_API_KEY` is already set** in your environment:
   ```bash
   export OPENROUTER_API_KEY=your-key-here
   make test-char-basic
   ```

2. **If `OPENROUTER_API_KEY` is not set**, it will automatically load from `.env` file:
   ```bash
   # Loads from .env automatically
   make test-char-basic
   ```

### Available Targets

| Target | Description |
|--------|-------------|
| `make test-char-basic` | Run only the basic character tests (3 tests, ~6s) |
| `make test-char` | Run all character tests (95+ tests, ~5min) |
| `make test-char-fast` | Run all tests but stop on first failure |

### Manual pytest Usage

You can also run tests directly with pytest:

```bash
# Activate virtual environment and set API key
source venv/bin/activate
export OPENROUTER_API_KEY=your-key-here

# Run specific test files
pytest tests/character-test/test_basic.py -v
pytest tests/character-test/test_agent_character.py -v

# Run with specific patterns
pytest tests/character-test/ -k "unicode" -v
pytest tests/character-test/ -k "basic" -v
```

### Expected Results

#### Basic Tests (test-char-basic)
```
tests/character-test/test_basic.py::test_agent_basic_instantiation PASSED
tests/character-test/test_basic.py::test_simple_character_handling PASSED  
tests/character-test/test_basic.py::test_unicode_basic PASSED
3 passed in ~6s
```

#### Full Test Suite (test-char)
- **95+ tests** covering unicode, emoji, special characters, security, performance
- Some tests may fail or be skipped if certain character inputs aren't supported
- **Expected runtime**: 2-5 minutes depending on network and model response times

### Troubleshooting

#### API Key Issues
```bash
# Check if API key is loaded
echo $OPENROUTER_API_KEY

# Verify .env file exists and contains the key
grep OPENROUTER_API_KEY .env
```

#### Test Failures
- **Character truncation**: Some tests may fail if the LLM truncates long inputs
- **Unicode support**: Some tests may be skipped if unicode isn't fully supported
- **Network timeouts**: Tests may fail due to API timeouts

#### Performance
- Use `make test-char-fast` to stop on first failure for faster debugging
- Use `make test-char-basic` for quick validation
- Full test suite can take several minutes due to API calls

### Integration with CI/CD

Example GitHub Actions workflow:
```yaml
- name: Run Character Tests
  env:
    OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
  run: make test-char-basic
```

Example for local development:
```bash
# Add to your development script
if make test-char-basic; then
    echo "✅ Character tests passed"
else
    echo "❌ Character tests failed"
    exit 1
fi
```