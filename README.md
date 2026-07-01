# Pixel Photo Backup Tool

This project contains a repeatable CLI script to interactively transfer batches of images/videos from your local computer to an attached Google Pixel's Camera folder (via MTP), verifying backups step-by-step to save storage on the device.

## Why this exists
Transferring massive amounts of images directly to a Google Pixel via MTP for backing up to Google Photos can overwhelm the device's storage or crash the slow/unstable MTP connection. 

This tool supports two scenarios:
1.  **Nested Subdirectories (Scenario A):** If your source directory contains folders, it will copy folder-by-folder and pause for confirmation after each folder is completed.
2.  **Flat Directory (Scenario B):** If your source directory contains no subdirectories and just a large flat list of media files, it will automatically group the files into virtual chunks/batches (e.g. 100 files at a time) and pause for confirmation after each batch is completed.

After each batch is successfully copied, it pauses, waits for you to verify that they have been backed up to the cloud (e.g. via Google Photos), deletes them from the device to free up space, and then proceeds to the next batch.

## The Pixel 1 Proxy Strategy & Advantages
Using a **first-generation Google Pixel (2016)** as a proxy device for backups offers a unique and highly beneficial setup:

*   **Unlimited Lifetime Backups:** The original Google Pixel (Pixel 1) is the only device that retains a lifetime grant of **unlimited free backups at Original Quality** to Google Photos. Photos and videos uploaded from this phone do not count against your Google Account storage quota (Google One storage).
*   **Zero Compression:** Unlike other newer phones that are capped at "Storage Saver" quality or receive no free backup quota, uploads from a Pixel 1 are stored in their raw, native resolution/quality (DSLR raw files, 4K video, ProRes/LOG formats).
*   **Cost-Efficient Archiving:** By using the Pixel 1 as a proxy, you can offload and archive massive amounts of media from other phones, cameras, or computers for free without having to pay for expensive Google One storage subscriptions.
*   **Automated Pipeline:** The script helps you easily feed media from your high-end workspace computers directly into this free backup pipeline without manual drag-and-drop fatigue or running out of storage on the Pixel's local drive during the transfer.


## Configuration (.env)
A `.env` file is used to store paths. Copy the example file and customize it:
```bash
cp .env.example .env
```
Open `.env` and set:
*   `SRC_DIR`: The path to the directory containing the subdirectories of pictures you want to back up.
*   `PIXEL_CAMERA_DIR`: (Optional) The explicit mount path to your Pixel's Camera folder. If left blank, the tool will try to auto-detect it under `/run/user/<uid>/gvfs/`.
*   `BATCH_SIZE`: (Optional) The size of virtual batches when processing flat directories (default: 100).

## Do I need a virtual environment (venv)?
**No, a virtual environment is not required.** The script relies entirely on standard Python libraries (`os`, `sys`, `shutil`, `glob`, `argparse`) so you can run it out of the box with your system Python.

If you decide to extend the tool and install third-party dependencies in the future, you can initialize a virtual environment:
```bash
# Create a venv
python3 -m venv venv

# Activate it
source venv/bin/activate
```

## How to run

1. Connect your Google Pixel to your computer via USB.
2. Unlock your phone, swipe down, select the Android System USB notification, and change the USB mode to **File Transfer / Android Auto**.
3. Run the script:
   ```bash
   ./backup_tool.py
   ```

### Overrides
You can also override the `.env` configuration using CLI arguments:
*   `--src`: Override the source directory path.
*   `--dest`: Override the destination directory path.
*   `--batch-size`: Override the batch size (default: 100).
