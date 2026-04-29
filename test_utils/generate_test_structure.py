#!/usr/bin/env python3
"""
Generate test directory structure for Notarizer testing.
Platform-independent script that creates nested directories, many files, and unusual character names.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# ============================================================================
# CONFIGURATION PARAMETERS - Edit these as needed
# ============================================================================

# Base directory where the test structure will be created
BASE_DIR = Path("./test_structure")

# Nested directory structure parameters
NESTING_DEPTH = 30                    # Number of nested folder levels (depth of each chain)
NESTED_FOLDERS_COUNT = 1              # Number of parallel chains (each chain is NESTING_DEPTH levels deep)

# Large file directory parameters
LARGE_DIR_FILE_COUNT = 1000           # Number of files in the "many files" directory

# Unusual characters test parameters
UNUSUAL_CHARS_ENABLED = True          # Enable/disable unusual character tests
UNUSUAL_FILES_COUNT = 50              # Number of files with unusual names
UNUSUAL_DIRS_COUNT = 10               # Number of directories with unusual names

# Safety check: prevent creating in critical directories
SAFETY_CHECK_ENABLED = True
PROHIBITED_DIRS = [
    Path("/usr"),
    Path("/etc"),
    Path("/var"),
    Path("/sys"),
    Path("/proc"),
    Path("/bin"),
    Path("/sbin"),
    Path("/lib"),
    Path("/lib64"),
    Path("/boot"),
    Path("/root"),
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def safety_check(base_dir: Path) -> bool:
    """Check if the base directory is safe to use."""
    if not SAFETY_CHECK_ENABLED:
        return True
    
    abs_base = base_dir.resolve()
    
    # Check if any prohibited directory is exactly the base_dir or a parent of base_dir
    for prohibited in PROHIBITED_DIRS:
        try:
            prohibited_resolved = prohibited.resolve()
            # Only block if we're creating directly in or under a specific system directory
            # Use is_relative_to if available (Python 3.9+), otherwise use string comparison
            try:
                is_under = abs_base.is_relative_to(prohibited_resolved)
            except AttributeError:
                # Fallback for Python < 3.9
                abs_base_str = str(abs_base)
                prohibited_str = str(prohibited_resolved)
                is_under = abs_base_str.startswith(prohibited_str + "/") or abs_base_str == prohibited_str
            
            if abs_base == prohibited_resolved or is_under:
                print(f"ERROR: Cannot create test structure in or under {prohibited_resolved}")
                print("This is a safety check to prevent accidental damage to system directories.")
                return False
        except (OSError, ValueError):
            # Handle cases where path resolution fails (e.g., non-existent paths)
            continue
    
    return True


def create_directory_safe(path: Path) -> bool:
    """Create a directory safely, handling errors."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as e:
        print(f"WARNING: Failed to create directory {path}: {e}")
        return False


def create_file_safe(path: Path, content: str = "") -> bool:
    """Create a file safely, handling errors."""
    try:
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return True
    except OSError as e:
        print(f"WARNING: Failed to create file {path}: {e}")
        return False


# ============================================================================
# STRUCTURE GENERATION FUNCTIONS
# ============================================================================

def create_nested_structure(base_path: Path) -> int:
    """Create a deeply nested directory structure.
    
    Creates NESTED_FOLDERS_COUNT separate chains, each NESTING_DEPTH levels deep.
    
    Returns:
        Number of directories created.
    """
    print(f"\nCreating nested directory structure ({NESTED_FOLDERS_COUNT} chains, each {NESTING_DEPTH} levels deep)...")
    
    created_count = 0
    nested_base = base_path / "nested_deep"
    
    if not create_directory_safe(nested_base):
        return 0
    
    created_count = 1  # Count the base directory
    
    # Create multiple parallel chains of nested directories
    for chain_num in range(NESTED_FOLDERS_COUNT):
        current_path = nested_base / f"chain_{chain_num:03d}"
        
        if not create_directory_safe(current_path):
            continue
        
        created_count += 1
        
        # Create a linear chain of nested directories
        for level in range(1, NESTING_DEPTH + 1):
            folder_name = f"level_{level:03d}"
            folder_path = current_path / folder_name
            
            if create_directory_safe(folder_path):
                created_count += 1
                # Create a test file in each directory with level in filename
                test_file = folder_path / f"test_level_{level:03d}.txt"
                create_file_safe(test_file, f"Test file at level {level}, chain {chain_num}\n")
                current_path = folder_path  # Move deeper
            else:
                break  # Stop this chain if we can't create a directory
        
        # Show progress
        if (chain_num + 1) % max(1, NESTED_FOLDERS_COUNT // 10) == 0:
            progress = ((chain_num + 1) / NESTED_FOLDERS_COUNT) * 100
            print(f"  Progress: {chain_num + 1}/{NESTED_FOLDERS_COUNT} chains ({progress:.1f}%)")
    
    print(f"Created {created_count} nested directories.")
    return created_count


def create_many_files_structure(base_path: Path) -> int:
    """Create a directory with many files.
    
    Returns:
        Number of files created.
    """
    print(f"\nCreating directory with many files ({LARGE_DIR_FILE_COUNT} files)...")
    
    many_files_base = base_path / "many_files"
    
    if not create_directory_safe(many_files_base):
        return 0
    
    created_count = 0
    
    # Create files in batches and show progress
    batch_size = max(1, LARGE_DIR_FILE_COUNT // 10)
    
    for i in range(LARGE_DIR_FILE_COUNT):
        file_name = f"file_{i:06d}.txt"
        file_path = many_files_base / file_name
        
        content = f"Test file {i}\nThis is file number {i:06d} in the many_files directory.\n"
        
        if create_file_safe(file_path, content):
            created_count += 1
        
        # Show progress every batch
        if (i + 1) % batch_size == 0:
            progress = ((i + 1) / LARGE_DIR_FILE_COUNT) * 100
            print(f"  Progress: {i + 1}/{LARGE_DIR_FILE_COUNT} files ({progress:.1f}%)")
    
    print(f"Created {created_count} files in many_files directory.")
    return created_count


def create_unusual_names_structure(base_path: Path) -> int:
    """Create files and directories with unusual character names.
    
    Returns:
        Number of items created.
    """
    if not UNUSUAL_CHARS_ENABLED:
        print("\nSkipping unusual character names (UNUSUAL_CHARS_ENABLED is False).")
        return 0
    
    print(f"\nCreating structure with unusual character names...")
    
    unusual_base = base_path / "unusual_names"
    
    if not create_directory_safe(unusual_base):
        return 0
    
    created_count = 0
    
    # Define unusual name patterns
    unusual_patterns = [
        # Spaces
        "file with spaces.txt",
        "  leading spaces.txt",
        "trailing spaces  .txt",
        "multiple   spaces.txt",
        "directory with spaces/",
        
        # Special characters
        "file(with)parentheses.txt",
        "file[with]brackets.txt",
        "file{with}braces.txt",
        "file'with'quotes.txt",
        'file"with"doublequotes.txt',
        "file&with&ampersand.txt",
        "file#with#hash.txt",
        "file%with%percent.txt",
        "file@with@at.txt",
        "file!with!exclamation.txt",
        "file?with?question.txt",
        "file*with*asterisk.txt",
        "file;with;semicolon.txt",
        "file:with:colon.txt",
        "file,with,comma.txt",
        "file|with|pipe.txt",
        "file<with>angle.txt",
        "file=with=equals.txt",
        "file+with+plus.txt",
        
        # Unicode characters
        "file_äöü_umlaut.txt",
        "file_ñ_spanish.txt",
        "file_é_accent.txt",
        "file_中文_chinese.txt",
        "file_日本語_japanese.txt",
        "file_русский_russian.txt",
        "file_العربية_arabic.txt",
        "file_Ελληνικά_greek.txt",
        
        # Emojis (if supported by filesystem)
        "file_📁_emoji.txt",
        "file_⚡_lightning.txt",
        "file_🎉_celebration.txt",
        
        # Very long names
        "file_with_very_" + "long_" * 20 + "name.txt",
        "a" * 200 + ".txt",
        
        # Hidden files (starting with dot)
        ".hidden_file.txt",
        ".another_hidden.txt",
        "directory/.hidden_in_subdir.txt",
        
        # Mixed patterns
        "file with spaces & symbols (test).txt",
        "directory with spaces & symbols/",
        "unicode_äöü_&_symbols.txt",
    ]
    
    # Create directories with unusual names
    print("  Creating directories with unusual names...")
    for i in range(UNUSUAL_DIRS_COUNT):
        if i < len(unusual_patterns):
            dir_name = unusual_patterns[i] if unusual_patterns[i].endswith('/') else unusual_patterns[i] + '_dir'
            dir_name = dir_name.rstrip('/')
        else:
            dir_name = f"unusual_dir_{i:03d}"
        
        dir_path = unusual_base / dir_name
        if create_directory_safe(dir_path):
            created_count += 1
            # Create a file inside
            test_file = dir_path / "test.txt"
            create_file_safe(test_file, f"Test file in unusual directory: {dir_name}\n")
    
    # Create files with unusual names
    print("  Creating files with unusual names...")
    file_patterns = [p for p in unusual_patterns if p.endswith('.txt')]
    
    for i in range(UNUSUAL_FILES_COUNT):
        if i < len(file_patterns):
            file_name = file_patterns[i]
        else:
            file_name = f"unusual_file_{i:03d}.txt"
        
        file_path = unusual_base / file_name
        content = f"Test file with unusual name: {file_name}\n"
        
        if create_file_safe(file_path, content):
            created_count += 1
    
    # Create nested structure with unusual names
    print("  Creating nested structure with unusual names...")
    nested_unusual = unusual_base / "nested_unusual"
    if create_directory_safe(nested_unusual):
        created_count += 1
        
        # Create subdirectories and files
        for i in range(5):
            subdir_name = f"subdir_{i}_with spaces & symbols"
            subdir_path = nested_unusual / subdir_name
            if create_directory_safe(subdir_path):
                created_count += 1
                for j in range(3):
                    file_name = f"file_{j}_with unusual chars.txt"
                    file_path = subdir_path / file_name
                    if create_file_safe(file_path, f"File {j} in {subdir_name}\n"):
                        created_count += 1
    
    print(f"Created {created_count} items with unusual character names.")
    return created_count


# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    """Main function to generate the test structure."""
    print("=" * 70)
    print("Notarizer Test Structure Generator")
    print("=" * 70)
    print(f"Base directory: {BASE_DIR}")
    print(f"Nesting depth: {NESTING_DEPTH}")
    print(f"Nested folders per level: {NESTED_FOLDERS_COUNT}")
    print(f"Large file count: {LARGE_DIR_FILE_COUNT}")
    print(f"Unusual characters enabled: {UNUSUAL_CHARS_ENABLED}")
    print("=" * 70)
    
    # Convert to Path if it's a string
    base_path = Path(BASE_DIR)
    
    # Safety check
    if not safety_check(base_path):
        print("\nAborting due to safety check failure.")
        sys.exit(1)
    
    # Check if directory already exists
    if base_path.exists():
        response = input(f"\nDirectory {base_path} already exists. Overwrite? [y/N]: ").strip().lower()
        if response != 'y':
            print("Aborted.")
            sys.exit(0)
        print(f"\nRemoving existing directory {base_path}...")
        try:
            import shutil
            shutil.rmtree(base_path)
            print("Removed.")
        except OSError as e:
            print(f"ERROR: Failed to remove existing directory: {e}")
            sys.exit(1)
    
    print(f"\nCreating test structure in {base_path}...")
    
    # Create the base directory
    if not create_directory_safe(base_path):
        print(f"ERROR: Failed to create base directory {base_path}")
        sys.exit(1)
    
    total_dirs = 0
    total_files = 0
    
    try:
        # Create nested structure
        dirs_created = create_nested_structure(base_path)
        total_dirs += dirs_created
        
        # Create many files structure
        files_created = create_many_files_structure(base_path)
        total_files += files_created
        
        # Create unusual names structure
        items_created = create_unusual_names_structure(base_path)
        # Note: items_created includes both dirs and files, we'll approximate
        total_dirs += items_created // 2
        total_files += items_created // 2
        
        print("\n" + "=" * 70)
        print("Test structure generation complete!")
        print("=" * 70)
        print(f"Total directories created: ~{total_dirs}")
        print(f"Total files created: ~{total_files}")
        print(f"Base directory: {base_path.resolve()}")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\nGeneration interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: Unexpected error during generation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

