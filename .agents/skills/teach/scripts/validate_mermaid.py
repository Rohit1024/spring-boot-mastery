#!/usr/bin/env python3
import re
import subprocess
import tempfile
import os
import glob
import sys
import json
import hashlib
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE_DIR = ".cache"
CACHE_FILE = os.path.join(CACHE_DIR, "mermaid_validation_cache.json")

def get_block_hash(block_content: str) -> str:
    """Computes SHA-256 hash of a stripped Mermaid code block."""
    return hashlib.sha256(block_content.strip().encode("utf-8")).hexdigest()

def load_cache() -> set:
    """Loads previously validated diagram hashes from cache."""
    if not os.path.exists(CACHE_FILE):
        return set()
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("valid_hashes", []))
    except Exception:
        return set()

def save_cache(valid_hashes: set):
    """Saves valid diagram hashes to cache."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"valid_hashes": sorted(list(valid_hashes))}, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save validation cache: {e}", file=sys.stderr)

def validate_block(item):
    file_path, idx, block, block_hash = item
    cleaned_block = block.strip()
    with tempfile.NamedTemporaryFile("w", suffix=".mmd", delete=False) as tmp:
        tmp.write(cleaned_block)
        tmp_path = tmp.name

    out_svg = tmp_path + ".svg"
    try:
        res = subprocess.run(
            ["npx", "-y", "@mermaid-js/mermaid-cli", "-i", tmp_path, "-o", out_svg],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            return (file_path, idx, cleaned_block, res.stderr.strip(), block_hash, False)
        return (file_path, idx, cleaned_block, None, block_hash, True)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        if os.path.exists(out_svg):
            os.remove(out_svg)

def main():
    parser = argparse.ArgumentParser(description="Incremental Mermaid Diagram Validator")
    parser.add_argument("--force", "--all", action="store_true", help="Force validation on all diagrams, ignoring cache")
    parser.add_argument("--clear-cache", action="store_true", help="Clear existing validation cache and exit")
    parser.add_argument("files", nargs="*", help="Optional specific files to scan")
    args = parser.parse_args()

    if args.clear_cache:
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            print(f"Cleared cache at {CACHE_FILE}")
        else:
            print("No cache file found.")
        sys.exit(0)

    if args.files:
        files = args.files
    else:
        pattern = "docs/**/*.md"
        files = glob.glob(pattern, recursive=True)

    cache = set() if args.force else load_cache()

    items_to_validate = []
    total_found = 0
    cached_count = 0

    for file_path in sorted(files):
        if not os.path.exists(file_path):
            continue
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        blocks = re.findall(r"```\s*mermaid\s*\n(.*?)\n```", content, re.DOTALL)
        for idx, block in enumerate(blocks, 1):
            total_found += 1
            b_hash = get_block_hash(block)
            if not args.force and b_hash in cache:
                cached_count += 1
            else:
                items_to_validate.append((file_path, idx, block, b_hash))

    print(f"Found {total_found} Mermaid diagram(s) across {len(files)} file(s).")
    if not args.force:
        print(f"⚡ {cached_count} diagram(s) already verified in cache (skipped).")
        print(f"🔍 Validating {len(items_to_validate)} new/modified diagram(s)...")
    else:
        print(f"🔍 Force-validating all {len(items_to_validate)} diagram(s)...")

    errors = []
    new_valid_hashes = set()

    if items_to_validate:
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(validate_block, item): item for item in items_to_validate}
            for future in as_completed(futures):
                file_path, idx, code, err, b_hash, is_valid = future.result()
                if not is_valid:
                    print(f"\n❌ ERROR in {file_path} (diagram #{idx}):")
                    print(err)
                    print("--- Code ---")
                    print(code)
                    print("------------\n")
                    errors.append((file_path, idx, code, err))
                else:
                    new_valid_hashes.add(b_hash)

    # Update cache with newly validated valid hashes
    if not errors and new_valid_hashes:
        cache.update(new_valid_hashes)
        save_cache(cache)
    elif new_valid_hashes:
        cache.update(new_valid_hashes)
        save_cache(cache)

    print(f"\n==========================================")
    print(f"Mermaid Syntax Verification Report:")
    print(f"Total diagrams scanned: {total_found}")
    print(f"Cached (already verified): {cached_count}")
    print(f"Newly validated: {len(items_to_validate)}")
    print(f"Total syntax errors: {len(errors)}")
    print(f"==========================================")

    if errors:
        sys.exit(1)
    else:
        print("✅ All Mermaid diagrams passed syntax validation successfully!")

if __name__ == "__main__":
    main()
