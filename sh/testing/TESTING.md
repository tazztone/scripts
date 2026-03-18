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
bash testing/test_runner.sh
```

### Universal Script Testing
```bash
bash testing/test_runner.sh
```
The runner will:
1.  Generate dummy media (H.264/AAC) in `/tmp/scripts_test_data`.
2.  Execute scripts against this data.
3.  Analyze the output files using `ffprobe` to verify codecs, resolution, and metadata.

**Example Output (v2.6+):**
```text
=== Final Test Summary ===
Total Tests:  34
Tests Passed: 34
Tests Failed: 0

All tests passed!
```

### Lossless Operations Toolbox Testing
```bash
bash testing/test_lossless_toolbox.sh
```
This suite validates:
- **Remuxing & Format Preservation**: Safely swaps containers (`MOV` to `MP4`) without re-encoding.
- **Lossless Extraction**: Frame-accurate trimming.
- **Stream Editing**: Audio stream removal and metadata tagging/clearing.
- **Video Merging**: Robust `concat` demuxing handling.

**Test Coverage**: 6 standard end-to-end operations with 100% pass rate validation.

---

## 📊 Current Test Coverage

The test suite provides specialized coverage across the different toolboxes:

| Test File | What it covers |
|---|---|
| `test_lossless_toolbox.sh` | 6 end-to-end scenarios: remux, lossless trim, remove audio, metadata title, metadata clean, merge videos |
| `test_image_toolbox.sh` | 9 scenarios: Scale/BW/WebP, Square, 9:16, Flatten, sRGB, Montage, 16:9, Custom Resize, Text Annotation |
| `test_universal_extended.sh` | 3 complex scenarios: Speed control (2x), Hardware encoding (NVENC), and Multi-file processing |
| `test_ui_resilience.sh` | 6 resilience scenarios: Cancel flows, sub-dialog cancels, no-files error, resilience (cancel→retry→success) |
| `test_negative.sh` | 4 edge cases: Missing files, invalid presets, user cancellations, corrupt/empty file handling |
| `test_install.sh` | Full install/uninstall flow, symlink verification for multiple tools, mock HOME |
| `test_loop_detection.sh` | Detection of infinite Zenity menu loops |
| `test_wizard_contract.sh` | Wizard UI contract compliance |
| `test_wizard_robust.sh` | Wizard robustness |
| `test_cross_version.sh` | Cross-version compatibility |
| `test_zenity_smoke.sh` | Basic Zenity binary availability and mock functionality |
| `test_zenity4_repro.sh` | Reproduces Zenity 4.x "FALSE" return bug and verifies recursion guard |
| `test_lint.sh` | Static syntax analysis (ShellCheck-lite) |

### File Validation: Unified Approach

The testing framework relies on `lib_test.sh`'s `validate_media()` to perform rigorous end-to-end assertions on output files. It validates properties such as:
- Codec matching (`vcodec=hevc`)
- Exact framerate calculation (`fps=30`, handled robustly via `bc`)
- Sub-second duration tolerance (`duration=0.5s` with `±0.1s` accuracy)
- Stream identification (`has_audio`, `no_audio`, `subtitle_stream=1`)
- Accurate format headers via `magick` and `ffprobe` (`format=webp`)
- Exact file size and bitrate constraints (`file_size_gt`, `bitrate`)

All toolboxes (Universal, Image, and Lossless) utilize this unified `run_test` integration pipeline.

## 🛑 Previous Technical Debt (Resolved)

Older iterations of the test suite had coverage gaps (like float rounding bugs, missing audio stream verifications, fragile GUI inputs, and GNU-only `find -printf` commands). 
As of the latest refactoring, the suite is fully standardized:
- **Consistent Rounding**: `bc -l` and `awk` compute exact floating-point tolerances (e.g., 0.1s for trims).
- **Format Integrity**: File type sniffing uses robust FFprobe and ImageMagick detection, circumventing ambiguities in `file -b`.
- **Posix Portability**: macOS/BSD compatibilities are maintained across core detection logic.

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
run_fail_test "myscript.sh" "Error: Expected Message" "input.mp4"
unset ZENITY_MOCK_EXIT_CODE
```

### 2. Testing Resilience
Use `run_resilience_test` when you want to verify that a script survives a cancellation mid-flow but eventually produces a valid output.
- Set up a `/tmp/zenity_responses` queue with mixed "cancel" strings (empty) and valid selections.
- The test succeeds only if an output file is correctly generated despite the internal "continue" loops.

### 3. Testing Installation
`test_install.sh` uses a transient `MOCK_HOME` to verify that `install.sh` and `uninstall.sh` correctly manage symlinks in the user's Nautilus scripts directory without affecting the developer's actual environment. It uses `trap` to ensure cleanup even on failure.

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

- [ ] Run `bash testing/test_runner.sh` - all tests (including Lossless 6/6) should pass
- [ ] Run `bash testing/test_lint.sh` - no syntax errors
- [ ] Verify UI strings match between script and test mocks
- [ ] Check that all FFmpeg commands include `-nostdin`

## 📈 Expansion
To add a new test case:
1.  Add a new `run_test` call to a dedicated feature file (e.g., `testing/test_universal_extended.sh`).
2.  Define validation rules (e.g., `"vcodec=hevc,width=1280"`).
3.  If the script requires specific user input, use `cat <<EOF > /tmp/zenity_responses` or use the `ZENITY_LIST_RESPONSE`/`ZENITY_ENTRY_RESPONSE` environment variables.

---

## 🔧 Quick Reference: Common Testing Scenarios

#### Test a Specific Script with Custom Input
*Note: These variables will affect the entire test suite if exported. Use them for manual testing or scoped within a single test case.*

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

The Lossless Operations Toolbox suite operates with a fully end-to-end execution model, applying the established UI/Zenity mocks utilized in the rest of the testing suite.

### Test Scenarios
The test suite spans the most critical lossless operations:

1. **Remuxing**: Validates container swapping while retaining video/audio codecs.
2. **Lossless Trimming**: Ensures precise extraction (±0.1s tolerance) using stream copying.
3. **Stream Removal**: Confirms total elimination of audio streams without re-encoding video.
4. **Metadata Targeting**: Sets specific metadata objects (e.g., Title) and validates tag injection.
5. **Metadata Scrubbing**: Clears exhaustive EXIF/metadata properties without re-encoding.
6. **Video Merging**: Validates `concat` mechanics across consecutive files.

### Running Lossless Tests
```bash
bash testing/test_lossless_toolbox.sh
```

**Expected Output:**
```
=== Lossless Operations Toolbox Tests ===
Test 1: Remux (MOV -> MP4)
[INFO] Testing: 🔒 Lossless-Operations-Toolbox.sh with [/tmp/scripts_test_data/input.mp4]
[INFO] Detected: input_remuxed.mp4
...
Test 6: Merge Videos
[INFO] Testing: 🔒 Lossless-Operations-Toolbox.sh with [/tmp/scripts_test_data/input.mp4 /tmp/scripts_test_data/input2.mp4]
[INFO] Detected: merged.mp4

Lossless Toolbox Tests Finished!
```

### Test Data Generation
The tests generate standard dummy media files in `/tmp/scripts_test_data` via `generate_test_media()` in `lib_test.sh`. The test data includes:

```bash
# Generated by lib_test.sh
input.mp4          # Basic 1s H.264/AAC source file
input.jpg          # 1280x720 blue rectangle for image tests
alpha.png          # 100x100 transparent image

# Generated by test_lossless_toolbox.sh locally
input2.mp4         # Duplicated source for merge operations
```
