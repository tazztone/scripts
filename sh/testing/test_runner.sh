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
bash "$SCRIPT_DIR/test_lint.sh" || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Isolated Wizard Parser & Contract Tests ===${NC}"
bash "$SCRIPT_DIR/test_wizard_robust.sh" || FAILED=$((FAILED+1))
bash "$SCRIPT_DIR/test_wizard_contract.sh" || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Zenity Binary Smoke Test ===${NC}"
bash "$SCRIPT_DIR/test_zenity_smoke.sh" || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Universal Toolbox Core Tests ===${NC}"

# 1. Basic Suite
echo "Test 1: Core Recipe"
cat <<EOF > /tmp/zenity_responses
Speed Control|Scale / Resize|Audio Tools
2x (Fast)||720p||||||Keep Source||Medium (CRF 23)||Auto/MP4|None (CPU Only)
EOF
# Adding acodec=aac and tags to verify the new rules work
run_test "$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264,fps=30,acodec=aac,tags=2x|720p" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# 2. Subtitle Burn-in
echo "Test 2: Subtitle Burn-in"
echo -e "1\n00:00:00,000 --> 00:00:01,000\nTest Subtitle" > "$TEST_DATA/input.srt"
cat <<EOF > /tmp/zenity_responses
📝|Subtitles
|||||||||Burn-in|Medium (CRF 23)||Auto/MP4|None (CPU Only)
EOF
run_test "$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))
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
# slug order might change, but properties must remain correct
PRESET_OUTPUT=$(ls "$TEST_DATA"/input_*.mp4 2>/dev/null | head -1)
if [[ -n "$PRESET_OUTPUT" ]]; then
    log_pass "CLI Preset loaded successfully: $(basename "$PRESET_OUTPUT")"
    validate_media "$PRESET_OUTPUT" "duration=0.5,width=1280,no_audio" || FAILED=$((FAILED+1))
else
    log_fail "CLI Preset failed to generate expected output"
    FAILED=$((FAILED+1))
fi

echo -e "\n${YELLOW}=== Running Lossless Operations Toolbox Tests ===${NC}"
bash "$SCRIPT_DIR/test_lossless_toolbox.sh" || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Running Extended Universal Toolbox Tests ===${NC}"
bash "$SCRIPT_DIR/test_universal_extended.sh" || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Running Image Toolbox Tests ===${NC}"
bash "$SCRIPT_DIR/test_image_toolbox.sh" || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Running Cross-Version Compatibility Tests ===${NC}"
bash "$SCRIPT_DIR/test_cross_version.sh" || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Running Infinite Loop Detection Tests ===${NC}"
bash "$SCRIPT_DIR/test_loop_detection.sh" || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Running Negative & Edge-Case Tests ===${NC}"
bash "$SCRIPT_DIR/test_negative.sh" || FAILED=$((FAILED+1))
bash "$SCRIPT_DIR/test_ui_resilience.sh" || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Running Zenity 4.x UI Loop Repro ===${NC}"
bash "$SCRIPT_DIR/test_zenity4_repro.sh" || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Running Installation & Uninstallation Tests ===${NC}"
bash "$SCRIPT_DIR/test_install.sh" || FAILED=$((FAILED+1))

# --- Summary ---
echo -e "\n${YELLOW}=== Final Test Summary ===${NC}"
# Get global counts
if [ -f /tmp/scripts_test_count.log ]; then
    counts=($(cat /tmp/scripts_test_count.log))
    TOTAL_TESTS=${counts[0]}
    TOTAL_PASSED=${counts[1]}
    echo -e "Total Tests:  $TOTAL_TESTS"
    echo -e "Tests Passed: ${GREEN}$TOTAL_PASSED${NC}"
    echo -e "Tests Failed: ${RED}$((TOTAL_TESTS - TOTAL_PASSED))${NC}"
fi

# Consolidate: if FAILED > 0 OR REPORT_FILE has FAIL, it's a failure.
if [ -f "$REPORT_FILE" ] && grep -q "FAIL" "$REPORT_FILE"; then
    # Ensure FAILED is at least 1 if something was logged to report
    [ $FAILED -eq 0 ] && FAILED=1
fi

if [ $FAILED -gt 0 ]; then
    echo -e "\n${RED}FAILURE DETECTED: $FAILED component(s) failed or logged errors.${NC}"
    echo -e "${RED}Check $REPORT_FILE for details.${NC}"
    cleanup_test_data
    rm -f /tmp/scripts_test_count.log
    exit 1
else
    echo -e "\n${GREEN}All tests passed!${NC}"
    cleanup_test_data
    rm -f /tmp/scripts_test_count.log
    exit 0
fi
