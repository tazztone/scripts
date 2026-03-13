import safetensors.torch

# Path to your original LoRA file
lora_path = "m1r4.safetensors"

try:
    state_dict = safetensors.torch.load_file(lora_path)
    print("Found the following keys in your LoRA file:")
    # We print the first 20 keys to give you an idea of the structure
    all_keys = list(state_dict.keys())
    for key in all_keys[:20]:
        print(key)
    print(f"\n... and {len(all_keys) - 20} more keys.")
    # Save all keys to a file
    with open("lora_keys.txt", "w", encoding="utf-8") as f:
        for key in all_keys:
            f.write(f"{key}\n")
    print("All keys have been saved to lora_keys.txt.")
except FileNotFoundError:
    print(f"Error: The file was not found at '{lora_path}'")