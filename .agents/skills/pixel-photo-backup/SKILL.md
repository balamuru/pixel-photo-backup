---
name: pixel-photo-backup
description: Backs up batches/subdirectories of photos/videos to an attached Google Pixel device via MTP.
---

# Pixel Photo Backup Skill

Use this skill when the user wants to back up directories of photos/videos to an attached Google Pixel device via USB/MTP.

## Execution Flow

1. **Locate the attached Google Pixel**
   - The device is mounted under GVFS at `/run/user/<uid>/gvfs/mtp:host=Google_Pixel_<device_serial>/Internal shared storage/DCIM/Camera`.
   - Verify the mount is active by listing `/run/user/<uid>/gvfs/`.
   - If the folder is empty or not found, ask the user to unlock the phone and switch USB usage to **File Transfer / Android Auto**.

2. **(Optional) Ingest Media from Source Phone**
   - If the user wants to pull photos and WhatsApp media from their primary phone first, run:
     ```bash
     python3 pull_source_media.py
     ```
     This copies files from the source phone's Camera and WhatsApp media folders to the local staging directory.

3. **Run the backup script**
   - The reusable script is saved at the root of the project: `backup_tool.py`.
   - The script can be configured via a local `.env` file in the project folder, containing the source directory `SRC_DIR` and optionally the destination `PIXEL_CAMERA_DIR`.
   - In your turn, you can invoke the script:
     ```bash
     python3 backup_tool.py
     ```
     Or override parameters directly:
     ```bash
     python3 backup_tool.py --src "/path/to/source" --batch-size-mb 2000
     ```
     To clear the history and start fresh:
     ```bash
     python3 backup_tool.py --src "/path/to/source" --reset-history
     ```



## Critical Guidelines
- **Use basic file copy:** MTP GVFS mounts do not support writing standard Unix file permissions, metadata, or timestamps. Always copy raw bytes using `shutil.copyfile()` or stream buffers; do NOT copy permission flags or metadata.
- **Clean the destination first:** Always ensure the Pixel Camera folder is cleared before copying a new batch to avoid duplicating or mixing batches.
- **Ensure confirmation:** Never delete images or move to the next batch until the user explicitly confirms that the current batch is backed up.
