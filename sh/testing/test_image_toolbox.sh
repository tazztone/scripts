# --- Library ---
source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"

[ "$HEADLESS" = true ] && setup_mock_zenity
generate_test_media

echo -e "\n${YELLOW}=== Image-Magick-Toolbox Tests ===${NC}"

# Test 1: Stacked Scale + BW + WEBP
echo "Test 1: Stacked Scale + BW + WEBP"
cat <<EOF > /tmp/zenity_responses
📏|Scale & Resize|✨|Effects & Branding|📦|Convert Format
1280x (720p)|
Black & White|(Inactive)|
WEBP|Web Ready (Quality 85)
EOF
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "width=1280,format=webp,tags=720p_bw_web" "$TEST_DATA/src.jpg"

# Test 2: Square Crop + PNG
echo "Test 2: Square Crop + PNG"
cat <<EOF > /tmp/zenity_responses
✂️|Crop & Geometry|📦|Convert Format
🔲 Square Crop (Center 1:1)
PNG|Archive (Lossless)
EOF
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "format=png,tags=sq_arch" "$TEST_DATA/src.jpg"

# Test 3: Vertical 9:16 Crop
echo "Test 3: Vertical 9:16 Crop"
cat <<EOF > /tmp/zenity_responses
✂️|Crop & Geometry
📱 Vertical (9:16)
EOF
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "tags=9x16" "$TEST_DATA/src.jpg"

# Test 4: Flatten Background
echo "Test 4: Flatten Background"
cat <<EOF > /tmp/zenity_responses
🎨|Flatten Background
EOF
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "tags=flat" "$TEST_DATA/src.jpg"

# Test 5: Convert to sRGB
echo "Test 5: Convert to sRGB"
cat <<EOF > /tmp/zenity_responses
🌈|Convert to sRGB
EOF
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "tags=srgb" "$TEST_DATA/src.jpg"

# Test 6: Montage (Multiple Inputs)
echo "Test 6: Montage"
cat <<EOF > /tmp/zenity_responses
🖼️|Montage & Grid
🏁 2x Grid
EOF
# Verify output file exists
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "tags=grid2x" "$TEST_DATA/src.jpg" "$TEST_DATA/src.jpg"

# Test 7: Horizontal Crop (16:9)
echo "Test 7: Horizontal Crop (16:9)"
cat <<EOF > /tmp/zenity_responses
✂️|Crop & Geometry
🖥️ Landscape (16:9)
EOF
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "tags=16x9" "$TEST_DATA/src.jpg"

# Test 8: Custom Resize
echo "Test 8: Custom Resize (800x600)"
cat <<EOF > /tmp/zenity_responses
📏|Scale & Resize
Custom|800x600
EOF
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "width=800,tags=800x600" "$TEST_DATA/src.jpg"

# Test 9: Text Annotation (Overlay)
echo "Test 9: Text Annotation (Overlay)"
cat <<EOF > /tmp/zenity_responses
✨|Effects & Branding
No Change|Text Annotation
Watermark Text
EOF
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "tags=text" "$TEST_DATA/src.jpg"

echo -e "\n${GREEN}Image Toolbox Tests Finished!${NC}"
