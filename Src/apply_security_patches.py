#!/usr/bin/env python3
"""
Apply security patches to replace subprocess calls with secure executor
"""

import os
import re
import sys
from pathlib import Path

def patch_file(file_path: str):
    """Apply security patches to a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Add import for secure executor
        if 'subprocess.run' in content or 'subprocess.call' in content or 'subprocess.Popen' in content:
            if 'from secure_command_executor import' not in content:
                # Find the last import statement
                import_pattern = r'(from \w+ import.*\n|import \w+.*\n)'
                imports = re.findall(import_pattern, content)
                if imports:
                    last_import = imports[-1]
                    insert_pos = content.find(last_import) + len(last_import)
                    content = content[:insert_pos] + 'from secure_command_executor import secure_run, secure_check_output, secure_popen\n' + content[insert_pos:]
                else:
                    # Add at the beginning after any shebang
                    if content.startswith('#!'):
                        first_line_end = content.find('\n') + 1
                        content = content[:first_line_end] + 'from secure_command_executor import secure_run, secure_check_output, secure_popen\n' + content[first_line_end:]
                    else:
                        content = 'from secure_command_executor import secure_run, secure_check_output, secure_popen\n' + content
        
        # Replace subprocess calls
        replacements = [
            (r'subprocess\.run\(', 'secure_run('),
            (r'subprocess\.check_output\(', 'secure_check_output('),
            (r'subprocess\.Popen\(', 'secure_popen('),
            (r'subprocess\.call\(', 'secure_run('),
        ]
        
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content)
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Patched: {file_path}")
            return True
        else:
            print(f"No changes needed: {file_path}")
            return False
            
    except Exception as e:
        print(f"Error patching {file_path}: {e}")
        return False

def main():
    """Apply patches to all Python files in the wiregate directory"""
    wiregate_dir = Path(__file__).parent / 'wiregate'
    
    if not wiregate_dir.exists():
        print(f"WireGate directory not found: {wiregate_dir}")
        return
    
    patched_files = 0
    total_files = 0
    
    # Find all Python files
    for py_file in wiregate_dir.rglob('*.py'):
        total_files += 1
        if patch_file(str(py_file)):
            patched_files += 1
    
    print(f"\nPatched {patched_files} out of {total_files} Python files")
    
    # Also patch the main wiregate.py file
    main_file = Path(__file__).parent / 'wiregate.py'
    if main_file.exists():
        if patch_file(str(main_file)):
            patched_files += 1
            print(f"Patched main file: {main_file}")

if __name__ == '__main__':
    main()
