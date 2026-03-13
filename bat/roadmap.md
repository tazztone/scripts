# Roadmap: 100 Script Ideas

This document outlines 100 ideas for future Windows batch scripts (and potentially PowerShell/Python scripts) to add to this repository. The goal is to build a comprehensive toolkit for file management, system maintenance, automation, and media processing.

## File Organization & Management
1. **Move files older than X days** - Move files to an "Archive" folder based on creation/modification date.
2. **Prefix filenames with date** - Add `YYYY-MM-DD_` to the beginning of all files in a folder.
3. **Remove spaces from filenames** - Replace spaces with underscores or hyphens.
4. **Lowercase filenames** - Convert all filenames in a directory to lowercase.
5. **Uppercase filenames** - Convert all filenames in a directory to uppercase.
6. **Flatten directory** - Move all files from subdirectories to the root folder.
7. **Alphabetical sorter** - Create folders A-Z and move files based on their first letter.
8. **Delete empty folders** - Recursively find and remove empty directories.
9. **List files recursively** - Generate a `filelist.txt` containing all files in a tree.
10. **Count files** - Count files in current dir and subdirs, outputting stats by extension.
11. **Compare directories** - Report missing files between two similar directory structures.
12. **Sequential rename** - Rename files to `file_001`, `file_002`, etc.
13. **Find and Replace in filenames** - Batch replace a specific string in filenames.
14. **Sort by Year** - Organize files into `Year` folders based on creation time.
15. **Sort by Size** - Move files into `Small`, `Medium`, `Large` folders.
16. **Delete specific extensions** - Recursively delete all files of a certain type (e.g., `.tmp`).
17. **Set Read-Only** - Batch make files read-only.
18. **Unset Read-Only** - Batch remove read-only attribute.
19. **Hide folders** - Set the hidden attribute for specific directories.
20. **Unhide folders** - Remove the hidden attribute.

## Media Processing (Images & ExifTool)
21. **Extract GPS to CSV** - Use ExifTool to list file path and GPS coordinates.
22. **Strip Metadata** - Remove all EXIF data for privacy.
23. **Add Copyright** - Write copyright information to EXIF Artist/Copyright tags.
24. **Timezone Fix** - Shift EXIF capture dates by X hours.
25. **Sort by Camera Model** - Organize photos into folders named after the camera used.
26. **Sort by ISO** - Organize photos based on ISO sensitivity.
27. **Sort by Lens** - Organize photos based on the lens model.
28. **Batch Resize** - Use ImageMagick to resize images to a specific width.
29. **Convert PNG to JPG** - Batch convert formats.
30. **Convert WebP to JPG** - Batch convert WebP images for compatibility.
31. **Contact Sheet** - Generate an HTML or image contact sheet of a folder.
32. **Check Corrupted** - Identify images that fail to render.
33. **Sort by Resolution** - Separate images into folders based on dimensions.
34. **Extract Raw Previews** - Extract embedded JPEGs from RAW files.
35. **Watermark Images** - Batch apply a watermark overlay.

## Media Processing (Video & Audio)
36. **Extract Audio** - Convert video files to MP3/WAV using FFmpeg.
37. **Merge Videos** - Concatenate all video files in a folder.
38. **Convert Containers** - Batch convert `.mkv` to `.mp4`.
39. **Trim Video** - Remove the first X seconds from videos.
40. **Get Durations** - List filename and duration for all videos.
41. **Generate Thumbnails** - Extract a frame from the middle of each video.
42. **Sort by Duration** - Separate short clips from long videos.
43. **Sort by Bitrate** - Identify high-quality vs low-quality files.
44. **Mute Video** - Remove the audio track from video files.
45. **Timelapse Effect** - Speed up videos by 2x, 4x, etc.

## System Maintenance & Cleanup
46. **Clean Temp Folders** - Safely delete Windows temporary files.
47. **Clear Browser Cache** - Clear cache for Chrome/Firefox/Edge.
48. **Empty Recycle Bin** - Force empty the recycle bin via command line.
49. **List Installed Programs** - Export a list of installed apps to text.
50. **Disk Space Alert** - Check free space and pop up an alert if below 10%.
51. **Run Defrag** - Wrapper to run defragmentation on specific drives.
52. **Check Disk Health** - Run `chkdsk` and log output.
53. **Find Large Files** - List all files larger than 1GB.
54. **Monitor CPU** - Log CPU usage every 5 seconds to a CSV.
55. **Restart Print Spooler** - Fix common printing issues.
56. **Flush DNS** - Clear the DNS resolver cache.
57. **Reset Network** - Release/Renew IP and flush DNS.
58. **Create Restore Point** - Trigger a Windows System Restore point.
59. **Scheduled Shutdown** - Schedule a shutdown in X minutes.
60. **Cancel Shutdown** - Abort a pending shutdown command.

## Backup & Archiving
61. **Mirror Folders** - Use Robocopy to mirror Source to Dest.
62. **Incremental Backup** - Copy only new/changed files to a backup drive.
63. **Date-Stamped Zip** - Compress a folder into `Folder_YYYYMMDD.zip`.
64. **Batch Unzip** - Extract all zip files in the current folder.
65. **Backup Bookmarks** - Copy browser bookmark files to a backup location.
66. **Registry Backup** - Export specific registry keys to `.reg` files.
67. **USB Auto-Sync** - Detect USB drive and sync specific folders.
68. **Verify Backup** - Compare source and destination file hashes.
69. **Archive Logs** - Move log files older than X days to a zip archive.
70. **Driver Backup** - Export all 3rd party drivers using `dism`.

## Network & Internet
71. **Ping Monitor** - Ping a list of servers and log downtime.
72. **Get Public IP** - Retrieve external IP address.
73. **Batch Download** - Download files from a list of URLs (curl/wget).
74. **Internet Check** - Loop to check connectivity and log outages.
75. **Active Connections** - List apps using the network (`netstat`).
76. **Block Website** - Append entry to `hosts` file (Requires Admin).
77. **Network Scan** - List devices on the local network (`arp`).
78. **Renew IP** - Simple script to refresh local IP.
79. **Speed Test** - Run a CLI speed test utility.
80. **Wifi Passwords** - Export saved Wi-Fi profiles and passwords.

## Developer Tools
81. **Init Git Repo** - Initialize git and create a standard `.gitignore`.
82. **Recursive Git Status** - Check status of all git repos in subfolders.
83. **Batch Git Pull** - Update all local repositories.
84. **Python Venv Setup** - Create venv and install `requirements.txt`.
85. **Java Compiler** - Compile and run java files in folder.
86. **Local Server** - Start a Python HTTP server in current dir.
87. **Grep Code** - Search for a string in all code files.
88. **Count Lines of Code** - Simple LOC counter for a project.
89. **Minify JSON** - Strip whitespace from JSON files.
90. **Format XML** - Pretty-print XML files.

## Miscellaneous & Productivity
91. **CLI Clock** - Display a digital clock in the terminal.
92. **Stopwatch** - Simple start/stop timer.
93. **Password Generator** - Generate random string of characters.
94. **Dice Roller** - Simulate rolling a 6-sided die.
95. **Text to Speech** - Speak the input text (via VBScript).
96. **Morning Launcher** - Open email, calendar, and news sites.
97. **Kill Non-Responsive** - Taskkill programs labeled "Not Responding".
98. **Matrix Effect** - The classic falling green numbers animation.
99. **System Info** - Display summary of OS, RAM, Processor.
100. **Toggle Theme** - Switch Windows between Dark and Light mode.
