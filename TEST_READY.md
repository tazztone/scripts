# TEST_READY: media_toolbox (Milestone 7)

This document certifies the testing readiness, feature mapping, execution semantics, and performance benchmarks for `media_toolbox`.

---

## 1. Executive Summary

- **Package**: `python/media_toolbox`
- **Current Test Count**: 439 tests (100% passing)
- **Full Suite Execution Time**: ~1.95s (Target: < 2.00s)
- **Headless Invariant**: ZERO GUI imports (`gi`, `Gtk`, `Adw`, `Nautilus`) in `core/`, `cli.py`, `installer.py`, `__main__.py`
- **Legacy Compatibility**: 97/97 legacy shell toolbox tests passing (100% backward-compatible)

---

## 2. Feature Coverage Matrix (31 Features across 5 Tiers)

Tiers:
- **T1: Feature (Unit)** — Nominal contracts, standard fixtures, valid operations.
- **T2: Boundary (BVA)** — Extremes, zeros, None, empty collections, clamping limits.
- **T3: Cross (Pairwise)** — Multi-module combinations (codecs, containers, filters, speeds).
- **T4: Workload (Scenarios)** — End-to-end real-world user workflows (`test_e2e.py`).
- **T5: Adversarial (Hardening)** — Corrupt data, crashed processes, fuzzing, signal stress (`test_adversarial.py`).

| # | Feature Description | Milestone | T1 (Feature) | T2 (Boundary) | T3 (Cross) | T4 (Workload) | T5 (Adversarial) | Primary Test Module |
|---|---------------------|:---------:|:------------:|:-------------:|:----------:|:-------------:|:----------------:|---------------------|
| 1 | Probing: JSON Deserialization | M1 | Standard MP4 / H.264+AAC | Empty JSON dict, missing keys | MediaInfo passed to Builder | Scenario 1, 6 | Truncated/corrupt JSON | `test_probe.py` |
| 2 | Probing: Duration Resolution | M1 | Format numeric duration | Format "N/A" -> Stream duration | Duration passed to Bitrate Math | Scenario 6 | Negative/NaN durations | `test_probe.py` |
| 3 | Probing: Fractional FPS | M1 | 24000/1001, 30000/1001 | 0/0 -> None, 0/1 -> 0.0 | FPS passed to Filtergraph | Scenario 4 | Divide-by-zero, non-numeric | `test_probe.py` |
| 4 | Probing: Missing Streams | M1 | Video+Audio, Audio-only | Silent video, Still image | Silent video suppresses audio filters | Scenario 3, 6 | No audio/video (data-only) | `test_probe.py` |
| 5 | Probing: Attached Cover Art | M1 | MP3 with ID3 cover art | Multiple pictures, missing tags | Audio route selected in UI/CLI | Scenario 3 | Video track tagged attached | `test_probe.py` |
| 6 | Math: 2-Pass Bitrate Calculation | M1 | 25MB/60s -> 3183 kbps | 0 kbps audio, 1s duration | Bitrate emitted in -b:v flag | Scenario 1 | 100k sec duration + 1MB | `test_bitrate.py` |
| 7 | Math: Container Overhead Margin | M1 | Default 3% & custom 5% | 0% margin, 99% margin | Target size limit compliance | Scenario 1 | Margin <0 or >=1 raises error | `test_bitrate.py` |
| 8 | Math: 64 kbps Bitrate Clamp | M1 | Calculated <64k clamps to 64k | 63k->64k, 64k->64k, 65k->65k | Builder emits -b:v 64k floor | Scenario 1 | Negative floor, extreme neg | `test_bitrate.py` |
| 9 | Filtergraph: Video Scaling | M2 | 1080p, 720p, 480p presets | Even dimension snapping (-2) | Scale combined with pad/speed | Scenario 2, 5 | Negative dims, 0x0 scale | `test_filtergraph.py` |
| 10 | Filtergraph: Aspect Ratio Padding | M2 | Letterbox / pillarbox pad | 0-pad (matching aspect ratio) | Scale + Pad combined chain | Scenario 1 | Injection characters in color | `test_filtergraph.py` |
| 11 | Filtergraph: Video Speed | M2 | 0.5x, 2.0x PTS adjustment | 0.25x, 3.0x, 4.0x, precision | Speed synchronized with audio | Scenario 2 | Speed=0, negative speed | `test_filtergraph.py` |
| 12 | Filtergraph: Audio `atempo` Chaining | M2 | Atempo within [0.5, 2.0] | Exact 0.5 & 2.0 boundaries | Chained atempo + loudnorm | Scenario 2 | Speed<=0, extreme chaining | `test_filtergraph.py` |
| 13 | Filtergraph: Video Cropping | M2 | 9:16, 1:1, 16:9 aspect crops | Same ratio (crop omitted) | Crop + Scale + FPS combined | Scenario 4 | Invalid crop strings, 0:0 | `test_filtergraph.py` |
| 14 | Filtergraph: Volume Normalization | M2 | Loudnorm -16 LUFS, +3dB boost | 0 dB boost, -6dB attenuation | Loudnorm + atempo chained | Scenario 3 | Volume +100dB, loud+mute | `test_filtergraph.py` |
| 15 | Filtergraph: Audio Mute / Extract | M2 | Mute (-an), Extract (-vn) | Mute already silent, extract audio | Extract + audio codec preset | Scenario 3 | Mute + Extract simultaneous | `test_filtergraph.py` |
| 16 | Presets: 10 Codec Presets | M2 | Flags for 10 presets | Codec/container compatibility | Preset + CRF vs 2-pass matrix | Scenario 1, 3, 4, 5 | Unknown codec name raises | `test_presets.py` |
| 17 | Builder: 2-Pass vs CRF Argument Generation | M2 | CRF (1 cmd) vs 2-pass (2 cmds) | /dev/null vs NUL, passlog | Filtergraph identical pass 1 & 2 | Scenario 1, 4 | Concurrent passlog collision | `test_builder.py` |
| 18 | Runner: Key-Value Progress Streaming | M3 | frame=, fps=, total_size= | Empty lines, unknown keys | Key-value updates UI progress | Scenario 1, 2 | Non-numeric tokens, corrupt | `test_runner.py` |
| 19 | Runner: Microsecond Time Conversion | M3 | out_time_us -> seconds | out_time_us=0, sub-ms | Time fed to monotonic tracker | Scenario 1, 2 | out_time_us=N/A, negative | `test_runner.py` |
| 20 | Runner: Percentage & ETA Calculation | M3 | Standard percentage & ETA | Unknown duration, speed=0 | Multi-pass scaled progress | Scenario 1 | Clamped to 100%, ETA>=0 | `test_runner.py` |
| 21 | Runner: Process Group Cancellation | M3 | SIGTERM terminates group | Cancel before launch, dead pid | Multi-pass abort between passes | Scenario 1, 2 | SIGKILL escalation (<100ms) | `test_runner.py` |
| 22 | CLI: Formatted Metadata Output | M4 | Human-readable & JSON info | Missing fields, still images | CLI options map to EncodeOptions | Scenario 6 | Non-existent file, bad binary | `test_cli.py` |
| 23 | CLI: Headless AST Invariant | M4 | AST walk across core/ & cli | Dynamic discovery of core/*.py | sys.modules fresh process check | Scenario 6 | Dynamic __import__ evasion | `test_headless_ast.py` |
| 24 | UI: Dynamic Libadwaita Interface | M5 | CRF vs Target Size revealers | Rate control hidden for GIF/ProRes | Widget values -> EncodeOptions | Scenario 1, 4 | Rapid toggles, display=None | `test_ui.py` |
| 25 | UI: Non-Blocking Transcode Execution | M5 | Daemon thread worker | Controls disabled during work | GLib.idle_add error marshalled | Scenario 1, 2 | Thread leak verification | `test_ui.py` |
| 26 | UI: Live Progress & Speed/ETA | M5 | Progress fraction, ETA format | Indeterminate mode, ETA unknown | Multi-pass pass 1/2 indicators | Scenario 1 | Speed drops to 0x, clock jitter | `test_ui.py` |
| 27 | Nautilus: User Launcher Script | M6 | Iterate $NAUTILUS_SELECTED | Zero args exit 0, spaces in path | Script launches UI window | Scenario 7 | Shell metachars, read-only | `test_nautilus.py` |
| 28 | Nautilus: Python-Nautilus Extension | M6 | MenuProvider get_file_items() | Non-media filtered out | Detached process dispatch | Scenario 7 | Missing MIME, corrupt items | `test_nautilus.py` |
| 29 | Nautilus: Dual Installer CLI | M6 | Install 0o755/0o644 & uninstall | Idempotent reinstall, status | CLI flags --install-nautilus | Scenario 7 | Read-only dest, --dry-run | `test_nautilus.py` |
| 30 | E2E: Full Suite Automated Pass | M7 | Full suite 100% pass | Forward & reverse test order | All modules cross-tested | All 7 Scenarios | Zero regression guarantee | `test_e2e.py` |
| 31 | E2E: Adversarial Hardening | M7 | White-box stress suite | Min/max bounds, empty streams | Concurrency & signal stress | Resilient batch CLI | Malicious payloads, SIGKILL | `test_adversarial.py` |

---

## 3. Test Runner Invocation Semantics

### 3.1 Primary Test Invocations

1. **Standard Fast Test Suite (Recommended for Development & CI)**:
   ```bash
   .venv/bin/pytest python/media_toolbox/tests/ -v
   ```
   - Target runtime: < 2.00s
   - Execution semantics: Pure in-memory synthetic fixtures, headless, zero external dependencies.

2. **Repository-Wide Python Test Suite**:
   ```bash
   .venv/bin/pytest python/ -v
   ```
   - Target runtime: < 4.00s
   - Execution semantics: Exercises `media_toolbox`, `bitwarden`, `google_drive_remove_duplicates`, `immich-api`, `put_files_into_folder_by_extension`, `remove_jpg_if_raw_exists`, and `signal-stickers`.

3. **Dedicated Tier 4 Real-World Workload Scenarios**:
   ```bash
   .venv/bin/pytest python/media_toolbox/tests/test_e2e.py -v
   ```
   - Validates all 7 user workflows (Discord 25MB, High-Speed Preview, Audio Extract, Vertical Crop, GIF, CLI batch, Nautilus context).

4. **Dedicated Tier 5 Adversarial Hardening Suite**:
   ```bash
   .venv/bin/pytest python/media_toolbox/tests/test_adversarial.py -v
   ```
   - Stress-tests malformed payloads, abrupt terminations, fuzzed inputs, and security invariants.

5. **Static Headless AST Invariant Check**:
   ```bash
   .venv/bin/pytest python/media_toolbox/tests/test_headless_ast.py -v
   ```
   - Asserts zero GUI imports (`gi`, `Gtk`, `Adw`, `Nautilus`) across `core/`, `cli.py`, `installer.py`, `__main__.py`.

6. **Legacy Shell Toolbox Regression Suites**:
   ```bash
   cd sh/TOOLBOXES
   bash testing/test_cross_version.sh
   bash testing/test_runner.sh
   ```
   - Verifies 100% backward compatibility with Zenity 3/4 legacy scripts.

---

## 4. Acceptance Criteria & Pass/Fail Semantics

1. **Test Pass Rate**: Strictly 100% (exit code 0, 0 failures, 0 skipped/xfail without justification).
2. **Execution Speed**: Full `media_toolbox/tests` suite must complete in < 2.0s.
3. **Isolation Invariant**: Tests must pass in any arbitrary order, including reverse alphabetical order:
   ```bash
   .venv/bin/pytest $(find python/media_toolbox/tests/ -name "test_*.py" | sort -r)
   ```
4. **Desktop Integration Invariants**:
   - `desktop-file-validate python/media_toolbox/nautilus/io.github.tazztone.MediaToolbox.desktop` exits 0.
   - `bash -n python/media_toolbox/nautilus/launcher.sh` exits 0.
