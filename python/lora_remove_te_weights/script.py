import safetensors.torch
import os

# --- Configuration ---
# Folder containing the LoRA files to process
input_folder = "PUT-SAFETENSORS-HERE"

# Prefix for the main model weights you want to keep
UNET_PREFIX = "lora_unet_"

# --- Script ---
input_folder_path = os.path.join(os.path.dirname(__file__), input_folder)

if not os.path.exists(input_folder_path):
    print(f"Error: Input folder not found at '{input_folder_path}'")
else:
    files = [f for f in os.listdir(input_folder_path) if f.endswith('.safetensors')]
    if not files:
        print(f"No .safetensors files found in '{input_folder_path}'")
    for filename in files:
        input_lora_path = os.path.join(input_folder_path, filename)
        output_lora_path = os.path.join(input_folder_path, filename.replace('.safetensors', '_unet_only.safetensors'))
        print(f"\nProcessing: {filename}")
        state_dict = safetensors.torch.load_file(input_lora_path)
        filtered_state_dict = {}
        print(f"Filtering to keep only keys starting with '{UNET_PREFIX}'...")
        for key, value in state_dict.items():
            if key.startswith(UNET_PREFIX):
                filtered_state_dict[key] = value
        if not filtered_state_dict:
            print("  Error: No U-Net keys were found with that prefix.")
            print("  Please double-check the UNET_PREFIX variable in the script.")
        else:
            safetensors.torch.save_file(filtered_state_dict, output_lora_path)
            print(f"  Success! New LoRA saved to: {output_lora_path}")
            print(f"  {len(filtered_state_dict)} U-Net keys were kept out of {len(state_dict)} total keys.")