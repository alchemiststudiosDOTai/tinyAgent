# Limits Module Refactoring Plan

## Overview
This document outlines the plan to move the 'limits' module from its current location to a utility directory in the tinyagent project structure.

## Current Structure
The limits module is currently located at:
- `/home/tuna/tinyAgent/tinyagent/limits/`
  - `__init__.py` - exports ExecutionLimits and ExecutionTimeout
  - `boundaries.py` - contains core logic for resource limits

## Target Structure
We will move the limits module to a utility directory:
- `/home/tuna/tinyAgent/tinyagent/utils/limits/`

## Rationale
Moving the limits module to a utilities directory aligns with project architecture principles by:
1. Centralizing utility modules in one location
2. Making it easier for developers to locate common tools and helpers
3. Following established patterns where utilities are organized separately from core functional components

## Implementation Steps

### 1. Identify All Current Imports
First, we need to identify all places in the codebase that import from the limits module.

### 2. Create Utility Directory Structure
Create the new utility directory structure and move the files.

### 3. Update Import Statements
Update all import statements throughout the codebase to point to the new location.

## Detailed Implementation

### Step 1: Identify Current Imports
The following imports currently reference the limits module:
- `from tinyagent.limits import ExecutionLimits, ExecutionTimeout`
- `from .limits import ExecutionLimits` (in agents/code.py)
- Direct usage in multiple documentation files and execution components

### Step 2: Create Utility Directory Structure
We will create `/home/tuna/tinyAgent/tinyagent/utils/limits/` directory with:
- `__init__.py` - exports the same public interfaces
- `boundaries.py` - contains the core logic

### Step 3: Update All Import Statements
All imports referencing `tinyagent.limits` or relative paths to limits will need updating.

## Migration Impact Analysis
This refactoring is a breaking change that requires updating all import statements throughout the codebase. The impact is limited since it's only affecting internal modules, but thorough testing will be required after migration.