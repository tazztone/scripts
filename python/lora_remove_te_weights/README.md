i made this script to make my LoRA compatible with nunchaku LoRA loader, as it couldn't handle the text encoder weights from kohya_ss with "train_t5xxl: true".

# LoRA Remove Text Encoder Weights

This script filters a LoRA `.safetensors` file to keep only the U-Net weights, removing any text encoder weights. Useful for sharing or optimizing LoRA files for inference.

## Files
- `script.py`: Main script to filter LoRA weights.
- `WINDOWS-install.bat`: Sets up a Python virtual environment and installs dependencies (Windows).
- `WINDOWS-start.bat`: Activates the environment and runs the script (Windows).
- `inspect-lora.py`: (Optional) Script to inspect LoRA keys.
- `lora_keys.txt`: (Optional) Example output of LoRA keys.

## Quick Start (Windows)
0. open cmd and `git clone https://github.com/tazztone/lora-remove-te-weights`
1. Place your LoRA file(s) (e.g., `m1r4.safetensors`) in the `PUT-SAFETENSORS-HERE` folder.
2. Run `WINDOWS-install.bat` to set up the environment and install dependencies.
3. Run `WINDOWS-start.bat` to process your files.

## Manual Usage (Other OS / Advanced)
1. Place your LoRA file (e.g., `m1r4.safetensors`) in this directory or the correct folder.
2. Edit `script.py` to set the correct input/output filenames or folder if needed.
3. (Recommended) Use a Python virtual environment.
4. Install dependencies:
   ```pwsh
   pip install torch safetensors numpy
   ```
5. Run the script:
   ```pwsh
   python script.py
   ```

## Output
- A new file (e.g., `m1r4_unet_only.safetensors`) containing only U-Net weights.

## Notes
- Do **not** commit large model files (`.safetensors`) to GitHub.
- Add your virtual environment and model files to `.gitignore` (see below).

## License
MIT
