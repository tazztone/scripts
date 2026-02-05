#!/bin/bash
# Lossless Operations Toolbox
# Specialized script for lossless video operations using FFmpeg stream copy only

# Function to get video duration
get_duration() {
    ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$1" | cut -d. -f1
}

# Function to analyze codec information
analyze_codec() {
    local file="$1"
    ffprobe -v quiet -print_format json -show_format -show_streams "$file" 2>/dev/null
}

# Function to extract video codec information
get_video_codec_info() {
    local file="$1"
    local codec_name=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null)
    local profile=$(ffprobe -v error -select_streams v:0 -show_entries stream=profile -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null)
    local level=$(ffprobe -v error -select_streams v:0 -show_entries stream=level -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null)
    local pix_fmt=$(ffprobe -v error -select_streams v:0 -show_entries stream=pix_fmt -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null)
    local width=$(ffprobe -v error -select_streams v:0 -show_entries stream=width -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null)
    local height=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null)
    local fps=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null)
    
    echo "VIDEO:$codec_name:$profile:$level:$pix_fmt:$width:$height:$fps"
}

# Function to extract audio codec information
get_audio_codec_info() {
    local file="$1"
    local codec_name=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null)
    local sample_rate=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null)
    local channels=$(ffprobe -v error -select_streams a:0 -show_entries stream=channels -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null)
    local channel_layout=$(ffprobe -v error -select_streams a:0 -show_entries stream=channel_layout -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null)
    
    echo "AUDIO:$codec_name:$sample_rate:$channels:$channel_layout"
}

# Function to get container format
get_container_format() {
    local file="$1"
    local format=$(ffprobe -v error -show_entries format=format_name -of default=noprint_wrappers=1:nokey=1 "$file" 2>/dev/null | cut -d',' -f1)
    echo "$format"
}

# Function to check if codecs are supported for lossless operations
is_codec_supported() {
    local codec="$1"
    local type="$2"  # video or audio
    
    case "$type" in
        "video")
            case "$codec" in
                "h264"|"hevc"|"vp8"|"vp9"|"av01"|"prores")
                    return 0
                    ;;
                *)
                    return 1
                    ;;
            esac
            ;;
        "audio")
            case "$codec" in
                "aac"|"mp3"|"opus"|"flac"|"vorbis"|"pcm_s16le")
                    return 0
                    ;;
                *)
                    return 1
                    ;;
            esac
            ;;
    esac
    return 1
}

# Function to validate codec compatibility between files
validate_codec_compatibility() {
    local file1="$1"
    local file2="$2"
    
    local video1=$(get_video_codec_info "$file1")
    local video2=$(get_video_codec_info "$file2")
    local audio1=$(get_audio_codec_info "$file1")
    local audio2=$(get_audio_codec_info "$file2")
    
    # Extract codec names for comparison
    local v1_codec=$(echo "$video1" | cut -d':' -f2)
    local v2_codec=$(echo "$video2" | cut -d':' -f2)
    local a1_codec=$(echo "$audio1" | cut -d':' -f2)
    local a2_codec=$(echo "$audio2" | cut -d':' -f2)
    
    # Check if video codecs match
    if [ "$v1_codec" != "$v2_codec" ]; then
        echo "INCOMPATIBLE: Video codecs differ ($v1_codec vs $v2_codec)"
        return 1
    fi
    
    # Check if audio codecs match
    if [ "$a1_codec" != "$a2_codec" ]; then
        echo "INCOMPATIBLE: Audio codecs differ ($a1_codec vs $a2_codec)"
        return 1
    fi
    
    echo "COMPATIBLE: Codecs match"
    return 0
}

# Function to validate if operation can be performed losslessly
validate_lossless_operation() {
    local operation="$1"
    local file="$2"
    
    case "$operation" in
        "trim"|"remux"|"metadata"|"stream_select")
            return 0  # These operations are always lossless with stream copy
            ;;
        "merge")
            # Merging requires codec compatibility validation (handled separately)
            return 0
            ;;
        *)
            echo "ERROR: Operation '$operation' is not supported in lossless mode"
            return 1
            ;;
    esac
}

# Function to validate trimming operation
validate_trimming_operation() {
    local file="$1"
    local start_time="$2"
    local end_time="$3"
    
    # Check if file exists and is readable
    if [ ! -f "$file" ] || [ ! -r "$file" ]; then
        echo "ERROR: File '$file' not found or not readable"
        return 1
    fi
    
    # Get file duration
    local duration=$(get_duration "$file")
    if [ -z "$duration" ] || [ "$duration" -eq 0 ]; then
        echo "ERROR: Could not determine file duration or file has zero duration"
        return 1
    fi
    
    # Validate time ranges
    if [ -n "$start_time" ] && [ "$start_time" -lt 0 ]; then
        echo "ERROR: Start time cannot be negative"
        return 1
    fi
    
    if [ -n "$end_time" ] && [ "$end_time" -gt "$duration" ]; then
        echo "ERROR: End time ($end_time) exceeds file duration ($duration)"
        return 1
    fi
    
    if [ -n "$start_time" ] && [ -n "$end_time" ] && [ "$start_time" -ge "$end_time" ]; then
        echo "ERROR: Start time must be less than end time"
        return 1
    fi
    
    echo "VALID: Trimming operation can be performed losslessly"
    return 0
}

# Function to validate remuxing operation
validate_remuxing_operation() {
    local input_file="$1"
    local target_container="$2"
    
    # Check if file exists
    if [ ! -f "$input_file" ] || [ ! -r "$input_file" ]; then
        echo "ERROR: Input file '$input_file' not found or not readable"
        return 1
    fi
    
    # Get codec information
    local video_info=$(get_video_codec_info "$input_file")
    local audio_info=$(get_audio_codec_info "$input_file")
    
    if [ -z "$video_info" ] || [ -z "$audio_info" ]; then
        echo "ERROR: Could not analyze codec information"
        return 1
    fi
    
    # Extract codec names
    local video_codec=$(echo "$video_info" | cut -d':' -f2)
    local audio_codec=$(echo "$audio_info" | cut -d':' -f2)
    
    # Check container compatibility
    if check_container_compatibility "$target_container" "$video_codec" "$audio_codec"; then
        echo "VALID: Remuxing to $target_container is compatible with codecs ($video_codec/$audio_codec)"
        return 0
    else
        echo "ERROR: Target container '$target_container' is not compatible with codecs ($video_codec/$audio_codec)"
        echo "SUGGESTION: Try a different container format or use the original container"
        return 1
    fi
}

# Function to validate merging operation
validate_merging_operation() {
    local files=("$@")
    
    if [ ${#files[@]} -lt 2 ]; then
        echo "ERROR: At least 2 files required for merging"
        return 1
    fi
    
    # Get codec info from first file as reference
    local ref_file="${files[0]}"
    local ref_video=$(get_video_codec_info "$ref_file")
    local ref_audio=$(get_audio_codec_info "$ref_file")
    
    if [ -z "$ref_video" ] || [ -z "$ref_audio" ]; then
        echo "ERROR: Could not analyze reference file '$ref_file'"
        return 1
    fi
    
    # Check all other files against reference
    for ((i=1; i<${#files[@]}; i++)); do
        local current_file="${files[i]}"
        
        if [ ! -f "$current_file" ] || [ ! -r "$current_file" ]; then
            echo "ERROR: File '$current_file' not found or not readable"
            return 1
        fi
        
        local compat_result=$(validate_codec_compatibility "$ref_file" "$current_file")
        if [[ "$compat_result" == *"INCOMPATIBLE"* ]]; then
            echo "ERROR: File '$current_file' has incompatible codecs with reference file '$ref_file'"
            echo "$compat_result"
            echo "SUGGESTION: Convert files to matching codecs first, or merge only compatible files"
            return 1
        fi
    done
    
    echo "VALID: All files have compatible codecs for lossless merging"
    return 0
}

# Function to validate stream selection operation
validate_stream_selection() {
    local file="$1"
    local operation="$2"  # "remove_audio", "remove_video", "select_streams"
    
    if [ ! -f "$file" ] || [ ! -r "$file" ]; then
        echo "ERROR: File '$file' not found or not readable"
        return 1
    fi
    
    # Check if file has the streams we're trying to manipulate
    local video_info=$(get_video_codec_info "$file")
    local audio_info=$(get_audio_codec_info "$file")
    
    case "$operation" in
        "remove_audio")
            if [ -z "$audio_info" ] || [[ "$audio_info" == *"N/A"* ]]; then
                echo "WARNING: File has no audio stream to remove"
                return 1
            fi
            ;;
        "remove_video")
            if [ -z "$video_info" ] || [[ "$video_info" == *"N/A"* ]]; then
                echo "ERROR: Cannot remove video stream - file would be empty"
                return 1
            fi
            ;;
        "select_streams")
            # Always valid for stream copy operations
            ;;
    esac
    
    echo "VALID: Stream selection operation can be performed losslessly"
    return 0
}

# Function to suggest alternative lossless operations
suggest_lossless_alternatives() {
    local requested_operation="$1"
    local file="$2"
    
    case "$requested_operation" in
        "scale"|"resize")
            echo "ALTERNATIVE: Use container remuxing to change format, or trim to reduce file size"
            echo "ALTERNATIVE: Use metadata editing to change display aspect ratio without re-encoding"
            ;;
        "crop")
            echo "ALTERNATIVE: Use trimming to cut time segments instead of spatial cropping"
            echo "ALTERNATIVE: Use metadata rotation to change orientation without re-encoding"
            ;;
        "speed"|"tempo")
            echo "ALTERNATIVE: Use trimming to extract shorter segments"
            echo "ALTERNATIVE: Use stream selection to remove audio if speed change was for audio"
            ;;
        "filter"|"effect")
            echo "ALTERNATIVE: Use metadata editing to add information without changing content"
            echo "ALTERNATIVE: Use stream selection to remove unwanted tracks"
            ;;
        "quality"|"compress")
            echo "ALTERNATIVE: Use container remuxing to a more efficient format"
            echo "ALTERNATIVE: Use trimming to reduce content length"
            ;;
        *)
            echo "ALTERNATIVE: Consider using trimming, remuxing, merging, or metadata editing"
            ;;
    esac
}

# Container-codec compatibility matrix
declare -A CONTAINER_CODECS
CONTAINER_CODECS[mp4]="h264,hevc,av01"
CONTAINER_CODECS[mkv]="h264,hevc,vp8,vp9,av01"
CONTAINER_CODECS[mov]="h264,hevc,prores"
CONTAINER_CODECS[webm]="vp8,vp9,av01"

# Audio codec compatibility
declare -A CONTAINER_AUDIO_CODECS
CONTAINER_AUDIO_CODECS[mp4]="aac,mp3"
CONTAINER_AUDIO_CODECS[mkv]="aac,mp3,opus,flac,vorbis"
CONTAINER_AUDIO_CODECS[mov]="aac,pcm_s16le"
CONTAINER_AUDIO_CODECS[webm]="opus,vorbis"

# Function to check container-codec compatibility
check_container_compatibility() {
    local container="$1"
    local video_codec="$2"
    local audio_codec="$3"
    
    # Check video codec compatibility
    if [[ "${CONTAINER_CODECS[$container]}" == *"$video_codec"* ]]; then
        # Check audio codec compatibility
        if [[ "${CONTAINER_AUDIO_CODECS[$container]}" == *"$audio_codec"* ]]; then
            return 0
        fi
    fi
    return 1
}

# Core data model for file processing state
declare -A FILE_STATES
declare -A FILE_CODECS
declare -A FILE_PROGRESS

# Initialize file processing state
init_file_state() {
    local file="$1"
    local id=$(basename "$file" | tr '.' '_')
    
    FILE_STATES[$id]="pending"
    FILE_PROGRESS[$id]=0
    
    # Analyze codec information
    local codec_info=$(analyze_codec "$file")
    FILE_CODECS[$id]="$codec_info"
}

# Update file processing state
update_file_state() {
    local file="$1"
    local status="$2"
    local progress="${3:-0}"
    
    local id=$(basename "$file" | tr '.' '_')
    FILE_STATES[$id]="$status"
    FILE_PROGRESS[$id]="$progress"
}

# Get file processing state
get_file_state() {
    local file="$1"
    local id=$(basename "$file" | tr '.' '_')
    echo "${FILE_STATES[$id]:-unknown}"
}

# Configuration directory
CONFIG_DIR="$HOME/.config/lossless-toolbox"
PRESET_FILE="$CONFIG_DIR/presets.conf"
HISTORY_FILE="$CONFIG_DIR/history.conf"
mkdir -p "$CONFIG_DIR"
touch "$HISTORY_FILE"

# Initialize default presets for lossless operations
if [ ! -s "$PRESET_FILE" ]; then
    echo "Quick Trim|Trim Video Segment" > "$PRESET_FILE"
    echo "Format Convert|Remux Container Format" >> "$PRESET_FILE"
    echo "Merge Videos|Concatenate Compatible Files" >> "$PRESET_FILE"
    echo "Clean Metadata|Remove Personal Information" >> "$PRESET_FILE"
fi

# Main execution starts here
echo "Lossless Operations Toolbox - Initializing..."

# Validate FFmpeg availability
if ! command -v ffmpeg &> /dev/null; then
    zenity --error --text="FFmpeg is not installed or not in PATH.\nPlease install FFmpeg to use this tool."
    exit 1
fi

if ! command -v ffprobe &> /dev/null; then
    zenity --error --text="FFprobe is not installed or not in PATH.\nPlease install FFmpeg (includes FFprobe) to use this tool."
    exit 1
fi

echo "Core FFmpeg integration initialized successfully."

# ===== LOSSLESS OPERATION ENGINES =====

# Trimming Engine - Extract video segments using stream copy
execute_trimming() {
    local input_file="$1"
    local output_file="$2"
    local start_time="$3"
    local end_time="$4"
    
    # Validate operation first
    if ! validate_trimming_operation "$input_file" "$start_time" "$end_time"; then
        return 1
    fi
    
    # Build FFmpeg command with stream copy
    local cmd="ffmpeg -y -nostdin"
    
    # Add start time if specified
    if [ -n "$start_time" ] && [ "$start_time" != "0" ]; then
        cmd="$cmd -ss $start_time"
    fi
    
    # Add input file
    cmd="$cmd -i \"$input_file\""
    
    # Add duration/end time if specified
    if [ -n "$end_time" ]; then
        if [ -n "$start_time" ]; then
            # Calculate duration
            local duration=$((end_time - start_time))
            cmd="$cmd -t $duration"
        else
            cmd="$cmd -t $end_time"
        fi
    fi
    
    # Use stream copy for lossless operation
    cmd="$cmd -c copy"
    
    # Add output file
    cmd="$cmd \"$output_file\""
    
    echo "Executing: $cmd"
    eval $cmd
    
    local status=$?
    if [ $status -eq 0 ]; then
        echo "SUCCESS: Trimmed video saved to $output_file"
        return 0
    else
        echo "ERROR: Trimming failed with status $status"
        return 1
    fi
}

# Remuxing Engine - Change container format using stream copy
execute_remuxing() {
    local input_file="$1"
    local output_file="$2"
    local target_container="$3"
    
    # Validate operation first
    if ! validate_remuxing_operation "$input_file" "$target_container"; then
        return 1
    fi
    
    # Build FFmpeg command with stream copy
    local cmd="ffmpeg -y -nostdin -i \"$input_file\" -c copy"
    
    # Add container-specific options
    case "$target_container" in
        "mp4")
            cmd="$cmd -movflags +faststart"
            ;;
        "mkv")
            # MKV doesn't need special flags for stream copy
            ;;
        "mov")
            cmd="$cmd -movflags +faststart"
            ;;
        "webm")
            # WebM with stream copy
            ;;
    esac
    
    cmd="$cmd \"$output_file\""
    
    echo "Executing: $cmd"
    eval $cmd
    
    local status=$?
    if [ $status -eq 0 ]; then
        echo "SUCCESS: Remuxed video saved to $output_file"
        return 0
    else
        echo "ERROR: Remuxing failed with status $status"
        return 1
    fi
}

# Merging Engine - Concatenate files using stream copy
execute_merging() {
    local output_file="$1"
    shift
    local input_files=("$@")
    
    # Validate operation first
    if ! validate_merging_operation "${input_files[@]}"; then
        return 1
    fi
    
    # Create temporary concat file list
    local concat_file="/tmp/lossless_concat_$$.txt"
    
    # Write file list for FFmpeg concat demuxer
    for file in "${input_files[@]}"; do
        echo "file '$(realpath "$file")'" >> "$concat_file"
    done
    
    # Build FFmpeg command with concat demuxer and stream copy
    local cmd="ffmpeg -y -nostdin -f concat -safe 0 -i \"$concat_file\" -c copy \"$output_file\""
    
    echo "Executing: $cmd"
    eval $cmd
    
    local status=$?
    rm -f "$concat_file"
    
    if [ $status -eq 0 ]; then
        echo "SUCCESS: Merged video saved to $output_file"
        return 0
    else
        echo "ERROR: Merging failed with status $status"
        return 1
    fi
}

# Stream Selection Engine - Remove or select specific streams
execute_stream_selection() {
    local input_file="$1"
    local output_file="$2"
    local operation="$3"
    
    # Validate operation first
    if ! validate_stream_selection "$input_file" "$operation"; then
        return 1
    fi
    
    # Build FFmpeg command based on operation
    local cmd="ffmpeg -y -nostdin -i \"$input_file\""
    
    case "$operation" in
        "remove_audio")
            cmd="$cmd -c:v copy -an"
            ;;
        "remove_video")
            cmd="$cmd -c:a copy -vn"
            ;;
        "video_only")
            cmd="$cmd -c:v copy -an"
            ;;
        "audio_only")
            cmd="$cmd -c:a copy -vn"
            ;;
        *)
            echo "ERROR: Unknown stream selection operation: $operation"
            return 1
            ;;
    esac
    
    cmd="$cmd \"$output_file\""
    
    echo "Executing: $cmd"
    eval $cmd
    
    local status=$?
    if [ $status -eq 0 ]; then
        echo "SUCCESS: Stream selection completed, saved to $output_file"
        return 0
    else
        echo "ERROR: Stream selection failed with status $status"
        return 1
    fi
}

# Metadata Editor - Modify metadata without touching streams
execute_metadata_editing() {
    local input_file="$1"
    local output_file="$2"
    local operation="$3"
    local value="$4"
    
    # Build FFmpeg command with stream copy and metadata changes
    local cmd="ffmpeg -y -nostdin -i \"$input_file\" -c copy"
    
    case "$operation" in
        "clean_metadata")
            cmd="$cmd -map_metadata -1"
            ;;
        "set_title")
            cmd="$cmd -metadata title=\"$value\""
            ;;
        "set_rotation")
            # Set rotation metadata without re-encoding
            case "$value" in
                "90")
                    cmd="$cmd -metadata:s:v:0 rotate=90"
                    ;;
                "180")
                    cmd="$cmd -metadata:s:v:0 rotate=180"
                    ;;
                "270")
                    cmd="$cmd -metadata:s:v:0 rotate=270"
                    ;;
                "0")
                    cmd="$cmd -metadata:s:v:0 rotate=0"
                    ;;
            esac
            ;;
        *)
            echo "ERROR: Unknown metadata operation: $operation"
            return 1
            ;;
    esac
    
    cmd="$cmd \"$output_file\""
    
    echo "Executing: $cmd"
    eval $cmd
    
    local status=$?
    if [ $status -eq 0 ]; then
        echo "SUCCESS: Metadata editing completed, saved to $output_file"
        return 0
    else
        echo "ERROR: Metadata editing failed with status $status"
        return 1
    fi
}
# ===== BATCH PROCESSING SYSTEM =====

# Batch processing state tracking
declare -A BATCH_STATES
declare -A BATCH_PROGRESS
declare -A BATCH_SUMMARIES

# Initialize batch processing
init_batch_processing() {
    local batch_id="$1"
    shift
    local files=("$@")
    
    BATCH_STATES[$batch_id]="pending"
    BATCH_PROGRESS[$batch_id]=0
    BATCH_SUMMARIES[$batch_id]="total:${#files[@]},completed:0,failed:0,skipped:0"
    
    echo "Batch $batch_id initialized with ${#files[@]} files"
}

# Update batch progress
update_batch_progress() {
    local batch_id="$1"
    local completed="$2"
    local failed="$3"
    local skipped="$4"
    local total="$5"
    
    local progress=$(( (completed + failed + skipped) * 100 / total ))
    BATCH_PROGRESS[$batch_id]=$progress
    BATCH_SUMMARIES[$batch_id]="total:$total,completed:$completed,failed:$failed,skipped:$skipped"
    
    if [ $((completed + failed + skipped)) -eq $total ]; then
        if [ $failed -eq 0 ]; then
            BATCH_STATES[$batch_id]="completed"
        else
            BATCH_STATES[$batch_id]="partial_failure"
        fi
    else
        BATCH_STATES[$batch_id]="running"
    fi
}

# Execute batch trimming operation
execute_batch_trimming() {
    local batch_id="$1"
    local start_time="$2"
    local end_time="$3"
    shift 3
    local files=("$@")
    
    init_batch_processing "$batch_id" "${files[@]}"
    
    local completed=0
    local failed=0
    local skipped=0
    local total=${#files[@]}
    
    echo "Starting batch trimming: $total files"
    
    for file in "${files[@]}"; do
        echo "Processing: $(basename "$file")"
        
        # Validate file first
        if ! validate_trimming_operation "$file" "$start_time" "$end_time"; then
            echo "SKIPPED: $(basename "$file") - validation failed"
            ((skipped++))
            update_batch_progress "$batch_id" $completed $failed $skipped $total
            continue
        fi
        
        # Generate output filename
        local base="${file%.*}"
        local ext="${file##*.}"
        local output_file="${base}_trimmed_${start_time}s-${end_time}s.${ext}"
        
        # Execute trimming
        if execute_trimming "$file" "$output_file" "$start_time" "$end_time" >/dev/null 2>&1; then
            echo "SUCCESS: $(basename "$output_file")"
            ((completed++))
        else
            echo "FAILED: $(basename "$file")"
            ((failed++))
        fi
        
        update_batch_progress "$batch_id" $completed $failed $skipped $total
    done
    
    echo "Batch trimming completed: $completed successful, $failed failed, $skipped skipped"
    return 0
}

# Execute batch remuxing operation
execute_batch_remuxing() {
    local batch_id="$1"
    local target_container="$2"
    shift 2
    local files=("$@")
    
    init_batch_processing "$batch_id" "${files[@]}"
    
    local completed=0
    local failed=0
    local skipped=0
    local total=${#files[@]}
    
    echo "Starting batch remuxing to $target_container: $total files"
    
    for file in "${files[@]}"; do
        echo "Processing: $(basename "$file")"
        
        # Validate file first
        if ! validate_remuxing_operation "$file" "$target_container"; then
            echo "SKIPPED: $(basename "$file") - validation failed"
            ((skipped++))
            update_batch_progress "$batch_id" $completed $failed $skipped $total
            continue
        fi
        
        # Generate output filename
        local base="${file%.*}"
        local output_file="${base}_remuxed.${target_container}"
        
        # Execute remuxing
        if execute_remuxing "$file" "$output_file" "$target_container" >/dev/null 2>&1; then
            echo "SUCCESS: $(basename "$output_file")"
            ((completed++))
        else
            echo "FAILED: $(basename "$file")"
            ((failed++))
        fi
        
        update_batch_progress "$batch_id" $completed $failed $skipped $total
    done
    
    echo "Batch remuxing completed: $completed successful, $failed failed, $skipped skipped"
    return 0
}

# Execute batch stream selection operation
execute_batch_stream_selection() {
    local batch_id="$1"
    local operation="$2"
    shift 2
    local files=("$@")
    
    init_batch_processing "$batch_id" "${files[@]}"
    
    local completed=0
    local failed=0
    local skipped=0
    local total=${#files[@]}
    
    echo "Starting batch stream selection ($operation): $total files"
    
    for file in "${files[@]}"; do
        echo "Processing: $(basename "$file")"
        
        # Validate file first
        if ! validate_stream_selection "$file" "$operation"; then
            echo "SKIPPED: $(basename "$file") - validation failed"
            ((skipped++))
            update_batch_progress "$batch_id" $completed $failed $skipped $total
            continue
        fi
        
        # Generate output filename
        local base="${file%.*}"
        local ext="${file##*.}"
        local suffix=""
        case "$operation" in
            "remove_audio") suffix="_no_audio" ;;
            "remove_video") suffix="_audio_only" ;;
            "video_only") suffix="_video_only" ;;
            "audio_only") suffix="_audio_only" ;;
        esac
        local output_file="${base}${suffix}.${ext}"
        
        # Execute stream selection
        if execute_stream_selection "$file" "$output_file" "$operation" >/dev/null 2>&1; then
            echo "SUCCESS: $(basename "$output_file")"
            ((completed++))
        else
            echo "FAILED: $(basename "$file")"
            ((failed++))
        fi
        
        update_batch_progress "$batch_id" $completed $failed $skipped $total
    done
    
    echo "Batch stream selection completed: $completed successful, $failed failed, $skipped skipped"
    return 0
}

# Get batch processing summary
get_batch_summary() {
    local batch_id="$1"
    local summary="${BATCH_SUMMARIES[$batch_id]}"
    local state="${BATCH_STATES[$batch_id]}"
    local progress="${BATCH_PROGRESS[$batch_id]}"
    
    echo "Batch ID: $batch_id"
    echo "Status: $state"
    echo "Progress: $progress%"
    echo "Summary: $summary"
}
# ===== USER INTERFACE =====

# Main user interface following Universal Toolbox patterns
show_main_menu() {
    local MENU_ARGS=(
        "--list" "--width=600" "--height=400"
        "--title=🔒 Lossless Operations Toolbox" "--print-column=2"
        "--column=Type" "--column=Operation" "--column=Description"
        "✂️" "Trim Video" "Extract segments without re-encoding"
        "📦" "Change Format" "Remux to MP4/MKV/MOV/WebM containers"
        "🔗" "Merge Videos" "Concatenate files with identical codecs"
        "🎚️" "Edit Streams" "Remove audio/video tracks losslessly"
        "📝" "Edit Metadata" "Change file information without re-encoding"
        "⚡" "Batch Operations" "Process multiple files simultaneously"
    )
    
    zenity "${MENU_ARGS[@]}" --text="Select a lossless operation (no quality loss, fast processing):"
}

# Trimming interface
show_trimming_interface() {
    local files=("$@")
    
    if [ ${#files[@]} -eq 0 ]; then
        zenity --error --text="No files selected for trimming."
        return 1
    fi
    
    # Get trimming parameters
    local params=$(zenity --forms --title="Trim Video Segments" --width=400 \
        --text="Extract video segments using lossless stream copy:" \
        --add-entry="Start Time (seconds or hh:mm:ss):" \
        --add-entry="End Time (seconds or hh:mm:ss):" \
        --separator="|")
    
    if [ -z "$params" ]; then
        return 1
    fi
    
    IFS='|' read -ra VALS <<< "$params"
    local start_time="${VALS[0]}"
    local end_time="${VALS[1]}"
    
    if [ -z "$start_time" ] || [ -z "$end_time" ]; then
        zenity --error --text="Both start and end times are required."
        return 1
    fi
    
    # Process files
    (
        local total=${#files[@]}
        local current=0
        
        for file in "${files[@]}"; do
            echo "# Processing $(basename "$file")..."
            echo $(( current * 100 / total ))
            
            # Validate operation
            if ! validate_trimming_operation "$file" "$start_time" "$end_time"; then
                echo "# SKIPPED: $(basename "$file") - validation failed"
                ((current++))
                continue
            fi
            
            # Generate output filename
            local base="${file%.*}"
            local ext="${file##*.}"
            local output_file="${base}_trimmed_${start_time}s-${end_time}s.${ext}"
            
            # Execute trimming
            if execute_trimming "$file" "$output_file" "$start_time" "$end_time"; then
                echo "# SUCCESS: $(basename "$output_file")"
            else
                echo "# FAILED: $(basename "$file")"
            fi
            
            ((current++))
        done
        
        echo "100"
    ) | zenity --progress --title="Trimming Videos" --auto-close
    
    zenity --notification --text="Trimming completed!"
}

# Remuxing interface
show_remuxing_interface() {
    local files=("$@")
    
    if [ ${#files[@]} -eq 0 ]; then
        zenity --error --text="No files selected for remuxing."
        return 1
    fi
    
    # Get target container
    local container=$(zenity --list --title="Select Target Container" --width=400 --height=300 \
        --text="Choose output container format:" \
        --column="Format" --column="Description" \
        "mp4" "MP4 - Universal compatibility" \
        "mkv" "MKV - Open format, supports all codecs" \
        "mov" "MOV - Apple QuickTime format" \
        "webm" "WebM - Web-optimized format")
    
    if [ -z "$container" ]; then
        return 1
    fi
    
    # Process files
    (
        local total=${#files[@]}
        local current=0
        
        for file in "${files[@]}"; do
            echo "# Processing $(basename "$file")..."
            echo $(( current * 100 / total ))
            
            # Validate operation
            if ! validate_remuxing_operation "$file" "$container"; then
                echo "# SKIPPED: $(basename "$file") - incompatible codecs"
                ((current++))
                continue
            fi
            
            # Generate output filename
            local base="${file%.*}"
            local output_file="${base}_remuxed.${container}"
            
            # Execute remuxing
            if execute_remuxing "$file" "$output_file" "$container"; then
                echo "# SUCCESS: $(basename "$output_file")"
            else
                echo "# FAILED: $(basename "$file")"
            fi
            
            ((current++))
        done
        
        echo "100"
    ) | zenity --progress --title="Remuxing Videos" --auto-close
    
    zenity --notification --text="Remuxing completed!"
}

# Merging interface
show_merging_interface() {
    local files=("$@")
    
    if [ ${#files[@]} -lt 2 ]; then
        zenity --error --text="At least 2 files are required for merging."
        return 1
    fi
    
    # Validate codec compatibility
    if ! validate_merging_operation "${files[@]}"; then
        zenity --error --text="Files have incompatible codecs and cannot be merged losslessly.\n\nAll files must have identical video and audio codec parameters."
        return 1
    fi
    
    # Get output filename
    local output_file=$(zenity --file-selection --save --title="Save Merged Video As" --filename="merged_video.mp4")
    
    if [ -z "$output_file" ]; then
        return 1
    fi
    
    # Execute merging
    (
        echo "# Merging ${#files[@]} files..."
        echo "50"
        
        if execute_merging "$output_file" "${files[@]}"; then
            echo "# SUCCESS: Merged video saved"
        else
            echo "# FAILED: Merging operation failed"
        fi
        
        echo "100"
    ) | zenity --progress --title="Merging Videos" --auto-close
    
    zenity --notification --text="Merging completed!"
}

# Stream editing interface
show_stream_editing_interface() {
    local files=("$@")
    
    if [ ${#files[@]} -eq 0 ]; then
        zenity --error --text="No files selected for stream editing."
        return 1
    fi
    
    # Get operation type
    local operation=$(zenity --list --title="Select Stream Operation" --width=400 --height=300 \
        --text="Choose stream editing operation:" \
        --column="Operation" --column="Description" \
        "remove_audio" "Remove audio track (video only)" \
        "remove_video" "Remove video track (audio only)" \
        "video_only" "Keep video track only" \
        "audio_only" "Keep audio track only")
    
    if [ -z "$operation" ]; then
        return 1
    fi
    
    # Process files
    (
        local total=${#files[@]}
        local current=0
        
        for file in "${files[@]}"; do
            echo "# Processing $(basename "$file")..."
            echo $(( current * 100 / total ))
            
            # Validate operation
            if ! validate_stream_selection "$file" "$operation"; then
                echo "# SKIPPED: $(basename "$file") - validation failed"
                ((current++))
                continue
            fi
            
            # Generate output filename
            local base="${file%.*}"
            local ext="${file##*.}"
            local suffix=""
            case "$operation" in
                "remove_audio") suffix="_no_audio" ;;
                "remove_video") suffix="_audio_only" ;;
                "video_only") suffix="_video_only" ;;
                "audio_only") suffix="_audio_only" ;;
            esac
            local output_file="${base}${suffix}.${ext}"
            
            # Execute stream selection
            if execute_stream_selection "$file" "$output_file" "$operation"; then
                echo "# SUCCESS: $(basename "$output_file")"
            else
                echo "# FAILED: $(basename "$file")"
            fi
            
            ((current++))
        done
        
        echo "100"
    ) | zenity --progress --title="Editing Streams" --auto-close
    
    zenity --notification --text="Stream editing completed!"
}

# Metadata editing interface
show_metadata_interface() {
    local files=("$@")
    
    if [ ${#files[@]} -eq 0 ]; then
        zenity --error --text="No files selected for metadata editing."
        return 1
    fi
    
    # Get operation type
    local operation=$(zenity --list --title="Select Metadata Operation" --width=400 --height=300 \
        --text="Choose metadata editing operation:" \
        --column="Operation" --column="Description" \
        "clean_metadata" "Remove all metadata (privacy)" \
        "set_rotation" "Set rotation metadata (0°, 90°, 180°, 270°)")
    
    if [ -z "$operation" ]; then
        return 1
    fi
    
    local value=""
    if [ "$operation" = "set_rotation" ]; then
        value=$(zenity --list --title="Select Rotation" --width=300 --height=250 \
            --text="Choose rotation angle:" \
            --column="Angle" "0" "90" "180" "270")
        
        if [ -z "$value" ]; then
            return 1
        fi
    fi
    
    # Process files
    (
        local total=${#files[@]}
        local current=0
        
        for file in "${files[@]}"; do
            echo "# Processing $(basename "$file")..."
            echo $(( current * 100 / total ))
            
            # Generate output filename
            local base="${file%.*}"
            local ext="${file##*.}"
            local suffix="_metadata_edited"
            local output_file="${base}${suffix}.${ext}"
            
            # Execute metadata editing
            if execute_metadata_editing "$file" "$output_file" "$operation" "$value"; then
                echo "# SUCCESS: $(basename "$output_file")"
            else
                echo "# FAILED: $(basename "$file")"
            fi
            
            ((current++))
        done
        
        echo "100"
    ) | zenity --progress --title="Editing Metadata" --auto-close
    
    zenity --notification --text="Metadata editing completed!"
}

# Batch operations interface
show_batch_interface() {
    local files=("$@")
    
    if [ ${#files[@]} -eq 0 ]; then
        zenity --error --text="No files selected for batch processing."
        return 1
    fi
    
    # Get batch operation type
    local operation=$(zenity --list --title="Select Batch Operation" --width=400 --height=300 \
        --text="Choose batch operation for ${#files[@]} files:" \
        --column="Operation" --column="Description" \
        "batch_trim" "Trim all files with same parameters" \
        "batch_remux" "Remux all files to same container" \
        "batch_stream" "Apply same stream editing to all files")
    
    if [ -z "$operation" ]; then
        return 1
    fi
    
    case "$operation" in
        "batch_trim")
            show_trimming_interface "${files[@]}"
            ;;
        "batch_remux")
            show_remuxing_interface "${files[@]}"
            ;;
        "batch_stream")
            show_stream_editing_interface "${files[@]}"
            ;;
    esac
}

# Main script execution
main() {
    # Check if files were passed as arguments
    if [ $# -eq 0 ]; then
        zenity --error --text="No files selected.\n\nPlease select video files and run this script from the right-click menu."
        exit 1
    fi
    
    local files=("$@")
    
    # Show main menu
    local choice=$(show_main_menu)
    
    if [ -z "$choice" ]; then
        exit 0
    fi
    
    case "$choice" in
        "Trim Video")
            show_trimming_interface "${files[@]}"
            ;;
        "Change Format")
            show_remuxing_interface "${files[@]}"
            ;;
        "Merge Videos")
            show_merging_interface "${files[@]}"
            ;;
        "Edit Streams")
            show_stream_editing_interface "${files[@]}"
            ;;
        "Edit Metadata")
            show_metadata_interface "${files[@]}"
            ;;
        "Batch Operations")
            show_batch_interface "${files[@]}"
            ;;
        *)
            zenity --error --text="Unknown operation: $choice"
            exit 1
            ;;
    esac
}

# Only run main if script is executed directly (not sourced)
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi