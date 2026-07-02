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

---

## Pre-splitting Folders by Size (Optional)
If you have a very large, flat folder of photos and want to physically organize them into size-bounded subfolders *before* transferring them, you can use the included `create_batches.py` utility:

```bash
./create_batches.py /path/to/flat/photos /path/to/output/batches --max-size 500
```
This utility:
*   Groups files so that the sum of file sizes in each subfolder does not exceed the limit (e.g. `--max-size 500` for 500MB).
*   Creates directories named `01_batch`, `02_batch`, etc. inside the output path.
*   By default, it **copies** the files. Add the `--move` flag to physically move the files instead.
*   Once split, you can set `SRC_DIR` to the output folder and `backup_tool.py` will process it folder-by-folder.

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

# Optional: Number of files per batch for flat directories
BATCH_SIZE=100
```

### 3. Running the Tool
Run the executable script:
```bash
./backup_tool.py
```
*Note: You can override `.env` settings on the fly using command-line arguments (e.g., `./backup_tool.py --src /my/custom/path --batch-size 50`).*

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
