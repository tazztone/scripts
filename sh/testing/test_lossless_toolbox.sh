#!/bin/bash
# testing/test_lossless_toolbox.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"
[ "$HEADLESS" = true ] && setup_mock_zenity
setup_mock_ffmpeg
generate_test_media
FAILED=0

echo -e "\n${YELLOW}=== Lossless Operations Toolbox Tests ===${NC}"

# Test 1: Remux (MOV -> MP4)
echo "Test 1: Remux (MOV -> MP4)"
export MOCK_LIST="Change Format"
export MOCK_FORMS="mp4"
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "vcodec=h264" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# Test 2: Trim (Lossless)
echo "Test 2: Lossless Trim"
export MOCK_LIST="Trim Video"
export MOCK_FORMS="00:00:00|00:00:00.5"
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "duration=0.5" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# Test 3: Remove Audio
echo "Test 3: Remove Audio"
export MOCK_LIST="Edit Streams
remove_audio"
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "no_audio" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# Test 3c: Batch Remove Audio (Multi-file)
echo "Test 3c: Batch Remove Audio"
cp "$TEST_DATA/input.mp4" "$TEST_DATA/input_batch1.mp4"
cp "$TEST_DATA/input.mp4" "$TEST_DATA/input_batch2.mp4"
export MOCK_LIST="Edit Streams
remove_audio
Edit Streams
remove_audio"
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "no_audio" "$TEST_DATA/input_batch1.mp4" "$TEST_DATA/input_batch2.mp4" || FAILED=$((FAILED+1))

# Check second file
OUTPUT_B2=$(find "$LAST_TEMP_DIR" -maxdepth 1 -name "input_batch2_no_audio*.mp4" 2>/dev/null | head -1)
if [[ -n "$OUTPUT_B2" ]]; then
    log_pass "Batch processing: second output exists ($(basename "$OUTPUT_B2"))"
    validate_media "$OUTPUT_B2" "no_audio" || FAILED=$((FAILED+1))
else
    log_fail "Batch processing: second output missing in $LAST_TEMP_DIR"
    FAILED=$((FAILED+1))
fi
rm -f "$TEST_DATA/input_batch1.mp4" "$TEST_DATA/input_batch2.mp4"

# Test 4: Metadata Title
echo "Test 4: Metadata Title"
export MOCK_LIST="Edit Metadata
set_title"
export MOCK_ENTRY="TestTitle"
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "title=TestTitle" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# Test 5: Metadata Clean
echo "Test 5: Metadata Clean"
export MOCK_LIST="Edit Metadata
clean_metadata"
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "vcodec=h264,title=EMPTY" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# Test 6: Merge Videos
echo "Test 6: Merge Videos"
rm -f "$TEST_DATA/merged_final.mp4"
cp "$TEST_DATA/input.mp4" "$TEST_DATA/input2.mp4"
export MOCK_LIST="Merge Videos"
export MOCK_FILE="merged_final.mp4"
run_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "duration=2.0" --pattern "merged_final.mp4" "$TEST_DATA/input.mp4" "$TEST_DATA/input2.mp4" || FAILED=$((FAILED+1))
rm "$TEST_DATA/input2.mp4"

echo -e "\n${GREEN}Lossless Toolbox Tests Finished!${NC}"
exit $FAILED
