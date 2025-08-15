#!/bin/bash

# =============================================================================
# TinyAgent PyPI Credentials Setup Script
# Secure credential management for package deployment
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
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

setup_pypi_token() {
    local service="$1"
    local token_file="$PROJECT_ROOT/.${service,,}-token"

    log_info "Setting up $service API token..."

    echo "Please paste your $service API token (input will be hidden):"
    read -s token
    echo

    if [[ -z "$token" ]]; then
        log_error "No token provided"
        return 1
    fi

    # Validate token format
    if [[ ! "$token" =~ ^pypi- ]]; then
        log_warning "Token doesn't start with 'pypi-' - this might not be a valid API token"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 1
        fi
    fi

    # Save token securely
    echo "$token" > "$token_file"
    chmod 600 "$token_file"

    log_success "$service token saved to $token_file (permissions: 600)"
}

setup_gitignore() {
    local gitignore_file="$PROJECT_ROOT/.gitignore"

    log_info "Updating .gitignore to exclude credential files..."

    # Patterns to ensure are in .gitignore
    local patterns=(
        ".pypi-token"
        ".testpypi-token"
        "*.pem"
        "*.key"
        ".env"
    )

    # Create .gitignore if it doesn't exist
    if [[ ! -f "$gitignore_file" ]]; then
        touch "$gitignore_file"
    fi

    # Add patterns if not already present
    for pattern in "${patterns[@]}"; do
        if ! grep -q "^$pattern$" "$gitignore_file" 2>/dev/null; then
            echo "$pattern" >> "$gitignore_file"
            log_info "Added '$pattern' to .gitignore"
        fi
    done

    log_success ".gitignore updated"
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Setup PyPI credentials for TinyAgent deployment

OPTIONS:
    -h, --help          Show this help message
    -t, --test-only     Setup Test PyPI credentials only
    -p, --prod-only     Setup Production PyPI credentials only
    -g, --gitignore     Update .gitignore only

By default, sets up both Test and Production PyPI credentials.

SECURITY NOTES:
- Tokens are stored with 600 permissions (owner read/write only)
- .gitignore is updated to exclude credential files
- Use API tokens, not passwords
- Generate tokens at https://pypi.org/manage/account/token/

EOF
}

main() {
    local setup_test=true
    local setup_prod=true
    local gitignore_only=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -t|--test-only)
                setup_test=true
                setup_prod=false
                shift
                ;;
            -p|--prod-only)
                setup_test=false
                setup_prod=true
                shift
                ;;
            -g|--gitignore)
                gitignore_only=true
                shift
                ;;
            *)
                log_error "Unknown argument: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    log_info "Starting credential setup..."

    # Always update .gitignore for security
    setup_gitignore

    if [[ "$gitignore_only" == true ]]; then
        log_success "Gitignore update complete"
        exit 0
    fi

    if [[ "$setup_test" == true ]]; then
        setup_pypi_token "TestPyPI"
    fi

    if [[ "$setup_prod" == true ]]; then
        setup_pypi_token "PyPI"
    fi

    log_success "Credential setup complete!"
    log_info "You can now run the deployment script with your configured credentials"
    log_warning "Remember: Never commit credential files to version control"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
