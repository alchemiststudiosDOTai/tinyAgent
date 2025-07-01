#!/bin/bash

# claude-rag.sh
# RAG (Retrieval-Augmented Generation) tool for .claude directory

set -euo pipefail

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly RAG_DIR="${SCRIPT_DIR}/claude-rag"
readonly CLAUDE_DIR=".claude"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m'

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date +"%H:%M:%S")]${NC} ${message}"
}

# Function to check if Rust is installed
check_rust() {
    if ! command -v cargo &> /dev/null; then
        print_status "${RED}" "Rust/Cargo not found. Please install Rust first."
        echo "Visit: https://rustup.rs/"
        exit 1
    fi
}

# Function to build the RAG tools if needed
build_tools() {
    if [[ ! -f "${RAG_DIR}/target/release/build_index" ]] || [[ ! -f "${RAG_DIR}/target/release/retrieve" ]]; then
        print_status "${YELLOW}" "Building RAG tools (first time setup)..."
        cd "${RAG_DIR}"
        cargo build --release --quiet
        print_status "${GREEN}" "Build complete!"
        cd - > /dev/null
    fi
}

# Function to build/rebuild the index
build_index() {
    print_status "${CYAN}" "Building .claude index..."
    
    # Ensure .claude directory exists
    if [[ ! -d "${CLAUDE_DIR}" ]]; then
        print_status "${YELLOW}" "Warning: ${CLAUDE_DIR} directory not found"
        print_status "${YELLOW}" "Run setup-claude-optimization.sh first to create the structure"
        return 1
    fi
    
    # Run the indexer from the main directory (where .claude is)
    "${RAG_DIR}/target/release/build_index"
}

# Function to query the index
query_index() {
    local query="$*"
    
    if [[ -z "${query}" ]]; then
        print_status "${RED}" "Error: Query required"
        echo "Usage: $(basename "$0") query <search terms>"
        exit 1
    fi
    
    # Check if index exists
    if [[ ! -d "${RAG_DIR}/data/claude_idx" ]]; then
        print_status "${YELLOW}" "Index not found. Building index first..."
        build_index
    fi
    
    # Run the query from the main directory
    "${RAG_DIR}/target/release/retrieve" "$@"
}

# Function to show usage
show_usage() {
    cat << EOF
Claude RAG (Retrieval-Augmented Generation) Tool

Usage: $(basename "$0") <command> [options]

Commands:
  build                       Build/rebuild the .claude index
  
  query <terms>               Search the index
                             Options:
                               --category <cat>  Filter by category
                               --limit <n>       Limit results (default: 12)
  
  stats                       Show index statistics
  
  clean                       Remove the index
  
  help                        Show this help message

Examples:
  $(basename "$0") build
  $(basename "$0") query "error handling patterns"
  $(basename "$0") query "debug" --category debug_history
  $(basename "$0") query "authentication" --limit 5

Categories:
  - debug_history    Debugging sessions and fixes
  - patterns         Implementation patterns
  - qa              Questions and answers
  - cheatsheets     Quick references
  - metadata        Component information
  - code_index      Code relationships
  - anchors         Important code locations
  - scratchpad      Working notes
  - delta           Change logs

EOF
}

# Function to show index statistics
show_stats() {
    if [[ ! -d "${RAG_DIR}/data/claude_idx" ]]; then
        print_status "${RED}" "No index found. Run 'build' first."
        exit 1
    fi
    
    print_status "${CYAN}" "Index Statistics:"
    
    # Count files in .claude
    if [[ -d "${CLAUDE_DIR}" ]]; then
        local file_count=$(find "${CLAUDE_DIR}" -type f -name "*.md" -o -name "*.txt" -o -name "*.json" | wc -l)
        echo "  Source files: ${file_count}"
    fi
    
    # Show index size
    local index_size=$(du -sh "${RAG_DIR}/data/claude_idx" 2>/dev/null | cut -f1)
    echo "  Index size: ${index_size:-unknown}"
    
    # Show categories
    echo "  Categories indexed:"
    for cat in debug_history patterns qa cheatsheets metadata code_index anchors scratchpad delta; do
        if [[ -d "${CLAUDE_DIR}/${cat}" ]]; then
            local count=$(find "${CLAUDE_DIR}/${cat}" -type f 2>/dev/null | wc -l)
            if [[ ${count} -gt 0 ]]; then
                echo "    - ${cat}: ${count} files"
            fi
        fi
    done
}

# Function to clean the index
clean_index() {
    print_status "${YELLOW}" "Removing index..."
    rm -rf "${RAG_DIR}/data/claude_idx"
    print_status "${GREEN}" "Index removed"
}

# Main function
main() {
    check_rust
    build_tools
    
    local command="${1:-help}"
    shift || true
    
    case "${command}" in
        build)
            build_index
            ;;
            
        query)
            query_index "$@"
            ;;
            
        stats)
            show_stats
            ;;
            
        clean)
            clean_index
            ;;
            
        help)
            show_usage
            ;;
            
        *)
            print_status "${RED}" "Unknown command: ${command}"
            show_usage
            exit 1
            ;;
    esac
}

# Execute main function
main "$@"