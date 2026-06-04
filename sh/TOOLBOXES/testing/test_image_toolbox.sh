#!/bin/bash
# testing/test_image_toolbox.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"
[ "$HEADLESS" = true ] && setup_mock_zenity
setup_mock_ffmpeg
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
export MOCK_LIST="Scale & Resize|Effects & Branding|Convert Format"
export MOCK_FORMS="50%|
Black & White|No Change||
WEBP|Web Ready (Quality 85)|"
run_test "$IM_TOOLBOX" "format=webp" "$TEST_DATA/input.jpg" || FAILED=1

# Test 2: Square Crop + PNG
echo "Test 2: Square Crop + PNG"
export MOCK_LIST="Crop & Geometry|Convert Format
🔲 Square Crop (Center 1:1)"
export MOCK_FORMS="PNG|Web Ready (Quality 85)|"
run_test "$IM_TOOLBOX" "tags=sq" "$TEST_DATA/input.jpg" || FAILED=1

# Test 3: Vertical 9:16 Crop
echo "Test 3: Vertical 9:16 Crop"
export MOCK_LIST="Crop & Geometry
📱 Vertical (9:16)"
run_test "$IM_TOOLBOX" "tags=9x16" "$TEST_DATA/input.jpg" || FAILED=1

# Test 4: Flatten Background
echo "Test 4: Flatten Background"
export MOCK_LIST="Flatten Background"
run_test "$IM_TOOLBOX" "tags=flat" "$TEST_DATA/alpha.png" || FAILED=1

# Test 5: Convert to sRGB
echo "Test 5: Convert to sRGB"
export MOCK_LIST="Convert to sRGB"
run_test "$IM_TOOLBOX" "tags=srgb" "$TEST_DATA/input.jpg" || FAILED=1

# Test 6: Montage
echo "Test 6: Montage"
export MOCK_LIST="Montage & Grid"
export MOCK_FORMS="🏁 2x Grid|"
run_test "$IM_TOOLBOX" "format=jpeg" --pattern "montage_*" "$TEST_DATA/input.jpg" "$TEST_DATA/input.jpg" || FAILED=1

# Test 7: Horizontal Crop (16:9)
echo "Test 7: Horizontal Crop (16:9)"
export MOCK_LIST="Crop & Geometry
🖥️ Landscape (16:9)"
run_test "$IM_TOOLBOX" "tags=16x9" "$TEST_DATA/input.jpg" || FAILED=1

# Test 8: Custom Resize (800x600)
echo "Test 8: Custom Resize (800x600)"
export MOCK_LIST="Scale & Resize"
export MOCK_FORMS="Custom|800x600"
run_test "$IM_TOOLBOX" "width=800" "$TEST_DATA/input.jpg" || FAILED=1

# Test 9: Text Annotation (Overlay)
echo "Test 9: Text Annotation"
export MOCK_LIST="Effects & Branding"
export MOCK_FORMS="No Change|Text Annotation|Watermark Text|"
run_test "$IM_TOOLBOX" "tags=text" "$TEST_DATA/input.jpg" || FAILED=1

# Test 10: PDF Extract (Images from PDF)
echo "Test 10: PDF Extract"
cp "$TEST_DATA/input.jpg" "$TEST_DATA/extract_test.jpg"
magick "$TEST_DATA/extract_test.jpg" "$TEST_DATA/extract_test.pdf"
export MOCK_LIST="Action: ExtractPDF|Convert Format"
export MOCK_FILE="."
export MOCK_FORMS="JPG|Web Ready (Quality 85)|"
run_test "$IM_TOOLBOX" "format=jpeg" --pattern "extract_test_web*" "$TEST_DATA/extract_test.pdf" || FAILED=1
rm "$TEST_DATA/extract_test.jpg" "$TEST_DATA/extract_test.pdf"

# Test 11: PDF Merge (Images to PDF)
echo "Test 11: PDF Merge"
export MOCK_LIST="Convert Format"
export MOCK_FILE="merged_images.pdf"
export MOCK_FORMS="PDF|Archive (Lossless)|"
run_test "$IM_TOOLBOX" "file_size_gt=1000" --pattern "*arch*.pdf" "$TEST_DATA/input.jpg" "$TEST_DATA/input.jpg" || FAILED=1

echo -e "\n${GREEN}Image Toolbox Tests Finished!${NC}"
exit $FAILED
