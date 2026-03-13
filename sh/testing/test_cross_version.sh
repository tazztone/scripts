#!/bin/bash
# testing/test_cross_version.sh
# Verifies all toolboxes against Zenity 3, 4, and Ghost profiles

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"

log_info "Starting Cross-Version Compatibility Tests..."

setup_mock_zenity
generate_test_media

FAILED=0

run_matrix_test() {
    local script="$1"
    local rules="$2"
    local inputs=("${@:3}")
    
    for profile in zenity3 zenity4 ghost; do
        echo -e "\n[PROFILE: $profile] Testing $(basename "$script")"
        export ZENITY_PROFILE="$profile"
        
        # Clear queues
        > /tmp/zenity_responses
        unset ZENITY_LIST_RESPONSE
        unset ZENITY_FORMS_RESPONSE
        
        # Script-specific mocks
        case "$(basename "$script")" in
            *"Universal"*)
                export ZENITY_LIST_RESPONSE="Scale / Resize"
                export ZENITY_FORMS_RESPONSE="1x (Normal)||720p||||||||||Auto/MP4"
                ;;
            *"Image-Magick"*)
                export ZENITY_LIST_RESPONSE="Scale & Resize"
                export ZENITY_FORMS_RESPONSE="1280x|"
                ;;
            *"Lossless"*)
                # Lossless needs TWO list responses in a queue
                echo "Edit Streams" > /tmp/zenity_responses
                echo "remove_video" >> /tmp/zenity_responses
                ;;
        esac
        
        if run_test "$script" "$rules" "${inputs[@]}"; then
            log_pass "Passed on $profile"
        else
            log_fail "Failed on $profile"
            FAILED=$((FAILED+1))
        fi
    done
}

# 1. Universal Toolbox Test
run_matrix_test "ffmpeg/🧰 Universal-Toolbox.sh" "vcodec=h264,width=1280" "$TEST_DATA/src.mp4"

# 2. Image Magick Toolbox Test
run_matrix_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "format=jpeg,width=1280" "$TEST_DATA/src.jpg"

# 3. Lossless Toolbox Test
run_matrix_test "ffmpeg/🔒 Lossless-Operations-Toolbox.sh" "no_video,acodec=aac" "$TEST_DATA/src.mp4"

if [ $FAILED -eq 0 ]; then
    log_info "All toolboxes are cross-version compatible!"
    exit 0
else
    log_fail "Cross-version compatibility check failed ($FAILED failures)."
    exit 1
fi
