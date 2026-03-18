#!/bin/bash
# testing/test_universal_extended.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"
[ "$HEADLESS" = true ] && setup_mock_zenity
generate_test_media
FAILED=0

echo -e "\n${YELLOW}=== Extended Universal Toolbox Tests ===${NC}"

# Test 9: Speed Change
echo "Test 9: Speed Change (2x)"
cat <<EOF > /tmp/zenity_responses
⏪|Speed Control
2x (Fast)||||||||||Medium (CRF 23)||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "duration=0.5" "$TEST_DATA/input.mp4" || FAILED=1

# Test 10: Fake Hardware Encoding (NVENC) + H.265
echo "Test 10: Hardware Encoding (Mocked NVENC) + H.265"
seed_gpu_cache "nvenc"
cat <<EOF > /tmp/zenity_responses
📐|Scale / Resize|📦|Output Format
 (Inactive)||720p||||||||Medium (CRF 23)||H.265|Use NVENC (Nvidia)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=hevc,tags=_nvenc" "$TEST_DATA/input.mp4" || FAILED=1
rm -f "${XDG_CACHE_HOME:-$HOME/.cache}/scripts-sh-gpu-cache"

# Test 11: Multi-file processing
echo "Test 11: Multi-file processing"
cp "$TEST_DATA/input.mp4" "$TEST_DATA/input_another.mp4"
cat <<EOF > /tmp/zenity_responses
📐|Scale / Resize
||720p||||||||Medium (CRF 23)||Auto/MP4|None (CPU Only)
||720p||||||||Medium (CRF 23)||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "width=1280" "$TEST_DATA/input.mp4" "$TEST_DATA/input_another.mp4" || FAILED=1

# Check for the second file using a robust glob
OUTPUT2=$(ls "$TEST_DATA"/input_another*720*.mp4 2>/dev/null | head -1)
if [[ -n "$OUTPUT2" ]]; then
    log_pass "Multi-file processing: second output exists ($(basename "$OUTPUT2"))"
    validate_media "$OUTPUT2" "width=1280" || FAILED=1
else
    log_fail "Multi-file processing: second output missing"
    FAILED=1
fi
rm "$TEST_DATA/input_another.mp4"

echo -e "\n${GREEN}Extended Universal Toolbox Tests Finished!${NC}"
exit $FAILED
