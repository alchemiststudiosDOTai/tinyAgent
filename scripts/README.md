# TinyAgent Deployment Scripts

Best practice PyPI package deployment system using UV for the official TinyAgent library.

## 🚀 Quick Start

```bash
# 1. Validate deployment setup
./scripts/validate-deployment.sh

# 2. Setup PyPI credentials
./scripts/setup-credentials.sh

# 3. Deploy to Test PyPI
./scripts/deploy.sh test

# 4. Deploy to Production PyPI
./scripts/deploy.sh prod
```

## 📁 Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `deploy.sh` | Main deployment pipeline | `./scripts/deploy.sh [test\|prod\|both]` |
| `setup-credentials.sh` | Secure credential management | `./scripts/setup-credentials.sh` |
| `validate-deployment.sh` | Pre-deployment validation | `./scripts/validate-deployment.sh` |

## 🔧 Deployment Pipeline Features

### ✅ Security First
- API token-based authentication
- Secure credential storage (600 permissions)
- Hardcoded secret detection
- Sensitive file scanning
- .gitignore protection for credentials

### 🏗️ Robust Build Process
- UV virtual environment management
- Clean build isolation
- Comprehensive testing (pytest + ruff + pre-commit)
- Package integrity validation
- Semantic version checking

### 🎯 Production Ready
- Test PyPI validation before production
- Git tag creation and management
- Detailed logging and error handling
- Dry-run mode for testing
- Atomic operations (all-or-nothing)

## 📋 Detailed Usage

### Main Deployment Script

```bash
# Deploy to Test PyPI only
./scripts/deploy.sh test

# Deploy to Production PyPI only
./scripts/deploy.sh prod

# Deploy to both (Test PyPI first, then Production)
./scripts/deploy.sh both

# Build package but don't upload (testing)
./scripts/deploy.sh --dry-run test

# Skip tests (not recommended)
./scripts/deploy.sh --skip-tests prod

# Clean build artifacts only
./scripts/deploy.sh --clean-only

# Show help
./scripts/deploy.sh --help
```

### Credential Management

```bash
# Setup both Test and Production PyPI tokens
./scripts/setup-credentials.sh

# Setup Test PyPI token only
./scripts/setup-credentials.sh --test-only

# Setup Production PyPI token only
./scripts/setup-credentials.sh --prod-only

# Update .gitignore security patterns only
./scripts/setup-credentials.sh --gitignore
```

### Pre-Deployment Validation

```bash
# Validate entire deployment setup
./scripts/validate-deployment.sh
```

## 🔐 Security Configuration

### Credential Storage

**PyPI Configuration File** (Used by this deployment system)
```bash
# Token stored in /root/.pypirc
# Standard Python packaging configuration file
# Automatically used by twine for authentication
```

The deployment script reads credentials from `/root/.pypirc` which should contain your PyPI tokens in the standard format:

```ini
[distutils]
index-servers = pypi testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = pypi-your-production-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-test-token-here
```

### API Token Generation

1. **Production PyPI**: https://pypi.org/manage/account/token/
2. **Test PyPI**: https://test.pypi.org/manage/account/token/

**Important**: Use API tokens, not passwords. Tokens provide better security and granular permissions.

## 🏗️ Build Process Details

The deployment pipeline follows these steps:

1. **Environment Validation**
   - Check required tools (uv, git, python3)
   - Verify project structure
   - Validate pyproject.toml syntax
   - Check git working directory status

2. **Security Checks**
   - Scan for sensitive files
   - Check for hardcoded secrets in code
   - Validate credential configuration

3. **Environment Setup**
   - Create/activate UV virtual environment
   - Install package in development mode
   - Install build dependencies (build, twine, pytest, ruff)

4. **Testing & Quality Assurance**
   - Run ruff linting and formatting
   - Execute pytest test suite
   - Run pre-commit hooks

5. **Package Building**
   - Clean previous build artifacts
   - Build source distribution (sdist) and wheel
   - Validate package integrity with twine

6. **Deployment**
   - Upload to specified PyPI repository
   - Create git tags for production releases
   - Provide installation instructions

## 📦 Package Information

- **Name**: `tiny_agent_os`
- **Current Version**: `0.73.0`
- **Python**: `>=3.10`
- **Build Backend**: `setuptools`
- **License**: Business Source License 1.1

## 🔍 Troubleshooting

### Common Issues

**Build failures**:
```bash
# Check test failures
pytest tests/api_test/test_agent.py -v

# Check linting issues
ruff check . --fix
ruff format .

# Run pre-commit hooks
pre-commit run --all-files
```

**Credential issues**:
```bash
# Verify token files exist and have correct permissions
ls -la .pypi-token .testpypi-token

# Re-setup credentials
./scripts/setup-credentials.sh
```

**Version conflicts**:
```bash
# Check if version tag already exists
git tag -l | grep v0.73.0

# Update version in pyproject.toml if needed
```

### Debug Mode

For detailed debugging, examine the script logs or run individual components:

```bash
# Verbose UV operations
uv --verbose venv
uv --verbose pip install -e .

# Detailed twine upload
twine upload --verbose dist/*

# Git status check
git status --porcelain
```

## 🎯 Best Practices

### Before Each Release

1. ✅ Update version in `pyproject.toml`
2. ✅ Update changelog/release notes
3. ✅ Run full test suite: `pytest tests/ -v`
4. ✅ Run validation: `./scripts/validate-deployment.sh`
5. ✅ Test deploy: `./scripts/deploy.sh --dry-run test`
6. ✅ Deploy to Test PyPI first: `./scripts/deploy.sh test`
7. ✅ Verify test installation works
8. ✅ Deploy to Production: `./scripts/deploy.sh prod`

### Security Best Practices

- ✅ Never commit credential files
- ✅ Use API tokens instead of passwords
- ✅ Regularly rotate API tokens
- ✅ Use separate tokens for Test and Production PyPI
- ✅ Store tokens with restrictive file permissions (600)
- ✅ Use environment variables in CI/CD systems

### Development Workflow

```bash
# Daily development
source .venv/bin/activate
uv pip install -e .

# Before commits
ruff check . --fix && ruff format .
pytest tests/api_test/test_agent.py -v

# Release preparation
./scripts/validate-deployment.sh
./scripts/deploy.sh --dry-run test
```

## 📊 Monitoring & Metrics

After deployment, monitor:

- Package download statistics on PyPI
- Installation success rates
- User feedback and bug reports
- Security vulnerability alerts

---

**💡 Pro Tip**: Always test with `--dry-run` and deploy to Test PyPI first before production releases!
