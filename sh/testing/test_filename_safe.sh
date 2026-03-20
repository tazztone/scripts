#!/bin/bash
# testing/test_filename_safe.sh
# Unit tests for generate_safe_filename in ffmpeg/common.sh

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"
source "$PROJECT_ROOT/ffmpeg/common.sh"

log_info "Testing generate_safe_filename..."

test_case() {
    local base="$1"
    local tag="$2"
    local ext="$3"
    local expected="$4"
    local desc="$5"
    
    # Mocking file existence if needed
    # (Actually we want to test both with and without existing files)
    local result=$(generate_safe_filename "$base" "$tag" "$ext")
    if [ "$result" == "$expected" ]; then
        log_pass "$desc: $result"
    else
        log_fail "$desc: Expected $expected, got $result"
    fi
}

# 1. Basic Case
test_case "video" "_edit" "mp4" "video_edit.mp4" "Basic filename"

# 2. Recursive Tag Stripping
test_case "video_720p" "_1080p" "mp4" "video_1080p.mp4" "Strip single tag"
test_case "video_720p_v2" "_1080p" "mp4" "video_1080p.mp4" "Strip tag with version"
test_case "video_720p_sq_9x16" "_low" "mp4" "video_low.mp4" "Strip multiple tags"
test_case "video_720p_v1_sq_v3" "_high" "mp4" "video_high.mp4" "Strip multiple tags with versions"

# 3. Path Handling
test_case "/tmp/input" "_web" "jpg" "/tmp/input_web.jpg" "Absolute path handling"
test_case "./input" "_min" "webp" "./input_min.webp" "Relative path handling"

# 4. Versioning (Requires actual files)
mkdir -p "$TEST_DATA/version_test"
touch "$TEST_DATA/version_test/file_edit.mp4"
test_case "$TEST_DATA/version_test/file" "_edit" "mp4" "$TEST_DATA/version_test/file_edit_v1.mp4" "Auto-versioning v1"

touch "$TEST_DATA/version_test/file_edit_v1.mp4"
test_case "$TEST_DATA/version_test/file" "_edit" "mp4" "$TEST_DATA/version_test/file_edit_v2.mp4" "Auto-versioning v2"

# 5. Complex Case: Path + Tags + Versioning
touch "$TEST_DATA/version_test/shoot_edit.mp4"
test_case "$TEST_DATA/version_test/shoot_720p_v2" "_edit" "mp4" "$TEST_DATA/version_test/shoot_edit_v1.mp4" "Combined strip and version"

rm -rf "$TEST_DATA/version_test"

log_info "Filename safety tests completed."
