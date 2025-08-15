#!/bin/bash

# =============================================================================
# TinyAgent Production Deployment Script
# Best Practice PyPI Package Deployment with UV
# =============================================================================

set -euo pipefail  # Exit on error, undefined vars, pipe failures
IFS=$'\n\t'       # Secure Internal Field Separator

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly PACKAGE_NAME="tiny_agent_os"
readonly PYPROJECT_FILE="$PROJECT_ROOT/pyproject.toml"
readonly VENV_PATH="$PROJECT_ROOT/.venv"

# PyPI Configuration
readonly TEST_PYPI_URL="https://test.pypi.org/simple/"
readonly PROD_PYPI_URL="https://pypi.org/simple/"

# =============================================================================
# Utility Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -rf "$PROJECT_ROOT/dist" "$PROJECT_ROOT/build" "$PROJECT_ROOT"/*.egg-info
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "Required command '$1' not found"
        exit 1
    fi
}

# =============================================================================
# Validation Functions
# =============================================================================

validate_environment() {
    log_info "Validating environment..."

    # Check required tools
    check_command "uv"
    check_command "git"

    # Verify we're in project root
    if [[ ! -f "$PYPROJECT_FILE" ]]; then
        log_error "pyproject.toml not found. Are you in the project root?"
        exit 1
    fi

    # Check git status
    if [[ -n "$(git status --porcelain)" ]]; then
        log_warning "Working directory is not clean. Uncommitted changes detected."
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    log_success "Environment validation passed"
}

validate_version() {
    log_info "Validating version..."

    local version
    version=$(grep -E '^version = ' "$PYPROJECT_FILE" | sed -E 's/version = "(.+)"/\1/')

    if [[ -z "$version" ]]; then
        log_error "Could not extract version from pyproject.toml"
        exit 1
    fi

    log_info "Current version: $version"

    # Check if version follows semantic versioning
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][a-zA-Z0-9]+)*$ ]]; then
        log_warning "Version '$version' doesn't follow semantic versioning"
    fi

    # Check if tag already exists
    if git tag -l | grep -q "^v$version$"; then
        log_error "Git tag 'v$version' already exists"
        exit 1
    fi

    export PACKAGE_VERSION="$version"
    log_success "Version validation passed: $version"
}

validate_pypi_credentials() {
    local target="$1"
    log_info "Validating PyPI credentials for $target..."

    # Check for .pypirc file in root directory
    if [[ ! -f "/root/.pypirc" ]]; then
        log_error "PyPI credentials file not found: /root/.pypirc"
        exit 1
    fi

    # Validate .pypirc has correct sections
    if [[ "$target" == "testpypi" ]]; then
        if ! grep -q "\[testpypi\]" "/root/.pypirc"; then
            log_error "TestPyPI section not found in /root/.pypirc"
            exit 1
        fi
    else
        if ! grep -q "\[tiny-agent-os\]" "/root/.pypirc"; then
            log_error "tiny-agent-os section not found in /root/.pypirc"
            exit 1
        fi
    fi

    log_success "PyPI credentials validation passed"
}

security_check() {
    log_info "Performing security checks..."

    # Check for sensitive files
    local sensitive_patterns=(
        "*.pem"
        "*.key"
        "*.p12"
        "*.pfx"
        "*secret*"
        "*password*"
        ".env"
        "id_rsa*"
    )

    for pattern in "${sensitive_patterns[@]}"; do
        if find "$PROJECT_ROOT" -name "$pattern" -not -path "*/.git/*" -not -path "*/.*" | head -1 | grep -q .; then
            log_warning "Potentially sensitive files found matching pattern: $pattern"
        fi
    done

    # Check for hardcoded secrets in code (exclude environment variable reads)
    if grep -r -E "(api_key|password|secret|token).*=.*['\"][^'\"]{20,}" --include="*.py" "$PROJECT_ROOT/tinyagent/" 2>/dev/null | grep -v "os.environ.get\|getenv\|env.get" | head -1 | grep -q .; then
        log_error "Potential hardcoded secrets found in source code"
        exit 1
    fi

    log_success "Security check passed"
}

# =============================================================================
# Build and Test Functions
# =============================================================================

setup_environment() {
    log_info "Setting up development environment with UV..."

    cd "$PROJECT_ROOT"

    # Create virtual environment if it doesn't exist
    if [[ ! -d "$VENV_PATH" ]]; then
        uv venv
    fi

    # Activate environment
    source "$VENV_PATH/bin/activate"

    # Install project in development mode
    uv pip install -e .

    # Install build dependencies
    uv pip install build twine pytest pre-commit ruff

    log_success "Environment setup complete"
}

run_tests() {
    log_info "Running test suite..."

    cd "$PROJECT_ROOT"
    source "$VENV_PATH/bin/activate"

    # Run linting
    log_info "Running ruff checks..."
    ruff check . --fix
    ruff format .

    # Run tests
    log_info "Running pytest..."
    pytest tests/api_test/test_agent.py -v

    # Run pre-commit hooks
    log_info "Running pre-commit hooks..."
    pre-commit run --all-files

    log_success "All tests passed"
}

build_package() {
    log_info "Building package..."

    cd "$PROJECT_ROOT"
    source "$VENV_PATH/bin/activate"

    # Clean previous builds
    cleanup

    # Build package
    python -m build --sdist --wheel

    # Verify build artifacts
    if [[ ! -d "$PROJECT_ROOT/dist" ]] || [[ -z "$(ls -A "$PROJECT_ROOT/dist")" ]]; then
        log_error "Build failed - no artifacts in dist/"
        exit 1
    fi

    # Check package integrity
    twine check dist/*

    log_success "Package built successfully"
    ls -la "$PROJECT_ROOT/dist/"
}

# =============================================================================
# Deployment Functions
# =============================================================================

deploy_to_testpypi() {
    log_info "Deploying to Test PyPI..."

    cd "$PROJECT_ROOT"
    source "$VENV_PATH/bin/activate"

    # Use .pypirc file for authentication
    twine upload \
        --repository testpypi \
        --config-file /root/.pypirc \
        dist/*

    log_success "Successfully deployed to Test PyPI"
    log_info "Test installation: pip install --index-url $TEST_PYPI_URL $PACKAGE_NAME==$PACKAGE_VERSION"
}

deploy_to_pypi() {
    log_info "Deploying to Production PyPI..."

    cd "$PROJECT_ROOT"
    source "$VENV_PATH/bin/activate"

    # Extract project-specific token and upload
    local token=$(grep -A2 "\[tiny-agent-os\]" /root/.pypirc | grep "password" | cut -d'=' -f2 | tr -d ' ')
    twine upload \
        --repository-url https://upload.pypi.org/legacy/ \
        --username __token__ \
        --password "$token" \
        dist/*

    log_success "Successfully deployed to Production PyPI"
    log_info "Installation: pip install $PACKAGE_NAME==$PACKAGE_VERSION"
}

create_git_tag() {
    log_info "Creating git tag..."

    git tag -a "v$PACKAGE_VERSION" -m "Release v$PACKAGE_VERSION"
    log_success "Created git tag: v$PACKAGE_VERSION"
    log_info "Push tag with: git push origin v$PACKAGE_VERSION"
}

# =============================================================================
# Main Deployment Pipeline
# =============================================================================

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] TARGET

Deploy TinyAgent package to PyPI

TARGETS:
    test        Deploy to Test PyPI
    prod        Deploy to Production PyPI
    both        Deploy to Test PyPI, then Production PyPI

OPTIONS:
    -h, --help      Show this help message
    -s, --skip-tests Skip test execution (not recommended)
    -c, --clean-only Only clean build artifacts and exit
    --dry-run       Build package but don't upload

ENVIRONMENT VARIABLES:
    PYPI_API_TOKEN      Production PyPI API token
    TESTPYPI_API_TOKEN  Test PyPI API token

CREDENTIAL FILES:
    .pypi-token         Production PyPI API token (alternative to env var)
    .testpypi-token     Test PyPI API token (alternative to env var)

EXAMPLES:
    $0 test                    # Deploy to Test PyPI
    $0 prod                    # Deploy to Production PyPI
    $0 both                    # Deploy to both Test and Production PyPI
    $0 --dry-run test          # Build but don't upload
    $0 --clean-only            # Clean build artifacts only

EOF
}

main() {
    local target=""
    local skip_tests=false
    local clean_only=false
    local dry_run=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -s|--skip-tests)
                skip_tests=true
                shift
                ;;
            -c|--clean-only)
                clean_only=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            test|prod|both)
                target="$1"
                shift
                ;;
            *)
                log_error "Unknown argument: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Handle clean-only option
    if [[ "$clean_only" == true ]]; then
        cleanup
        log_success "Cleanup complete"
        exit 0
    fi

    # Validate target
    if [[ -z "$target" ]]; then
        log_error "No target specified"
        show_usage
        exit 1
    fi

    log_info "Starting TinyAgent deployment pipeline..."
    log_info "Target: $target"
    [[ "$skip_tests" == true ]] && log_warning "Skipping tests (not recommended)"
    [[ "$dry_run" == true ]] && log_info "Dry run mode - will not upload"

    # Execute pipeline
    validate_environment
    validate_version
    security_check
    setup_environment

    if [[ "$skip_tests" != true ]]; then
        run_tests
    fi

    build_package

    if [[ "$dry_run" == true ]]; then
        log_info "Dry run complete - package built but not uploaded"
        exit 0
    fi

    # Deploy based on target
    case "$target" in
        test)
            validate_pypi_credentials "testpypi"
            deploy_to_testpypi
            ;;
        prod)
            validate_pypi_credentials "prod"
            deploy_to_pypi
            create_git_tag
            ;;
        both)
            validate_pypi_credentials "testpypi"
            validate_pypi_credentials "prod"

            deploy_to_testpypi

            log_info "Waiting 60 seconds before production deployment..."
            sleep 60

            deploy_to_pypi
            create_git_tag
            ;;
    esac

    log_success "Deployment pipeline completed successfully!"

    # Final cleanup
    trap cleanup EXIT
}

# Execute main function if script is run directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
