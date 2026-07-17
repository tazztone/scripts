# Lossless Operations Toolbox UI Adapter
# Contains Zenity interactive dialogs and wizard selection screens.

# Sourcing Guard
[ "${_LOSSLESS_UI_SH_LOADED:-0}" -eq 1 ] && return
readonly _LOSSLESS_UI_SH_LOADED=1

# Enhanced main menu with unified wizard
show_main_menu() {
    if [ -n "$PRELOADED_PRESET" ]; then
        echo "$PRELOADED_PRESET"
        return 0
    fi

    local INTENTS="✂️|Trim Video|Extract segments;📦|Change Format|Remux to MP4/MKV/MOV/WebM;🔗|Merge Videos|Concatenate identical codecs;🎚️|Edit Streams|Remove audio/video tracks;📝|Edit Metadata|Change file info;⚡|Batch Operations|Process multiple files"
    
    local PICKED_RAW
    PICKED_RAW=$(show_unified_wizard "Lossless Toolbox Wizard" "$INTENTS" "$PRESET_FILE" "$HISTORY_FILE")
    [ -z "$PICKED_RAW" ] && return 1

    # Result format: "Name|Name|..."
    local -a PARTS=()
    IFS='|' read -ra PARTS <<< "$PICKED_RAW"
    
    local SELECTED_INTENT=""
    for VALUE in "${PARTS[@]}"; do
        VALUE=$(echo -n "$VALUE" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        if [[ -z "$VALUE" || "$VALUE" == "---" ]]; then
            continue
        elif [[ "$VALUE" == "PRESET:"* ]]; then
            local p_name="${VALUE#PRESET:}"
            local pd
            pd=$(grep "^$p_name|" "$PRESET_FILE" | head -n 1 | cut -d'|' -f2-)
            if [ -n "$pd" ]; then
                echo "$pd"
                return 0
            fi
        elif [[ "$VALUE" == "HISTORY:"* ]]; then
             echo "${VALUE#HISTORY:}"
             return 0
        else
            SELECTED_INTENT="$VALUE"
        fi
    done

    echo "$SELECTED_INTENT"
    return 0
}

# Enhanced trimming interface with smart validation and auto-rename
show_trimming_interface() {
    local files=("$@")
    
    if [ ${#files[@]} -eq 0 ]; then
        zenity --error --text="No files selected for trimming."
        return 1
    fi
    
    local params
    params=$(zenity --forms --title="Trim Video Segments" --width=450 \
        --text="Extract video segments using lossless stream copy:" \
        --add-entry="Start Time (e.g., 10, 1:30, 01:30:45):" \
        --add-entry="End Time (e.g., 60, 5:00, 02:15:30):" \
        --separator="|") || true
    
    if [ -z "$params" ]; then
        return 1
    fi
    
    local -a VALS=()
    IFS='|' read -ra VALS <<< "$params"
    local start_input="${VALS[0]}"
    local end_input="${VALS[1]}"
    
    if [ -z "$start_input" ] || [ -z "$end_input" ]; then
        zenity --error --text="Both start and end times are required."
        return 1
    fi
    
    local start_time
    start_time=$(validate_time_format "$start_input")
    if [ $? -ne 0 ]; then
        zenity --error --text="Invalid start time format: '$start_input'\nUse seconds (e.g., 30) or time format (e.g., 1:30 or 01:30:45)"
        return 1
    fi
    
    local end_time
    end_time=$(validate_time_format "$end_input")
    if [ $? -ne 0 ]; then
        zenity --error --text="Invalid end time format: '$end_input'\nUse seconds (e.g., 120) or time format (e.g., 2:00 or 00:02:00)"
        return 1
    fi
    
    state_add_history "trim|$start_time|$end_time"
    
    (
        local total=${#files[@]}
        local current=0
        
        for file in "${files[@]}"; do
            echo "# Processing $(basename "$file")..."
            echo $(( current * 100 / total ))
            
            if ! validate_trimming_operation "$file" "$start_time" "$end_time"; then
                echo "# SKIPPED: $(basename "$file") - validation failed"
                (( current += 1 ))
                continue
            fi
            
            local base="${file%.*}"
            local ext="${file##*.}"
            local output_file
            output_file=$(generate_safe_filename "$base" "_trimmed_${start_time}s-${end_time}s" "$ext")
            
            if execute_trimming "$file" "$output_file" "$start_time" "$end_time"; then
                echo "# SUCCESS: $(basename "$output_file")"
            else
                echo "# FAILED: $(basename "$file")"
            fi
            
            (( current += 1 ))
        done
        
        echo "100"
    ) | zenity --progress --title="Trimming Videos" --auto-close
    
    zenity --notification --text="Trimming completed!"
}

# Enhanced remuxing interface with container optimization
show_remuxing_interface() {
    local files=("$@")
    
    if [ ${#files[@]} -eq 0 ]; then
        zenity --error --text="No files selected for remuxing."
        return 1
    fi
    
    local RES
    RES=$(zenity --forms --title="📦 Remuxing Options" --width=500 \
        --text="Choose output container and extra flags (lossless):" \
        --add-combo="Target Container" --combo-values="mp4|mkv|mov|webm" \
        --add-entry="🔧 Extra FFmpeg Flags" || true)
    
    if [ -z "$RES" ]; then
        return 1
    fi
    
    local container
    container=$(echo "$RES" | cut -d'|' -f1)
    local extra_flags
    extra_flags=$(echo "$RES" | cut -d'|' -f2)
    
    state_add_history "remux|$container|$extra_flags"
    
    (
        local total=${#files[@]}
        local current=0
        local successful=0
        local failed=0
        local skipped=0
        
        for file in "${files[@]}"; do
            echo "# Processing $(basename "$file")..."
            echo $(( current * 100 / total ))
            
            if ! validate_remuxing_operation "$file" "$container"; then
                echo "# SKIPPED: $(basename "$file") - incompatible codecs"
                ((skipped += 1))
                (( current += 1 ))
                continue
            fi
            
            local base="${file%.*}"
            local output_file
            output_file=$(generate_safe_filename "$base" "_remuxed" "$container")
            
            if execute_remuxing "$file" "$output_file" "$container"; then
                echo "# SUCCESS: $(basename "$output_file")"
                (( successful += 1 ))
            else
                echo "# FAILED: $(basename "$file")"
                (( failed += 1 ))
            fi
            
            (( current += 1 ))
        done
        
        echo "100"
        echo "# Completed: $successful successful, $failed failed, $skipped skipped"
    ) | zenity --progress --title="Remuxing Videos to $container" --auto-close
    
    zenity --notification --text="Remuxing completed! Check output for details."
}

# Merging interface
show_merging_interface() {
    local files=("$@")
    
    if [ ${#files[@]} -lt 2 ]; then
        zenity --error --text="At least 2 files are required for merging."
        return 1
    fi
    
    if ! validate_merging_operation "${files[@]}"; then
        zenity --error --text="Files have incompatible codecs and cannot be merged losslessly.\n\nAll files must have identical video and audio codec parameters."
        return 1
    fi
    
    local output_file
    output_file=$(zenity --file-selection --save --title="Save Merged Video As" --filename="merged_video.mp4" || true)
    
    if [ -z "$output_file" ]; then
        return 1
    fi
    
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
    
    local operation
    operation=$(zenity --list --title="Select Stream Operation" --width=400 --height=300 \
        --text="Choose stream editing operation:" \
        --column="Operation" --column="Description" \
        "remove_audio" "Remove audio track (video only)" \
        "remove_video" "Remove video track (audio only)" \
        "video_only" "Keep video track only" \
        "audio_only" "Keep audio track only") || true
    
    if [ -z "$operation" ]; then
        return 1
    fi
    
    (
        local total=${#files[@]}
        local current=0
        
        for file in "${files[@]}"; do
            echo "# Processing $(basename "$file")..."
            echo $(( current * 100 / total ))
            
            if ! validate_stream_selection "$file" "$operation"; then
                echo "# SKIPPED: $(basename "$file") - validation failed"
                (( current += 1 ))
                continue
            fi
            
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
            
            if execute_stream_selection "$file" "$output_file" "$operation"; then
                echo "# SUCCESS: $(basename "$output_file")"
            else
                echo "# FAILED: $(basename "$file")"
            fi
            
            (( current += 1 ))
        done
        
        echo "100"
    ) | zenity --progress --title="Editing Streams" --auto-close
    
    zenity --notification --text="Stream editing completed!"
}

# Enhanced metadata editing interface with comprehensive cleaning
show_metadata_interface() {
    local files=("$@")
    
    if [ ${#files[@]} -eq 0 ]; then
        zenity --error --text="No files selected for metadata editing."
        return 1
    fi
    
    local operation
    operation=$(zenity --list --title="Select Metadata Operation" --width=500 --height=350 \
        --text="Choose metadata editing operation (lossless):" \
        --column="Operation" --column="Description" --column="Privacy Level" \
        "clean_metadata" "Remove all metadata" "High - Complete privacy" \
        "set_rotation" "Set rotation metadata only" "Low - Orientation fix" \
        "set_title" "Set custom title" "Medium - Basic info" \
        "set_custom" "Set custom tag (Key=Value)" "Variable - User defined") || true
    
    if [ -z "$operation" ]; then
        return 1
    fi
    
    local value=""
    case "$operation" in
        "set_rotation")
            value=$(zenity --list --title="Select Rotation" --width=300 --height=250 \
                --text="Choose rotation angle (metadata only, no re-encoding):" \
                --column="Angle" --column="Description" \
                "0" "No rotation (reset)" \
                "90" "Rotate 90° clockwise" \
                "180" "Rotate 180° (upside down)" \
                "270" "Rotate 270° clockwise (90° CCW)") || true
            ;;
        "set_title")
            value=$(zenity --entry --title="Set Title" --text="Enter new title for the video:" \
                --entry-text="") || true
            ;;
        "set_custom")
            value=$(zenity --entry --title="Set Custom Tag" --text="Enter custom metadata (e.g. comment=MyComment):" \
                --entry-text="comment=") || true
            ;;
    esac
    
    if [ "$operation" != "clean_metadata" ] && [ -z "$value" ]; then
        return 1
    fi
    
    state_add_history "metadata|$operation|$value"
    
    (
        local total=${#files[@]}
        local current=0
        
        for file in "${files[@]}"; do
            echo "# Processing $(basename "$file")..."
            echo $(( current * 100 / total ))
            
            local base="${file%.*}"
            local ext="${file##*.}"
            local suffix=""
            case "$operation" in
                "clean_metadata") suffix="_cleaned" ;;
                "set_rotation") suffix="_rotated_${value}deg" ;;
                "set_title") suffix="_titled" ;;
                "set_custom") suffix="_metadata" ;;
            esac
            local output_file
            output_file=$(generate_safe_filename "$base" "$suffix" "$ext")
            
            if execute_metadata_editing "$file" "$output_file" "$operation" "$value"; then
                echo "# SUCCESS: $(basename "$output_file")"
            else
                echo "# FAILED: $(basename "$file")"
            fi
            
            (( current += 1 ))
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
    
    local operation
    operation=$(zenity --list --title="Select Batch Operation" --width=400 --height=300 \
        --text="Choose batch operation for ${#files[@]} files:" \
        --column="Operation" --column="Description" \
        "batch_trim" "Trim all files with same parameters" \
        "batch_remux" "Remux all files to same container" \
        "batch_stream" "Apply same stream editing to all files") || true
    
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
