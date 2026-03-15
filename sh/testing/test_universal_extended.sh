#!/bin/bash
# testing/test_universal_extended.sh
# Extended tests for Universal Toolbox gaps

source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"

[ "$HEADLESS" = true ] && setup_mock_zenity
generate_test_media

echo -e "\n${YELLOW}=== Extended Universal Toolbox Tests ===${NC}"

# 1. Landscape 16:9 Crop
echo "1. Testing Landscape 16:9 Crop"
cat <<EOF > /tmp/zenity_responses
Crop / Aspect Ratio
 (Inactive)|| (Inactive)||16:9 (Landscape)|No Change||| (Inactive)| (Inactive)|Medium Default||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264" "$TEST_DATA/src.mp4"

# 2. Vertical 9:16 Crop
echo "2. Testing Vertical 9:16 Crop"
cat <<EOF > /tmp/zenity_responses
Crop / Aspect Ratio
 (Inactive)|| (Inactive)||9:16 (Vertical)|No Change||| (Inactive)| (Inactive)|Medium Default||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264" "$TEST_DATA/src.mp4"

# 3. Rotate 90 CW
echo "3. Testing Rotate 90 CW"
cat <<EOF > /tmp/zenity_responses
Rotate & Flip
 (Inactive)|| (Inactive)|| (Inactive)|Rotate 90 CW||| (Inactive)| (Inactive)|Medium Default||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264" "$TEST_DATA/src.mp4"

# 4. Audio Normalize (R128)
echo "4. Testing Audio Normalize"
cat <<EOF > /tmp/zenity_responses
Audio Tools
 (Inactive)|| (Inactive)|| (Inactive)|No Change|||Normalize (R128)| (Inactive)|Medium Default||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "acodec=aac" "$TEST_DATA/src.mp4"

# 5. Extract MP3
echo "5. Testing Extract MP3"
cat <<EOF > /tmp/zenity_responses
Audio Tools
 (Inactive)|| (Inactive)|| (Inactive)|No Change|||Extract MP3| (Inactive)|Medium Default||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "no_video,acodec=mp3" "$TEST_DATA/src.mp4"

# 6. Trim Test (Start/End)
echo "6. Testing Trim"
cat <<EOF > /tmp/zenity_responses
Trim (Cut Time)
 (Inactive)|| (Inactive)|| (Inactive)|No Change|00:00:01|00:00:01| (Inactive)| (Inactive)|Medium Default||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264" "$TEST_DATA/src.mp4"

# 7. Complex Combination: Scale 480p + Rotate 90 CCW + Mute
echo "7. Testing Complex Combination (Scale 480p + Rotate + Mute)"
cat <<EOF > /tmp/zenity_responses
Scale / Resize|Rotate & Flip|Audio Tools
 (Inactive)||480p|| (Inactive)|Rotate 90 CCW|||Remove Audio Track| (Inactive)|Medium Default||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "width=854,no_audio" "$TEST_DATA/src.mp4"

# 8. Export Format: GIF
echo "8. Testing Export GIF"
cat <<EOF > /tmp/zenity_responses
Scale / Resize
 (Inactive)|| (Inactive)|| (Inactive)|No Change||| (Inactive)| (Inactive)|Medium Default||GIF|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "format=gif" "$TEST_DATA/src.mp4"

# 9. Speed Change (2x Fast)
echo "9. Testing Speed Change (2x Fast)"
cat <<EOF > /tmp/zenity_responses
Speed Control
2x (Fast)|| (Inactive)|| (Inactive)|No Change||| (Inactive)| (Inactive)|Medium Default||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "duration=1.0" "$TEST_DATA/src.mp4"

# 10. Hardware Encoding Mock (NVENC)
echo "10. Testing Hardware Encoding Mock (NVENC)"
# Mock GPU cache
mkdir -p "/tmp"
GPU_CACHE="/tmp/scripts-sh-gpu-cache-$(id -u)"
echo "nvenc" > "$GPU_CACHE"
cat <<EOF > /tmp/zenity_responses
Scale / Resize
 (Inactive)||720p|| (Inactive)|No Change||| (Inactive)| (Inactive)|Medium Default||H.265|Use NVENC (Nvidia)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=hevc,tags=_nvenc" "$TEST_DATA/src.mp4"
rm "$GPU_CACHE"

# 11. Multi-file Processing
echo "11. Testing Multi-file Processing"
cp "$TEST_DATA/src.mp4" "$TEST_DATA/src_another.mp4"
cat <<EOF > /tmp/zenity_responses
Scale / Resize
 (Inactive)||480p|| (Inactive)|No Change||| (Inactive)| (Inactive)|Medium Default||Auto/MP4|None (CPU Only)
EOF
# run_test normally picks the newest output. For multi-file, it should run and produce 2 files.
# lib_test.sh's run_test deletes non-source files before starting, so we should be good.
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "width=854" "$TEST_DATA/src.mp4" "$TEST_DATA/src_another.mp4"
# Check if second file exists
if [ -f "$TEST_DATA/src_another_480p.mp4" ]; then
    log_pass "Multi-file processing: second output exists"
else
    log_fail "Multi-file processing: second output missing"
fi
rm "$TEST_DATA/src_another.mp4"

unset ZENITY_LIST_RESPONSE
echo -e "\n${GREEN}Extended Universal Toolbox Tests Finished!${NC}"
