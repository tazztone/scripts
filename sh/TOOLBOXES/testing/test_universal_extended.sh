#!/bin/bash
# testing/test_universal_extended.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"
[ "$HEADLESS" = true ] && setup_mock_zenity
setup_mock_ffmpeg
generate_test_media
FAILED=0

echo -e "\n${YELLOW}=== Extended Universal Toolbox Tests ===${NC}"

# Test 9: Speed Change
echo "Test 9: Speed Change (2x)"
export MOCK_LIST="Speed Control"
export MOCK_FORMS="2x (Fast)||720p|||||||||||Medium (CRF 23)|||Auto/MP4|None (CPU Only)|"
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "duration=0.5" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# Test 9b: Extreme Speed (4x)
echo "Test 9b: Extreme Speed (4x)"
export MOCK_LIST="Speed Control"
export MOCK_FORMS="4x (Super Fast)|||||||||||||Medium (CRF 23)|||Auto/MP4|None (CPU Only)|"
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "duration=0.25" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# Test 10: Fake Hardware Encoding (NVENC) + H.265
echo "Test 10: Hardware Encoding (Mocked NVENC) + H.265"
seed_gpu_cache "nvenc"
export MOCK_LIST="Scale / Resize|Output Format"
export MOCK_FORMS=" (Inactive)||720p|| (Inactive)|| (Inactive)|||||||Medium (CRF 23)|||H.265|Use NVENC (Nvidia)|"
export MOCK_FFMPEG_NVENC=1
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "tags=_nvenc" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))
rm -f "${XDG_CACHE_HOME:-$HOME/.cache}/scripts-sh-gpu-cache"

# Test 11: Multi-file processing
echo "Test 11: Multi-file processing"
cp "$TEST_DATA/input.mp4" "$TEST_DATA/input_another.mp4"
export MOCK_LIST="Scale / Resize"
export MOCK_FORMS=" (Inactive)||720p|| (Inactive)|| (Inactive)|||||||Medium (CRF 23)|||Auto/MP4|None (CPU Only)|"
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "width=1280" "$TEST_DATA/input.mp4" "$TEST_DATA/input_another.mp4" || FAILED=$((FAILED+1))

OUTPUT2=$(find "$LAST_TEMP_DIR" -maxdepth 1 -name "input_another*720*.mp4" 2>/dev/null | head -1)
if [[ -n "$OUTPUT2" ]]; then
    log_pass "Multi-file processing: second output exists ($(basename "$OUTPUT2"))"
    validate_media "$OUTPUT2" "width=1280" || FAILED=$((FAILED+1))
else
    log_fail "Multi-file processing: second output missing in $LAST_TEMP_DIR"
    FAILED=$((FAILED+1))
fi

echo -e "\n${GREEN}Extended Universal Toolbox Tests Finished!${NC}"
exit $FAILED
