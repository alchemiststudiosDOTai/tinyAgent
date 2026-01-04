---
title: tinyAgent Structure Documentation
path: docs/structure/
type: index
depth: 0
description: Index of all directory structure documentation
seams: []
---

# tinyAgent Structure Documentation

This directory contains comprehensive documentation for the structure and organization of the tinyAgent codebase. Each document follows a standardized format with mandatory frontmatter and detailed analysis of directory purpose, naming conventions, relationships, and architecture.

## Directory Structure Overview

The tinyAgent codebase is organized into the following top-level directories:

- **[agents/](agents.md)** - Agent implementations including BaseAgent, TinyCodeAgent, and ReactAgent
- **[core/](core.md)** - Foundational abstractions for LLM interaction, tool management, and agent operations
- **[execution/](execution.md)** - Sandboxed code execution with resource limits and safety controls
- **[limits/](limits.md)** - Resource boundaries and timeout management for code execution
- **[memory/](memory.md)** - Conversation history and agent working state management
- **[observability/](observability.md)** - Reserved for future tracing and metrics implementation
- **[prompts/](prompts.md)** - Prompt template management and loading for agent system prompts
- **[signals/](signals.md)** - LLM communication primitives for uncertainty and exploration signaling
- **[tools/](tools.md)** - Built-in tools and validation utilities for agent operations

## Documentation Standard

Each structure document includes:

### Required Frontmatter

```yaml
---
title: Human-readable name
path: relative/path/from/root
type: directory
depth: 0-N
description: One-line purpose summary
seams: [Seam1, Seam2]
---
```

### Document Sections

1. **Directory Purpose and Organization**
   - High-level description of the directory's role
   - Organization structure and key components
   - File breakdown

2. **Naming Conventions**
   - File naming patterns
   - Class/function naming conventions
   - Constants and variables
   - Private/internal members

3. **Relationship to Sibling Directories**
   - Dependencies on other directories
   - Integration points
   - Data flow and communication patterns

4. **File Structure and Architecture**
   - Detailed file-by-file breakdown
   - Architectural patterns used
   - Key design decisions

## Key Architectural Patterns

### Layered Architecture

The codebase follows a clear layered architecture:

1. **Foundation Layer** (`core/`, `limits/`, `prompts/`)
   - Provides fundamental abstractions and utilities
   - Defines contracts and protocols
   - Manages resources and constraints

2. **Service Layer** (`execution/`, `memory/`, `tools/`, `signals/`)
   - Implements core services and capabilities
   - Provides execution environments
   - Manages state and communication

3. **Agent Layer** (`agents/`)
   - Orchestrates services to build complete agent systems
   - Implements different agent paradigms (ReAct, Code execution)
   - Coordinates interactions between services

4. **Observability Layer** (`observability/`)
   - Reserved for future tracing and metrics
   - Will provide cross-cutting monitoring capabilities

### Key Design Principles

- **Separation of Concerns**: Each directory has a focused, well-defined responsibility
- **Interface Segregation**: Protocols and abstract classes define clear contracts
- **Dependency Inversion**: High-level modules depend on abstractions, not concrete implementations
- **Registry Pattern**: Tools and components are registered for discoverability
- **Observer Pattern**: Signals use a collector pattern for flexible handling

## Usage

These documents serve as:

1. **Onboarding Guide**: New contributors can understand the codebase organization
2. **Architecture Reference**: Developers can look up directory relationships and integration points
3. **Design Documentation**: Architectural decisions and patterns are documented for future maintenance
4. **Code Navigation**: Understanding where functionality is located and how components interact

## Maintenance

When making structural changes to the codebase:

1. Update the relevant structure document to reflect changes
2. Maintain consistent frontmatter format
3. Document new relationships between directories
4. Update naming conventions if they evolve
5. Keep architecture descriptions current with implementation

## Analysis Methodology

These documents were generated using Gemini MCP (Model: gemini-2.5-flash) with systematic analysis of:

- Directory contents and file organization
- Naming patterns across files, classes, and functions
- Import statements and dependency relationships
- Architectural patterns and design decisions
- Integration points between modules

Each document represents a depth 0-1 analysis from the root directory, providing comprehensive coverage of the codebase structure.
