#!/usr/bin/env python3
import os
import sys
import shutil
import glob
import argparse

def load_env(env_path=None):
    """Loads environment variables from a .env file if it exists."""
    if env_path is None:
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
                    val = val.strip().strip("'\"")
                    os.environ[key.strip()] = val

def detect_source_device(pixel_mount_path=None):
    """Attempts to locate any attached non-Pixel MTP device under GVFS."""
    uid = os.getuid()
    gvfs_dir = f"/run/user/{uid}/gvfs"
    if not os.path.isdir(gvfs_dir):
        return None
        
    mtp_mounts = glob.glob(os.path.join(gvfs_dir, "mtp:host=*"))
    if not mtp_mounts:
        return None
        
    # Filter out the Pixel device if a path or serial is provided
    # The backup Pixel in this configuration is: Google_Pixel_MB8090303718
    source_mounts = []
    for mount in mtp_mounts:
        # Normalize paths for comparison
        if pixel_mount_path and os.path.realpath(mount).startswith(os.path.realpath(pixel_mount_path)):
            continue
        if "Google_Pixel_MB8090303718" in mount:
            continue
        source_mounts.append(mount)
        
    if not source_mounts:
        return None
        
    # Return the first detected non-Pixel device
    return source_mounts[0]

def pull_files(src_folder, dest_folder):
    if not os.path.isdir(src_folder):
        print(f"Directory not found on source device: {src_folder} (skipping)")
        return
        
    os.makedirs(dest_folder, exist_ok=True)
    
    # Get files in source folder (ignoring subdirectories)
    files = [f for f in os.listdir(src_folder) if os.path.isfile(os.path.join(src_folder, f)) and not f.startswith(".")]
    if not files:
        print(f"No files in source: {src_folder}")
        return
        
    print(f"\nPulling {len(files)} files from {os.path.basename(src_folder)} -> {dest_folder}...")
    copied = 0
    skipped = 0
    failed = []
    
    for idx, f in enumerate(files, 1):
        src_file = os.path.join(src_folder, f)
        dest_file = os.path.join(dest_folder, f)
        
        # Avoid pulling if file already exists with same size
        if os.path.exists(dest_file):
            try:
                if os.path.getsize(src_file) == os.path.getsize(dest_file):
                    skipped += 1
                    continue
            except Exception:
                pass
                
        try:
            print(f"[{idx}/{len(files)}] Copying {f} ...", end="", flush=True)
            # Use copyfile to avoid copying permission bits/metadata (fails on MTP mounts)
            shutil.copyfile(src_file, dest_file)
            print(" Done")
            copied += 1
        except Exception as e:
            print(f" Failed: {e}")
            failed.append((f, str(e)))
            
    print(f"Finished pulling. Copied: {copied}, Skipped (existing): {skipped}, Failed: {len(failed)}")
    if failed:
        print("Failures:")
        for name, err in failed:
            print(f"  - {name}: {err}")

def run_pull(local_dest, source_device_path=None):
    if not local_dest:
        print("Error: No local destination directory specified. Define 'LOCAL_STAGE_DIR' in '.env' or use '--dest'.")
        sys.exit(1)
        
    if source_device_path is None:
        pixel_camera_dir = os.environ.get("BACKUP_PIXEL_CAMERA_DIR")
        # Try to extract mount root from camera directory
        pixel_mount = None
        if pixel_camera_dir:
            parts = pixel_camera_dir.split("/Internal shared storage")
            if parts:
                pixel_mount = parts[0]
                
        source_device_path = os.environ.get("SOURCE_PHONE_DIR") or detect_source_device(pixel_mount)
        if not source_device_path:
            print("Error: Could not locate your source phone device.")
            print("Ensure your source phone is connected, unlocked, and set to 'File Transfer' mode.")
            sys.exit(1)
            
    print(f"Source Phone Path: {source_device_path}")
    print(f"Local Stage Destination: {local_dest}")
    
    # Define paths to pull from the source phone
    source_paths = {
        "DCIM_Camera": os.path.join(source_device_path, "Internal shared storage", "DCIM", "Camera"),
        "WhatsApp_Images": os.path.join(source_device_path, "Internal shared storage", "Android", "media", "com.whatsapp", "WhatsApp", "Media", "WhatsApp Images"),
        "WhatsApp_Video": os.path.join(source_device_path, "Internal shared storage", "Android", "media", "com.whatsapp", "WhatsApp", "Media", "WhatsApp Video")
    }
    
    for category, path in source_paths.items():
        dest_category_dir = os.path.join(local_dest, category)
        pull_files(path, dest_category_dir)
        
    print("\nSource phone media ingestion completed!")

if __name__ == "__main__":
    load_env()
    
    parser = argparse.ArgumentParser(description="Ingest backup-able media from a source phone to local storage.")
    parser.add_argument("--dest", default=os.environ.get("LOCAL_STAGE_DIR"), help="Local directory to stage pulled media (default: value of LOCAL_STAGE_DIR env var).")
    parser.add_argument("--source-device", default=os.environ.get("SOURCE_PHONE_DIR"), help="Explicit mount directory of the source phone.")
    
    args = parser.parse_args()
    
    # Default local_dest to SRC_DIR if LOCAL_STAGE_DIR is not set (so they seamlessly align)
    local_dest = args.dest or os.environ.get("SRC_DIR")
    
    run_pull(local_dest, args.source_device)
