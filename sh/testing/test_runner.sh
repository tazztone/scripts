#!/bin/bash
# testing/test_runner.sh
# Main test suite for scripts-sh

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
source "$SCRIPT_DIR/lib_test.sh"

# Ensure headless mode for CI/Automated tests
export HEADLESS=true
setup_mock_zenity
setup_mock_ffmpeg
generate_test_media

FAILED=0

echo -e "${YELLOW}=== Static Syntax Analysis (Linting) ===${NC}"
bash "$SCRIPT_DIR/test_lint.sh" || FAILED=$((FAILED+1))

echo -e "\n${YELLOW}=== Unit Tests ===${NC}"
bash "$SCRIPT_DIR/test_filename_safe.sh" || FAILED=$((FAILED+1))
bash "$SCRIPT_DIR/test_gpu_probe.sh" || FAILED=$((FAILED+1))
bash "$SCRIPT_DIR/test_units.sh" || FAILED=$((FAILED+1))

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
2x (Fast)||720p|||||||||||Medium (CRF 23)|||Auto/MP4|None (CPU Only)||
EOF
run_test "$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264,fps=30,acodec=aac,tags=2x|720p" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# 2. Subtitle Burn-in
echo "Test 2: Subtitle Burn-in"
echo -e "1\n00:00:00,000 --> 00:00:01,000\nTest Subtitle" > "$TEST_DATA/input.srt"
cat <<EOF > /tmp/zenity_responses
Subtitles
|||||||||||Burn-in||Medium (CRF 23)|||Auto/MP4|None (CPU Only)||
EOF
run_test "$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))
rm -f "$TEST_DATA/input.srt"

# 4. Trim Test (0.5s duration)
echo "Test 4: Trim (0.5s)"
cat <<EOF > /tmp/zenity_responses
Trim (Cut Time)
1x (Normal)|||||||00:00:00.000|0.5||||||Medium (CRF 23)|||Auto/MP4|None (CPU Only)||
EOF
run_test "$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh" "duration=0.5" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# 5. Crop Test (9:16 Vertical)
echo "Test 5: Crop (9:16 Vertical)"
cat <<EOF > /tmp/zenity_responses
Crop / Aspect Ratio
 (Inactive)||||9:16 (Vertical)|||||||||Medium (CRF 23)|||Auto/MP4|None (CPU Only)|
EOF
run_test "$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh" "width=404,height=720" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

echo "Test 5b: Crop (16:9 Landscape)"
cat <<EOF > /tmp/zenity_responses
Crop / Aspect Ratio
 (Inactive)||||16:9 (Landscape)|||||||||Medium (CRF 23)|||Auto/MP4|None (CPU Only)|
EOF
run_test "$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh" "width=1280,height=720" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

echo "Test 5c: Crop (Square 1:1)"
cat <<EOF > /tmp/zenity_responses
Crop / Aspect Ratio
 (Inactive)||||Square 1:1|||||||||Medium (CRF 23)|||Auto/MP4|None (CPU Only)|
EOF
run_test "$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh" "width=720,height=720" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# 6. GIF Output
echo "Test 6: GIF Output"
cat <<EOF > /tmp/zenity_responses
Output Format
 (Inactive)|||||||||||||Medium (CRF 23)|||GIF|None (CPU Only)||
EOF
run_test "$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh" "format=gif" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

echo "Test 6b: AV1 Output"
cat <<EOF > /tmp/zenity_responses
Output Format
 (Inactive)|||||||||||||Medium (CRF 23)|||AV1|None (CPU Only)||
EOF
run_test "$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=av1" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

echo "Test 6c: WebM Output"
cat <<EOF > /tmp/zenity_responses
Output Format
 (Inactive)|||||||||||||Medium (CRF 23)|||WebM|None (CPU Only)||
EOF
run_test "$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh" "format=webm" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

echo "Test 6d: ProRes Output"
cat <<EOF > /tmp/zenity_responses
Output Format
 (Inactive)|||||||||||||Medium (CRF 23)|||ProRes|None (CPU Only)||
EOF
run_test "$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=prores" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# 7. Target Size (2-Pass)
echo "Test 7: Target Size (0.5MB)"
cat <<EOF > /tmp/zenity_responses
Quality Strategy
 (Inactive)|||||||||||||Medium (CRF 23)||0.5|Auto/MP4|None (CPU Only)|
EOF
run_test "$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh" "file_size_lt=600000,vcodec=h264" "$TEST_DATA/input.mp4" || FAILED=$((FAILED+1))

# 3. CLI Preset Test
echo "Test 3: CLI Preset"
find "$TEST_DATA" -name "input_*.mp4" -delete
U_TOOLBOX="$SCRIPT_DIR/../ffmpeg/🧰 Universal-Toolbox.sh"
mkdir -p "$HOME/.config/scripts-sh/ffmpeg"
echo "TestPreset|Speed: 2x (Fast)|Scale: 720p|Quality: Medium|Remove Audio Track" > "$HOME/.config/scripts-sh/ffmpeg/presets.conf"
( 
    cd "$TEST_DATA" || exit 1
    bash "$U_TOOLBOX" --preset "TestPreset" "input.mp4"
)

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
if [ -f /tmp/scripts_test_count.log ]; then
    counts=()
    mapfile -t counts < /tmp/scripts_test_count.log
    TOTAL_TESTS=${counts[0]:-0}
    TOTAL_PASSED=${counts[1]:-0}
    echo -e "Total Tests:  $TOTAL_TESTS"
    echo -e "Tests Passed: ${GREEN}$TOTAL_PASSED${NC}"
    echo -e "Tests Failed: ${RED}$((TOTAL_TESTS - TOTAL_PASSED))${NC}"
fi

if [ -f "$REPORT_FILE" ] && grep -q "FAIL" "$REPORT_FILE"; then
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
