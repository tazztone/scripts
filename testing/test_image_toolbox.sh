# --- Library ---
source "$(dirname "${BASH_SOURCE[0]}")/lib_test.sh"

[ "$HEADLESS" = true ] && setup_mock_zenity
generate_test_media

echo -e "\n${YELLOW}=== Image-Magick-Toolbox Tests ===${NC}"

# Test 1: Stacked Scale + BW + WEBP
echo "Test 1: Stacked Scale + BW + WEBP"
cat <<EOF > /tmp/zenity_responses
📏 Scale & Resize|✨ Effects & Branding|📦 Convert Format
1280x (720p)|
Black & White|(Inactive)|
WEBP|Web Ready (Quality 85)
EOF
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "width=1280,format=webp" "$TEST_DATA/src.jpg"

# Test 2: Square Crop + PNG
echo "Test 2: Square Crop + PNG"
cat <<EOF > /tmp/zenity_responses
✂️ Crop & Geometry|📦 Convert Format
Square Crop (Center 1:1)
PNG|Archive (Lossless)
EOF
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "format=png" "$TEST_DATA/src.jpg"

# Test 3: Vertical 9:16 Crop
echo "Test 3: Vertical 9:16 Crop"
cat <<EOF > /tmp/zenity_responses
✂️ Crop & Geometry
Vertical (9:16)
EOF
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "format=jpeg" "$TEST_DATA/src.jpg"

# Test 4: Flatten Background
echo "Test 4: Flatten Background"
cat <<EOF > /tmp/zenity_responses
🎨 Flatten Background
EOF
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "format=jpeg" "$TEST_DATA/src.jpg"

# Test 5: Convert to sRGB
echo "Test 5: Convert to sRGB"
cat <<EOF > /tmp/zenity_responses
🌈 Convert to sRGB
EOF
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "format=jpeg" "$TEST_DATA/src.jpg"

# Test 6: Montage (Multiple Inputs)
echo "Test 6: Montage"
cat <<EOF > /tmp/zenity_responses
🖼️ Montage & Grid
2x Grid
EOF
# Verify output file exists
run_test "imagemagick/🖼️ Image-Magick-Toolbox.sh" "" "$TEST_DATA/src.jpg" "$TEST_DATA/src.jpg"

echo -e "\n${GREEN}Image Toolbox Tests Finished!${NC}"
