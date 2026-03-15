#!/bin/bash
# testing/test_image_toolbox.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"
[ "$HEADLESS" = true ] && setup_mock_zenity
generate_test_media
FAILED=0

# Use the symlink to avoid emoji issues in shell call
IM_TOOLBOX="imagemagick/im_toolbox.sh"

echo -e "\n${YELLOW}=== Image Toolbox Tests ===${NC}"

# Test 1: Scale + BW + WebP
echo "Test 1: WebP Conversion"
cat <<EOF > /tmp/zenity_responses
Scale & Resize|Effects & Branding|Convert Format
50%|
Black & White|No Change|
WEBP|Web Ready (Quality 85)
EOF
run_test "$IM_TOOLBOX" "format=webp" "$TEST_DATA/input.jpg" || FAILED=1

# Test 2: Square Crop + PNG
echo "Test 2: Square Crop + PNG"
cat <<EOF > /tmp/zenity_responses
Crop & Geometry|Convert Format
🔲 Square Crop (Center 1:1)
PNG|Web Ready (Quality 85)
EOF
run_test "$IM_TOOLBOX" "tags=sq" "$TEST_DATA/input.jpg" || FAILED=1

# Test 3: Vertical 9:16 Crop
echo "Test 3: Vertical 9:16 Crop"
cat <<EOF > /tmp/zenity_responses
Crop & Geometry
📱 Vertical (9:16)
EOF
run_test "$IM_TOOLBOX" "tags=9x16" "$TEST_DATA/input.jpg" || FAILED=1

# Test 4: Flatten Background
echo "Test 4: Flatten Background"
cat <<EOF > /tmp/zenity_responses
Flatten Background
EOF
run_test "$IM_TOOLBOX" "tags=flat" "$TEST_DATA/alpha.png" || FAILED=1

# Test 5: Convert to sRGB
echo "Test 5: Convert to sRGB"
cat <<EOF > /tmp/zenity_responses
Convert to sRGB
EOF
run_test "$IM_TOOLBOX" "tags=srgb" "$TEST_DATA/input.jpg" || FAILED=1

# Test 6: Montage
echo "Test 6: Montage"
cat <<EOF > /tmp/zenity_responses
Montage & Grid
🏁 2x Grid
EOF
run_test "$IM_TOOLBOX" "format=jpeg" --pattern "montage_*" "$TEST_DATA/input.jpg" "$TEST_DATA/input.jpg" || FAILED=1

# Test 7: Horizontal Crop (16:9)
echo "Test 7: Horizontal Crop (16:9)"
cat <<EOF > /tmp/zenity_responses
Crop & Geometry
🖥️ Landscape (16:9)
EOF
run_test "$IM_TOOLBOX" "tags=16x9" "$TEST_DATA/input.jpg" || FAILED=1

# Test 8: Custom Resize (800x600)
echo "Test 8: Custom Resize (800x600)"
cat <<EOF > /tmp/zenity_responses
Scale & Resize
Custom|800x600
EOF
run_test "$IM_TOOLBOX" "width=800" "$TEST_DATA/input.jpg" || FAILED=1

# Test 9: Text Annotation (Overlay)
echo "Test 9: Text Annotation"
cat <<EOF > /tmp/zenity_responses
Effects & Branding
No Change|Text Annotation|Watermark Text
EOF
run_test "$IM_TOOLBOX" "tags=text" "$TEST_DATA/input.jpg" || FAILED=1

echo -e "\n${GREEN}Image Toolbox Tests Finished!${NC}"
exit $FAILED
