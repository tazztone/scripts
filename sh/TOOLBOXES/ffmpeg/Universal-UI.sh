# Universal Toolbox UI Adapter
# Contains the Zenity interactive wizard and configuration form loops.

# Sourcing Guard
[ "${_UNIVERSAL_UI_SH_LOADED:-0}" -eq 1 ] && return
readonly _UNIVERSAL_UI_SH_LOADED=1

show_universal_wizard_flow() {
    local LOOP_COUNT=0
    local DO_SAVE=false
    
    while true; do
        LOOP_COUNT=$((LOOP_COUNT + 1))
        if [ $LOOP_COUNT -gt 10 ]; then
            _wizard_log "RECURSION GUARD TRIGGERED ($LOOP_COUNT attempts)"
            zenity --error --text="Recursive UI loop detected ($LOOP_COUNT attempts). If this is intentional, please restart the script."
            exit 1
        fi

        PICKED_RAW=$(show_unified_wizard "Universal Toolbox Wizard" "$INTENTS_STR" "$PRESET_FILE" "$HISTORY_FILE")
        [ -z "$PICKED_RAW" ] && exit 0
        _wizard_log "wizard returned: [$PICKED_RAW]"

        # Parse results
        local -a PARTS=()
        IFS='|' read -ra PARTS <<< "$PICKED_RAW"
        
        local INTENTS=""
        local LOAD_PRESET=""
        local LOAD_HISTORY=""
        DO_SAVE=false

        for VALUE in "${PARTS[@]}"; do
            VALUE=$(echo -n "$VALUE" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
            if [[ -z "$VALUE" || "$VALUE" == "---" ]]; then
                continue
            elif [[ "$VALUE" == "PRESET:"* ]]; then
                LOAD_PRESET="${VALUE#PRESET:}"
            elif [[ "$VALUE" == "HISTORY:"* ]]; then
                LOAD_HISTORY="${VALUE#HISTORY:}"
            elif [[ "$VALUE" == "ACTION:SAVE" ]]; then
                DO_SAVE=true
            else
                INTENTS+="$VALUE|"
            fi
        done

        if [ -n "$LOAD_PRESET" ]; then
            CHOICES=$(grep "^$LOAD_PRESET|" "$PRESET_FILE" | head -n 1 | cut -d'|' -f2-)
            [ -n "$CHOICES" ] && break
        elif [ -n "$LOAD_HISTORY" ]; then
            CHOICES="$LOAD_HISTORY"
            [ -n "$CHOICES" ] && break
        elif [ -n "$INTENTS" ]; then
            # --- CONFIG & SAVE (Step 2) ---
            local -a ZENITY_FORMS=(
                "--forms" "--title=Universal Toolbox: Configure"
                "--width=500" "--separator=|" 
                "--text=Finalize your recipe settings below:"
            )

            # 1. SPEED
            local VAL_ispd=" (Inactive)"
            [[ "$INTENTS" == *"Speed"* ]] && VAL_ispd="1x (Normal)"
            ZENITY_FORMS+=( "--add-combo=⏩ Speed" "--combo-values=$VAL_ispd|2x (Fast)|4x (Super Fast)|0.5x (Slow)|0.25x (Very Slow)" )
            ZENITY_FORMS+=( "--add-entry=✍️ Custom Speed" )

            # 2. SCALE
            local VAL_ires=" (Inactive)"
            [[ "$INTENTS" == *"Scale"* ]] && VAL_ires="1080p"
            ZENITY_FORMS+=( "--add-combo=📐 Resolution" "--combo-values=$VAL_ires|1440p|720p|4k|480p|360p|50%" )
            ZENITY_FORMS+=( "--add-entry=✍️ Custom Width (overrides)" )

            # 3. GEOMETRY & TIME
            local VAL_icrp=" (Inactive)"
            [[ "$INTENTS" == *"Crop"* ]] && VAL_icrp="16:9 (Landscape)"
            ZENITY_FORMS+=( "--add-combo=🖼️ Crop/Aspect" "--combo-values=$VAL_icrp|9:16 (Vertical)|Square 1:1|4:3 (Classic)|21:9 (Cinema)" )
            ZENITY_FORMS+=( "--add-entry=✍️ Custom Aspect Ratio (e.g. 21:9)" )
            
            local VAL_ior=" (Inactive)"
            [[ "$INTENTS" == *"Rotate"* ]] && VAL_ior="No Change"
            ZENITY_FORMS+=( "--add-combo=🔄 Orientation" "--combo-values=$VAL_ior|Rotate 90 CW|Rotate 90 CCW|Flip Horizontal|Flip Vertical" )
            
            ZENITY_FORMS+=( "--add-entry=⏱️ Trim Start" "--add-entry=⏱️ Trim End" )

            # 4. AUDIO & SUBS
            local VAL_iaud=" (Inactive)"
            [[ "$INTENTS" == *"Audio"* ]] && VAL_iaud="No Change"
            ZENITY_FORMS+=( "--add-combo=🔊 Audio Action" "--combo-values=$VAL_iaud|Remove Audio Track|Normalize (R128)|Boost Volume (+6dB)|Downmix to Stereo|Recode to PCM (for Linux)|Extract MP3|Extract WAV" )
            ZENITY_FORMS+=( "--add-entry=✍️ Custom Audio Filter (e.g. volume=2.0)" )
            
            local VAL_isub=" (Inactive)"
            [[ "$INTENTS" == *"Subtitles"* ]] && VAL_isub="Burn-in"
            ZENITY_FORMS+=( "--add-combo=📝 Subtitles" "--combo-values=$VAL_isub|Burn-in|Mux (Softsub)" )
            ZENITY_FORMS+=( "--add-entry=✍️ Custom Subtitle Style (e.g. Fontsize=30)" )

            # 5. EXPORT (Always active)
            ZENITY_FORMS+=( "--add-combo=💎 Quality Strategy" "--combo-values=Medium (CRF 23)|High (CRF 18)|Low (CRF 28)|Lossless (CRF 0)" )
            ZENITY_FORMS+=( "--add-entry=✍️ Custom CRF (0-51)" )
            ZENITY_FORMS+=( "--add-entry=💾 Target Size MB (overrides)" )
            ZENITY_FORMS+=( "--add-combo=📦 Output Format" "--combo-values=Auto/MP4|H.265|AV1|WebM|ProRes|MOV|MKV|GIF" )
            
            local HW_OPTS=""
            if [ -s "$GPU_CACHE" ]; then
                grep -q "nvenc" "$GPU_CACHE" && HW_OPTS="${HW_OPTS}Use NVENC (Nvidia)|"
                grep -q "qsv" "$GPU_CACHE" && HW_OPTS="${HW_OPTS}Use QSV (Intel)|"
                grep -q "vaapi" "$GPU_CACHE" && HW_OPTS="${HW_OPTS}Use VAAPI (AMD/Intel)|"
            fi
            HW_OPTS="${HW_OPTS}None (CPU Only)"
            ZENITY_FORMS+=( "--add-combo=🏎️ Hardware" "--combo-values=$HW_OPTS" )
            ZENITY_FORMS+=( "--add-entry=🔧 Extra FFmpeg Flags" )

            local CONFIG_RESULT
            CONFIG_RESULT=$(zenity "${ZENITY_FORMS[@]}" || true)
            if [ -z "$CONFIG_RESULT" ]; then
                _wizard_log "User cancelled configuration form"
                continue 
            fi

            # --- EXTRACT CONFIG & MAP TO CHOICES ---
            CHOICES=""
            _wizard_log "CONFIG_RESULT: [$CONFIG_RESULT]"
            
            local -a FORM_KEYS=(
                speed custom_speed resolution custom_width
                crop custom_ratio rotation trim_start trim_end
                audio custom_audio subtitles custom_subs
                quality custom_crf target_size format hw_accel extra_flags
            )
            declare -A CONFIG
            parse_forms_result "$CONFIG_RESULT" "${FORM_KEYS[@]}"

            # 0. Speed
            local PICK_spd="${CONFIG[speed]}"
            local CUST_SPD="${CONFIG[custom_speed]}"
            if [ -n "$CUST_SPD" ]; then
                CHOICES+="Speed: ${CUST_SPD}|"
                USER_SPEED="$CUST_SPD"
            elif [ -n "$PICK_spd" ]; then
                CHOICES+="Speed: ${PICK_spd}|"
            fi

            # 1. Scale
            local PICK_res="${CONFIG[resolution]}"
            local CUST_W="${CONFIG[custom_width]}"
            if [ -n "$CUST_W" ]; then
                CHOICES+="Custom Scale Width:$CUST_W|"
                USER_W="$CUST_W"
            elif [ -n "$PICK_res" ]; then
                CHOICES+="Scale: ${PICK_res}|"
            fi

            # 3. Crop
            local PICK_crp="${CONFIG[crop]}"
            local CUST_RATIO="${CONFIG[custom_ratio]}"
            if [ -n "$CUST_RATIO" ]; then
                CHOICES+="Custom Aspect Ratio:$CUST_RATIO|"
                USER_RATIO="$CUST_RATIO"
            elif [ -n "$PICK_crp" ]; then
                CHOICES+="Crop: $PICK_crp|"
            fi

            # 4. Rotate
            local PICK_rot="${CONFIG[rotation]}"
            [[ -n "$PICK_rot" && "$PICK_rot" != "No Change" ]] && CHOICES+="$PICK_rot|"

            # 5. Trim
            local T_S="${CONFIG[trim_start]}"
            local T_E="${CONFIG[trim_end]}"
            [ -n "$T_S" ] && { CHOICES+="Trim: Start|"; USER_TRIM_S="$T_S"; }
            [ -n "$T_E" ] && { CHOICES+="Trim: End|"; USER_TRIM_E="$T_E"; }

            # 7. Audio
            local PICK_aud="${CONFIG[audio]}"
            local CUST_AUD="${CONFIG[custom_audio]}"
            if [ -n "$CUST_AUD" ]; then
                CHOICES+="Audio Filter: $CUST_AUD|"
                USER_AUDIO_FILTER="$CUST_AUD"
            elif [ -n "$PICK_aud" ]; then
                CHOICES+="$PICK_aud|"
            fi

            # 8. Subtitles
            local PICK_sub="${CONFIG[subtitles]}"
            local CUST_SUB="${CONFIG[custom_subs]}"
            if [ -n "$CUST_SUB" ]; then
                CHOICES+="Subtitle Style: $CUST_SUB|"
                USER_SUB_STYLE="$CUST_SUB"
            elif [ -n "$PICK_sub" ]; then
                CHOICES+="Subtitles: $PICK_sub|"
            fi

            # EXPORT
            local Q_STRAT="${CONFIG[quality]}"
            local CUST_CRF="${CONFIG[custom_crf]}"
            local T_MB="${CONFIG[target_size]}"
            local O_FMT="${CONFIG[format]}"
            local H_ACCEL="${CONFIG[hw_accel]}"
            EXTRA_OPTS="${CONFIG[extra_flags]}"
            
            if [ -n "$CUST_CRF" ]; then
                CHOICES+="Custom CRF:$CUST_CRF|"
                USER_CRF="$CUST_CRF"
            fi

            if [ -n "$T_MB" ]; then
                CHOICES+="Target Size:$T_MB|"
                USER_TARGET_MB="$T_MB"
            else
                case "$Q_STRAT" in
                    *"High"*) CHOICES+="Quality: High|" ;;
                    *"Low"*) CHOICES+="Quality: Low|" ;;
                    *"Lossless"*) CHOICES+="Quality: Lossless|" ;;
                    *) CHOICES+="Quality: Medium|" ;;
                esac
            fi
            
            [[ "$O_FMT" != "Auto/MP4" ]] && CHOICES+="Output: $O_FMT|"

            if [[ "$H_ACCEL" == *"NVENC"* ]]; then CHOICES+="🏎️ Use NVENC (Nvidia)|"; fi
            if [[ "$H_ACCEL" == *"QSV"* ]]; then CHOICES+="🏎️ Use QSV (Intel)|"; fi
            if [[ "$H_ACCEL" == *"VAAPI"* ]]; then CHOICES+="🏎️ Use VAAPI (AMD/Intel)|"; fi

            CHOICES=$(echo "$CHOICES" | sed 's/|$//')
            _wizard_log "Final CHOICES: [$CHOICES]"
            
            [ -z "$CHOICES" ] && continue
            
            local SLUG
            SLUG=$(echo "$CHOICES" | sed 's/[^[:alnum:]| ]//g' | sed 's/ (Inactive)//g; s/No Change//g; s/Speed //g; s/Scale //g; s/Rotate //g; s/Flip //g; s/Crop //g; s/Trim //g; s/Output //g; s/Subtitles //g; s/Use //g; s/Fast//g; s/Slow//g; s/pixels//g; s/Quality //g; s/TargetSizeMB //g; s/|/_/g; s/ //g' | tr '[:upper:]' '[:lower:]')
            
            local FORCE_SAVE="false"
            [ "$DO_SAVE" = true ] && FORCE_SAVE="true"
            state_save_preset "$CHOICES" "$SLUG" "$FORCE_SAVE"
            break
        else
            exit 0
        fi
    done
}
