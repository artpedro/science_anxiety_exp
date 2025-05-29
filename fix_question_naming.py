import os
import shutil # For a potentially safer rename, though os.rename is usually fine for this.

# --- Configuration ---
# Directory containing the files to rename. Use '.' for the current directory.
TARGET_DIRECTORY = '.'

# Text to find and replace in the main part of the filename
TEXT_TO_REPLACE = "conheciemnto geral"
REPLACEMENT_TEXT = "control"

# Suffix transformation rules:
# Each tuple is (original_suffix_to_match, new_suffix_to_apply)
# The script will check these in order. The first match wins.
# IMPORTANT: These suffixes are checked AFTER the TEXT_TO_REPLACE has been done.
SUFFIX_TRANSFORMATIONS = [
    ("_false.wav", "_true.wav"),  # If it now ends with _control_false.wav -> _control_true.wav
    ("_0.wav", "_false.wav"),      # If it now ends with _control_0.wav   -> _control_false.wav
]

# Set to False to actually rename files. True will only print what would happen.
DRY_RUN = True
# --- End of Configuration ---

def rename_files_in_directory(directory):
    print(f"Scanning directory: {os.path.abspath(directory)}\n")
    renamed_count = 0
    skipped_count = 0
    error_count = 0

    for filename in os.listdir(directory):
        original_filepath = os.path.join(directory, filename)

        # Skip if it's not a file
        if not os.path.isfile(original_filepath):
            continue

        new_filename_parts = filename # Start with the original
        made_change = False

        # 1. Replace the main text part
        if TEXT_TO_REPLACE in new_filename_parts:
            new_filename_parts = new_filename_parts.replace(TEXT_TO_REPLACE, REPLACEMENT_TEXT)
            made_change = True

        # 2. Apply suffix transformations
        #    We iterate through the rules. The first one that matches the current
        #    ending of new_filename_parts will be applied.
        temp_filename_for_suffix_check = new_filename_parts
        for old_suffix, new_suffix in SUFFIX_TRANSFORMATIONS:
            if temp_filename_for_suffix_check.endswith(old_suffix):
                # Remove the old suffix and add the new one
                base_name = temp_filename_for_suffix_check[:-len(old_suffix)]
                new_filename_parts = base_name + new_suffix
                made_change = True
                break # Important: apply only the first matching suffix rule

        # If any change was made, proceed to rename
        if made_change and filename != new_filename_parts:
            new_filepath = os.path.join(directory, new_filename_parts)
            print(f"Original: {filename}")
            print(f"Proposed: {new_filename_parts}")

            if DRY_RUN:
                print(f"DRY RUN: Would rename to '{new_filepath}'")
            else:
                try:
                    # os.rename is generally fine, shutil.move is more robust across filesystems
                    # but os.rename is atomic on the same filesystem.
                    os.rename(original_filepath, new_filepath)
                    print(f"SUCCESS: Renamed to '{new_filepath}'")
                    renamed_count += 1
                except OSError as e:
                    print(f"ERROR renaming '{filename}': {e}")
                    error_count += 1
            print("-" * 20)
        elif filename == new_filename_parts and made_change:
            # This can happen if a replacement makes it identical to original
            # or if rules are somehow circular (though not in this specific case)
            print(f"INFO: Transformations resulted in no change for '{filename}'. Skipping.")
            skipped_count +=1
            print("-" * 20)
        elif not made_change:
            # No applicable rules found for this file
            # print(f"Skipping '{filename}': No applicable transformation rules.")
            skipped_count +=1


    print("\n--- Summary ---")
    if DRY_RUN:
        print("DRY RUN complete. No files were actually changed.")
        print(f"To perform renaming, set DRY_RUN = False in the script.")
    else:
        print(f"Renaming complete.")
        print(f"Files renamed: {renamed_count}")
        print(f"Files skipped (no changes or errors): {skipped_count}")
        print(f"Errors: {error_count}")

if __name__ == "__main__":
    # Check if TARGET_DIRECTORY exists
    if not os.path.isdir(TARGET_DIRECTORY):
        print(f"Error: Target directory '{TARGET_DIRECTORY}' does not exist.")
        print("Please check the TARGET_DIRECTORY variable in the script.")
    else:
        rename_files_in_directory(TARGET_DIRECTORY)