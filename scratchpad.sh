#!/bin/bash

# scratchpad.sh
# AI Agent scratchpad tool for temporary notes, thoughts, and working memory

set -euo pipefail

# Configuration
readonly CLAUDE_DIR=".claude"
readonly SCRATCHPAD_DIR="${CLAUDE_DIR}/scratchpad"
readonly TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
readonly DEFAULT_EDITOR="${EDITOR:-nano}"

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

# Function to ensure scratchpad directory exists
ensure_scratchpad_dir() {
    if [[ ! -d "${SCRATCHPAD_DIR}" ]]; then
        mkdir -p "${SCRATCHPAD_DIR}/active"
        mkdir -p "${SCRATCHPAD_DIR}/archive"
        mkdir -p "${SCRATCHPAD_DIR}/templates"
        
        # Create README
        cat > "${SCRATCHPAD_DIR}/README.md" << 'EOF'
# AI Agent Scratchpad

This directory contains temporary working notes and thoughts for AI agents.

## Structure
- `active/`: Currently active scratchpad files
- `archive/`: Completed or old scratchpad files
- `templates/`: Templates for different types of notes

## File Naming Convention
- Task-specific: `task_[description]_[timestamp].md`
- Debug sessions: `debug_[component]_[timestamp].md`
- Planning: `plan_[feature]_[timestamp].md`
- General: `scratchpad_[timestamp].md`
EOF
        
        print_status "${GREEN}" "Created scratchpad directory structure"
    fi
}

# Function to create a new scratchpad
create_scratchpad() {
    local type="${1:-general}"
    local description="${2:-notes}"
    local filename=""
    
    # Sanitize description for filename
    local safe_description=$(echo "${description}" | tr ' ' '_' | tr -cd '[:alnum:]_-')
    
    case "${type}" in
        task)
            filename="task_${safe_description}_${TIMESTAMP}.md"
            ;;
        debug)
            filename="debug_${safe_description}_${TIMESTAMP}.md"
            ;;
        plan)
            filename="plan_${safe_description}_${TIMESTAMP}.md"
            ;;
        *)
            filename="scratchpad_${TIMESTAMP}.md"
            ;;
    esac
    
    local filepath="${SCRATCHPAD_DIR}/active/${filename}"
    
    # Create file with template
    cat > "${filepath}" << EOF
# Scratchpad: ${description}

**Type**: ${type}  
**Created**: $(date +"%Y-%m-%d %H:%M:%S")  
**Agent**: ${CLAUDE_AGENT_ID:-unknown}

## Context
<!-- Describe the current context or problem -->

## Working Notes
<!-- Add your thoughts, observations, and working notes here -->

## Key Findings
<!-- Important discoveries or insights -->

## Next Steps
<!-- What needs to be done next -->

## References
<!-- Links to relevant files, commits, or documentation -->

---
*This scratchpad is part of the Claude optimization layer*
EOF
    
    echo "${filepath}"
}

# Function to list active scratchpads
list_scratchpads() {
    local filter="${1:-}"
    
    print_status "${CYAN}" "Active Scratchpads:"
    
    if [[ -z "${filter}" ]]; then
        ls -la "${SCRATCHPAD_DIR}/active/" 2>/dev/null | grep -E "\.md$" | awk '{print "  " $9}'
    else
        ls -la "${SCRATCHPAD_DIR}/active/" 2>/dev/null | grep -E "\.md$" | grep "${filter}" | awk '{print "  " $9}'
    fi
    
    local count=$(ls "${SCRATCHPAD_DIR}/active/"*.md 2>/dev/null | wc -l)
    print_status "${BLUE}" "Total active: ${count}"
}

# Function to view a scratchpad
view_scratchpad() {
    local filename="${1}"
    local filepath="${SCRATCHPAD_DIR}/active/${filename}"
    
    if [[ ! -f "${filepath}" ]]; then
        # Try without .md extension
        filepath="${SCRATCHPAD_DIR}/active/${filename}.md"
    fi
    
    if [[ -f "${filepath}" ]]; then
        cat "${filepath}"
    else
        print_status "${RED}" "Scratchpad not found: ${filename}"
        return 1
    fi
}

# Function to edit a scratchpad
edit_scratchpad() {
    local filename="${1}"
    local filepath="${SCRATCHPAD_DIR}/active/${filename}"
    
    if [[ ! -f "${filepath}" ]]; then
        # Try without .md extension
        filepath="${SCRATCHPAD_DIR}/active/${filename}.md"
    fi
    
    if [[ -f "${filepath}" ]]; then
        ${DEFAULT_EDITOR} "${filepath}"
    else
        print_status "${RED}" "Scratchpad not found: ${filename}"
        return 1
    fi
}

# Function to append to a scratchpad
append_to_scratchpad() {
    local filename="${1}"
    local content="${2}"
    local filepath="${SCRATCHPAD_DIR}/active/${filename}"
    
    if [[ ! -f "${filepath}" ]]; then
        # Try without .md extension
        filepath="${SCRATCHPAD_DIR}/active/${filename}.md"
    fi
    
    if [[ -f "${filepath}" ]]; then
        echo "" >> "${filepath}"
        echo "### Update: $(date +"%Y-%m-%d %H:%M:%S")" >> "${filepath}"
        echo "${content}" >> "${filepath}"
        print_status "${GREEN}" "Added note to ${filename}"
    else
        print_status "${RED}" "Scratchpad not found: ${filename}"
        return 1
    fi
}

# Function to complete a scratchpad - prompts agent to file it properly
complete_scratchpad() {
    local filename="${1}"
    local filepath="${SCRATCHPAD_DIR}/active/${filename}"
    
    if [[ ! -f "${filepath}" ]]; then
        # Try without .md extension
        filepath="${SCRATCHPAD_DIR}/active/${filename}.md"
    fi
    
    if [[ ! -f "${filepath}" ]]; then
        print_status "${RED}" "Scratchpad not found: ${filename}"
        return 1
    fi
    
    # Display the scratchpad content
    print_status "${CYAN}" "=== SCRATCHPAD CONTENT ==="
    cat "${filepath}"
    echo ""
    print_status "${CYAN}" "======================="
    
    # Prompt for filing
    cat << EOF

${YELLOW}AGENT FILING INSTRUCTIONS:${NC}
Please review the above scratchpad and file it to the appropriate .claude directory:

${GREEN}Available directories:${NC}
- ${BLUE}debug_history/${NC} - For debugging sessions, error fixes, troubleshooting
- ${BLUE}patterns/${NC} - For implementation patterns, reusable solutions, best practices
- ${BLUE}qa/${NC} - For questions answered, problems solved with explanations
- ${BLUE}cheatsheets/${NC} - For quick references, common commands, shortcuts
- ${BLUE}delta/${NC} - For change logs, updates, modifications to existing code
- ${BLUE}metadata/${NC} - For component analysis, dependency info, system documentation
- ${BLUE}code_index/${NC} - For code relationships, function mappings, type hierarchies
- ${BLUE}anchors/${NC} - For important code locations to remember

${YELLOW}To file this scratchpad:${NC}
1. Choose the most appropriate directory based on content
2. Create a descriptive filename that will help future agents
3. Add any additional context or formatting needed
4. Use the Write tool to save it to: .claude/[directory]/[filename].md

${RED}IMPORTANT:${NC} After filing, run: ${GREEN}scratchpad.sh filed ${filename}${NC}

EOF
}

# Function to mark a scratchpad as filed and remove it
filed_scratchpad() {
    local filename="${1}"
    local filepath="${SCRATCHPAD_DIR}/active/${filename}"
    
    if [[ ! -f "${filepath}" ]]; then
        # Try without .md extension
        filepath="${SCRATCHPAD_DIR}/active/${filename}.md"
    fi
    
    if [[ -f "${filepath}" ]]; then
        # Log the filing
        echo "$(date +"%Y-%m-%d %H:%M:%S") | ${filename} | FILED BY AGENT" >> "${CLAUDE_DIR}/scratchpad_log.txt"
        
        # Remove the scratchpad
        rm "${filepath}"
        print_status "${GREEN}" "✓ Scratchpad filed and removed: ${filename}"
    else
        print_status "${RED}" "Scratchpad not found: ${filename}"
        return 1
    fi
}

# Function to archive a scratchpad (without sorting)
archive_scratchpad() {
    local filename="${1}"
    local filepath="${SCRATCHPAD_DIR}/active/${filename}"
    
    if [[ ! -f "${filepath}" ]]; then
        # Try without .md extension
        filepath="${SCRATCHPAD_DIR}/active/${filename}.md"
    fi
    
    if [[ -f "${filepath}" ]]; then
        mv "${filepath}" "${SCRATCHPAD_DIR}/archive/"
        print_status "${GREEN}" "Archived: ${filename}"
    else
        print_status "${RED}" "Scratchpad not found: ${filename}"
        return 1
    fi
}

# Function to search scratchpads
search_scratchpads() {
    local term="${1}"
    
    print_status "${CYAN}" "Searching for '${term}'..."
    
    echo -e "\n${YELLOW}In active scratchpads:${NC}"
    grep -l "${term}" "${SCRATCHPAD_DIR}/active/"*.md 2>/dev/null | while read -r file; do
        echo "  $(basename "${file}")"
        grep -n "${term}" "${file}" | head -3 | sed 's/^/    /'
    done
    
    echo -e "\n${YELLOW}In archived scratchpads:${NC}"
    grep -l "${term}" "${SCRATCHPAD_DIR}/archive/"*.md 2>/dev/null | while read -r file; do
        echo "  $(basename "${file}")"
        grep -n "${term}" "${file}" | head -3 | sed 's/^/    /'
    done
}

# Function to show usage
show_usage() {
    cat << EOF
AI Agent Scratchpad Tool

Usage: $(basename "$0") [command] [options]

Commands:
  new [type] [description]     Create a new scratchpad
                              Types: task, debug, plan, general (default)
                              
  list [filter]               List active scratchpads (optionally filtered)
  
  view <filename>             View a scratchpad
  
  edit <filename>             Edit a scratchpad in default editor
  
  append <filename> <text>    Append text to existing scratchpad
  
  complete <filename>         Display scratchpad and filing instructions
  
  filed <filename>            Mark scratchpad as filed and remove it
  
  archive <filename>          Move scratchpad to archive (temporary storage)
  
  search <term>               Search all scratchpads for term
  
  help                        Show this help message

Examples:
  $(basename "$0") new task "implement user authentication"
  $(basename "$0") list debug
  $(basename "$0") view task_implement_user_authentication_2024-01-20_14-30-45.md
  $(basename "$0") append task_auth "Added JWT validation"
  $(basename "$0") complete task_auth
  $(basename "$0") filed task_auth
  $(basename "$0") search "error handling"

Environment Variables:
  EDITOR                      Editor to use (default: nano)
  CLAUDE_AGENT_ID            Agent identifier for tracking

EOF
}

# Main function
main() {
    ensure_scratchpad_dir
    
    local command="${1:-help}"
    shift || true
    
    case "${command}" in
        new)
            local type="${1:-general}"
            local description="${2:-notes}"
            local filepath=$(create_scratchpad "${type}" "${description}")
            print_status "${GREEN}" "Created: $(basename "${filepath}")"
            echo "Path: ${filepath}"
            ;;
            
        list)
            local filter="${1:-}"
            list_scratchpads "${filter}"
            ;;
            
        view)
            if [[ -z "${1:-}" ]]; then
                print_status "${RED}" "Error: filename required"
                exit 1
            fi
            view_scratchpad "$1"
            ;;
            
        edit)
            if [[ -z "${1:-}" ]]; then
                print_status "${RED}" "Error: filename required"
                exit 1
            fi
            edit_scratchpad "$1"
            ;;
            
        append)
            if [[ -z "${1:-}" ]] || [[ -z "${2:-}" ]]; then
                print_status "${RED}" "Error: filename and content required"
                exit 1
            fi
            append_to_scratchpad "$1" "$2"
            ;;
            
        complete)
            if [[ -z "${1:-}" ]]; then
                print_status "${RED}" "Error: filename required"
                exit 1
            fi
            complete_scratchpad "$1"
            ;;
            
        filed)
            if [[ -z "${1:-}" ]]; then
                print_status "${RED}" "Error: filename required"
                exit 1
            fi
            filed_scratchpad "$1"
            ;;
            
        archive)
            if [[ -z "${1:-}" ]]; then
                print_status "${RED}" "Error: filename required"
                exit 1
            fi
            archive_scratchpad "$1"
            ;;
            
        search)
            if [[ -z "${1:-}" ]]; then
                print_status "${RED}" "Error: search term required"
                exit 1
            fi
            search_scratchpads "$1"
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