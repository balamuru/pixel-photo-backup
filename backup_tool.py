#!/usr/bin/env python3
import os
import sys
import shutil
import glob
import argparse

def load_env(env_path=None):
    """Loads environment variables from a .env file if it exists."""
    if env_path is None:
        # Check in the current working directory, then in the script's directory
        env_path = ".env"
        if not os.path.exists(env_path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            env_path = os.path.join(script_dir, ".env")
            
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    # Strip quotes if present
                    val = val.strip().strip("'\"")
                    os.environ[key.strip()] = val

def get_pixel_camera_dir():
    # Attempt to locate the Pixel mount dynamically under /run/user/<uid>/gvfs/
    uid = os.getuid()
    gvfs_dir = f"/run/user/{uid}/gvfs"
    if not os.path.isdir(gvfs_dir):
        return None
    
    # Look for mtp:host=Google_Pixel_*
    pixel_mounts = glob.glob(os.path.join(gvfs_dir, "mtp:host=Google_Pixel_*"))
    if not pixel_mounts:
        return None
    
    # Take the first matched mount
    mount_path = pixel_mounts[0]
    camera_path = os.path.join(mount_path, "Internal shared storage", "DCIM", "Camera")
    if os.path.isdir(camera_path):
        return camera_path
    return None

def clear_camera_dir(camera_dir):
    print(f"Clearing contents of '{camera_dir}'...")
    for item in os.listdir(camera_dir):
        if item in (".", ".."):
            continue
        item_path = os.path.join(camera_dir, item)
        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
            print(f"  Removed: {item}")
        except Exception as e:
            print(f"  Error removing {item}: {e}")

def copy_files(file_paths, dest_dir):
    total_files = len(file_paths)
    copied = 0
    failed = []
    
    for idx, src_file in enumerate(file_paths, 1):
        f = os.path.basename(src_file)
        dest_file = os.path.join(dest_dir, f)
        
        # Avoid copying if already exists with same size
        if os.path.exists(dest_file):
            try:
                if os.path.getsize(src_file) == os.path.getsize(dest_file):
                    print(f"[{idx}/{total_files}] Skipping {f} (already exists on destination)")
                    copied += 1
                    continue
            except Exception:
                pass
        
        try:
            print(f"[{idx}/{total_files}] Copying {f} ...", end="", flush=True)
            # Use copyfile to avoid copying permission bits/metadata (fails on MTP)
            shutil.copyfile(src_file, dest_file)
            print(" Done")
            copied += 1
        except Exception as e:
            print(f" Failed: {e}")
            failed.append((f, str(e)))
            
    print(f"Finished copy. Successfully copied/verified {copied}/{total_files} files.")
    return len(failed) == 0

def load_history(src_root):
    """Loads relative paths of already backed up files from the history log."""
    history_file = os.path.join(src_root, ".backup_history.txt")
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_history(src_root, rel_paths):
    """Saves relative paths of backed up files to the history log."""
    history_file = os.path.join(src_root, ".backup_history.txt")
    with open(history_file, "a") as f:
        for p in rel_paths:
            f.write(p + "\n")

def run_backup(src_root, dest_dir=None, batch_size_mb=2000, reset_history=False):
    if not src_root:
        print("Error: No source directory specified. Define 'SRC_DIR' in '.env' or use '--src'.")
        sys.exit(1)
        
    src_root = os.path.expanduser(src_root)
    if not os.path.isdir(src_root):
        print(f"Source directory '{src_root}' does not exist. Creating it...")
        os.makedirs(src_root, exist_ok=True)
        
    if not dest_dir:
        dest_dir = os.environ.get("BACKUP_PIXEL_CAMERA_DIR") or get_pixel_camera_dir()
        if not dest_dir:
            print("Error: Could not locate your Google Pixel Camera directory.")
            print("Ensure your phone is connected, unlocked, and set to 'File Transfer' mode,")
            print("or explicitly set 'BACKUP_PIXEL_CAMERA_DIR' in your '.env' file.")
            sys.exit(1)
            
    dest_dir = os.path.expanduser(dest_dir)
            
    print(f"Using source directory: {src_root}")
    print(f"Using destination Pixel directory: {dest_dir}")
    
    # Handle resetting history if requested
    history_file = os.path.join(src_root, ".backup_history.txt")
    if reset_history and os.path.exists(history_file):
        print("Resetting backup history log...")
        os.remove(history_file)
        
    # Load already backed up files
    history = load_history(src_root)
    if history:
        print(f"Loaded backup history. {len(history)} files will be skipped.")
        
    # 1. Check for physical subdirectories in the source root
    subdirs = [os.path.join(src_root, d) for d in os.listdir(src_root) if os.path.isdir(os.path.join(src_root, d))]
    subdirs.sort()
    
    if subdirs:
        # Scenario A: Source root contains physical subdirectories (batch by subdirectories)
        print(f"\nScenario A: Found {len(subdirs)} subdirectories to process:")
        
        for sd in subdirs:
            sd_name = os.path.basename(sd)
            
            # Get files and filter out already backed up files
            files_in_sd = [os.path.join(sd, f) for f in os.listdir(sd) if os.path.isfile(os.path.join(sd, f)) and not f.startswith(".")]
            files_to_copy = [p for p in files_in_sd if os.path.relpath(p, src_root) not in history]
            files_to_copy.sort()
            
            if not files_to_copy:
                print(f"Skipping subdirectory '{sd_name}' (all files already backed up).")
                continue
                
            print(f"\n==================================================")
            print(f"Processing subdirectory: {sd_name} ({len(files_to_copy)}/{len(files_in_sd)} files pending)")
            print(f"==================================================")
            
            # Ensure destination is clear before starting
            clear_camera_dir(dest_dir)
            
            # Copy files
            success = copy_files(files_to_copy, dest_dir)
            if not success:
                print("Warning: Some files failed to copy.")
                
            # Ask for confirmation
            while True:
                response = input(f"\nHave you confirmed that files from '{sd_name}' are backed up on Google Photos? (yes/no): ").strip().lower()
                if response in ("yes", "y"):
                    print(f"Confirmed. Proceeding to clear the device and copy the next folder...")
                    # Save progress to history
                    save_history(src_root, [os.path.relpath(p, src_root) for p in files_to_copy])
                    break
                elif response in ("no", "n"):
                    print("Holding. Please verify your backups and run again when ready.")
                    sys.exit(0)
                else:
                    print("Invalid input. Please enter 'yes' or 'no'.")
    else:
        # Scenario B: Flat directory with no subdirectories. Batch the files by cumulative size.
        all_files = [os.path.join(src_root, f) for f in os.listdir(src_root) if os.path.isfile(os.path.join(src_root, f)) and not f.startswith(".")]
        pending_files = [p for p in all_files if os.path.relpath(p, src_root) not in history]
        pending_files.sort()
        
        if not pending_files:
            print(f"No pending files found to process in '{src_root}' (all files already backed up).")
            return
            
        total_files = len(pending_files)
        
        # Group files into virtual batches not exceeding max size
        max_size_bytes = batch_size_mb * 1024 * 1024
        batches = []
        current_batch = []
        current_batch_bytes = 0
        
        for f_path in pending_files:
            try:
                f_size = os.path.getsize(f_path)
            except Exception:
                f_size = 0
                
            if f_size > max_size_bytes:
                # If a single file exceeds the max size, it gets its own batch
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_batch_bytes = 0
                batches.append([f_path])
                continue
                
            if current_batch_bytes + f_size > max_size_bytes:
                batches.append(current_batch)
                current_batch = [f_path]
                current_batch_bytes = f_size
            else:
                current_batch.append(f_path)
                current_batch_bytes += f_size
                
        if current_batch:
            batches.append(current_batch)
            
        total_batches = len(batches)
        
        print(f"\nScenario B: Flat directory found. {total_files} files pending backup.")
        print(f"Splitting into {total_batches} virtual batches (max size per batch: {batch_size_mb} MB).")
        
        for idx, batch in enumerate(batches, 1):
            batch_size_mb_actual = sum(os.path.getsize(p) for p in batch) / (1024 * 1024)
            batch_name = f"Batch {idx} of {total_batches} ({len(batch)} files, {batch_size_mb_actual:.1f} MB)"
            print(f"\n==================================================")
            print(f"Processing: {batch_name}")
            print(f"==================================================")
            
            # Ensure destination is clear before starting
            clear_camera_dir(dest_dir)
            
            # Copy files
            success = copy_files(batch, dest_dir)
            if not success:
                print("Warning: Some files failed to copy.")
                
            # Ask for confirmation
            while True:
                response = input(f"\nHave you confirmed that files from '{batch_name}' are backed up on Google Photos? (yes/no): ").strip().lower()
                if response in ("yes", "y"):
                    print(f"Confirmed. Proceeding to clear the device and copy the next batch...")
                    # Save progress to history
                    save_history(src_root, [os.path.relpath(p, src_root) for p in batch])
                    break
                elif response in ("no", "n"):
                    print("Holding. Please verify your backups and run again when ready.")
                    sys.exit(0)
                else:
                    print("Invalid input. Please enter 'yes' or 'no'.")
                    
    # Final clear
    clear_camera_dir(dest_dir)
    print("\nAll files processed successfully!")

if __name__ == "__main__":
    # Load environment variables from local .env
    load_env()
    
    # Get batch size configuration (default 2GB = 2000MB)
    env_batch_size_mb = os.environ.get("BATCH_SIZE_MB")
    default_batch_size_mb = int(env_batch_size_mb) if env_batch_size_mb and env_batch_size_mb.isdigit() else 2000
    
    parser = argparse.ArgumentParser(description="Iterative copy/backup tool for MTP Google Pixel.")
    parser.add_argument("--src", default=os.environ.get("SRC_DIR"), help="Source root directory containing subdirectories or files of images.")
    parser.add_argument("--dest", default=os.environ.get("BACKUP_PIXEL_CAMERA_DIR"), help="Explicit destination Camera directory (optional).")
    parser.add_argument("--batch-size-mb", type=int, default=default_batch_size_mb, help="Maximum batch size in MB when copying flat directory files (default: 2000).")
    parser.add_argument("--reset-history", action="store_true", help="Clear the backup history log and start fresh.")
    
    args = parser.parse_args()
    run_backup(args.src, args.dest, args.batch_size_mb, args.reset_history)
