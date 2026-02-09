#!/bin/bash
# testing/test_image_toolbox.sh
# Testing framework for ImageMagick Toolbox v2.1 (Smart Builder)

# --- Configuration ---
TEST_DATA="/tmp/image_test_data"
MOCK_BIN="/tmp/image_mock_bin"
REPORT_FILE="testing/output/image_test_report.log"
HEADLESS=true

mkdir -p "$TEST_DATA" "$MOCK_BIN"
echo "Image Test Session v2.1 Started at $(date)" > "$REPORT_FILE"

# --- Stateful Zenity Mock ---
# We use a file to queue responses for sequential zenity calls
RESPONSE_QUEUE="/tmp/zenity_responses"
touch "$RESPONSE_QUEUE"

setup_mock_zenity() {
    cat <<'EOF' > "$MOCK_BIN/zenity"
#!/bin/bash
ARGS="$*"
RESPONSE_QUEUE="/tmp/zenity_responses"

# Log original call for debugging
echo "CALL: zenity $ARGS" >> "/tmp/zenity_test.log"

# Read next response from queue
if [ -s "$RESPONSE_QUEUE" ]; then
    RESPONSE=$(head -n 1 "$RESPONSE_QUEUE")
    sed -i '1d' "$RESPONSE_QUEUE"
    echo "$RESPONSE"
    exit 0
fi

# Fallback: Default behaviors
if [[ "$ARGS" == *"--question"* ]]; then exit 1; fi
if [[ "$ARGS" == *"--progress"* ]]; then cat > /dev/null; exit 0; fi
if [[ "$ARGS" == *"--notification"* ]]; then exit 0; fi

echo "MOCK FAIL: No response queued for: $ARGS" >> "/tmp/zenity_test.log"
exit 1
EOF
    chmod +x "$MOCK_BIN/zenity"
    export PATH="$MOCK_BIN:$PATH"
}

[ "$HEADLESS" = true ] && setup_mock_zenity

# --- Helpers ---
generate_test_image() {
    magick -size 1920x1080 canvas:red "$TEST_DATA/src.jpg"
    magick -size 100x100 canvas:blue "$TEST_DATA/small.png"
}

validate_image() {
    local file="$1"
    local rules="$2"
    [ ! -f "$file" ] && { echo "FAIL: Missing $file"; return 1; }
    
    IFS=',' read -ra ADDR <<< "$rules"
    for rule in "${ADDR[@]}"; do
        local key="${rule%%=*}"
        local val="${rule#*=}"
        case $key in
            width)
                local w=$(magick identify -format "%w" "$file")
                [[ "$w" != "$val" ]] && { echo "FAIL: Width $w != $val"; return 1; }
                ;;
            format)
                local f=$(magick identify -format "%m" "$file" | tr '[:upper:]' '[:lower:]')
                [[ "$f" != "$val" ]] && { echo "FAIL: Format $f != $val"; return 1; }
                ;;
        esac
    done
    return 0
}

# --- Test Runs ---
generate_test_image
rm -f "/tmp/zenity_test.log"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/../imagemagick/🖼️ Image-Magick-Toolbox.sh"

echo "--------------------------------------"
echo "Test 1: Stacked Scale + BW + WEBP"
# Sequence:
# 1. Main Menu -> Add Operation
# 2. Ops Menu -> Scale & Resize
# 3. Scale Form -> 1280x||
# 4. Main Menu -> Add Operation
# 5. Ops Menu -> Effects & Branding
# 6. Effects Form -> Black & White||
# 7. Main Menu -> Add Operation
# 8. Ops Menu -> Convert Format
# 9. Convert Form -> WEBP|Web Ready
# 10. Main Menu -> RUN OPERATIONS
cat <<EOF > "$RESPONSE_QUEUE"
📏 Scale & Resize|✨ Effects & Branding|📦 Convert Format
1280x (720p)|
Black & White|(Inactive)|
WEBP|Web Ready (Quality 85)
EOF

( cd "$TEST_DATA" && bash "$SCRIPT" "src.jpg" ) > /dev/null 2>&1

if validate_image "$TEST_DATA/src_720p_bw_web.webp" "width=1280,format=webp"; then
    echo "[PASS] Stacked Scale + BW"
else
    echo "[FAIL] Stacked Scale + BW (Check /tmp/zenity_test.log)"
fi

echo "Test 2: Square Crop + PNG"
# Sequence:
# 1. Main Menu -> Add Operation
# 2. Ops Menu -> Crop & Geometry
# 3. Crop List -> Square Crop (Center 1:1)
# 4. Main Menu -> Add Operation
# 5. Ops Menu -> Convert Format
# 6. Convert Form -> PNG|Archive
# 7. Main Menu -> RUN OPERATIONS
cat <<EOF > "$RESPONSE_QUEUE"
✂️ Crop & Geometry|📦 Convert Format
Square Crop (Center 1:1)
PNG|Archive (Lossless)
EOF

( cd "$TEST_DATA" && bash "$SCRIPT" "src.jpg" ) > /dev/null 2>&1

if validate_image "$TEST_DATA/src_sq_arch.png" "format=png"; then
    # Square aspect ratio check
    W=$(magick identify -format "%w" "$TEST_DATA/src_sq_arch.png")
    H=$(magick identify -format "%h" "$TEST_DATA/src_sq_arch.png")
    if [ "$W" -eq "$H" ]; then
        echo "[PASS] Square Crop"
    else
        echo "[FAIL] Square Crop (Ratio: ${W}x${H})"
    fi
else
    echo "[FAIL] Square Crop"
fi

echo "Test 3: Montage (Terminal Operation)"
# Sequence:
# 1. Main Menu -> Add Operation
# 2. Ops Menu -> Montage & Grid
# 3. Montage List -> 2x Grid
# (Montage executes immediately in v2.1)
cat <<EOF > "$RESPONSE_QUEUE"
🖼️ Montage & Grid
2x Grid
EOF

( cd "$TEST_DATA" && bash "$SCRIPT" "src.jpg" "small.png" )

if [ -f "$TEST_DATA/montage_grid2x.jpg" ]; then
    echo "[PASS] Montage"
else
    echo "[FAIL] Montage"
fi

# Cleanup
# rm -rf "$TEST_DATA" "$MOCK_BIN"
