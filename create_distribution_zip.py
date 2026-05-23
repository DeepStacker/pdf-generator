#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IDFC Audit Engine Elite - Clean Distribution Zip Packager
Creates a clean, ready-to-distribute ZIP archive of the source code.
Excludes build artifacts, virtual environments, caches, logs, and databases.
"""

import os
import zipfile
import sys

# Target zip file name
ZIP_NAME = "IDFC_Audit_Engine_Elite_v5.0.0.zip"

# Excluded directory names (exact match or prefix match)
EXCLUDE_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "build",
    "dist",
    "scratch",
}

# Excluded file extensions or exact matches
EXCLUDE_EXTS = {
    ".zip",
    ".db",
    ".log",
    ".pyc",
    ".pyo",
    ".pyd",
    ".xlsx",
    ".pdf",
}

EXCLUDE_FILES = {
    "create_distribution_zip.py", # Exclude this packager script itself
}

def is_excluded_dir(dir_name):
    # Exclude directories starting with .venv
    if dir_name.startswith(".venv"):
        return True
    return dir_name in EXCLUDE_DIRS

def is_excluded_file(file_name):
    if file_name in EXCLUDE_FILES:
        return True
    _, ext = os.path.splitext(file_name.lower())
    if ext in EXCLUDE_EXTS:
        return True
    if file_name.startswith(".idfc_"):
        return True
    return False

def create_zip(root_dir):
    print("=" * 60)
    print("[-] IDFC AUDIT ENGINE ELITE - ZIP PACKAGER")
    print("=" * 60)
    print(f"[*] Root Directory: {root_dir}")
    print(f"[*] Target Archive:  {ZIP_NAME}")
    print("[-] Scanning files...")

    zip_path = os.path.join(root_dir, ZIP_NAME)
    
    # Remove existing zip if it exists to avoid self-inclusion or conflicts
    if os.path.exists(zip_path):
        os.remove(zip_path)

    added_files_count = 0
    total_size = 0

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for current_root, dirs, files in os.walk(root_dir):
            # Modify dirs in-place to prevent os.walk from scanning excluded directories
            dirs[:] = [d for d in dirs if not is_excluded_dir(d)]

            # Calculate relative directory path for archiving
            rel_dir = os.path.relpath(current_root, root_dir)

            for file in files:
                if is_excluded_file(file):
                    continue

                abs_file_path = os.path.join(current_root, file)
                
                # Determine name inside zip file
                if rel_dir == ".":
                    zip_entry_name = file
                else:
                    zip_entry_name = os.path.join(rel_dir, file)

                # Add to ZIP
                zipf.write(abs_file_path, zip_entry_name)
                
                # Stats
                file_size = os.path.getsize(abs_file_path)
                total_size += file_size
                added_files_count += 1
                
                print(f"  [+] Packed: {zip_entry_name} ({file_size:,} bytes)")

    print("=" * 60)
    if added_files_count > 0:
        archive_size = os.path.getsize(zip_path)
        print(f"[+++] SUCCESS: Created {ZIP_NAME} successfully!")
        print(f"[+] Total files packed:  {added_files_count}")
        print(f"[+] Uncompressed size:   {total_size:,} bytes")
        print(f"[+] Compressed ZIP size: {archive_size:,} bytes")
    else:
        print("[!!!] ERROR: No files were added to the ZIP.")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        sys.exit(1)
    print("=" * 60)

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.abspath(__file__))
    create_zip(project_root)
