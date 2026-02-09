#!/bin/bash
# test_runner.sh
# A unified testing framework for scripts-sh

# --- Library ---
source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"

# --- Main Execution ---
if [ "$HEADLESS" = true ]; then
    setup_mock_zenity
fi

generate_test_media

echo -e "\n${YELLOW}=== Universal Toolbox Core Tests ===${NC}"

# 1. Basic Suite: Speed 2x + Scale 720p + Mute + Medium Quality + H.264
echo "Test 1: Core Recipe"
cat <<EOF > /tmp/zenity_responses
⏪ Speed Control|📐 Scale / Resize|🔊 Audio Tools
2x (Fast)||720p|| (Inactive)|No Change||| (Inactive)| (Inactive)|Medium Default||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264,fps=30" "$TEST_DATA/src.mp4"

# 2. Subtitle Burn-in Test
echo "Test 2: Subtitle Burn-in"
touch "$TEST_DATA/src.srt"
cat <<EOF > /tmp/zenity_responses
📝 Subtitles
 (Inactive)|| (Inactive)|| (Inactive)|No Change||| (Inactive)|Burn-in|Medium Default||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264" "$TEST_DATA/src.mp4"
rm "$TEST_DATA/src.srt"

# 3. CLI Preset Test
echo "Test 3: CLI Preset"
mkdir -p "$HOME/.config/scripts-sh/ffmpeg"
# Realistic choice string (14 parts): Speed|Custom|Res|CustomW|Crop|Rotate|TrimS|TrimE|Audio|Subs|Quality|TargSize|Format|HW
echo "TestPreset|2x (Fast)||720p|| (Inactive)|No Change||| (Inactive)| (Inactive)|Medium (CRF 23)||Auto/MP4|None (CPU Only)" > "$HOME/.config/scripts-sh/ffmpeg/presets.conf"
( 
    cd "$TEST_DATA"
    bash "$HOME/_coding/scripts-sh/ffmpeg/🧰 Universal-Toolbox.sh" --preset "TestPreset" "src.mp4"
) > /dev/null 2>&1

if [ -f "$TEST_DATA/src_2x_720p.mp4" ]; then
    log_pass "CLI Preset loaded successfully"
    rm -f "$TEST_DATA/src_2x_720p.mp4"
else
    log_fail "CLI Preset failed to generate output (Expected src_2x_720p.mp4)"
    ls -l "$TEST_DATA"
fi

echo -e "\n${YELLOW}=== Running Extended Universal Toolbox Tests ===${NC}"
bash testing/test_universal_extended.sh

echo -e "\n${YELLOW}=== Running Image Toolbox Tests ===${NC}"
bash testing/test_image_toolbox.sh

# --- Summary ---
echo -e "\n${YELLOW}=== Final Test Summary ===${NC}"
FAILED_ANY=0
grep -q "FAIL" "$REPORT_FILE" 2>/dev/null && FAILED_ANY=1

if [ $FAILED_ANY -eq 1 ]; then
    echo -e "${RED}Some tests failed! Check $REPORT_FILE for details.${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
