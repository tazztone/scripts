#!/bin/bash
# testing/test_ui_resilience.sh
# Tests for UI cancellations, resilience, and error handling

source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"

[ "$HEADLESS" = true ] && setup_mock_zenity
generate_test_media

echo -e "\n${YELLOW}=== UI Resilience & Negative Path Tests ===${NC}"

# 1. Image-Magick: Cancel Main Wizard
echo "Test 1: Image-Magick - Cancel Main Wizard"
export ZENITY_MOCK_EXIT_CODE=1
run_negative_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "$TEST_DATA/src.jpg"
unset ZENITY_MOCK_EXIT_CODE

# 2. Image-Magick: Cancel Sub-dialog (Returns to menu, then we cancel menu)
echo "Test 2: Image-Magick - Cancel Sub-dialog (Verifying return to menu)"
# Queue: 1. Main Menu (Select Scale), 2. Sub-dialog (Cancel), 3. Main Menu (Cancel)
printf "Scale & Resize\n\n\n" > /tmp/zenity_responses
run_negative_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "$TEST_DATA/src.jpg"

# 3. Universal Toolbox: Cancel Main Wizard
echo "Test 3: Universal Toolbox - Cancel Main Wizard"
export ZENITY_MOCK_EXIT_CODE=1
run_negative_test "ffmpeg/🧰 Universal-Toolbox.sh" "$TEST_DATA/src.mp4"
unset ZENITY_MOCK_EXIT_CODE

# 4. Universal Toolbox: Cancel Config Form
echo "Test 4: Universal Toolbox - Cancel Config Form"
# Queue: 1. Main Menu (Select Scale), 2. Config Form (Cancel)
printf "Scale / Resize\n\n" > /tmp/zenity_responses
run_negative_test "ffmpeg/🧰 Universal-Toolbox.sh" "$TEST_DATA/src.mp4"

# 5. Resilience: Image-Magick - Cancel Scale, then select BW and finish
echo "Test 5: Image-Magick Resilience (Cancel Scale -> BW -> Success)"
# Queue: 1. Menu (Scale), 2. Scale Dialog (Cancel), 3. Menu (Effects), 4. Effects Dialog (BW)
printf "Scale & Resize\n\nEffects & Branding\nBlack & White| (Inactive)|\n" > /tmp/zenity_responses
export ZENITY_QUESTION_RESPONSE="NO"
run_resilience_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "format=jpeg" "$TEST_DATA/src.jpg"
unset ZENITY_QUESTION_RESPONSE

# 6. Error Case: No files selected
echo "Test 6: Error Case - No Files"
( bash "imagemagick/🖼️ Image-Magick-Toolbox.sh" 2>/dev/null )
if [ $? -eq 1 ]; then
    log_pass "Image-Magick correctly failed with exit 1 when no files passed"
else
    log_fail "Image-Magick did not fail correctly when no files passed"
fi

echo -e "\n${GREEN}UI Resilience Tests Finished!${NC}"
