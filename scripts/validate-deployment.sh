#!/bin/bash

# =============================================================================
# TinyAgent Deployment Validation Script
# Validates deployment setup and dependencies
# =============================================================================

set -euo pipefail
IFS=$'\n\t'

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*" >&2
}

check_command() {
    local cmd="$1"
    local version_flag="$2"

    if command -v "$cmd" &> /dev/null; then
        local version
        version=$($cmd "$version_flag" 2>&1 | head -n1)
        log_success "$cmd installed: $version"
        return 0
    else
        log_error "$cmd not found"
        return 1
    fi
}

validate_dependencies() {
    log_info "Validating dependencies..."

    local all_good=true

    # Core tools
    check_command "uv" "--version" || all_good=false
    check_command "git" "--version" || all_good=false
    check_command "python3" "--version" || all_good=false

    if [[ "$all_good" == false ]]; then
        log_error "Missing required dependencies"
        return 1
    fi

    log_success "All dependencies present"
}

validate_project_structure() {
    log_info "Validating project structure..."

    local required_files=(
        "pyproject.toml"
        "README.md"
        "tinyagent/__init__.py"
        "tinyagent/agent.py"
        "tinyagent/tools.py"
        "tests/api_test/test_agent.py"
    )

    for file in "${required_files[@]}"; do
        if [[ -f "$PROJECT_ROOT/$file" ]]; then
            log_success "Found: $file"
        else
            log_error "Missing: $file"
            return 1
        fi
    done

    log_success "Project structure validation passed"
}

validate_deployment_scripts() {
    log_info "Validating deployment scripts..."

    local scripts=(
        "scripts/deploy.sh"
        "scripts/setup-credentials.sh"
        "scripts/validate-deployment.sh"
    )

    for script in "${scripts[@]}"; do
        local script_path="$PROJECT_ROOT/$script"
        if [[ -f "$script_path" && -x "$script_path" ]]; then
            log_success "Found executable: $script"
        else
            log_error "Missing or not executable: $script"
            return 1
        fi
    done

    log_success "Deployment scripts validation passed"
}

validate_package_metadata() {
    log_info "Validating package metadata..."

    cd "$PROJECT_ROOT"

    # Check pyproject.toml syntax
    if python3 -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb'))" 2>/dev/null; then
        log_success "pyproject.toml syntax valid"
    else
        log_error "pyproject.toml syntax invalid"
        return 1
    fi

    # Extract and validate version
    local version
    if version=$(grep -E '^version = ' pyproject.toml | sed -E 's/version = "(.+)"/\1/'); then
        if [[ -n "$version" ]]; then
            log_success "Version found: $version"
        else
            log_error "Version field empty"
            return 1
        fi
    else
        log_error "Version field not found in pyproject.toml"
        return 1
    fi

    log_success "Package metadata validation passed"
}

test_build_process() {
    log_info "Testing build process (dry run)..."

    cd "$PROJECT_ROOT"

    # Create temporary virtual environment for testing
    local temp_venv="/tmp/tinyagent-validate-$$"

    cleanup_temp() {
        [[ -n "${temp_venv:-}" ]] && rm -rf "$temp_venv"
    }
    trap cleanup_temp EXIT

    # Test UV environment creation
    if uv venv "$temp_venv" &>/dev/null; then
        log_success "UV virtual environment creation works"
    else
        log_error "UV virtual environment creation failed"
        return 1
    fi

    # Test package installation
    if source "$temp_venv/bin/activate" && uv pip install -e . &>/dev/null; then
        log_success "Package installation works"
    else
        log_error "Package installation failed"
        return 1
    fi

    # Test build dependencies installation
    if source "$temp_venv/bin/activate" && uv pip install build twine &>/dev/null; then
        log_success "Build dependencies installation works"
    else
        log_error "Build dependencies installation failed"
        return 1
    fi

    log_success "Build process test passed"
}

validate_security_setup() {
    log_info "Validating security setup..."

    # Check .gitignore for credential patterns
    local gitignore="$PROJECT_ROOT/.gitignore"
    if [[ -f "$gitignore" ]]; then
        local security_patterns=(
            ".pypi-token"
            ".testpypi-token"
            ".deployment-config"
            "*.key"
            "*.pem"
            ".env"
        )

        local all_patterns_found=true
        for pattern in "${security_patterns[@]}"; do
            if grep -q "$pattern" "$gitignore"; then
                log_success "Security pattern in .gitignore: $pattern"
            else
                log_warning "Security pattern missing from .gitignore: $pattern"
                all_patterns_found=false
            fi
        done

        if [[ "$all_patterns_found" == true ]]; then
            log_success "All security patterns found in .gitignore"
        else
            log_warning "Some security patterns missing from .gitignore"
        fi
    else
        log_error ".gitignore not found"
        return 1
    fi

    log_success "Security setup validation passed"
}

show_deployment_readiness() {
    log_info "Deployment readiness summary:"

    echo
    echo "✅ Ready to deploy! Next steps:"
    echo
    echo "1. Setup credentials:"
    echo "   ./scripts/setup-credentials.sh"
    echo
    echo "2. Test deployment:"
    echo "   ./scripts/deploy.sh --dry-run test"
    echo
    echo "3. Deploy to Test PyPI:"
    echo "   ./scripts/deploy.sh test"
    echo
    echo "4. Deploy to Production PyPI:"
    echo "   ./scripts/deploy.sh prod"
    echo
    echo "📚 Documentation:"
    echo "   ./scripts/deploy.sh --help"
    echo "   ./scripts/setup-credentials.sh --help"
    echo
}

main() {
    log_info "Starting TinyAgent deployment validation..."

    local validation_steps=(
        validate_dependencies
        validate_project_structure
        validate_deployment_scripts
        validate_package_metadata
        validate_security_setup
        test_build_process
    )

    local failed_steps=0

    for step in "${validation_steps[@]}"; do
        if ! $step; then
            ((failed_steps++))
        fi
        echo
    done

    if [[ $failed_steps -eq 0 ]]; then
        log_success "All validation steps passed! ✨"
        show_deployment_readiness
    else
        log_error "$failed_steps validation step(s) failed"
        log_info "Please fix the issues above before deploying"
        exit 1
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
