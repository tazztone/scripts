#!/bin/bash
# test_runner.sh
# A unified testing framework for scripts-sh

# --- Library ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/lib_test.sh"

# --- Main Execution ---
[ "$HEADLESS" = true ] && setup_mock_zenity
generate_test_media
FAILED=0

echo -e "\n${YELLOW}=== Static Syntax Analysis (Linting) ===${NC}"
bash testing/test_lint.sh || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Isolated Wizard Parser & Contract Tests ===${NC}"
bash testing/test_wizard_robust.sh || FAILED=$((FAILED+1))
bash testing/test_wizard_contract.sh || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Zenity Binary Smoke Test ===${NC}"
bash testing/test_zenity_smoke.sh || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Universal Toolbox Core Tests ===${NC}"

# 1. Basic Suite
echo "Test 1: Core Recipe"
cat <<EOF > /tmp/zenity_responses
Speed Control|Scale / Resize|Audio Tools
2x (Fast)||720p||||||Remove Audio Track||Medium (CRF 23)||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264,fps=30" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# 2. Subtitle Burn-in
echo "Test 2: Subtitle Burn-in"
echo -e "1\n00:00:00,000 --> 00:00:01,000\nTest Subtitle" > "$TEST_DATA/input.srt"
cat <<EOF > /tmp/zenity_responses
📝|Subtitles
|||||||||Burn-in|Medium (CRF 23)||Auto/MP4|None (CPU Only)
EOF
run_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))
rm "$TEST_DATA/input.srt"

# 3. CLI Preset Test
echo "Test 3: CLI Preset"
find "$TEST_DATA" -name "input_*.mp4" -delete
U_TOOLBOX="$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh"
mkdir -p "$HOME/.config/scripts-sh/ffmpeg"
echo "TestPreset|Speed: 2x (Fast)|Scale: 720p|Quality: Medium|Remove Audio Track" > "$HOME/.config/scripts-sh/ffmpeg/presets.conf"
( 
    cd "$TEST_DATA"
    bash "$U_TOOLBOX" --preset "TestPreset" "input.mp4"
)

# Use glob and validate_media for better robustness
PRESET_OUTPUT=$(ls "$TEST_DATA"/input_*2x*720p*noaudio*.mp4 2>/dev/null | head -1)
if [[ -n "$PRESET_OUTPUT" ]]; then
    log_pass "CLI Preset loaded successfully: $(basename "$PRESET_OUTPUT")"
    validate_media "$PRESET_OUTPUT" "duration=0.5,width=1280,no_audio" || FAILED=$((FAILED+1))
else
    log_fail "CLI Preset failed to generate expected output matching glob"
    FAILED=$((FAILED+1))
fi

echo -e "\n${YELLOW}=== Running Lossless Operations Toolbox Tests ===${NC}"
bash testing/test_lossless_toolbox.sh || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Running Extended Universal Toolbox Tests ===${NC}"
bash testing/test_universal_extended.sh || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Running Image Toolbox Tests ===${NC}"
bash testing/test_image_toolbox.sh || FAILED=$((FAILED+1))

# --- Summary ---
echo -e "\n${YELLOW}=== Final Test Summary ===${NC}"
FAILED_ANY=0
[ -f "$REPORT_FILE" ] && grep -q "FAIL" "$REPORT_FILE" && FAILED_ANY=1

if [ $FAILED_ANY -eq 1 ] || [ $FAILED -gt 0 ]; then
    echo -e "${RED}FAILURE DETECTED: Log contains FAIL or FAILED script counter is $FAILED${NC}"
    [ $FAILED_ANY -eq 1 ] && echo -e "${RED}Check $REPORT_FILE for details.${NC}"
    cleanup_test_data
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    cleanup_test_data
    exit 0
fi
