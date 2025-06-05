#!/usr/bin/env python3
"""Fix exception chaining issues (B904) in Python files."""

import re
import sys
from pathlib import Path


def fix_exception_chaining(file_path):
    """Fix exception chaining in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False
    
    modified = False
    new_lines = []
    in_except_block = False
    except_var = None
    
    for i, line in enumerate(lines):
        # Check if we're entering an except block
        except_match = re.match(r'^(\s*)except\s+(\w+)(?:\s+as\s+(\w+))?:\s*$', line)
        if except_match:
            in_except_block = True
            except_var = except_match.group(3)
            new_lines.append(line)
            continue
        
        # Check if we're exiting the except block
        if in_except_block and line.strip() and not line.startswith((' ', '\t')):
            in_except_block = False
            except_var = None
        
        # Check for raise statements in except blocks
        if in_except_block and 'raise' in line:
            raise_match = re.match(r'^(\s*)raise\s+(\w+\(.*?\))\s*$', line)
            if raise_match and 'from' not in line:
                indent = raise_match.group(1)
                raise_stmt = raise_match.group(2)
                if except_var:
                    new_lines.append(f'{indent}raise {raise_stmt} from {except_var}\n')
                else:
                    new_lines.append(f'{indent}raise {raise_stmt} from None\n')
                modified = True
                continue
        
        new_lines.append(line)
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    return False


def main():
    """Fix exception chaining in all Python files."""
    fixed_count = 0
    
    # Find all Python files in src and tests
    for directory in ['src', 'tests']:
        if Path(directory).exists():
            for py_file in Path(directory).rglob('*.py'):
                try:
                    if fix_exception_chaining(py_file):
                        print(f"Fixed: {py_file}")
                        fixed_count += 1
                except Exception as e:
                    print(f"Error processing {py_file}: {e}")
    
    print(f"\nFixed {fixed_count} files")
    return 0


if __name__ == '__main__':
    sys.exit(main())