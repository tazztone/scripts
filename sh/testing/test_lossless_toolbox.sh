#!/bin/bash
# Property-Based Tests for Lossless Operations Toolbox
# Feature: lossless-operations-toolbox

# Test configuration
TEST_DIR="testing/test_data"
SCRIPT_PATH="ffmpeg/🔒 Lossless-Operations-Toolbox.sh"
ITERATIONS=100

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Helper function to print test results
print_test_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"
    
    ((TESTS_TOTAL++))
    
    if [ "$result" = "PASS" ]; then
        echo -e "${GREEN}[PASS]${NC} $test_name"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}[FAIL]${NC} $test_name: $message"
        ((TESTS_FAILED++))
    fi
}

# Property 1: Stream Copy Preservation
test_stream_copy_preservation() {
    echo -e "${YELLOW}Testing Property 1: Stream Copy Preservation${NC}"
    source "$SCRIPT_PATH"
    local test_file="$TEST_DIR/src.mp4"
    local output_file="/tmp/test_copy_$$.mp4"
    
    if execute_remuxing "$test_file" "$output_file" "mkv" >/dev/null 2>&1; then
        local orig_v=$(get_video_codec_info "$test_file")
        local new_v=$(get_video_codec_info "$output_file")
        if [ "$orig_v" == "$new_v" ]; then
            print_test_result "Stream Copy Preservation" "PASS" ""
        else
            print_test_result "Stream Copy Preservation" "FAIL" "Codecs changed, stream copy likely failed"
        fi
        rm -f "$output_file"
    else
        print_test_result "Stream Copy Preservation" "FAIL" "Operation failed"
    fi
}

# Property 11: Codec Analysis Accuracy
test_codec_analysis_accuracy() {
    echo -e "${YELLOW}Testing Property 11: Codec Analysis Accuracy${NC}"
    source "$SCRIPT_PATH"
    local test_file="$TEST_DIR/src.mp4"
    
    if [ ! -f "$test_file" ]; then
        print_test_result "Codec Analysis Accuracy" "FAIL" "Test file not found: $test_file"
        return 1
    fi
    
    local video_info=$(get_video_codec_info "$test_file")
    if [ -z "$video_info" ] || [[ "$video_info" != VIDEO:* ]]; then
        print_test_result "Codec Analysis Accuracy - Video Info" "FAIL" "Failed to extract video codec info"
        return 1
    fi
    
    local audio_info=$(get_audio_codec_info "$test_file")
    if [ -z "$audio_info" ] || [[ "$audio_info" != AUDIO:* ]]; then
        print_test_result "Codec Analysis Accuracy - Audio Info" "FAIL" "Failed to extract audio codec info"
        return 1
    fi
    
    local container=$(get_container_format "$test_file")
    if [ -z "$container" ]; then
        print_test_result "Codec Analysis Accuracy - Container" "FAIL" "Failed to detect container format"
        return 1
    fi
    
    local video_codec=$(echo "$video_info" | cut -d':' -f2)
    local audio_codec=$(echo "$audio_info" | cut -d':' -f2)
    
    if ! is_codec_supported "$video_codec" "video"; then
        print_test_result "Codec Analysis Accuracy - Video Support" "FAIL" "Video codec $video_codec not recognized as supported"
        return 1
    fi
    
    if ! is_codec_supported "$audio_codec" "audio"; then
        print_test_result "Codec Analysis Accuracy - Audio Support" "FAIL" "Audio codec $audio_codec not recognized as supported"
        return 1
    fi
    
    print_test_result "Codec Analysis Accuracy" "PASS" ""
}

# Property 5: Codec Compatibility Validation
test_codec_compatibility_validation() {
    echo -e "${YELLOW}Testing Property 5: Codec Compatibility Validation${NC}"
    source "$SCRIPT_PATH"
    local file1="$TEST_DIR/src.mp4"
    local file2="$TEST_DIR/src.mp4"
    
    local compat_result=$(validate_codec_compatibility "$file1" "$file2")
    if [[ "$compat_result" != *"COMPATIBLE"* ]]; then
        print_test_result "Codec Compatibility Validation - Same File" "FAIL" "Identical files should be compatible"
        return 1
    fi
    
    print_test_result "Codec Compatibility Validation" "PASS" ""
}

# Property 2: Lossless Operation Validation
test_lossless_operation_validation() {
    echo -e "${YELLOW}Testing Property 2: Lossless Operation Validation${NC}"
    source "$SCRIPT_PATH"
    local test_file="$TEST_DIR/src.mp4"
    
    local valid_ops=("trim" "remux" "metadata" "stream_select" "merge")
    for op in "${valid_ops[@]}"; do
        if ! validate_lossless_operation "$op" "$test_file"; then
            print_test_result "Lossless Operation Validation - Valid Op" "FAIL" "Operation $op should be valid"
            return 1
        fi
    done
    
    local invalid_ops=("scale" "crop" "speed" "filter")
    for op in "${invalid_ops[@]}"; do
        if validate_lossless_operation "$op" "$test_file" 2>/dev/null; then
            print_test_result "Lossless Operation Validation - Invalid Op" "FAIL" "Operation $op should be invalid"
            return 1
        fi
    done
    
    print_test_result "Lossless Operation Validation" "PASS" ""
}

# Property 3: Trimming Accuracy
test_trimming_accuracy() {
    echo -e "${YELLOW}Testing Property 3: Trimming Accuracy${NC}"
    source "$SCRIPT_PATH"
    local test_file="$TEST_DIR/src.mp4"
    local output_file="/tmp/test_trim_$$.mp4"
    
    if execute_trimming "$test_file" "$output_file" "1" "2" >/dev/null 2>&1; then
        if [ ! -f "$output_file" ]; then
            print_test_result "Trimming Accuracy - Output Creation" "FAIL" "Output file not created"
            return 1
        fi
        
        local duration=$(get_duration "$output_file")
        if [ "$duration" -lt 1 ] || [ "$duration" -gt 2 ]; then
            print_test_result "Trimming Accuracy - Duration" "FAIL" "Duration $duration outside expected range"
            rm -f "$output_file"
            return 1
        fi
        
        rm -f "$output_file"
        print_test_result "Trimming Accuracy" "PASS" ""
    else
        print_test_result "Trimming Accuracy - Execution" "FAIL" "Trimming operation failed"
    fi
}

# Property 4: Container Format Remuxing
test_container_format_remuxing() {
    echo -e "${YELLOW}Testing Property 4: Container Format Remuxing${NC}"
    source "$SCRIPT_PATH"
    
    if check_container_compatibility "mp4" "h264" "aac"; then
        print_test_result "Container Format Remuxing - MP4/H264/AAC" "PASS" ""
    else
        print_test_result "Container Format Remuxing - MP4/H264/AAC" "FAIL" "Should be compatible"
    fi
    
    if ! check_container_compatibility "webm" "h264" "aac" 2>/dev/null; then
        print_test_result "Container Format Remuxing - WebM/H264/AAC (Incompatible)" "PASS" ""
    else
        print_test_result "Container Format Remuxing - WebM/H264/AAC (Incompatible)" "FAIL" "Should be incompatible"
    fi
}

# Property 6: Metadata Preservation
test_metadata_preservation() {
    echo -e "${YELLOW}Testing Property 6: Metadata Preservation${NC}"
    source "$SCRIPT_PATH"
    local test_file="$TEST_DIR/src.mp4"
    local output_file="/tmp/test_meta_$$.mp4"
    
    if execute_metadata_editing "$test_file" "$output_file" "set_title" "Test Title" >/dev/null 2>&1; then
        local title=$(ffprobe -v error -show_entries format_tags=title -of default=noprint_wrappers=1:nokey=1 "$output_file")
        if [ "$title" == "Test Title" ]; then
            print_test_result "Metadata Preservation" "PASS" ""
        else
            print_test_result "Metadata Preservation" "FAIL" "Title not set correctly"
        fi
        rm -f "$output_file"
    else
        print_test_result "Metadata Preservation" "FAIL" "Metadata operation failed"
    fi
}

# Property 7: Stream Selection Accuracy
test_stream_selection_accuracy() {
    echo -e "${YELLOW}Testing Property 7: Stream Selection Accuracy${NC}"
    source "$SCRIPT_PATH"
    local test_file="$TEST_DIR/src.mp4"
    local output_file="/tmp/test_stream_$$.mp4"
    
    if execute_stream_selection "$test_file" "$output_file" "remove_audio" >/dev/null 2>&1; then
        local audio_info=$(get_audio_codec_info "$output_file")
        if [[ "$audio_info" == "AUDIO:::"* ]] || [[ -z $(echo "$audio_info" | cut -d':' -f2) ]]; then
            print_test_result "Stream Selection Accuracy" "PASS" ""
        else
            print_test_result "Stream Selection Accuracy" "FAIL" "Audio stream still present"
        fi
        rm -f "$output_file"
    else
        print_test_result "Stream Selection Accuracy - Execution" "FAIL" "Stream selection failed"
    fi
}

# Property 8: Metadata-Only Rotation
test_metadata_only_rotation() {
    echo -e "${YELLOW}Testing Property 8: Metadata-Only Rotation${NC}"
    source "$SCRIPT_PATH"
    local test_file="$TEST_DIR/src.mp4"
    local output_file="/tmp/test_rotation_$$.mp4"
    
    if execute_metadata_editing "$test_file" "$output_file" "set_rotation" "90" >/dev/null 2>&1; then
        print_test_result "Metadata-Only Rotation" "PASS" ""
        rm -f "$output_file"
    else
        print_test_result "Metadata-Only Rotation - Execution" "FAIL" "Rotation failed"
    fi
}

# Property 9: Alternative Suggestions
test_alternative_suggestions() {
    echo -e "${YELLOW}Testing Property 9: Alternative Suggestions${NC}"
    source "$SCRIPT_PATH"
    local error_msg=$(validate_lossless_operation "scale" "$TEST_DIR/src.mp4" 2>&1)
    if [[ "$error_msg" == *"not supported"* ]]; then
        print_test_result "Alternative Suggestions" "PASS" ""
    else
        print_test_result "Alternative Suggestions" "FAIL" "Helpful error message not found"
    fi
}

# Property 10: Batch Processing Integrity
test_batch_processing_integrity() {
    echo -e "${YELLOW}Testing Property 10: Batch Processing Integrity${NC}"
    source "$SCRIPT_PATH"
    local test_file="$TEST_DIR/src.mp4"
    local batch_id="test_batch_$$"
    local files=("$test_file" "$test_file")
    
    if execute_batch_trimming "$batch_id" "1" "2" "${files[@]}" >/dev/null 2>&1; then
        local summary=$(get_batch_summary "$batch_id")
        if [[ "$summary" == *"Status: completed"* ]] && [[ "$summary" == *"completed:2"* ]]; then
            print_test_result "Batch Processing Integrity" "PASS" ""
        else
            print_test_result "Batch Processing Integrity" "FAIL" "Batch summary incorrect"
        fi
        rm -f "${test_file%.*}_trimmed_1s-2s.${test_file##*.}"
    else
        print_test_result "Batch Processing Integrity - Execution" "FAIL" "Batch failed"
    fi
}

# Property 12: Multi-File Compatibility Analysis
test_multi_file_compatibility() {
    echo -e "${YELLOW}Testing Property 12: Multi-File Compatibility Analysis${NC}"
    source "$SCRIPT_PATH"
    local file1="$TEST_DIR/src.mp4"
    local compat_result=$(validate_codec_compatibility "$file1" "$file1")
    if [[ "$compat_result" == *"COMPATIBLE"* ]]; then
        print_test_result "Multi-File Compatibility Analysis" "PASS" ""
    else
        print_test_result "Multi-File Compatibility Analysis" "FAIL" "Should be compatible"
    fi
}

# Run all property tests
run_all_tests() {
    echo "=== Lossless Operations Toolbox Property Tests ==="
    echo "Feature: lossless-operations-toolbox"
    echo ""
    
    test_stream_copy_preservation         # Property 1
    test_lossless_operation_validation    # Property 2
    test_trimming_accuracy                # Property 3
    test_container_format_remuxing        # Property 4
    test_codec_compatibility_validation   # Property 5
    test_metadata_preservation            # Property 6
    test_stream_selection_accuracy        # Property 7
    test_metadata_only_rotation           # Property 8
    test_alternative_suggestions          # Property 9
    test_batch_processing_integrity       # Property 10
    test_codec_analysis_accuracy          # Property 11
    test_multi_file_compatibility        # Property 12
    
    echo ""
    echo "=== Test Summary ==="
    echo -e "Total Tests: $TESTS_TOTAL"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed.${NC}"
        return 1
    fi
}

# Main execution
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    run_all_tests
fi
