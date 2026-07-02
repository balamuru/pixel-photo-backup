#!/usr/bin/env python3
import os
import sys
import shutil
import argparse

def create_size_batches(src_dir, dest_dir, max_size_mb, move_files=False):
    if not os.path.isdir(src_dir):
        print(f"Error: Source directory '{src_dir}' does not exist.")
        sys.exit(1)
        
    os.makedirs(dest_dir, exist_ok=True)
    
    # Convert MB to bytes
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Get all files in the source directory
    files = [f for f in os.listdir(src_dir) if os.path.isfile(os.path.join(src_dir, f))]
    files.sort()
    
    if not files:
        print(f"No files found in '{src_dir}'.")
        return
        
    print(f"Found {len(files)} files to organize.")
    print(f"Max size per batch: {max_size_mb} MB ({max_size_bytes} bytes).")
    print(f"Action: {'Moving' if move_files else 'Copying'} files.")
    
    batch_idx = 1
    current_batch_size = 0
    current_batch_files = []
    
    def process_batch(idx, batch_files):
        batch_folder_name = f"{idx:02d}_batch"
        batch_folder_path = os.path.join(dest_dir, batch_folder_name)
        os.makedirs(batch_folder_path, exist_ok=True)
        
        print(f"Creating batch {batch_folder_name} with {len(batch_files)} files...")
        for f in batch_files:
            src_path = os.path.join(src_dir, f)
            dest_path = os.path.join(batch_folder_path, f)
            try:
                if move_files:
                    shutil.move(src_path, dest_path)
                else:
                    shutil.copyfile(src_path, dest_path)
            except Exception as e:
                print(f"  Error processing {f}: {e}")
                
    for f in files:
        f_path = os.path.join(src_dir, f)
        f_size = os.path.getsize(f_path)
        
        # If a single file exceeds the max size, it gets its own batch
        if f_size > max_size_bytes:
            # Process any accumulated batch first
            if current_batch_files:
                process_batch(batch_idx, current_batch_files)
                batch_idx += 1
                current_batch_files = []
                current_batch_size = 0
                
            process_batch(batch_idx, [f])
            batch_idx += 1
            continue
            
        if current_batch_size + f_size > max_size_bytes:
            # Process current batch and start a new one
            process_batch(batch_idx, current_batch_files)
            batch_idx += 1
            current_batch_files = [f]
            current_batch_size = f_size
        else:
            current_batch_files.append(f)
            current_batch_size += f_size
            
    # Process final batch
    if current_batch_files:
        process_batch(batch_idx, current_batch_files)
        
    print("\nBatch creation complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Organize a flat folder of files into size-bounded subdirectories.")
    parser.add_argument("src", help="Source directory containing flat files.")
    parser.add_argument("dest", help="Destination root directory where batch subfolders will be created.")
    parser.add_argument("--max-size", type=int, default=500, help="Maximum total size of each batch in MB (default: 500).")
    parser.add_argument("--move", action="store_true", help="Move files instead of copying them.")
    
    args = parser.parse_args()
    create_size_batches(args.src, args.dest, args.max_size, args.move)
