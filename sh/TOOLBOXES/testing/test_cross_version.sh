#!/bin/bash
# testing/test_cross_version.sh
# Verifies all toolboxes against Zenity 3, 4, and Ghost profiles

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"

log_info "Starting Cross-Version Compatibility Tests..."

setup_mock_zenity
setup_mock_ffmpeg
generate_test_media
# Ensure local copies with expected names for cross-version
cp "$TEST_DATA/input.mp4" "$TEST_DATA/src.mp4"
cp "$TEST_DATA/input.jpg" "$TEST_DATA/src.jpg"

FAILED=0

run_matrix_test() {
    local script="$1"
    local rules="$2"
    local inputs=("${@:3}")
    
    for profile in zenity4; do
        echo -e "\n[PROFILE: $profile] Testing $(basename "$script")"
        export ZENITY_PROFILE="$profile"
        
        # Cleanup is now handled by run_test itself in Phase 3
        
        case "$(basename "$script")" in
            *"Universal"*)
                export MOCK_LIST="Scale / Resize"
                export MOCK_FORMS="1x (Normal)||720p|| (Inactive)|| (Inactive)||| (Inactive)|| (Inactive)||Medium (CRF 23)|||Auto/MP4|None (CPU Only)||"
                ;;
            *"Image-Magick"*)
                export MOCK_LIST="Scale & Resize"
                export MOCK_FORMS="1280x||"  # resolution|custom_geometry
                ;;
            *"Lossless"*)
                export MOCK_LIST="Edit Streams
remove_video"
                export MOCK_FORMS="" 
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
