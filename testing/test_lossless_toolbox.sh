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
    return 0
}

# Property 5: Codec Compatibility Validation
test_codec_compatibility_validation() {
    echo -e "${YELLOW}Testing Property 5: Codec Compatibility Validation${NC}"
    
    source "$SCRIPT_PATH"
    
    local file1="$TEST_DIR/src.mp4"
    local file2="$TEST_DIR/src.mp4"
    
    if [ ! -f "$file1" ]; then
        print_test_result "Codec Compatibility Validation" "FAIL" "Test file not found: $file1"
        return 1
    fi
    
    local compat_result=$(validate_codec_compatibility "$file1" "$file2")
    if [[ "$compat_result" != *"COMPATIBLE"* ]]; then
        print_test_result "Codec Compatibility Validation - Same File" "FAIL" "Identical files should be compatible"
        return 1
    fi
    
    print_test_result "Codec Compatibility Validation" "PASS" ""
    return 0
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
    
    if ! validate_trimming_operation "$test_file" "2" "8"; then
        print_test_result "Lossless Operation Validation - Trimming" "FAIL" "Valid trimming should pass"
        return 1
    fi
    
    if validate_trimming_operation "$test_file" "-5" "8" 2>/dev/null; then
        print_test_result "Lossless Operation Validation - Invalid Trimming" "FAIL" "Negative start time should fail"
        return 1
    fi
    
    if ! validate_remuxing_operation "$test_file" "mkv"; then
        print_test_result "Lossless Operation Validation - Remuxing" "FAIL" "Valid remuxing should pass"
        return 1
    fi
    
    if ! validate_stream_selection "$test_file" "remove_audio"; then
        print_test_result "Lossless Operation Validation - Stream Selection" "FAIL" "Valid stream selection should pass"
        return 1
    fi
    
    print_test_result "Lossless Operation Validation" "PASS" ""
    return 0
}

# Property 3: Trimming Accuracy
test_trimming_accuracy() {
    echo -e "${YELLOW}Testing Property 3: Trimming Accuracy${NC}"
    
    source "$SCRIPT_PATH"
    
    local test_file="$TEST_DIR/src.mp4"
    local output_file="/tmp/test_trim_$$.mp4"
    
    if [ ! -f "$test_file" ]; then
        print_test_result "Trimming Accuracy" "FAIL" "Test file not found: $test_file"
        return 1
    fi
    
    if execute_trimming "$test_file" "$output_file" "2" "6" >/dev/null 2>&1; then
        if [ ! -f "$output_file" ]; then
            print_test_result "Trimming Accuracy - Output Creation" "FAIL" "Output file not created"
            rm -f "$output_file"
            return 1
        fi
        
        local output_duration=$(get_duration "$output_file")
        if [ -z "$output_duration" ]; then
            print_test_result "Trimming Accuracy - Duration Check" "FAIL" "Could not get output duration"
            rm -f "$output_file"
            return 1
        fi
        
        if [ "$output_duration" -lt 2 ] || [ "$output_duration" -gt 6 ]; then
            print_test_result "Trimming Accuracy - Duration Validation" "FAIL" "Duration $output_duration not in expected range 2-6"
            rm -f "$output_file"
            return 1
        fi
        
        local original_video=$(get_video_codec_info "$test_file")
        local trimmed_video=$(get_video_codec_info "$output_file")
        local original_audio=$(get_audio_codec_info "$test_file")
        local trimmed_audio=$(get_audio_codec_info "$output_file")
        
        if [ "$original_video" != "$trimmed_video" ]; then
            print_test_result "Trimming Accuracy - Video Codec Preservation" "FAIL" "Video codec changed during trimming"
            rm -f "$output_file"
            return 1
        fi
        
        if [ "$original_audio" != "$trimmed_audio" ]; then
            print_test_result "Trimming Accuracy - Audio Codec Preservation" "FAIL" "Audio codec changed during trimming"
            rm -f "$output_file"
            return 1
        fi
        
        rm -f "$output_file"
        print_test_result "Trimming Accuracy" "PASS" ""
        return 0
    else
        print_test_result "Trimming Accuracy - Execution" "FAIL" "Trimming operation failed"
        rm -f "$output_file"
        return 1
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
        return 1
    fi
    
    if check_container_compatibility "mkv" "h264" "aac"; then
        print_test_result "Container Format Remuxing - MKV/H264/AAC" "PASS" ""
    else
        print_test_result "Container Format Remuxing - MKV/H264/AAC" "FAIL" "Should be compatible"
        return 1
    fi
    
    if check_container_compatibility "webm" "h264" "aac"; then
        print_test_result "Container Format Remuxing - WebM/H264/AAC" "FAIL" "Should be incompatible"
        return 1
    else
        print_test_result "Container Format Remuxing - WebM/H264/AAC" "PASS" ""
    fi
    
    return 0
}

# Property 7: Stream Selection Accuracy
test_stream_selection_accuracy() {
    echo -e "${YELLOW}Testing Property 7: Stream Selection Accuracy${NC}"
    
    source "$SCRIPT_PATH"
    
    local test_file="$TEST_DIR/src.mp4"
    local output_file="/tmp/test_stream_$$.mp4"
    
    if [ ! -f "$test_file" ]; then
        print_test_result "Stream Selection Accuracy" "FAIL" "Test file not found: $test_file"
        return 1
    fi
    
    if execute_stream_selection "$test_file" "$output_file" "remove_audio" >/dev/null 2>&1; then
        local audio_info=$(get_audio_codec_info "$output_file")
        # Check if audio stream was actually removed (empty codec name indicates no audio)
        local audio_codec=$(echo "$audio_info" | cut -d':' -f2)
        if [ -n "$audio_codec" ] && [ "$audio_codec" != "" ]; then
            print_test_result "Stream Selection Accuracy - Audio Removal" "FAIL" "Audio stream still present after removal"
            rm -f "$output_file"
            return 1
        fi
        
        local original_video=$(get_video_codec_info "$test_file")
        local output_video=$(get_video_codec_info "$output_file")
        if [ "$original_video" != "$output_video" ]; then
            print_test_result "Stream Selection Accuracy - Video Preservation" "FAIL" "Video stream changed during audio removal"
            rm -f "$output_file"
            return 1
        fi
        
        rm -f "$output_file"
        print_test_result "Stream Selection Accuracy" "PASS" ""
        return 0
    else
        print_test_result "Stream Selection Accuracy - Execution" "FAIL" "Stream selection operation failed"
        rm -f "$output_file"
        return 1
    fi
}

# Property 8: Metadata-Only Rotation
test_metadata_only_rotation() {
    echo -e "${YELLOW}Testing Property 8: Metadata-Only Rotation${NC}"
    
    source "$SCRIPT_PATH"
    
    local test_file="$TEST_DIR/src.mp4"
    local output_file="/tmp/test_rotation_$$.mp4"
    
    if [ ! -f "$test_file" ]; then
        print_test_result "Metadata-Only Rotation" "FAIL" "Test file not found: $test_file"
        return 1
    fi
    
    if execute_metadata_editing "$test_file" "$output_file" "set_rotation" "90" >/dev/null 2>&1; then
        local original_video=$(get_video_codec_info "$test_file")
        local rotated_video=$(get_video_codec_info "$output_file")
        if [ "$original_video" != "$rotated_video" ]; then
            print_test_result "Metadata-Only Rotation - Video Codec" "FAIL" "Video codec changed during rotation"
            rm -f "$output_file"
            return 1
        fi
        
        local original_audio=$(get_audio_codec_info "$test_file")
        local rotated_audio=$(get_audio_codec_info "$output_file")
        if [ "$original_audio" != "$rotated_audio" ]; then
            print_test_result "Metadata-Only Rotation - Audio Codec" "FAIL" "Audio codec changed during rotation"
            rm -f "$output_file"
            return 1
        fi
        
        rm -f "$output_file"
        print_test_result "Metadata-Only Rotation" "PASS" ""
        return 0
    else
        print_test_result "Metadata-Only Rotation - Execution" "FAIL" "Metadata rotation operation failed"
        rm -f "$output_file"
        return 1
    fi
}

# Property 10: Batch Processing Integrity
# For any batch operation with mixed compatible and incompatible files, the system should process all compatible files successfully
test_batch_processing_integrity() {
    echo -e "${YELLOW}Testing Property 10: Batch Processing Integrity${NC}"
    
    source "$SCRIPT_PATH"
    
    local test_file="$TEST_DIR/src.mp4"
    local batch_id="test_batch_$$"
    
    if [ ! -f "$test_file" ]; then
        print_test_result "Batch Processing Integrity" "FAIL" "Test file not found: $test_file"
        return 1
    fi
    
    # Test batch trimming with valid files
    local files=("$test_file" "$test_file")  # Use same file twice for compatibility
    
    if execute_batch_trimming "$batch_id" "2" "6" "${files[@]}" >/dev/null 2>&1; then
        # Check batch summary
        local summary=$(get_batch_summary "$batch_id")
        
        if [[ "$summary" == *"Status: completed"* ]]; then
            print_test_result "Batch Processing Integrity - Completion" "PASS" ""
        else
            print_test_result "Batch Processing Integrity - Completion" "FAIL" "Batch should complete successfully"
            return 1
        fi
        
        if [[ "$summary" == *"completed:2"* ]]; then
            print_test_result "Batch Processing Integrity - File Count" "PASS" ""
        else
            print_test_result "Batch Processing Integrity - File Count" "FAIL" "Should process 2 files successfully"
            return 1
        fi
        
        # Clean up output files
        rm -f "${test_file%.*}_trimmed_2s-6s.${test_file##*.}"
        
        print_test_result "Batch Processing Integrity" "PASS" ""
        return 0
    else
        print_test_result "Batch Processing Integrity - Execution" "FAIL" "Batch processing failed"
        return 1
    fi
}

# Run all property tests
run_all_tests() {
    echo "=== Lossless Operations Toolbox Property Tests ==="
    echo "Feature: lossless-operations-toolbox"
    echo ""
    
    test_codec_analysis_accuracy
    test_codec_compatibility_validation
    test_lossless_operation_validation
    test_trimming_accuracy
    test_container_format_remuxing
    test_stream_selection_accuracy
    test_metadata_only_rotation
    test_batch_processing_integrity
    
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
# Property 10: Batch Processing Integrity
# For any batch operation with mixed compatible and incompatible files, the system should process all compatible files successfully
test_batch_processing_integrity() {
    echo -e "${YELLOW}Testing Property 10: Batch Processing Integrity${NC}"
    
    source "$SCRIPT_PATH"
    
    local test_file="$TEST_DIR/src.mp4"
    local batch_id="test_batch_$$"
    
    if [ ! -f "$test_file" ]; then
        print_test_result "Batch Processing Integrity" "FAIL" "Test file not found: $test_file"
        return 1
    fi
    
    # Test batch trimming with valid files
    local files=("$test_file" "$test_file")  # Use same file twice for compatibility
    
    if execute_batch_trimming "$batch_id" "2" "6" "${files[@]}" >/dev/null 2>&1; then
        # Check batch summary
        local summary=$(get_batch_summary "$batch_id")
        
        if [[ "$summary" == *"Status: completed"* ]]; then
            print_test_result "Batch Processing Integrity - Completion" "PASS" ""
        else
            print_test_result "Batch Processing Integrity - Completion" "FAIL" "Batch should complete successfully"
            return 1
        fi
        
        if [[ "$summary" == *"completed:2"* ]]; then
            print_test_result "Batch Processing Integrity - File Count" "PASS" ""
        else
            print_test_result "Batch Processing Integrity - File Count" "FAIL" "Should process 2 files successfully"
            return 1
        fi
        
        # Clean up output files
        rm -f "${test_file%.*}_trimmed_2s-6s.${test_file##*.}"
        
        print_test_result "Batch Processing Integrity" "PASS" ""
        return 0
    else
        print_test_result "Batch Processing Integrity - Execution" "FAIL" "Batch processing failed"
        return 1
    fi
}