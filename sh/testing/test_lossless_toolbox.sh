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

# Test 4: Metadata Title
echo "Test 4: Metadata Title"
cat <<EOF > /tmp/zenity_responses
Edit Metadata
set_title
TestTitle
EOF
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "title=TestTitle" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

echo -e "\n${GREEN}Lossless Toolbox Tests Finished!${NC}"
exit $FAILED
