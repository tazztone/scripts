#!/bin/bash
# testing/test_lossless_toolbox.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"
[ "$HEADLESS" = true ] && setup_mock_zenity
generate_test_media
FAILED=0

echo -e "\n${YELLOW}=== Lossless Operations Toolbox Tests ===${NC}"

# Test 1: Remux (MOV -> MP4)
echo "Test 1: Remux (MOV -> MP4)"
cat <<EOF > /tmp/zenity_responses
Change Format
mp4
EOF
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "vcodec=h264" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# Test 2: Trim (Lossless)
echo "Test 2: Lossless Trim"
cat <<EOF > /tmp/zenity_responses
Trim Video
00:00:00|00:00:00.5
EOF
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "duration=0.5" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# Test 3: Remove Audio
echo "Test 3: Remove Audio"
cat <<EOF > /tmp/zenity_responses
Edit Streams
remove_audio
EOF
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "no_audio" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# Test 4: Metadata Title
echo "Test 4: Metadata Title"
cat <<EOF > /tmp/zenity_responses
Edit Metadata
set_title
TestTitle
EOF
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "title=TestTitle" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# Test 5: Metadata Clean
echo "Test 5: Metadata Clean"
cat <<EOF > /tmp/zenity_responses
Edit Metadata
clean_metadata
EOF
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "vcodec=h264" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# Test 6: Merge Videos
echo "Test 6: Merge Videos"
cp "$TEST_DATA/input.mp4" "$TEST_DATA/input2.mp4"
cat <<EOF > /tmp/zenity_responses
Merge Videos
$TEST_DATA/merged.mp4
EOF
# Use --pattern merged.mp4 since we specified an explicit output name
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "duration=2.0" --pattern "merged.mp4" "$TEST_DATA/input.mp4" "$TEST_DATA/input2.mp4" || FAILED=$((FAILED+1))
rm "$TEST_DATA/input2.mp4"

echo -e "\n${GREEN}Lossless Toolbox Tests Finished!${NC}"
exit $FAILED
