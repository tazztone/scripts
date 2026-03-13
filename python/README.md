# Python Scripts

A collection of utility scripts for various Python-based tasks.

## Scripts

### [compress_png_to_webp_and_keep_comfyui_workflow.py](./compress_png_to_webp_and_keep_comfyui_workflow.py)
A high-performance, parallelized script to convert ComfyUI PNG images to WebP format while preserving essential generation metadata.

#### Features
- **Parallel Processing**: Uses all available CPU cores to process images simultaneously, significantly speeding up large batch conversions.
- **Metadata Preservation**: Specifically maps ComfyUI `workflow` and `prompt` data to EXIF tags (`ImageDescription` and `Make`). This ensures compatibility with nodes like WAS Node Suite and other tools that look for metadata in standard EXIF locations.
- **Smart Resume**: Automatically skips files that have already been converted. You can safely stop and restart the script at any time without re-processing completed images.
- **Space Saving**: Reduces file size by ~90% compared to standard PNGs.
- **Auto-Cleanup**: Option to delete original PNG files after successful conversion.
- **Quality Control**: Configurable WebP quality settings (default set to 90).

#### Configuration
You can modify the `TARGET_FOLDERS` list in the script to point to your Stability Matrix or ComfyUI output directories:
```python
TARGET_FOLDERS = [
    r"C:\_stability_matrix\Data\Images\Img2Img",
    r"C:\_stability_matrix\Data\Images\Text2Img",
    r"C:\_stability_matrix\Data\Images\Text2ImgGrids"
]
```

#### Requirements
- Python 3.x
- Pillow (`pip install Pillow`)
- 