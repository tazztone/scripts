# 🧪 Testing Framework Guide

This repository uses a custom-built, headless testing framework designed to validate Nautilus scripts without requiring a physical display or user interaction. The framework includes both traditional script testing and specialized property-based testing for the Lossless Operations Toolbox.

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

### Universal Script Testing
```bash
bash testing/test_runner.sh
```
The runner will:
1.  Generate dummy media (H.264/AAC) in `/tmp/scripts_test_data`.
2.  Execute scripts against this data.
3.  Analyze the output files using `ffprobe` to verify codecs, resolution, and metadata.

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

## 🤖 Guide for AI Agents
When modifying these scripts, follow these strict rules to keep the test suite green:

1.  **Verify UI Strings**: If you add an emoji or change a label prefix (like adding a colon), you **MUST** update both the logic in the script and the `ZENITY_ARGS` inside `test_runner.sh`.
2.  **Use -nostdin**: Every new FFmpeg command added must include `-nostdin`.
3.  **Mock Context**: If you add a new Zenity dialog type (e.g., `--calendar`), you must update the mock script inside `test_runner.sh` to handle that flag, or it will return an empty string and potentially crash the test.
4.  **Column Accuracy**: The Universal Toolbox uses `--print-column=2`. Never change this to `1` or `3` without updating the `test_runner`'s strict verification check.

## 📈 Expansion
To add a new test case:
1.  Open `testing/test_runner.sh`.
2.  Add a new `run_test` call at the bottom.
3.  Define validation rules (e.g., `"vcodec=hevc,width=1280"`).
4.  If the script requires specific user input, `export` the necessary `ZENITY_` variables before calling `run_test`.

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
The lossless tests use the same test data as the universal tests but focus on validation rather than transcoding:

```bash
# Test files are created in testing/test_data/
src.mp4          # H.264/AAC source file
converted.mkv    # Different container, same codecs
compressed.mp4   # Different parameters
```
