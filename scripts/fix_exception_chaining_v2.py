#!/usr/bin/env python3
"""Fix exception chaining issues (B904) in Python files - Version 2."""

import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple

def fix_exception_chaining_in_file(file_path: Path) -> Tuple[bool, int]:
    """Fix exception chaining in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        lines = content.splitlines()
        changes = 0
        
        # Common patterns to fix
        patterns = [
            # Simple raise with string
            (r'(\s+)except\s+(\w+)(?:\s+as\s+(\w+))?:\s*\n(?:\s*#.*\n)*(\s+)raise\s+(\w+)\((.*?)\)\s*$',
             lambda m: f'{m.group(1)}except {m.group(2)}{" as " + m.group(3) if m.group(3) else ""}:\n{m.group(4)}raise {m.group(5)}({m.group(6)}) from {"None" if not m.group(3) else m.group(3)}'),
            
            # Multi-line raise with continuation
            (r'(\s+)except\s+(\w+)(?:\s+as\s+(\w+))?:\s*\n(?:[^\n]*\n)*?(\s+)raise\s+(\w+)\(\s*\n([^)]+)\)\s*(?<!from\s\w+)\s*$',
             lambda m: m.group(0).rstrip() + f' from {"None" if not m.group(3) else m.group(3)}'),
        ]
        
        # Process file line by line for more precise handling
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check if this is an except line
            except_match = re.match(r'^(\s*)except\s+(.+?)(?:\s+as\s+(\w+))?\s*:\s*$', line)
            if except_match:
                indent = except_match.group(1)
                exception_type = except_match.group(2)
                exception_var = except_match.group(3)
                
                # Look for raise statements in the except block
                j = i + 1
                while j < len(lines) and (not lines[j].strip() or lines[j].startswith(indent + ' ') or lines[j].startswith(indent + '\t')):
                    raise_line = lines[j]
                    
                    # Check for simple raise statements
                    simple_raise_match = re.match(r'^(\s+)raise\s+(\w+)\((.*?)\)\s*$', raise_line)
                    if simple_raise_match and not re.search(r'\s+from\s+', raise_line):
                        # Add 'from' clause
                        new_line = raise_line.rstrip() + f' from {exception_var if exception_var else "None"}'
                        lines[j] = new_line
                        changes += 1
                        break
                    
                    # Check for multi-line raise statements
                    if re.match(r'^(\s+)raise\s+\w+\(\s*$', raise_line):
                        # Find the closing parenthesis
                        k = j + 1
                        while k < len(lines) and not re.match(r'^[^)]*\)\s*$', lines[k]):
                            k += 1
                        if k < len(lines) and not re.search(r'\s+from\s+', lines[k]):
                            lines[k] = lines[k].rstrip() + f' from {exception_var if exception_var else "None"}'
                            changes += 1
                            j = k
                            break
                    
                    j += 1
            
            i += 1
        
        # Write back if changes were made
        if changes > 0:
            new_content = '\n'.join(lines)
            if not new_content.endswith('\n'):
                new_content += '\n'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True, changes
        
        return False, 0
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0

def main():
    """Main function to fix exception chaining in all Python files."""
    # Get all Python files in src and tests directories
    python_files = []
    for directory in ['src', 'tests']:
        if Path(directory).exists():
            python_files.extend(Path(directory).rglob('*.py'))
    
    total_files_changed = 0
    total_changes = 0
    
    for file_path in python_files:
        changed, num_changes = fix_exception_chaining_in_file(file_path)
        if changed:
            print(f"Fixed {num_changes} exception(s) in {file_path}")
            total_files_changed += 1
            total_changes += num_changes
    
    print(f"\nTotal: Fixed {total_changes} exceptions in {total_files_changed} files")

if __name__ == '__main__':
    main()