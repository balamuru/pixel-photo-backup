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

def run_backup(src_root, dest_dir=None, batch_size=100):
    if not src_root:
        print("Error: No source directory specified. Define 'SRC_DIR' in '.env' or use '--src'.")
        sys.exit(1)
        
    if not os.path.isdir(src_root):
        print(f"Error: Source directory '{src_root}' does not exist.")
        sys.exit(1)
        
    if dest_dir is None:
        dest_dir = os.environ.get("PIXEL_CAMERA_DIR") or get_pixel_camera_dir()
        if dest_dir is None:
            print("Error: Could not locate your Google Pixel Camera directory.")
            print("Ensure your phone is connected, unlocked, and set to 'File Transfer' mode,")
            print("or explicitly set 'PIXEL_CAMERA_DIR' in your '.env' file.")
            sys.exit(1)
            
    print(f"Using source directory: {src_root}")
    print(f"Using destination Pixel directory: {dest_dir}")
    
    # 1. Check for physical subdirectories in the source root
    subdirs = [os.path.join(src_root, d) for d in os.listdir(src_root) if os.path.isdir(os.path.join(src_root, d))]
    subdirs.sort()
    
    if subdirs:
        # Scenario A: Source root contains physical subdirectories (batch by subdirectories)
        print(f"\nScenario A: Found {len(subdirs)} subdirectories to process:")
        for sd in subdirs:
            print(f"  - {os.path.basename(sd)}")
            
        for sd in subdirs:
            sd_name = os.path.basename(sd)
            print(f"\n==================================================")
            print(f"Processing subdirectory: {sd_name}")
            print(f"==================================================")
            
            # Ensure destination is clear before starting
            clear_camera_dir(dest_dir)
            
            # Get files
            files_to_copy = [os.path.join(sd, f) for f in os.listdir(sd) if os.path.isfile(os.path.join(sd, f))]
            files_to_copy.sort()
            
            # Copy files
            success = copy_files(files_to_copy, dest_dir)
            if not success:
                print("Warning: Some files failed to copy.")
                
            # Ask for confirmation
            while True:
                response = input(f"\nHave you confirmed that files from '{sd_name}' are backed up on Google Photos? (yes/no): ").strip().lower()
                if response in ("yes", "y"):
                    print(f"Confirmed. Proceeding to clear the device and copy the next folder...")
                    break
                elif response in ("no", "n"):
                    print("Holding. Please verify your backups and run again when ready.")
                    sys.exit(0)
                else:
                    print("Invalid input. Please enter 'yes' or 'no'.")
    else:
        # Scenario B: Flat directory with no subdirectories. Batch the files directly.
        all_files = [os.path.join(src_root, f) for f in os.listdir(src_root) if os.path.isfile(os.path.join(src_root, f))]
        all_files.sort()
        
        if not all_files:
            print(f"No files or subdirectories found to process in '{src_root}'.")
            return
            
        total_files = len(all_files)
        # Create virtual batches
        batches = [all_files[i:i + batch_size] for i in range(0, total_files, batch_size)]
        total_batches = len(batches)
        
        print(f"\nScenario B: Flat directory found with {total_files} files.")
        print(f"Splitting into {total_batches} virtual batches (batch size: {batch_size}).")
        
        for idx, batch in enumerate(batches, 1):
            batch_name = f"Batch {idx} of {total_batches} (files {((idx-1)*batch_size)+1} - {min(idx*batch_size, total_files)})"
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
    
    # Get batch size configuration
    env_batch_size = os.environ.get("BATCH_SIZE")
    default_batch_size = int(env_batch_size) if env_batch_size and env_batch_size.isdigit() else 100
    
    parser = argparse.ArgumentParser(description="Iterative copy/backup tool for MTP Google Pixel.")
    parser.add_argument("--src", default=os.environ.get("SRC_DIR"), help="Source root directory containing subdirectories or files of images.")
    parser.add_argument("--dest", default=os.environ.get("PIXEL_CAMERA_DIR"), help="Explicit destination Camera directory (optional).")
    parser.add_argument("--batch-size", type=int, default=default_batch_size, help="Batch size when copying flat directory files (default: 100).")
    
    args = parser.parse_args()
    run_backup(args.src, args.dest, args.batch_size)
