#!/bin/bash
# Concatenate (Join)
# Stitches selected files together (Must be same format/codec).

DIR="$(dirname "$0")"
source "$DIR/common.sh"

# Create a temporary list file in current dir
LISTFILE=$(get_cwd_temp "concat_list")

(
# Sort files to ensure order? Nautilus sends them in selection order usually.
for f in "$@"; do
    # Use printf %q to escape special characters (spaces, quotes) safely
    SAFE_F=$(printf '%q' "$f")
    echo "file $SAFE_F" >> "$LISTFILE"
done

echo "# Joining files..."
# -safe 0 allows absolute paths (though we use relative now)
# -nostdin prevents ffmpeg from hanging waiting for input in background scripts
ffmpeg -y -nostdin -f concat -safe 0 -i "$LISTFILE" -c copy "joined_output.mp4"

rm -f "$LISTFILE"
) | Z_PROGRESS "Joining Videos..."

zenity --notification --text="Join Finished! (Saved as joined_output.mp4)"
