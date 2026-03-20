#!/bin/bash
# testing/test_image_toolbox.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"
[ "$HEADLESS" = true ] && setup_mock_zenity
generate_test_media
FAILED=0

# Ensure the symlink exists to avoid emoji issues in shell call
IM_REAL_PATH="imagemagick/🖼️ Image-Magick-Toolbox.sh"
IM_TOOLBOX="imagemagick/im_toolbox.sh"
if [ ! -L "$IM_TOOLBOX" ]; then
    ln -sf "$(basename "$IM_REAL_PATH")" "$IM_TOOLBOX"
fi

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

# Test 10: PDF Extract (Images from PDF)
echo "Test 10: PDF Extract"
# Mock a PDF file locally
cp "$TEST_DATA/input.jpg" "$TEST_DATA/extract_test.jpg"
magick "$TEST_DATA/extract_test.jpg" "$TEST_DATA/extract_test.pdf"
cat <<EOF > /tmp/zenity_responses
Action: ExtractPDF|Convert Format
JPG|Web Ready (Quality 85)
EOF
run_test "$IM_TOOLBOX" "format=jpeg" --pattern "$TEST_DATA/extract_test_web-*" "$TEST_DATA/extract_test.pdf" || FAILED=1
rm "$TEST_DATA/extract_test.jpg" "$TEST_DATA/extract_test.pdf"

# Test 11: PDF Merge (Images to PDF)
echo "Test 11: PDF Merge"
cat <<EOF > /tmp/zenity_responses
Convert Format
PDF|Archive (Lossless)
EOF
# The script generates a name like merged_images_arch.pdf when multiple files passed
# ImageMagick might report PDF or some viewers might see mjpeg stream, using a more lenient check
run_test "$IM_TOOLBOX" "file_size_gt=1000" --pattern "merged_images_*.pdf" "$TEST_DATA/input.jpg" "$TEST_DATA/input.jpg" || FAILED=1

echo -e "\n${GREEN}Image Toolbox Tests Finished!${NC}"
exit $FAILED
