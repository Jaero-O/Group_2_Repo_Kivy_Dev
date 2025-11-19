"""
Script to fix deprecated Kivy Image properties across all KV files.

Replaces:
- allow_stretch: True/False → fit_mode: "contain"/"fill"
- keep_ratio: True/False → (removed, default behavior)
"""

import os
import re
from pathlib import Path

def fix_kv_file(filepath):
    """Fix deprecated properties in a single KV file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check if this line has allow_stretch
        if 'allow_stretch:' in line:
            indent = len(line) - len(line.lstrip())
            
            # Check next line for keep_ratio
            has_keep_ratio_next = (i + 1 < len(lines) and 'keep_ratio:' in lines[i + 1])
            
            # Replace allow_stretch with fit_mode
            if 'True' in line:
                new_lines.append(' ' * indent + 'fit_mode: "contain"')
            else:
                new_lines.append(' ' * indent + 'fit_mode: "fill"')
            
            # Skip the keep_ratio line if it follows
            if has_keep_ratio_next:
                i += 2  # Skip both lines
                continue
            else:
                i += 1
                continue
        
        # If keep_ratio appears alone (not after allow_stretch), skip it
        elif 'keep_ratio:' in line:
            i += 1
            continue
        
        # Keep the line as-is
        new_lines.append(line)
        i += 1
    
    new_content = '\n'.join(new_lines)
    
    # Write back if changed
    if new_content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    """Fix all KV files in the project."""
    kv_dir = Path(__file__).parent.parent / 'src' / 'app' / 'kv'
    
    if not kv_dir.exists():
        print(f"KV directory not found: {kv_dir}")
        return
    
    kv_files = list(kv_dir.glob('*.kv'))
    fixed_count = 0
    
    for kv_file in kv_files:
        if fix_kv_file(kv_file):
            print(f"✓ Fixed: {kv_file.name}")
            fixed_count += 1
        else:
            print(f"  Skipped: {kv_file.name} (no deprecated properties)")
    
    print(f"\n✅ Fixed {fixed_count} of {len(kv_files)} KV files")

if __name__ == '__main__':
    main()
