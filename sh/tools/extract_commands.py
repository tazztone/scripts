#!/usr/bin/env python3
import os
import glob
import sys

def extract_ffmpeg_commands():
    # Get the directory of the script to find the relative ffmpeg path
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ffmpeg_dir = os.path.join(base_dir, "ffmpeg")
    output_file = os.path.join(base_dir, "ffmpeg_commands_summary.txt")

    if not os.path.exists(ffmpeg_dir):
        print(f"Error: {ffmpeg_dir} not found.")
        sys.exit(1)

    scripts = sorted(glob.glob(os.path.join(ffmpeg_dir, "*.sh")))

    with open(output_file, 'w') as out:
        out.write("# FFmpeg Commands Summary\n")
        out.write("# Generated for total analysis of all scripts\n\n")

        for script in scripts:
            basename = os.path.basename(script)
            commands_found = []
            
            with open(script, 'r') as f:
                lines = f.readlines()
                capturing = False
                current_command = []
                
                for line in lines:
                    trimmed = line.strip()
                    # Start capturing when a line starts with ffmpeg (ignore comments)
                    if trimmed.startswith('ffmpeg'):
                        current_command.append(line.strip())
                        if trimmed.endswith('\\'):
                            capturing = True
                        else:
                            commands_found.append(" ".join(current_command))
                            current_command = []
                    elif capturing:
                        current_command.append(line.strip())
                        if not trimmed.endswith('\\'):
                            commands_found.append(" ".join(current_command))
                            current_command = []
                            capturing = False
            
            if commands_found:
                out.write(f"## {basename}\n")
                for cmd in commands_found:
                    # Clean up escaped newlines for a single-line view
                    clean_cmd = cmd.replace('\\', ' ').replace('  ', ' ').strip()
                    out.write(f"```bash\n{clean_cmd}\n```\n")
                out.write("\n")

    print(f"Extraction complete. Found {len(scripts)} scripts.")
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    extract_ffmpeg_commands()
