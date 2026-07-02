# Pixel Photo Backup Tool

An interactive CLI utility to stream photo and video backups from your computer to an attached Google Pixel device via USB/MTP. Designed to orchestrate and throttle large transfers so you can leverage the Pixel's unlimited cloud backup without exhausting its local storage or crashing the MTP connection.

---

## The Pixel 1 Proxy Strategy
The original **first-generation Google Pixel (2016)** retains a lifetime grant of **unlimited free backups at Original Quality** to Google Photos. This project builds an automated bridge to this free archive pipeline:

*   **Unlimited Storage:** Uploads do not consume any Google Account or Google One storage quota.
*   **Original Quality:** Photos and videos (including raw files and 4K media) are preserved at native resolution with zero compression.
*   **Cost-Efficient Archiving:** Safely offloads media libraries from cameras, DSLRs, main computers, or newer smartphones.

---

## Why This Tool is Necessary
Moving a large photo library to a Pixel over a standard USB cable presents major issues:
1.  **Storage Exhaustion:** If your source folder is 500GB and the Pixel only has 32GB of free space, a direct copy will fail instantly.
2.  **MTP Instability:** Transferring thousands of files in a single operation regularly causes Linux GVFS/MTP mounts to hang or crash.

### The Solution: Batch & Verify
This script copies files in throttled, sequential batches. After each batch:
1.  It **pauses** and prompts you to verify that Google Photos has successfully uploaded the files to the cloud.
2.  Once you confirm, it **deletes** the files from the Pixel to free up local space.
3.  It automatically proceeds to copy the next batch.

### Crash & Interruption Recovery
The script keeps track of already backed up files in a local `.backup_history.txt` log file inside your source directory:
*   **Automatic Skip:** If the copy process is interrupted, crashes, or is stopped midway, simply run the script again. It will read the history log and immediately skip any files that have already been backed up and confirmed, picking up exactly where it left off.
*   **Reset History:** If you want to clear the history log and start the entire backup fresh, pass the `--reset-history` command-line flag.

---

## Ingesting Media from Source Phone (First Stage)
Before running the backup tool, you can pull media (Camera photos, WhatsApp Images, and WhatsApp Videos) from your primary source phone (not the Pixel device) to your computer's local staging folder:

```bash
./pull_source_media.py
```
This utility:
*   Auto-detects any attached MTP phone device (filtering out your backup Pixel).
*   Scans the standard locations on the phone for `DCIM/Camera`, `WhatsApp Images`, and `WhatsApp Video`.
*   Copies files to your local staging directory (defined as `LOCAL_STAGE_DIR` in `.env` or defaulting to `SRC_DIR`).
*   Automatically skips already copied files to enable quick resuming if the ingestion is interrupted.

---

## Getting Started

### 1. Prerequisites
*   A Google Pixel phone connected via USB.
*   The phone must be **unlocked** with USB settings set to **File Transfer / Android Auto** (usually accessible from the swipe-down notification drawer).
*   **No Virtual Environment Required:** The tool only uses standard Python libraries (`os`, `sys`, `shutil`, `glob`, `argparse`).

### 2. Configuration
Copy the configuration template:
```bash
cp .env.example .env
```
Edit `.env` to set your paths:
```env
# Path to your local photo directory (source)
SRC_DIR=/path/to/your/photos

# Optional: Manual mount path (leave empty for auto-detection)
PIXEL_CAMERA_DIR=

# Optional: The maximum cumulative size of virtual batches in MB (default: 2000)
BATCH_SIZE_MB=2000
```

### 3. Running the Tool
Run the executable script:
```bash
./backup_tool.py
```
*Note: You can override `.env` settings on the fly using command-line arguments (e.g., `./backup_tool.py --src /my/custom/path --batch-size-mb 2000 --reset-history`).*

### 4. Running the Tests
You can run the mock-based unit tests to validate the batching and recovery behavior:
```bash
python3 -m unittest test_backup_tool.py
```

---

## Driving via AI Assistants
This project is configured out-of-the-box for AI coding agents.

### Google Antigravity
The workspace contains a project-scoped skill at `.agents/skills/pixel-photo-backup/SKILL.md` that is auto-discovered when you open this directory. You can trigger it by asking:
> *"Back up my media folder to the Pixel"*

The agent will automatically manage the CLI, copy files, prompt you for verification at each checkpoint, clear the Pixel, and notify you when the entire transfer is finished.

### Claude Code & General Agents
Since the project utilizes a clean CLI interface and simple `.env` configurations, you can instruct general-purpose terminal agents:
> *"Run the photo backup script"*

The agent will run the command, monitor the logs, and interactively prompt you for confirmation before writing responses back to the subprocess.
