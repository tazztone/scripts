#!/bin/bash
# test_runner.sh
# A unified testing framework for scripts-sh

# --- Configuration ---
TEST_DATA="/tmp/scripts_test_data"
MOCK_BIN="/tmp/scripts_mock_bin"
REPORT_FILE="testing/output/test_report.log"
HEADLESS=true
STRICT=true

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Library ---
source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"

# --- Main Execution ---
if [ "$HEADLESS" = true ]; then
    setup_mock_zenity
fi

generate_test_media

echo -e "\n${YELLOW}=== Running New: Universal Toolbox ===${NC}"
# Test combination: Speed 2x + Scale 720p + Mute + Medium Quality + H.264
# We use the response queue for complex flows if needed, but here simple overrides work
export ZENITY_LIST_RESPONSE="⏪ Speed Control|📐 Scale / Resize|🔊 Audio Tools"
# Forms responses are harder to override via env, so we use the queue for the forms call
echo "2x (Fast)||720p|| (Inactive)|No Change||| (Inactive)| (Inactive)|Medium Default||Auto/MP4|None (CPU Only)" > /tmp/zenity_responses
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "width=1280,no_audio,vcodec=h264,fps=30" "$TEST_DATA/src.mp4"
unset ZENITY_LIST_RESPONSE

echo -e "\n${YELLOW}=== Running New: Universal Toolbox v2 (Features) ===${NC}"
# 1. Subtitle Burn-in Test
touch "$TEST_DATA/src.srt"
export ZENITY_LIST_RESPONSE="📝 Subtitles"
# For subtitles: configure form needs to return "Burn-in"
echo " (Inactive)|| (Inactive)|| (Inactive)|No Change||| (Inactive)|Burn-in|Medium Default||Auto/MP4|None (CPU Only)" > /tmp/zenity_responses
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264" "$TEST_DATA/src.mp4"
rm "$TEST_DATA/src.srt"
unset ZENITY_LIST_RESPONSE

# --- Main Execution ---
if [[ "$*" == *"--no-run"* ]]; then
    return 0 2>/dev/null || exit 0
fi

generate_test_media


echo -e "\n${YELLOW}=== Running New: Universal Toolbox ===${NC}"
# Test combination: Speed 2x + Scale 720p + Mute + Medium Quality + H.265
# Wizard Mock in Step 3 is currently set to return Auto/MP4 (H264)
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "width=1280,no_audio,vcodec=h264,fps=30" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running New: Universal Toolbox v2 (Features) ===${NC}"
# 1. Subtitle Burn-in Test
touch "$TEST_DATA/src.srt"
export ZENITY_LIST_RESPONSE="📝 Subtitles"
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264" "$TEST_DATA/src.mp4"
rm "$TEST_DATA/src.srt"
unset ZENITY_LIST_RESPONSE

# 2. Target Size (2-Pass) Test
# We don't have a specific INTENT for Target Size anymore, it's always in the form.
# But we can test if selecting an intent still shows the form.
export ZENITY_LIST_RESPONSE="⏪ Speed Control"
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264" "$TEST_DATA/src.mp4"
unset ZENITY_LIST_RESPONSE

mkdir -p "$HOME/.config/scripts-sh"
echo "TestPreset|Speed: 2x (Fast)|Scale: 720p" > "$HOME/.config/scripts-sh/presets.conf"
echo "Testing CLI Preset..."
( 
    cd "$TEST_DATA"
    bash "$HOME/_coding/scripts-sh/ffmpeg/🧰 Universal-Toolbox.sh" --preset "TestPreset" "src.mp4"
) > /dev/null 2>&1
# Check if output exists (Universal-Toolbox now uses Smart Tagging e.g. _2x_1280p)
if [ -f "$TEST_DATA/src_2x_1280p.mp4" ]; then
    log_pass "CLI Preset loaded successfully"
    rm "$TEST_DATA/src_2x_1280p.mp4"
else
    log_fail "CLI Preset failed to generate output"
fi

echo -e "\n${YELLOW}=== Running Image Toolbox Tests ===${NC}"
bash testing/test_image_toolbox.sh

# --- Summary ---
echo -e "\n${YELLOW}=== Test Summary ===${NC}"
FAILED_ANY=0
grep -q "FAIL" "testing/output/test_report.log" 2>/dev/null && FAILED_ANY=1
grep -q "FAIL" "testing/output/image_test_report.log" 2>/dev/null && FAILED_ANY=1

if [ $FAILED_ANY -eq 1 ]; then
    echo -e "${RED}Some tests failed! Check testing/output/ for details.${NC}"
else
    echo -e "${GREEN}All tests passed!${NC}"
fi

# Cleanup
# rm -rf "$TEST_DATA" "$MOCK_BIN"
