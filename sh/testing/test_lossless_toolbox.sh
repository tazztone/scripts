#!/bin/bash
# testing/test_lossless_toolbox.sh
# Refactored tests for Lossless Operations Toolbox

# --- Library ---
source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"

[ "$HEADLESS" = true ] && setup_mock_zenity
generate_test_media

SCRIPT_PATH="ffmpeg/🔒 Lossless-Operations-Toolbox.sh"

echo -e "\n${YELLOW}=== Lossless-Operations-Toolbox End-to-End Tests ===${NC}"

# Test 1: Trim (Lossless)
echo "Test 1: Lossless Trim (1s to 2s)"
# Mock wizard: Trim Video -> Form: 1|2
cat <<EOF > /tmp/zenity_responses
Trim Video
1|2
EOF
run_test "$SCRIPT_PATH" "duration=1.0" "$TEST_DATA/src.mp4"

# Test 2: Remux (to MKV)
echo "Test 2: Lossless Remux (to MKV)"
# Mock wizard: Change Format -> List: mkv
cat <<EOF > /tmp/zenity_responses
Change Format
mkv
EOF
run_test "$SCRIPT_PATH" "format=matroska" "$TEST_DATA/src.mp4"

# Test 3: Metadata Clean
echo "Test 3: Metadata Clean"
# Mock wizard: Edit Metadata -> List: clean_metadata
cat <<EOF > /tmp/zenity_responses
Edit Metadata
clean_metadata
EOF
run_test "$SCRIPT_PATH" "" "$TEST_DATA/src.mp4"

# Test 4: Metadata Title
echo "Test 4: Metadata Title"
# Mock wizard: Edit Metadata -> List: set_title -> Entry: "Test Lossless Title"
cat <<EOF > /tmp/zenity_responses
Edit Metadata
set_title
Test Lossless Title
EOF
run_test "$SCRIPT_PATH" "tags=Test Lossless Title" "$TEST_DATA/src.mp4"

# Test 5: Stream Selection (Remove Audio)
echo "Test 5: Remove Audio"
# Mock wizard: Edit Streams -> List: remove_audio
cat <<EOF > /tmp/zenity_responses
Edit Streams
remove_audio
EOF
run_test "$SCRIPT_PATH" "no_audio" "$TEST_DATA/src.mp4"

# Test 6: Merge Operation
echo "Test 6: Merge 2 Files"
cp "$TEST_DATA/src.mp4" "$TEST_DATA/src2.mp4"
# Mock wizard: Merge Videos -> File Selection Save: src_merged.mp4
cat <<EOF > /tmp/zenity_responses
Merge Videos
$TEST_DATA/src_merged.mp4
EOF
run_test "$SCRIPT_PATH" "duration=4.0" "$TEST_DATA/src.mp4" "$TEST_DATA/src2.mp4"
rm "$TEST_DATA/src2.mp4"

echo -e "\n${YELLOW}=== Lossless Toolbox Unit Property Tests (Isolated) ===${NC}"

# Property: Analysis Logic
echo "Property: Analysis Logic Accuracy"
(
    source "$SCRIPT_PATH"
    log_info "Testing get_video_codec_info..."
    info=$(get_video_codec_info "$TEST_DATA/src.mp4")
    [[ "$info" == VIDEO:h264:* ]] || { log_fail "Analysis failed: $info"; exit 1; }
    log_pass "Analysis logic verified"
) || FAILED=1

# Property: Compatibility Guard
echo "Property: Compatibility Guard"
(
    source "$SCRIPT_PATH"
    log_info "Testing validate_codec_compatibility..."
    validate_codec_compatibility "$TEST_DATA/src.mp4" "$TEST_DATA/src.mp4" >/dev/null || { log_fail "Compatibility failed on same file"; exit 1; }
    log_pass "Compatibility guard verified"
) || FAILED=1

echo -e "\n${GREEN}Lossless Toolbox Tests Finished!${NC}"
[ "$FAILED" == "1" ] && exit 1 || exit 0
