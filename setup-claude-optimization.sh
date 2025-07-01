#!/bin/bash

# setup-claude-optimization.sh
# Creates a Claude-optimized directory structure for enhanced codebase navigation and understanding

set -euo pipefail

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly CLAUDE_DIR=".claude"
readonly TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date +"%H:%M:%S")]${NC} ${message}"
}

# Function to create directory with error handling
create_directory() {
    local dir_path=$1
    local description=$2
    
    if mkdir -p "${dir_path}" 2>/dev/null; then
        print_status "${GREEN}" "✓ Created: ${description}"
        return 0
    else
        print_status "${RED}" "✗ Failed to create: ${description}"
        return 1
    fi
}

# Function to create README file with template
create_readme() {
    local dir_path=$1
    local title=$2
    local description=$3
    
    cat > "${dir_path}/README.md" << EOF
# ${title}

${description}

## Purpose
This directory is part of the Claude-optimized metadata structure designed to enhance AI-assisted development.

## Structure
- Files are organized by [specific organization method]
- Each file contains [specific content type]

## Usage
[Specific usage instructions for this directory]

## Last Updated
${TIMESTAMP}
EOF
    
    print_status "${BLUE}" "  Added README.md to ${dir_path}"
}

# Function to create example metadata file
create_metadata_example() {
    local dir_path=$1
    
    cat > "${dir_path}/example_component.json" << 'EOF'
{
  "component": "example_component",
  "version": "1.0.0",
  "dependencies": {
    "internal": ["component_a", "component_b"],
    "external": ["library_x", "library_y"]
  },
  "interfaces": {
    "public": [
      {
        "name": "processData",
        "signature": "processData(input: DataType): Result",
        "purpose": "Processes input data and returns result"
      }
    ]
  },
  "error_patterns": [
    {
      "pattern": "NullPointerException in processData",
      "solution": "Check input validation in line 42",
      "frequency": 3
    }
  ],
  "last_analyzed": "${TIMESTAMP}"
}
EOF
    
    print_status "${BLUE}" "  Added example metadata file"
}

# Function to create pattern example
create_pattern_example() {
    local dir_path=$1
    
    cat > "${dir_path}/error_handling_pattern.md" << 'EOF'
# Error Handling Pattern

## Pattern Name
Graceful Degradation with Context Preservation

## Intent
Handle errors without losing operational context while maintaining system stability

## Implementation
```typescript
async function robustOperation<T>(
  operation: () => Promise<T>,
  context: OperationContext,
  fallback?: T
): Promise<Result<T>> {
  try {
    const result = await operation();
    return { success: true, data: result, context };
  } catch (error) {
    logger.error('Operation failed', { error, context });
    
    if (fallback !== undefined) {
      return { success: false, data: fallback, error, context };
    }
    
    throw new ContextualError(error, context);
  }
}
```

## Usage Example
```typescript
const result = await robustOperation(
  () => fetchUserData(userId),
  { operation: 'fetchUser', userId },
  DEFAULT_USER_DATA
);
```

## Known Issues
- Fallback data might not satisfy all invariants
- Context objects can grow large in memory

## Related Patterns
- Circuit Breaker
- Retry with Backoff
EOF
    
    print_status "${BLUE}" "  Added pattern example"
}

# Function to create cheatsheet example
create_cheatsheet_example() {
    local dir_path=$1
    
    cat > "${dir_path}/component_cheatsheet.md" << 'EOF'
# Component Cheatsheet

## Quick Reference

### Common Operations
- Initialize: `new Component(config)`
- Process data: `component.process(data)`
- Clean up: `component.dispose()`

### Configuration Options
```javascript
{
  timeout: 5000,        // milliseconds
  retries: 3,          // number of retry attempts
  cache: true,         // enable caching
  logLevel: 'info'     // 'debug' | 'info' | 'warn' | 'error'
}
```

### Common Pitfalls
1. **Not disposing resources**: Always call `dispose()` when done
2. **Synchronous callbacks**: Use async/await for all callbacks
3. **Missing error boundaries**: Wrap in try-catch blocks

### Debug Commands
```bash
# Enable verbose logging
export DEBUG=component:*

# Check component state
component.getState()

# Validate configuration
component.validateConfig()
```

### Error Codes
- E001: Invalid configuration
- E002: Connection timeout
- E003: Resource exhausted
- E004: Invalid input format

### Performance Tips
- Batch operations when possible
- Use connection pooling
- Enable caching for read-heavy workloads
EOF
    
    print_status "${BLUE}" "  Added cheatsheet example"
}

# Function to create QA example
create_qa_example() {
    local dir_path=$1
    
    cat > "${dir_path}/qa_example.json" << 'EOF'
{
  "id": "qa_001",
  "timestamp": "2024-01-15T10:30:00Z",
  "component": "data_processor",
  "file": "src/processors/data_processor.ts",
  "error_type": "TypeMismatchError",
  "question": "Why is TypeMismatchError thrown when processing user data?",
  "context": {
    "error_message": "TypeMismatchError: Expected string, got number",
    "stack_trace": "at validateInput (data_processor.ts:45)",
    "input_data": { "userId": 12345, "name": "John" }
  },
  "solution": {
    "fix": "Convert userId to string before validation",
    "code_change": "const validatedId = String(input.userId);",
    "reasoning": "The API contract expects userId as string but frontend sends number"
  },
  "prevention": "Add runtime type coercion in API gateway",
  "related_issues": ["qa_002", "qa_015"]
}
EOF
    
    print_status "${BLUE}" "  Added Q&A example"
}

# Function to create memory anchor example
create_memory_anchor_example() {
    local dir_path=$1
    
    cat > "${dir_path}/memory_anchors.md" << 'EOF'
# Memory Anchors Registry

## Purpose
This file maintains a registry of memory anchors used throughout the codebase for precise reference by Claude instances.

## Anchor Format
`CLAUDE-ANCHOR-[UUID]-[SEMANTIC-TAG]`

## Active Anchors

### Core System Anchors
- `CLAUDE-ANCHOR-a1b2c3d4-MAIN-ENTRY`: Main application entry point (src/index.ts:1)
- `CLAUDE-ANCHOR-e5f6g7h8-ERROR-HANDLER`: Global error handler (src/errors/handler.ts:15)
- `CLAUDE-ANCHOR-i9j0k1l2-CONFIG-LOADER`: Configuration loading logic (src/config/loader.ts:42)

### Critical Functions
- `CLAUDE-ANCHOR-m3n4o5p6-AUTH-CHECK`: Authentication verification (src/auth/verify.ts:78)
- `CLAUDE-ANCHOR-q7r8s9t0-DATA-VALIDATE`: Data validation pipeline (src/validate/pipeline.ts:23)

### Known Problem Areas
- `CLAUDE-ANCHOR-u1v2w3x4-MEMORY-LEAK`: Potential memory leak location (src/cache/manager.ts:156)
- `CLAUDE-ANCHOR-y5z6a7b8-RACE-CONDITION`: Race condition in async handler (src/async/handler.ts:89)

## Usage
Reference these anchors in queries like:
"Check the error handling at CLAUDE-ANCHOR-e5f6g7h8-ERROR-HANDLER"

## Maintenance
- Add new anchors when identifying critical code sections
- Remove obsolete anchors during refactoring
- Update line numbers when code moves
EOF
    
    print_status "${BLUE}" "  Added memory anchors example"
}

# Main setup function
main() {
    print_status "${YELLOW}" "Starting Claude optimization setup..."
    
    # Check if .claude directory already exists and is properly set up
    if [[ -d "${CLAUDE_DIR}" ]]; then
        # Check if all required directories exist
        local required_dirs=(
            "${CLAUDE_DIR}/metadata"
            "${CLAUDE_DIR}/code_index"
            "${CLAUDE_DIR}/debug_history"
            "${CLAUDE_DIR}/patterns"
            "${CLAUDE_DIR}/cheatsheets"
            "${CLAUDE_DIR}/qa"
            "${CLAUDE_DIR}/delta"
            "${CLAUDE_DIR}/anchors"
            "${CLAUDE_DIR}/scratchpad"
            "${CLAUDE_DIR}/scratchpad/active"
            "${CLAUDE_DIR}/scratchpad/archive"
            "${CLAUDE_DIR}/scratchpad/templates"
        )
        
        local all_exist=true
        for dir in "${required_dirs[@]}"; do
            if [[ ! -d "${dir}" ]]; then
                all_exist=false
                break
            fi
        done
        
        if [[ "${all_exist}" == "true" ]]; then
            print_status "${GREEN}" "✓ ${CLAUDE_DIR} directory already properly set up"
            print_status "${BLUE}" "All required directories present. No action needed."
            exit 0
        else
            print_status "${YELLOW}" "Warning: ${CLAUDE_DIR} exists but is incomplete"
            print_status "${YELLOW}" "Will create missing directories..."
        fi
    fi
    
    # Create main .claude directory
    create_directory "${CLAUDE_DIR}" "Main Claude directory"
    
    # Create metadata structure
    create_directory "${CLAUDE_DIR}/metadata" "Metadata directory"
    create_readme "${CLAUDE_DIR}/metadata" "Metadata Directory" "Contains normalized information about the codebase including dependency graphs, file classifications, and error patterns."
    create_metadata_example "${CLAUDE_DIR}/metadata"
    
    # Create code index
    create_directory "${CLAUDE_DIR}/code_index" "Code index directory"
    create_readme "${CLAUDE_DIR}/code_index" "Code Index" "Pre-analyzed semantic relationships including function call graphs, type relationships, and intent classifications."
    
    # Create debug history
    create_directory "${CLAUDE_DIR}/debug_history" "Debug history directory"
    create_readme "${CLAUDE_DIR}/debug_history" "Debug History" "Historical debugging sessions with error-to-solution pairs, categorized by component and error type."
    
    # Create patterns library
    create_directory "${CLAUDE_DIR}/patterns" "Patterns directory"
    create_readme "${CLAUDE_DIR}/patterns" "Pattern Library" "Canonical implementation patterns including error handling, composition patterns, and reliability metrics."
    create_pattern_example "${CLAUDE_DIR}/patterns"
    
    # Create cheatsheets
    create_directory "${CLAUDE_DIR}/cheatsheets" "Cheatsheets directory"
    create_readme "${CLAUDE_DIR}/cheatsheets" "Cheatsheets" "Quick-reference guides for each component including common operations, pitfalls, and gotchas."
    create_cheatsheet_example "${CLAUDE_DIR}/cheatsheets"
    
    # Create Q&A database
    create_directory "${CLAUDE_DIR}/qa" "Q&A directory"
    create_readme "${CLAUDE_DIR}/qa" "Questions & Answers" "Previously solved problems indexed by component, file, and error type with full context."
    create_qa_example "${CLAUDE_DIR}/qa"
    
    # Create delta summaries
    create_directory "${CLAUDE_DIR}/delta" "Delta summaries directory"
    create_readme "${CLAUDE_DIR}/delta" "Delta Summaries" "Semantic change logs between versions focusing on API changes and behavior modifications."
    
    # Create memory anchors
    create_directory "${CLAUDE_DIR}/anchors" "Memory anchors directory"
    create_readme "${CLAUDE_DIR}/anchors" "Memory Anchors" "UUID-based anchors for precise code reference with semantic structure."
    create_memory_anchor_example "${CLAUDE_DIR}/anchors"
    
    # Create scratchpad directory
    create_directory "${CLAUDE_DIR}/scratchpad" "Scratchpad directory"
    create_directory "${CLAUDE_DIR}/scratchpad/active" "Active scratchpads"
    create_directory "${CLAUDE_DIR}/scratchpad/archive" "Archived scratchpads"
    create_directory "${CLAUDE_DIR}/scratchpad/templates" "Scratchpad templates"
    create_readme "${CLAUDE_DIR}/scratchpad" "AI Agent Scratchpad" "Temporary working notes and thoughts for AI agents during development and debugging sessions."
    
    # Create main README
    cat > "${CLAUDE_DIR}/README.md" << EOF
# Claude Optimization Layer

This directory contains Claude-specific metadata and optimization structures designed to enhance AI-assisted development.

## Directory Structure

- **metadata/**: Normalized codebase information and dependency graphs
- **code_index/**: Pre-analyzed semantic relationships
- **debug_history/**: Historical debugging sessions and solutions
- **patterns/**: Canonical implementation patterns
- **cheatsheets/**: Quick-reference guides for components
- **qa/**: Questions and answers database
- **delta/**: Version-to-version semantic change logs
- **anchors/**: Memory anchors for precise code reference
- **scratchpad/**: AI agent temporary working notes and thoughts

## Usage

This structure is designed to be used by Claude instances to:
1. Quickly understand codebase structure and relationships
2. Access historical debugging information
3. Reference established patterns and best practices
4. Navigate code using semantic anchors

## Maintenance

- Update metadata when adding new components
- Document debugging sessions in debug_history
- Add new patterns as they emerge
- Keep cheatsheets current with API changes

## Created
${TIMESTAMP}
EOF
    
    print_status "${GREEN}" "✓ Claude optimization setup complete!"
    print_status "${BLUE}" "Next steps:"
    echo "  1. Review the created structure in ${CLAUDE_DIR}/"
    echo "  2. Customize the example files for your specific codebase"
    echo "  3. Start populating directories with your project-specific content"
    echo "  4. Consider adding this directory to version control"
}

# Execute main function
main "$@"