# Project: media_toolbox

## Architecture
Modern Python media toolbox package in `python/media_toolbox` replacing legacy Bash/Zenity scripts.
Architected in three isolated layers:
1. **Core Headless Engine (`core/`)**: Zero GUI dependencies (`gi`, `Gtk`, `Adw`, `Nautilus`). Frozen dataclass models, mockable `ffprobe -print_format json` probing, deterministic filtergraph and CLI builder, container muxing math engine, and async/threaded subprocess runner with `-progress pipe:1 -nostats` streaming.
2. **Desktop UI Layer (`ui/`)**: Libadwaita / GTK4 desktop interface (`Gtk` 4.0, `Adw` 1) using dynamic forms with revealers (revealing target size vs CRF, custom resolutions), non-blocking progress tracking, speed/ETA display, and graceful cancellation.
3. **Desktop Integrations (`nautilus/`)**: Dual Nautilus file manager integration consisting of a zero-privilege user script in `~/.local/share/nautilus/scripts/Media-Toolbox` and a native `python-nautilus` extension in `~/.local/share/nautilus-python/extensions/` with MIME-type contextual menus.

## Code Layout
```
python/media_toolbox/
├── __init__.py
├── __main__.py               # CLI/UI package execution router
├── cli.py                    # Standalone CLI entrypoint for inspection & batch commands
├── core/
│   ├── __init__.py
│   ├── models.py             # Frozen dataclasses (VideoStream, AudioStream, FormatInfo, MediaInfo, ProgressEvent)
│   ├── probe.py              # ffprobe JSON deserializer, N/A duration fallback, fractional fps
│   ├── bitrate.py            # 2-pass bitrate math, 3-5% container mux margin, 64 kbps clamp
│   ├── filtergraph.py        # Video/audio filter chains, crop/scale/pad, atempo splitting (>2.0x, <0.5x)
│   ├── presets.py            # Codec presets (H.264, H.265, AV1, VP9, GIF, ProRes, MP3, AAC, Opus, FLAC)
│   ├── builder.py            # Deterministic FFmpeg CLI argument builder (CRF & 2-pass)
│   └── runner.py             # Process-isolated runner, -progress pipe:1 parser, SIGTERM/SIGKILL cancellation
├── ui/
│   ├── __init__.py
│   ├── app.py                # Adw.Application, display detection, lifecycle
│   ├── window.py             # Main Libadwaita application window with dynamic preferences groups
│   └── widgets.py            # Custom reactive widgets (progress bar, speed/ETA labels, revealers)
├── nautilus/
│   ├── __init__.py
│   ├── launcher.sh           # User script for ~/.local/share/nautilus/scripts/Media-Toolbox
│   ├── extension.py          # python-nautilus MenuProvider for ~/.local/share/nautilus-python/extensions/
│   └── installer.py          # CLI installer/uninstaller for dual Nautilus integration
└── tests/
    ├── __init__.py
    ├── conftest.py           # Synthetic ffprobe JSON fixtures, mock progress streams, sys.path
    ├── test_headless_ast.py  # Static AST import verification (asserts ZERO GUI imports in core/)
    ├── test_models.py        # Immutability and defaults tests
    ├── test_probe.py         # Valid videos, silent media, audio-only, images, N/A durations, 0/0 fps
    ├── test_bitrate.py       # Bitrate calculations, container overhead margins, 64kbps floor
    ├── test_filtergraph.py   # Filter chains, atempo splitting, crop/scale/pad
    ├── test_presets.py       # Codec preset CLI flag generations
    ├── test_builder.py       # Complete FFmpeg command line assembly (CRF and 2-pass)
    ├── test_runner.py        # Subprocess runner, progress parsing, ETA, cancellation
    ├── test_cli.py           # CLI invocation and formatted metadata output
    ├── test_ui.py            # UI logic, state transitions, headless mocking
    └── test_nautilus.py      # Extension MIME matching, launcher script generation, installer tests
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Probing: JSON Deserialization | `ffprobe -print_format json` deserialized into typed dataclasses | M1 | survey (spec_miner) |
| 2 | Probing: Duration Resolution | Fallback from format to stream duration, handling `"N/A"` as `None` | M1 | survey (spec_miner) |
| 3 | Probing: Fractional FPS | Evaluating fractional `r_frame_rate` (e.g. `24000/1001`), handling `"0/0"` safely | M1 | survey (spec_miner) |
| 4 | Probing: Missing Streams | Clean handling of silent videos, audio-only files, and still images | M1 | survey (spec_miner) |
| 5 | Probing: Attached Cover Art | Distinguishing MP3 album art from video tracks (`attached_pic == 1`) | M1 | survey (spec_miner) |
| 6 | Math: 2-Pass Bitrate Calculation | Total bitrate math from target MB and duration | M1 | survey (spec_miner) |
| 7 | Math: Container Overhead Margin | Reserving 3-5% safety margin for muxing overhead | M1 | survey (spec_miner) |
| 8 | Math: 64 kbps Bitrate Clamp | Enforcing minimum 64 kbps video bitrate floor | M1 | survey (spec_miner) |
| 9 | Filtergraph: Video Scaling | Deterministic `scale=w:h` with even dimension snapping (`scale=w:-2`) | M2 | survey (explorer_1) |
| 10 | Filtergraph: Aspect Ratio Padding | Pillarbox/letterbox padding (`pad=w:h:x:y:color`) | M2 | survey (spec_miner) |
| 11 | Filtergraph: Video Speed | Adjusting PTS via `setpts=(1/speed)*PTS` | M2 | survey (spec_miner) |
| 12 | Filtergraph: Audio `atempo` Chaining | Splitting multipliers >2.0x and <0.5x into valid `atempo` filter chains | M2 | survey (spec_miner) |
| 13 | Filtergraph: Video Cropping | Aspect ratio center cropping (9:16, 16:9, 1:1, 4:3, 21:9) | M2 | survey (explorer_1) |
| 14 | Filtergraph: Volume Normalization | Audio loudness normalization (`loudnorm`) and volume boost | M2 | survey (explorer_1) |
| 15 | Filtergraph: Audio Mute / Extract | Muting audio (`-an`) or extracting audio (`-vn`) | M2 | survey (spec_miner) |
| 16 | Presets: 10 Codec Presets | Exact CLI flags for H.264, H.265, AV1, VP9, GIF, ProRes, MP3, AAC, Opus, FLAC | M2 | survey (spec_miner) |
| 17 | Builder: 2-Pass vs CRF Argument Generation | Assembly of Pass 1 null output and Pass 2 final output or single-pass CRF | M2 | survey (spec_miner) |
| 18 | Runner: Key-Value Progress Streaming | Parsing line-by-line `-progress pipe:1 -nostats` key=value pairs | M3 | survey (spec_miner) |
| 19 | Runner: Microsecond Time Conversion | Converting `out_time_us` / `out_time_ms` microseconds to seconds | M3 | survey (explorer_3) |
| 20 | Runner: Percentage & ETA Calculation | Calculating percentage and ETA from elapsed time and total duration | M3 | survey (spec_miner) |
| 21 | Runner: Process Group Cancellation | Clean `SIGTERM` followed by `SIGKILL` on process group to avoid zombies | M3 | survey (spec_miner) |
| 22 | CLI: Formatted Metadata Output | Terminal output of probed media details without GUI dependencies | M4 | survey (explorer_3) |
| 23 | CLI: Headless AST Invariant | Test ensuring zero `gi`/GUI imports across `core/` modules | M4 | survey (explorer_3) |
| 24 | UI: Dynamic Libadwaita Interface | Adw window with dynamic revealers for mode (CRF vs Target Size) and resolution | M5 | survey (explorer_3) |
| 25 | UI: Non-Blocking Transcode Execution | Background worker thread executing runner with `GLib.idle_add` UI updates | M5 | survey (explorer_3) |
| 26 | UI: Live Progress & Speed/ETA | Real-time progress bar, speed factor, and time remaining indicators | M5 | survey (explorer_3) |
| 27 | Nautilus: User Launcher Script | User-space script in `~/.local/share/nautilus/scripts/Media-Toolbox` | M6 | survey (explorer_3) |
| 28 | Nautilus: Python-Nautilus Extension | Native extension in `~/.local/share/nautilus-python/extensions/` with MIME menus | M6 | survey (explorer_3) |
| 29 | Nautilus: Dual Installer CLI | Automated installer command (`--install-nautilus`, `--uninstall-nautilus`) | M6 | survey (explorer_3) |
| 30 | E2E: Full Suite Automated Pass | 100% test pass on `.venv/bin/pytest python/` with mock fixtures | M7 | survey (explorer_3) |
| 31 | E2E: Adversarial Hardening | Tier 5 adversarial tests covering malformed inputs and concurrency | M7 | survey (spec_miner) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Media Inspection & Math Engine | `core/models.py`, `core/probe.py`, `core/bitrate.py`, tests | none | DONE |
| M2 | Filtergraph, Presets & CLI Builder | `core/filtergraph.py`, `core/presets.py`, `core/builder.py`, tests | M1 | DONE |
| M3 | Non-Blocking Progress Runner | `core/runner.py`, tests | M1 | DONE |
| M4 | CLI Entrypoint & Headless AST Check | `cli.py`, `__main__.py`, `tests/test_headless_ast.py`, tests | M1, M2, M3 | DONE |
| M5 | Dynamic Libadwaita / GTK4 UI | `ui/app.py`, `ui/window.py`, `ui/widgets.py`, tests | M1, M2, M3 | DONE |
| M6 | Dual Nautilus Integration & Installer | `nautilus/launcher.sh`, `nautilus/extension.py`, `nautilus/installer.py`, tests | M4, M5 | DONE |
| M7 | E2E Test Suite 100% Pass & Hardening | Full suite pass (`.venv/bin/pytest python/`), Tier 1-5 validation | M1-M6 | DONE |

## Interface Contracts

### `core/models.py`
- `VideoStream`: `index: int`, `codec_name: str`, `width: int`, `height: int`, `fps: Optional[float]`, `bit_rate: Optional[int]`, `duration: Optional[float]`, `rotation: int`, `is_attached_pic: bool`
- `AudioStream`: `index: int`, `codec_name: str`, `channels: int`, `sample_rate: int`, `channel_layout: Optional[str]`, `bit_rate: Optional[int]`, `duration: Optional[float]`
- `FormatInfo`: `filename: str`, `format_name: str`, `duration: Optional[float]`, `size_bytes: Optional[int]`, `bit_rate: Optional[int]`
- `MediaInfo`: `format: FormatInfo`, `video_streams: tuple[VideoStream, ...]`, `audio_streams: tuple[AudioStream, ...]`, properties: `primary_video`, `primary_audio`, `has_video`, `has_audio`, `duration`
- `ProgressEvent`: `frame: int`, `fps: float`, `out_time_seconds: float`, `total_size_bytes: int`, `speed: Optional[float]`, `percentage: float`, `eta_seconds: Optional[float]`, `is_completed: bool`

### `core/probe.py`
- `probe_media(file_path: str | Path, ffprobe_bin: str = "ffprobe") -> MediaInfo`
- `parse_probe_json(data: dict[str, Any]) -> MediaInfo`

### `core/bitrate.py`
- `calculate_target_video_bitrate(target_size_mb: float, duration_seconds: float, audio_bitrate_kbps: int = 128, mux_overhead_margin: float = 0.03, min_video_bitrate_kbps: int = 64) -> int`

### `core/filtergraph.py`
- `build_video_filter(scale: Optional[tuple[int, int]], crop: Optional[str], pad: Optional[str], speed: Optional[float], fps: Optional[int]) -> list[str]`
- `build_atempo_chain(speed: float) -> list[str]`
- `build_audio_filter(speed: Optional[float], normalize_loudness: bool, volume_boost_db: Optional[float]) -> list[str]`

### `core/builder.py`
- `build_ffmpeg_commands(input_path: str, output_path: str, options: EncodeOptions) -> list[list[str]]`
  (Returns 1 command for CRF/single-pass, or 2 commands for 2-pass bitrate mode).

### `core/runner.py`
- `run_command(cmd: list[str], total_duration: float, progress_callback: Optional[Callable[[ProgressEvent], None]], cancel_event: Optional[threading.Event]) -> None`
