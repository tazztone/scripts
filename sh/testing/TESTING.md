# 🧪 Testing Framework Guide

This repository uses a custom-built, headless testing framework designed to validate Nautilus scripts without requiring a physical display or user interaction. The framework includes both traditional script testing and specialized property-based testing for the Lossless Operations Toolbox.

## 📋 Table of Contents

- [Architecture: The Zenity Mock](#-architecture-the-zenity-mock)
- [How to Run Tests](#-how-to-run-tests)
- [Current Test Coverage](#-current-test-coverage)
- [Coverage Gaps & Technical Debt](#-coverage-gaps--technical-debt)
- [Common Roadblocks & Pitfalls](#-common-roadblocks--pitfalls)
- [Negative Path & Resilience Testing](#-new-negative-path--resilience-testing)
- [Guide for AI Agents](#-guide-for-ai-agents)
- [Troubleshooting](#-troubleshooting)
- [Expansion](#-expansion)
- [Quick Reference: Common Testing Scenarios](#-quick-reference-common-testing-scenarios)

## 🏗️ Architecture: The Zenity Mock
The core of the testing suite is `testing/test_runner.sh`. It functions by "hijacking" the `zenity` command.

1.  **Mock Injection**: The runner creates a temporary bash script named `zenity` in `/tmp/scripts_mock_bin`.
2.  **PATH Precedence**: It prepends this directory to the `$PATH`. When scripts run `zenity`, they execute our mock instead of the system binary.
3.  **Programmable Responses**: The mock script inspects the incoming arguments (like `--list` or `--entry`) and returns predefined strings based on the context.

### Dynamic Overrides
You can control the mock's behavior for specific tests using environment variables:
*   `ZENITY_LIST_RESPONSE`: Force the mock to return specific checklist/list items (e.g., `"📐 Scale: 720p|📦 Output: H.265"`).
*   `ZENITY_ENTRY_RESPONSE`: Force the mock to return an input string (e.g., `"25"` for Target Size).

## 🚀 How to Run Tests

### Quick Start
Run all tests with a single command:
```bash
bash testing/test_runner.sh && bash testing/test_lossless_toolbox.sh
```

### Universal Script Testing
```bash
bash testing/test_runner.sh
```
The runner will:
1.  Generate dummy media (H.264/AAC) in `/tmp/scripts_test_data`.
2.  Execute scripts against this data.
3.  Analyze the output files using `ffprobe` to verify codecs, resolution, and metadata.

**Example Output:**
```
=== Universal Scripts Test Suite ===

Testing: Universal Toolbox - H.264 Compression
[PASS] H.264 Compression - vcodec=h264, width=1280

Testing: Universal Toolbox - HEVC Scaling
[PASS] HEVC Scaling - vcodec=hevc, width=1280, height=720

=== Test Summary ===
Total Tests: 15
Passed: 15
Failed: 0
All tests passed!
```

### Lossless Operations Toolbox Testing
```bash
bash testing/test_lossless_toolbox.sh
```
This specialized test suite uses **Property-Based Testing** to validate:
- **Stream Copy Preservation**: Ensures no re-encoding occurs
- **Codec Compatibility**: Validates container-codec combinations
- **Operation Safety**: Prevents destructive operations
- **Batch Processing**: Multi-file operation integrity
- **Metadata Handling**: Lossless metadata operations

**Test Coverage**: 12 comprehensive property tests with 100% pass rate validation.

---

## 📊 Current Test Coverage

The test suite provides specialized coverage across the different toolboxes:

| Test File | What it covers |
|---|---|
| `test_lossless_toolbox.sh` | 12 properties: stream copy, trimming, remux, metadata, stream selection, codec analysis, batch, rotation |
| `test_image_toolbox.sh` | 6 scenarios: scale+BW+WEBP, square crop, 9:16 crop, flatten, sRGB, montage |
| `test_universal_extended.sh` | 8 scenarios: 16:9 crop, 9:16 crop, rotate, normalize, extract MP3, trim, combo, GIF |
| `test_ui_resilience.sh` | Cancel flows, sub-dialog cancels, no-files error, resilience (cancel→retry→success) |
| `test_cross_version.sh` | Cross-version compatibility |
| `test_loop_detection.sh` | Loop/infinite cycle detection |
| `test_wizard_contract.sh` | Wizard UI contract compliance |
| `test_wizard_robust.sh` | Wizard robustness |

### File Validation: Inconsistencies & Gaps

While `lib_test.sh` contains a robust `validate_media()` function (checking width, height, codecs, format, and tags), its application is inconsistent:
- **Universal & Image Toolboxes**: Well-validated using end-to-end rules.
- **Lossless Toolbox**: Primarily tests internal functions by sourcing the script directly. This verifies logic but misses the end-to-end user flow and actual output file quality validation in the unified style.

## 🛑 Coverage Gaps & Technical Debt

### Missing Operation Tests
- **Universal Toolbox**: Subtitle burn-in/embed, speed changes, deinterlace, and hardware encoding paths (NVENC, etc.) are currently untested.
- **Image Toolbox**: Watermarking/overlays, borders/padding, and custom arbitrary resizing are untested.
- **Lossless Toolbox**: Lacks actual output file validation for "Merge" operations and tight duration tolerance checks (currently ±1s, should be ±0.1s).

### Technical Debt
- **Namespace Pollution**: `test_lossless_toolbox.sh` sources script paths directly, which can cause subtle interference.
- **Detection Fragility**: `run_test` output detection via `ls -1` is fragile and may miss outputs in different directories.
- **Rounding Issues**: `fps` validation in `validate_media` uses integer division, which can cause mismatches (e.g., 29 instead of 30).
- **Incomplete Validation**: Missing rules for exact `duration`, `bitrate`, and `subtitle_stream` presence.

---

## 🚧 Common Roadblocks & Pitfalls
If tests are hanging or failing unexpectedly, check these common issues discovered during the v2.5 refactor:

### 1. The "Zenity TTY" Hang
FFmpeg and Zenity can both attempt to interact with the terminal.
*   **The Trap**: FFmpeg usually waits for 'q' to quit. In a background test, this causes an infinite stall.
*   **The Fix**: **Always** use the `-nostdin` flag in FFmpeg calls within these scripts.

### 2. Menu vs. Checklist Loops
The **Universal Toolbox** uses a Launchpad menu. 
*   **The Trap**: If the mock returns a checklist string to the *main menu*, the menu doesn't recognize the input and refreshes infinitely.
*   **The Fix**: Ensure the Zenity mock specifically checks for `"Select a starting point:"` and returns `"New Custom Edit"` to bypass the menu before providing checklist choices.

### 3. String Mismatches (Emoji & Colons)
*   **The Trap**: If the UI label is `📐 Scale: 720p` but the script logic checks for `[[ "$CHOICES" == *"Scale 720p"* ]]`, the filter will be skipped (silently failing the test).
*   **The Fix**: Always synchronize the internal keyword checks with the exact string returned by the Zenity checklist.

### 4. FFmpeg Concat Escaping
*   **The Trap**: The `concat` demuxer requires a very specific path format in the list file. `printf %q` (Standard shell escaping) is **not** always compatible with FFmpeg's internal parser.
*   **The Fix**: Manually escape single quotes as `''` and wrap paths in single quotes inside the `concat_list` file.

---

## 🚀 New: Negative Path & Resilience Testing
As of v2.6, the framework supports testing "unhappy paths" such as user cancellations and empty forms.

### 1. Simulating Cancellations
Use the `ZENITY_MOCK_EXIT_CODE` environment variable to force the mock to return a specific exit status (e.g., `1` for Cancel).
```bash
export ZENITY_MOCK_EXIT_CODE=1
run_negative_test "myscript.sh" "input.mp4"
unset ZENITY_MOCK_EXIT_CODE
```

### 2. Testing Resilience
Use `run_resilience_test` when you want to verify that a script survives a cancellation mid-flow but eventually produces a valid output.
- Set up a `/tmp/zenity_responses` queue with mixed "cancel" strings (empty) and valid selections.
- The test succeeds only if an output file is correctly generated despite the internal "continue" loops.

---

## 🛠️ Troubleshooting

#### Tests Hang Indefinitely
**Cause:** FFmpeg waiting for terminal input or Zenity dialog stuck.

**Solution:**
1. Ensure all FFmpeg commands include `-nostdin` flag
2. Check that Zenity mock responses match expected UI strings exactly
3. Run with verbose output: `bash -x testing/test_runner.sh`

#### Tests Fail with "Command Not Found"
**Cause:** Missing dependencies or incorrect PATH.

**Solution:**
```bash
# Verify dependencies are installed
which ffmpeg zenity bc ffprobe

# Install missing packages
sudo apt install ffmpeg zenity bc
```

#### String Mismatch Errors
**Cause:** UI labels don't match test mock responses.

**Solution:**
1. Check the exact string in the script's zenity call
2. Update `ZENITY_ARGS` in `test_runner.sh` to match
3. Include emojis and colons exactly as they appear in the UI

#### FFmpeg Concat Demuxer Fails
**Cause:** Incorrect path escaping in concat list file.

**Solution:**
- Manually escape single quotes as `''`
- Wrap paths in single quotes inside the `concat_list` file
- Avoid using `printf %q` for FFmpeg concat paths

---

## 🤖 Guide for AI Agents

When modifying these scripts, follow these strict rules to keep the test suite green:

### Critical Rules

1.  **Verify UI Strings**: If you add an emoji or change a label prefix (like adding a colon), you **MUST** update both the logic in the script and the `ZENITY_ARGS` inside `test_runner.sh`.

2.  **Use -nostdin**: Every new FFmpeg command added must include `-nostdin`. This prevents FFmpeg from waiting for terminal input, which causes hangs in headless testing.

3.  **Mock Context**: If you add a new Zenity dialog type (e.g., `--calendar`), you must update the mock script inside `test_runner.sh` to handle that flag.

4.  **Handle Cancellations**: Every Zenity call should be checked for cancellation. Ensure that clicking "Cancel" in a sub-dialog returns the user to the main menu rather than exiting the script (unless it's the top-level menu).

5.  **Test Negative Paths**: When adding new UI features, add a corresponding test in [`testing/test_ui_resilience.sh`](testing/test_ui_resilience.sh).

### Testing Checklist

Before committing changes:

- [ ] Run `bash testing/test_runner.sh` - all tests should pass
- [ ] Run `bash testing/test_lossless_toolbox.sh` - 12/12 properties should pass
- [ ] Run `bash testing/test_lint.sh` - no syntax errors
- [ ] Verify UI strings match between script and test mocks
- [ ] Check that all FFmpeg commands include `-nostdin`

## 📈 Expansion
To add a new test case:
1.  Open `testing/test_runner.sh`.
2.  Add a new `run_test` call at the bottom.
3.  Define validation rules (e.g., `"vcodec=hevc,width=1280"`).
4.  If the script requires specific user input, `export` the necessary `ZENITY_` variables before calling `run_test`.

---

## 🔧 Quick Reference: Common Testing Scenarios

#### Test a Specific Script with Custom Input
```bash
# Set custom responses for zenity dialogs
export ZENITY_LIST_RESPONSE="📐 Scale: 720p|📦 Output: H.265"
export ZENITY_ENTRY_RESPONSE="25"

# Run the test
bash testing/test_runner.sh

# Clean up environment
unset ZENITY_LIST_RESPONSE ZENITY_ENTRY_RESPONSE
```

#### Test User Cancellation (Negative Path)
```bash
# Force zenity to return exit code 1 (Cancel)
export ZENITY_MOCK_EXIT_CODE=1

# Run test - should handle cancellation gracefully
bash testing/test_ui_resilience.sh

unset ZENITY_MOCK_EXIT_CODE
```

#### Run Syntax Check Only
```bash
# Fast syntax validation without running tests
bash testing/test_lint.sh
```

#### Debug a Failing Test
```bash
# Enable verbose output and check logs
bash -x testing/test_runner.sh 2>&1 | tee /tmp/test_debug.log

# To check unified wizard logs (if DEBUG_MODE=1)
cat ~/.local/share/scripts-sh/debug.log
```

---

## 🔒 Lossless Operations Toolbox Testing

The Lossless Operations Toolbox uses a specialized **Property-Based Testing** approach to validate correctness and safety of lossless operations.

### Property-Based Testing Philosophy
Instead of testing specific input/output combinations, property-based testing validates universal properties that should always hold true:

- **Stream Copy Preservation**: No re-encoding should ever occur
- **Codec Compatibility**: Container-codec combinations must be valid
- **Operation Safety**: Destructive operations must be prevented
- **Metadata Integrity**: Metadata operations must preserve streams

### Test Properties
The test suite validates 12 comprehensive properties:

1. **Stream Copy Preservation**: Validates FFmpeg commands use `-c copy`
2. **Lossless Operation Validation**: Ensures only safe operations are allowed
3. **Trimming Accuracy**: Validates time range and duration handling
4. **Container Format Remuxing**: Tests format conversion compatibility
5. **Codec Compatibility Validation**: Multi-file codec matching
6. **Metadata Preservation**: Lossless metadata handling
7. **Stream Selection Accuracy**: Track removal/selection validation
8. **Metadata-Only Rotation**: Rotation without re-encoding
9. **Alternative Suggestions**: Helpful error messages for invalid operations
10. **Batch Processing Integrity**: Multi-file operation consistency
11. **Codec Analysis Accuracy**: FFprobe integration validation
12. **Multi-File Compatibility Analysis**: Batch operation validation

### Running Lossless Tests
```bash
bash testing/test_lossless_toolbox.sh
```

**Expected Output:**
```
=== Lossless Operations Toolbox Property Tests ===
Feature: lossless-operations-toolbox

Testing Property 1: Stream Copy Preservation
[PASS] Stream Copy Preservation
...
Testing Property 12: Multi-File Compatibility Analysis
[PASS] Multi-File Compatibility Analysis

=== Test Summary ===
Total Tests: 12
Passed: 12
Failed: 0
All tests passed!
```

### Test Data Generation
The tests generate dummy media files in `/tmp/scripts_test_data` for universal tests and use property-based validation for lossless tests. The test data includes:

```bash
# Test files are generated in /tmp/scripts_test_data/
src.mp4          # H.264/AAC source file for transcoding tests
converted.mkv    # Different container, same codecs
compressed.mp4   # Different parameters
```
