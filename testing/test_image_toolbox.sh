#!/bin/bash
# testing/test_image_toolbox.sh
# Testing framework for ImageMagick Toolbox

# --- Configuration ---
TEST_DATA="/tmp/image_test_data"
MOCK_BIN="/tmp/image_mock_bin"
REPORT_FILE="./image_test_report.log"
HEADLESS=true

mkdir -p "$TEST_DATA" "$MOCK_BIN"
echo "Image Test Session Started at $(date)" > "$REPORT_FILE"

# --- Zenity Mocking ---
setup_mock_zenity() {
    cat <<'EOF' > "$MOCK_BIN/zenity"
#!/bin/bash
ARGS="$*"
echo "MOCK ZENITY: $ARGS" >> "/tmp/zenity_image_mock.log"

if [[ "$ARGS" == *"--list"* ]]; then
    if [[ "$ARGS" == *"Select a starting point:"* ]]; then
        echo "New Custom Edit"
        exit 0
    fi
    if [[ "$ARGS" == *"Wizard Step 2"* ]]; then
        echo "${ZENITY_LIST_RESPONSE:-📐 Scale / Resize|📦 Format Converter|🚀 Optimization}"
        exit 0
    fi
fi

if [[ "$ARGS" == *"--forms"* ]]; then
    # 0:Resolution, 1:CustomGeom, 2:Format, 3:Optimize, 4:Effects, 5:Canvas, 6:Branding, 7:BrandingPayload
    echo "${ZENITY_FORM_RESPONSE:-1280x (720p)||WEBP|Web Ready (Quality 85 + Strip)|No Change|(Inactive)|(Inactive)|}"
    exit 0
fi

if [[ "$ARGS" == *"--progress"* ]]; then
    cat > /dev/null
    exit 0
fi

if [[ "$ARGS" == *"--question"* ]]; then exit 1; fi
exit 0
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
# Use absolute path for script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/../imagemagick/🖼️ Image-Magick-Toolbox.sh"

echo "Running Resize + Convert Test..."
export ZENITY_LIST_RESPONSE="📐 Scale / Resize|📦 Format Converter"
export ZENITY_FORM_RESPONSE="1280x (720p)||WEBP|(Inactive)|No Change|(Inactive)|(Inactive)|"
( cd "$TEST_DATA" && bash "$SCRIPT" "src.jpg" )

if validate_image "$TEST_DATA/src_720p.webp" "width=1280,format=webp"; then
    echo "[PASS] Resize + Convert"
else
    echo "[FAIL] Resize + Convert"
fi

echo "Running Optimization + Effects Test..."
export ZENITY_LIST_RESPONSE="🚀 Optimization|🔄 Effects"
export ZENITY_FORM_RESPONSE="(Inactive)||PNG|Web Ready (Quality 85 + Strip)|Black & White|(Inactive)|(Inactive)|"
( cd "$TEST_DATA" && bash "$SCRIPT" "src.jpg" ) > /dev/null 2>&1

if validate_image "$TEST_DATA/src_web_bw.png" "format=png"; then
    echo "[PASS] Optimization + Effects"
else
    echo "[FAIL] Optimization + Effects"
fi

echo "Running Text Annotation Test..."
export ZENITY_LIST_RESPONSE="🏷️ Branding"
export ZENITY_FORM_RESPONSE="(Inactive)||JPG|(Inactive)|No Change|(Inactive)|Text Annotation|Hello World"
( cd "$TEST_DATA" && bash "$SCRIPT" "src.jpg" ) > /dev/null 2>&1

if validate_image "$TEST_DATA/src_text.jpg" "format=jpeg"; then
    echo "[PASS] Text Annotation"
else
    echo "[FAIL] Text Annotation"
fi

echo "Running Montage Test..."
export ZENITY_LIST_RESPONSE="🖼️ Canvas & Crop"
export ZENITY_FORM_RESPONSE="(Inactive)||JPG|(Inactive)|No Change|2x Grid|(Inactive)|"
( cd "$TEST_DATA" && bash "$SCRIPT" "src.jpg" "small.png" ) > /dev/null 2>&1

if [ -f "$TEST_DATA/montage_grid2x.jpg" ]; then
    echo "[PASS] Montage"
else
    echo "[FAIL] Montage"
fi

echo "Running PDF Merge Test..."
export ZENITY_LIST_RESPONSE="📦 Format Converter"
export ZENITY_FORM_RESPONSE="(Inactive)||PDF|(Inactive)|No Change|(Inactive)|(Inactive)|"
( cd "$TEST_DATA" && bash "$SCRIPT" "src.jpg" "small.png" ) > /dev/null 2>&1

if [ -f "$TEST_DATA/merged_images.pdf" ]; then
    echo "[PASS] PDF Merge"
else
    echo "[FAIL] PDF Merge"
fi

# Cleanup
# rm -rf "$TEST_DATA" "$MOCK_BIN"
