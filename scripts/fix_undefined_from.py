#!/usr/bin/env python3
"""Fix undefined 'from e' issues in exception raising."""

import re
from pathlib import Path

def fix_undefined_from_in_file(file_path: Path) -> bool:
    """Fix 'from e' where e is not defined."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern to find raise statements with 'from e' where e might not be defined
        # This will find lines like: raise SomeError("msg") from e
        # But not inside except blocks that define 'e'
        pattern = r'raise\s+\w+\([^)]*\)\s+from\s+(?:e|triage_error)\b'
        
        # For each match, check if it's inside an except block with 'as e'
        matches = list(re.finditer(pattern, content))
        
        for match in reversed(matches):  # Process from end to avoid offset issues
            # Get the line number
            line_start = content.rfind('\n', 0, match.start()) + 1
            line_num = content[:match.start()].count('\n')
            
            # Check if this is inside an except block with the variable defined
            # Look backwards for the nearest except block
            except_pattern = r'except\s+.*?\s+as\s+(\w+)\s*:'
            preceding_text = content[:match.start()]
            
            # Find all except blocks before this raise
            except_matches = list(re.finditer(except_pattern, preceding_text))
            
            # Check if we're inside an except block with matching variable
            is_valid = False
            if except_matches:
                last_except = except_matches[-1]
                var_name = last_except.group(1)
                
                # Check if the 'from' uses this variable
                from_match = re.search(r'from\s+(\w+)', match.group())
                if from_match and from_match.group(1) == var_name:
                    # Check that we're still inside this except block
                    # (simple heuristic: no dedent between except and raise)
                    between_text = content[last_except.end():match.start()]
                    if not re.search(r'\n(?![ \t])', between_text):  # No line with no indent
                        is_valid = True
            
            if not is_valid:
                # Remove the 'from ...' part
                new_text = re.sub(r'\s+from\s+\w+\s*$', '', match.group())
                content = content[:match.start()] + new_text + content[match.end():]
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix undefined from clauses."""
    # Get all Python files in src and tests directories
    python_files = []
    for directory in ['src', 'tests']:
        if Path(directory).exists():
            python_files.extend(Path(directory).rglob('*.py'))
    
    files_fixed = 0
    
    for file_path in python_files:
        if fix_undefined_from_in_file(file_path):
            print(f"Fixed {file_path}")
            files_fixed += 1
    
    print(f"\nTotal files fixed: {files_fixed}")

if __name__ == '__main__':
    main()