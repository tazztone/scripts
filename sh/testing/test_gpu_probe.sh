#!/bin/bash
# testing/test_gpu_probe.sh
# Unit tests for probe_gpu in ffmpeg/common.sh

SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
source "$SCRIPT_DIR/lib_test.sh"

# Mock GPU_CACHE for testing
export GPU_CACHE="/tmp/scripts-sh-gpu-cache-test"
rm -f "$GPU_CACHE"

# Source common.sh after setting GPU_CACHE
source "$PROJECT_ROOT/ffmpeg/common.sh"

log_info "Testing probe_gpu cache logic..."

# 1. Test Refresh Logic (Cache expiry)
# Create an old cache file (25h ago)
mkdir -p "$(dirname "$GPU_CACHE")"
touch -t "$(date -d '25 hours ago' +%Y%m%d%H%M)" "$GPU_CACHE" 2>/dev/null || touch -t "$(date -v-25H +%Y%m%d%H%M)" "$GPU_CACHE"

# Mock ffmpeg to always fail (no GPU)
ffmpeg() { return 1; }
export -f ffmpeg

probe_gpu
if [ -s "$GPU_CACHE" ]; then
    log_fail "Cache should be empty when ffmpeg fails"
else
    log_pass "Cache cleared on expiry and failed probe"
fi

# 2. Test Success Probe
ffmpeg() {
    # Check if we're probing for nvenc
    if [[ "$*" == *"h264_nvenc"* ]]; then return 0; fi
    return 1
}
export -f ffmpeg
# Ensure cache is old to trigger probe
touch -t "$(date -d '2 days ago' +%Y%m%d%H%M)" "$GPU_CACHE" 2>/dev/null || touch -t "$(date -v-2d +%Y%m%d%H%M)" "$GPU_CACHE"

probe_gpu
if grep -q "nvenc" "$GPU_CACHE"; then
    log_pass "Detected nvenc via mock ffmpeg"
else
    log_fail "Failed to detect nvenc in mock probe"
fi

# 3. Test Cache Skip (Fresh cache)
# Mock ffmpeg to succeed for qsv now
ffmpeg() {
    if [[ "$*" == *"h264_qsv"* ]]; then return 0; fi
    return 1
}
export -f ffmpeg
# Cache is now "fresh" (just wrote it)
probe_gpu
if grep -q "qsv" "$GPU_CACHE"; then
    log_fail "Should have skipped probe due to fresh cache"
else
    log_pass "Correctly skipped probe for fresh cache"
fi

rm -f "$GPU_CACHE"
log_info "GPU probe tests completed."
