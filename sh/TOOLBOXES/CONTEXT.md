# Domain Glossary (scripts-sh)

This document defines the domain language of the Nautilus Productivity Toolboxes ecosystem.

## Core Concepts

### Toolbox
An entrypoint Nautilus shell script integrated into the file manager context menu. It wraps media operations in a visual interface.
- **Universal-Toolbox**: Transcodes and applies visual filters.
- **Lossless-Toolbox**: Performs stream copy operations (zero re-encoding).
- **ImageMagick-Toolbox**: Performs batch image resizing, formatting, and effects.

### Media Profile
The parsed track layout, metadata, codecs, and dimensions of a media file.
- **Audio Track**: Sound stream (AAC, MP3, PCM).
- **Video Track**: Visual stream (H.264, VP9, ProRes).
- **Subtitle Track**: Embedded or external timed text (.srt).

### Recipe
A set of configuration parameters describing the stack of operations (e.g., speed, rotation, crop) to apply to a file.

### Wizard
The Zenity-based user interface consisting of the **Checklist** (Intent selection) and the **Dashboard** (Forms configuration).
