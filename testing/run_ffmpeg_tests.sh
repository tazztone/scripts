#!/bin/bash

# run_ffmpeg_tests.sh
# Tests all scripts in the ffmpeg/ directory

FFMPEG_DIR="../ffmpeg"
TEST_DATA_DIR="./test_data"
mkdir -p "$TEST_DATA_DIR"

echo "Generating test media..."
# 10s test video with audio
ffmpeg -f lavfi -i testsrc=duration=10:size=1280x720:rate=30 -f lavfi -i sine=frequency=1000:duration=10 -c:v libx264 -c:a aac -shortest -y "$TEST_DATA_DIR/src.mp4"
# Small watermark image
ffmpeg -f lavfi -i color=c=red:s=100x100:d=1 -frames:v 1 -y "$TEST_DATA_DIR/watermark.png"

cd "$FFMPEG_DIR" || exit 1

run_test() {
    echo "----------------------------------------------------"
    echo "TESTING: $1"
    eval "$2"
    if [ $? -eq 0 ]; then
        echo "SUCCESS: $1"
    else
        echo "FAILED: $1"
    fi
}

run_test "003-scale-video" "./003-scale-video.sh ../testing/$TEST_DATA_DIR/src.mp4 640 ../testing/$TEST_DATA_DIR/scaled.mp4"
run_test "004-convert-format" "./004-convert-format.sh ../testing/$TEST_DATA_DIR/src.mp4 mkv ../testing/$TEST_DATA_DIR/converted.mkv"
run_test "005-extract-audio" "./005-extract-audio.sh ../testing/$TEST_DATA_DIR/src.mp4 mp3" # outputs to src.mp3 in test_data
run_test "006-trim-video" "./006-trim-video.sh ../testing/$TEST_DATA_DIR/src.mp4 00:00:02 5 ../testing/$TEST_DATA_DIR/trimmed.mp4"
run_test "007-compress-video" "./007-compress-video.sh ../testing/$TEST_DATA_DIR/src.mp4 28 ultrafast ../testing/$TEST_DATA_DIR/compressed.mp4"
run_test "008-concat-videos" "./008-concat-videos.sh ../testing/$TEST_DATA_DIR/concat.mp4 ../testing/$TEST_DATA_DIR/src.mp4 ../testing/$TEST_DATA_DIR/trimmed.mp4"
run_test "009-make-gif" "./009-make-gif.sh ../testing/$TEST_DATA_DIR/src.mp4 0 2 320 ../testing/$TEST_DATA_DIR/output.gif"
run_test "010-add-watermark" "./010-add-watermark.sh ../testing/$TEST_DATA_DIR/src.mp4 ../testing/$TEST_DATA_DIR/watermark.png center ../testing/$TEST_DATA_DIR/watermarked.mp4"
run_test "011-generate-thumbnails" "./011-generate-thumbnails.sh ../testing/$TEST_DATA_DIR/src.mp4 2 ../testing/$TEST_DATA_DIR/thumb_%03d.jpg"

echo "----------------------------------------------------"
echo "Cleaning up..."
# Keep the script results for manual check if needed, but remove the source
# rm -rf "$TEST_DATA_DIR"
echo "Tests completed. Check $TEST_DATA_DIR for results."
