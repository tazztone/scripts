# E2E Test Infra: media_toolbox

## Test Philosophy
- Opaque-box, requirement-driven derived from `ORIGINAL_REQUEST.md` (R1-R5).
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinations + Real-World Workload Testing.
- Fast execution (~90ms guideline): synthetic `ffprobe` JSON fixtures and mock `-progress pipe:1` streams avoid heavy subprocess overhead.

## Feature Inventory & Test Coverage Matrix
| # | Feature | Requirement | Tier 1 (Feature) | Tier 2 (Boundary) | Tier 3 (Cross) |
|---|---------|-------------|:----------------:|:-----------------:|:--------------:|
| 1 | Media Probing & Stream Deserialization | R1 | 5 cases | 5 cases | ✓ |
| 2 | Duration & FPS Edge Cases | R1 | 5 cases | 5 cases | ✓ |
| 3 | Bitrate Calculator & Mux Margin | R1 | 5 cases | 5 cases | ✓ |
| 4 | Composable Video Filtergraph | R2 | 5 cases | 5 cases | ✓ |
| 5 | Composable Audio Filtergraph & `atempo` Chaining | R2 | 5 cases | 5 cases | ✓ |
| 6 | Codec Presets & 2-Pass/CRF CLI Builder | R2 | 5 cases | 5 cases | ✓ |
| 7 | Subprocess Progress Streaming & ETA | R3 | 5 cases | 5 cases | ✓ |
| 8 | Subprocess Cancellation & Process Groups | R3 | 5 cases | 5 cases | ✓ |
| 9 | Headless Core AST & CLI Formatter | R1, Functional | 5 cases | 5 cases | ✓ |
| 10 | Libadwaita / GTK4 UI Forms & Concurrency | R4 | 5 cases | 5 cases | ✓ |
| 11 | Dual Nautilus Launcher & Extension | R5 | 5 cases | 5 cases | ✓ |

## Test Architecture
- Test runner: `.venv/bin/pytest python/media_toolbox/tests/` (and root `.venv/bin/pytest python/`)
- Pass/fail semantics: 100% exit code 0, 0 failures, 0 regressions against existing 115 tests
- Test directory: `python/media_toolbox/tests/`
- AST headless import verification in `tests/test_headless_ast.py`
- Synthetic fixtures in `tests/conftest.py`

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Discord Video Compression (25MB target, 2-pass H.264, audio downmix to stereo, faststart) | F1, F3, F4, F6, F7 | High |
| 2 | High-Speed Preview (3.0x speed, chained atempo=2.0,1.5, setpts=0.3333*PTS, 720p scale) | F1, F4, F5, F6, F7 | Medium |
| 3 | Audio Extraction & Normalization (Extract to MP3, 192k, loudnorm normalization, mute video) | F1, F5, F6 | Medium |
| 4 | Vertical Social Media Crop (9:16 center crop, 60fps, H.265 CRF 28) | F1, F4, F6 | Medium |
| 5 | High-Quality GIF Conversion (Palettegen + paletteuse filter_complex, 15fps, 480p width) | F1, F4, F6 | Medium |
| 6 | Headless Batch CLI Pipeline (`media_toolbox.cli` inspection on audio-less, corrupt, and multi-stream files) | F1, F2, F9 | Medium |
| 7 | Nautilus Context Menu Dispatch (Launcher script & extension MIME type detection with space-separated file paths) | F10, F11 | Medium |

## Coverage Thresholds
- Tier 1: ≥5 per feature (≥55 test cases)
- Tier 2: ≥5 boundary/corner cases per feature (≥55 test cases)
- Tier 3: Pairwise combinations across codecs, speeds, and container modes (≥11 test cases)
- Tier 4: ≥7 realistic application scenarios
- Tier 5: Adversarial edge cases (malformed JSON, broken pipes, SIGKILL stress tests)
