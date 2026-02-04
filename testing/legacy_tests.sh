#!/bin/bash
# legacy_tests.sh
# Tests for individual utility scripts that have been moved to ffmpeg/legacy/

# Inherit setup from main runner if needed or standalone
# Standalone for now - simpler

DIR="$(dirname "$(readlink -f "$0")")"
source "$DIR/test_runner.sh" --no-run

echo -e "\n${YELLOW}=== Running Legacy Category: Web & Social ===${NC}"
run_test "ffmpeg/legacy/1-01 🌐 H264-Social-Web-Presets.sh" "vcodec=h264,acodec=aac" "$TEST_DATA/src.mp4"
run_test "ffmpeg/legacy/1-05 🎞️ GIF-Palette-Optimized.sh" "" "$TEST_DATA/src.mp4"
run_test "ffmpeg/legacy/1-03 ⚖️ H264-Compress-to-Target-Size.sh" "vcodec=h264" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running Legacy Category: Editing Pro ===${NC}"
run_test "ffmpeg/legacy/2-01 🍎 ProRes-Intermediate-Transcoder.sh" "vcodec=prores" "$TEST_DATA/src.mp4"
run_test "ffmpeg/legacy/2-07 🎁 Container-Remux-Rewrap.sh" "vcodec=h264" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running Legacy Category: Audio Ops ===${NC}"
run_test "ffmpeg/legacy/3-01 🔊 Audio-Format-Converter.sh" "no_video,acodec=mp3" "$TEST_DATA/src.mp4"
run_test "ffmpeg/legacy/3-02 🎚️ Audio-Normalize-Boost-Mute.sh" "acodec=aac" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running Legacy Category: Geometry & Time ===${NC}"
# Note: These paths will fail if they were originally in ffmpeg/ but now in ffmpeg/legacy/
run_test "ffmpeg/legacy/4-01 📐 Resolution-Smart-Scaler.sh" "width=1920,height=1080" "$TEST_DATA/src.mp4"
run_test "ffmpeg/legacy/4-02 🔄 Geometry-Rotate-Flip.sh" "width=1080,height=1920" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Running Legacy Category: Utils ===${NC}"
run_test "ffmpeg/legacy/5-01 🖼️ Image-Extract-Thumb-Sequence.sh" "" "$TEST_DATA/src.mp4"
run_test "ffmpeg/legacy/5-05 🧹 Metadata-Privacy-Web-Optimize.sh" "" "$TEST_DATA/src.mp4"

echo -e "\n${YELLOW}=== Legacy Test Summary ===${NC}"
grep "FAIL" "$REPORT_FILE" && echo -e "${RED}Some legacy tests failed!${NC}" || echo -e "${GREEN}All legacy tests passed!${NC}"
