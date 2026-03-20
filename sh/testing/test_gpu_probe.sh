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
touch -t "$(date -d '24 hours 1 minute ago' +%Y%m%d%H%M 2>/dev/null || date -v-24H -v-1M +%Y%m%d%H%M 2>/dev/null)" "$GPU_CACHE"

setup_mock_ffmpeg
# Mock ffmpeg to always fail (no GPU)
export MOCK_FFMPEG_NVENC=0 MOCK_FFMPEG_QSV=0 MOCK_FFMPEG_VAAPI=0

probe_gpu
if [ -s "$GPU_CACHE" ]; then
    log_fail "Cache should be empty when ffmpeg fails"
else
    log_pass "Cache cleared on expiry and failed probe"
fi

# 2. Test Success Probe
# Mock 'nvenc' success
export MOCK_FFMPEG_NVENC=1
# Ensure cache is old to trigger probe
touch -t "$(date -d '2 days ago' +%Y%m%d%H%M 2>/dev/null || date -v-2d +%Y%m%d%H%M 2>/dev/null)" "$GPU_CACHE"

probe_gpu
if grep -q "nvenc" "$GPU_CACHE"; then
    log_pass "Detected nvenc via mock binary"
else
    log_fail "Failed to detect nvenc in mock probe"
fi

# 3. Test Cache Skip (Fresh cache)
# Mock 'qsv' success now
export MOCK_FFMPEG_NVENC=0 MOCK_FFMPEG_QSV=1
# Cache is now "fresh" (just wrote it)
probe_gpu
if grep -q "qsv" "$GPU_CACHE"; then
    log_fail "Should have skipped probe due to fresh cache"
else
    log_pass "Correctly skipped probe for fresh cache"
fi

rm -f "$GPU_CACHE"
log_info "GPU probe tests completed."
