import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add project root to path to import backup_tool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backup_tool

class TestBackupTool(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory structure for testing
        self.test_dir = tempfile.mkdtemp()
        self.src_dir = os.path.join(self.test_dir, "src")
        self.dest_dir = os.path.join(self.test_dir, "dest")
        os.makedirs(self.src_dir)
        os.makedirs(self.dest_dir)
        
    def tearDown(self):
        # Clean up the temporary directories
        shutil.rmtree(self.test_dir)

    def test_load_and_save_history(self):
        # Verify history file operations
        rel_paths = ["file1.jpg", "dir/file2.jpg"]
        backup_tool.save_history(self.src_dir, rel_paths)
        
        history = backup_tool.load_history(self.src_dir)
        self.assertEqual(history, set(rel_paths))

    def test_reset_history(self):
        # Verify history file can be cleared
        rel_paths = ["file1.jpg"]
        backup_tool.save_history(self.src_dir, rel_paths)
        
        history_file = os.path.join(self.src_dir, ".backup_history.txt")
        self.assertTrue(os.path.exists(history_file))
        
        # Call run_backup with reset_history=True (mocking the rest of the execution)
        with patch('backup_tool.get_pixel_camera_dir', return_value=self.dest_dir):
            try:
                backup_tool.run_backup(self.src_dir, self.dest_dir, reset_history=True)
            except SystemExit:
                pass # Expected exit if no subdirs/files
                
        self.assertFalse(os.path.exists(history_file))

    def test_virtual_batching_by_size(self):
        # Create flat files of specific sizes (sizes in MB)
        # We will mock os.path.getsize to return custom sizes
        file_names = ["a.jpg", "b.jpg", "c.jpg", "d.jpg"]
        for f in file_names:
            with open(os.path.join(self.src_dir, f), "w") as fp:
                fp.write("dummy")
                
        # Mock file sizes:
        # a.jpg = 600MB
        # b.jpg = 1500MB (a + b = 2100MB > 2000MB limit -> starts new batch)
        # c.jpg = 800MB
        # d.jpg = 1300MB (c + d = 2100MB > 2000MB limit -> starts new batch)
        sizes = {
            os.path.join(self.src_dir, "a.jpg"): 600 * 1024 * 1024,
            os.path.join(self.src_dir, "b.jpg"): 1500 * 1024 * 1024,
            os.path.join(self.src_dir, "c.jpg"): 800 * 1024 * 1024,
            os.path.join(self.src_dir, "d.jpg"): 1300 * 1024 * 1024,
        }
        
        def mock_getsize(path):
            return sizes.get(path, 0)

        # Mock the run execution inputs/calls to verify batches
        with patch('os.path.getsize', side_effect=mock_getsize), \
             patch('backup_tool.copy_files', return_value=True) as mock_copy, \
             patch('backup_tool.clear_camera_dir') as mock_clear, \
             patch('builtins.input', side_effect=["y", "y", "y", "y"]):
             
            backup_tool.run_backup(self.src_dir, self.dest_dir, batch_size_mb=2000)
            
            # Verify copy was called 3 times (Batch 1: a.jpg, Batch 2: b.jpg + c.jpg, Batch 3: d.jpg)
            # Wait, let s calculate:
            # - a.jpg (600MB): current size = 600MB
            # - b.jpg (1500MB): 600MB + 1500MB = 2100MB (> 2000MB) -> Batch 1 = [a.jpg], current = [b.jpg] (1500MB)
            # - c.jpg (800MB): 1500MB + 800MB = 2300MB (> 2000MB) -> Batch 2 = [b.jpg], current = [c.jpg] (800MB)
            # - d.jpg (1300MB): 800MB + 1300MB = 2100MB (> 2000MB) -> Batch 3 = [c.jpg], current = [d.jpg] (1300MB)
            # End loop -> Batch 4 = [d.jpg]
            # Total batches = 4 (a, b, c, d all in separate batches because size sums exceed 2000MB sequentially)
            self.assertEqual(mock_copy.call_count, 4)

    def test_resume_behavior_after_interruption(self):
        # Create flat files
        file_names = ["a.jpg", "b.jpg", "c.jpg"]
        for f in file_names:
            with open(os.path.join(self.src_dir, f), "w") as fp:
                fp.write("dummy")

        # Mock sizes so each file is 1500MB (each file gets its own batch under 2000MB limit)
        sizes = {
            os.path.join(self.src_dir, "a.jpg"): 1500 * 1024 * 1024,
            os.path.join(self.src_dir, "b.jpg"): 1500 * 1024 * 1024,
            os.path.join(self.src_dir, "c.jpg"): 1500 * 1024 * 1024,
        }
        
        def mock_getsize(path):
            return sizes.get(path, 0)
            
        # Simulating that "a.jpg" was already confirmed and backed up in a previous run
        backup_tool.save_history(self.src_dir, ["a.jpg"])

        with patch('os.path.getsize', side_effect=mock_getsize), \
             patch('backup_tool.copy_files', return_value=True) as mock_copy, \
             patch('backup_tool.clear_camera_dir') as mock_clear, \
             patch('builtins.input', side_effect=["y", "y"]):
             
            backup_tool.run_backup(self.src_dir, self.dest_dir, batch_size_mb=2000)
            
            # Verify copy was called 2 times (only for b.jpg and c.jpg, skipping a.jpg)
            self.assertEqual(mock_copy.call_count, 2)
            
            # Extract paths passed to copy_files
            called_files = [os.path.basename(call.args[0][0]) for call in mock_copy.call_args_list]
            self.assertEqual(called_files, ["b.jpg", "c.jpg"])
            
            # Verify history now has a.jpg, b.jpg, and c.jpg
            history = backup_tool.load_history(self.src_dir)
            self.assertEqual(history, {"a.jpg", "b.jpg", "c.jpg"})

import pull_source_media

class TestPullSourceMedia(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.local_dest = os.path.join(self.test_dir, "local_dest")
        self.source_phone = os.path.join(self.test_dir, "source_phone")
        
        # Build source phone paths
        self.camera_path = os.path.join(self.source_phone, "Internal shared storage", "DCIM", "Camera")
        self.wa_img_path = os.path.join(self.source_phone, "Internal shared storage", "Android", "media", "com.whatsapp", "WhatsApp", "Media", "WhatsApp Images")
        self.wa_vid_path = os.path.join(self.source_phone, "Internal shared storage", "Android", "media", "com.whatsapp", "WhatsApp", "Media", "WhatsApp Video")
        
        os.makedirs(self.camera_path)
        os.makedirs(self.wa_img_path)
        os.makedirs(self.wa_vid_path)
        os.makedirs(self.local_dest)
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_detect_source_device(self):
        with patch('glob.glob', return_value=[
            "/run/user/1000/gvfs/mtp:host=Google_Pixel_MB8090303718",
            "/run/user/1000/gvfs/mtp:host=Samsung_Galaxy_S20"
        ]), patch('os.path.isdir', return_value=True):
            # Should choose the non-Pixel phone
            source = pull_source_media.detect_source_device("/run/user/1000/gvfs/mtp:host=Google_Pixel_MB8090303718")
            self.assertEqual(source, "/run/user/1000/gvfs/mtp:host=Samsung_Galaxy_S20")

    def test_run_pull_copies_files(self):
        # Create some files on the source phone
        with open(os.path.join(self.camera_path, "pic1.jpg"), "w") as f:
            f.write("dummy camera pic")
        with open(os.path.join(self.wa_img_path, "wa_pic1.jpg"), "w") as f:
            f.write("dummy whatsapp pic")
        with open(os.path.join(self.wa_vid_path, "wa_vid1.mp4"), "w") as f:
            f.write("dummy whatsapp video")
            
        # Run pull utility
        pull_source_media.run_pull(self.local_dest, self.source_phone)
        
        # Verify folders exist locally and files are copied
        self.assertTrue(os.path.exists(os.path.join(self.local_dest, "DCIM_Camera", "pic1.jpg")))
        self.assertTrue(os.path.exists(os.path.join(self.local_dest, "WhatsApp_Images", "wa_pic1.jpg")))
        self.assertTrue(os.path.exists(os.path.join(self.local_dest, "WhatsApp_Video", "wa_vid1.mp4")))
        
        # Verify content matches
        with open(os.path.join(self.local_dest, "DCIM_Camera", "pic1.jpg"), "r") as f:
            self.assertEqual(f.read(), "dummy camera pic")

if __name__ == "__main__":
    unittest.main()
