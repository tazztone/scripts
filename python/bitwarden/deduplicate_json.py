#!/usr/bin/env python3
"""
Bitwarden JSON Export Deduplicator (Streamlined Mode)

This script removes duplicate folders and items from a Bitwarden JSON export file.
It ignores 'notes' and URIs to aggressively find duplicates, but protects
entries if their Names, Passwords, Usernames, or 2FA (TOTP) seeds differ.
"""

import json
import os
import argparse
import sys


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Remove duplicates from Bitwarden JSON export files."
    )
    parser.add_argument("input_file", help="Path to the Bitwarden JSON export file")
    parser.add_argument(
        "-o", "--output", help="Path to save the deduplicated JSON file"
    )
    parser.add_argument(
        "-s", "--summary", help="Path to save the deduplication summary"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress progress output"
    )
    return parser.parse_args()


def log(message, quiet=False):
    if not quiet:
        print(message)


def normalize_uri(uri):
    if not uri:
        return ""
    return uri.strip().lower().rstrip("/")


def deduplicate_bitwarden_export(
    input_file, output_file=None, summary_file=None, quiet=False
):
    if not output_file:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_deduplicated{ext}"

    log(f"Loading JSON from {input_file}...", quiet)
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        log(f"Error: {str(e)}", quiet)
        sys.exit(1)

    original_size = os.path.getsize(input_file)

    # --- Process folders ---
    original_folders_count = len(data.get("folders", []))
    unique_folders = {}
    folder_id_mapping = {}

    for folder in data.get("folders", []):
        folder_name = folder.get("name", "")
        folder_id = folder.get("id", "")

        if folder_name not in unique_folders:
            unique_folders[folder_name] = folder
            if folder_id:
                folder_id_mapping[folder_id] = folder_id
        else:
            kept_folder = unique_folders[folder_name]
            if folder_id:
                folder_id_mapping[folder_id] = kept_folder.get("id", folder_id)

    data["folders"] = list(unique_folders.values())
    deduplicated_folders_count = len(data["folders"])

    # --- Process items ---
    original_items_count = len(data.get("items", []))
    unique_items = {}
    items_to_keep = []

    for item in data.get("items", []):
        item_type = str(item.get("type", ""))
        name = (item.get("name") or "").strip().lower()

        login = item.get("login", {})
        username = ""
        password = ""
        uris_str = ""
        totp = ""

        if login:
            username = (login.get("username") or "").strip().lower()
            password = login.get("password") or ""
            totp = login.get("totp") or ""  # Safety net for 2FA codes
            uris = sorted(
                [
                    normalize_uri(u.get("uri", ""))
                    for u in login.get("uris", [])
                    if u.get("uri")
                ]
            )
            uris_str = "|".join(uris)

        # --- KEY GENERATION ---
        if item_type == "1":  # Login
            key_parts = [
                f"type:{item_type}",
                f"name:{name}",
                f"user:{username}",
                f"pass:{password}",
                f"totp:{totp}",
            ]

        elif item_type == "3":  # Card
            c = item.get("card", {})
            key_parts = [
                f"type:{item_type}",
                f"name:{name}",
                f"card:{c.get('number')}|{c.get('expMonth')}|{c.get('expYear')}",
            ]

        else:  # Secure Notes (2) & Identities (4) - Simple name match
            key_parts = [f"type:{item_type}", f"name:{name}"]

        key = "||".join(key_parts)

        if key not in unique_items:
            folder_id = item.get("folderId")
            if folder_id and folder_id in folder_id_mapping:
                item["folderId"] = folder_id_mapping[folder_id]

            unique_items[key] = True
            items_to_keep.append(item)

    data["items"] = items_to_keep
    deduplicated_items_count = len(data["items"])

    # Save the deduplicated JSON
    log(f"Saving deduplicated JSON to {output_file}...", quiet)
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        log(f"Error saving output file: {str(e)}", quiet)
        sys.exit(1)

    deduplicated_size = os.path.getsize(output_file)
    log("Deduplication complete!", quiet)

    # Prepare summary
    summary = {
        "original_file": input_file,
        "original_size": original_size,
        "original_folders": original_folders_count,
        "original_items": original_items_count,
        "deduplicated_file": output_file,
        "deduplicated_size": deduplicated_size,
        "deduplicated_folders": deduplicated_folders_count,
        "deduplicated_items": deduplicated_items_count,
        "removed_folders": original_folders_count - deduplicated_folders_count,
        "removed_items": original_items_count - deduplicated_items_count,
    }

    if summary_file:
        try:
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write("# Bitwarden Deduplication Summary (STREAMLINED)\n\n")
                f.write(f"Items removed: {summary['removed_items']}\n")
                f.write(f"Items kept: {summary['deduplicated_items']}\n")
                f.write(
                    f"\nMethod: Notes and URIs ignored. Logins protected by exact matches on Name, Pass, User, and TOTP.\n"
                )
            log(f"Summary saved to {summary_file}", quiet)
        except IOError:
            pass

    return summary


def main():
    args = parse_arguments()
    deduplicate_bitwarden_export(args.input_file, args.output, args.summary, args.quiet)


if __name__ == "__main__":
    main()
