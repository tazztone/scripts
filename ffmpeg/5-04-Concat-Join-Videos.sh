#!/bin/bash
# Concatenate (Join)
# Stitches selected files together (Must be same format/codec).

# Create a temporary list file
LISTFILE=$(mktemp)

(
# Sort files to ensure order? Nautilus sends them in selection order usually.
for f in "$@"; do
    echo "file '$f'" >> "$LISTFILE"
done

echo "# Joining files..."
# -safe 0 allows absolute paths
ffmpeg -y -f concat -safe 0 -i "$LISTFILE" -c copy "joined_output.mp4"

rm -f "$LISTFILE"
) | zenity --progress --title="Joining Videos..." --pulsate --auto-close

zenity --notification --text="Join Finished! (Saved as joined_output.mp4)"
