import os
import concurrent.futures
from PIL import Image
import time

# CONFIGURATION
TARGET_FOLDERS = [
    r"C:\_stability_matrix\Data\Images\Img2Img",
    r"C:\_stability_matrix\Data\Images\Text2Img",
    r"C:\_stability_matrix\Data\Images\Text2ImgGrids"
]
QUALITY = 90
DELETE_ORIGINALS = True
MAX_WORKERS = None  # None = use all CPU cores. Set to 4 or 8 if it lags your PC.

def convert_single_image(full_path):
    """
    Worker function to process a single image.
    Returns a status string for logging.
    """
    try:
        webp_path = os.path.splitext(full_path)[0] + ".webp"
        
        # Skip if already exists
        if os.path.exists(webp_path):
            return None

        with Image.open(full_path) as img:
            # Use getexif() to create a new Exif container
            exif_data = img.getexif()
            found_data = False

            # 1. Map 'workflow' -> ImageDescription (0x010e)
            if 'workflow' in img.info:
                # WAS Node format: "Workflow:" + json_string
                exif_data[0x010e] = "Workflow:" + img.info['workflow']
                found_data = True

            # 2. Map 'prompt' -> Make (0x010f)
            if 'prompt' in img.info:
                # WAS Node format: "Prompt:" + json_string
                exif_data[0x010f] = "Prompt:" + img.info['prompt']
                found_data = True
            
            # Save
            if found_data:
                img.save(webp_path, "WEBP", quality=QUALITY, exif=exif_data.tobytes())
                status = f"Compressed [WAS Style]: {os.path.basename(full_path)}"
            else:
                img.save(webp_path, "WEBP", quality=QUALITY)
                status = f"Compressed [No Meta]: {os.path.basename(full_path)}"

        if DELETE_ORIGINALS:
            os.remove(full_path)
            
        return status

    except Exception as e:
        return f"Failed: {os.path.basename(full_path)} - {e}"

def main():
    print("Scanning folders...")
    png_files = []
    
    # 1. Collect all files first
    for folder in TARGET_FOLDERS:
        if not os.path.exists(folder):
            print(f"Skipping (not found): {folder}")
            continue
        
        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(".png"):
                    png_files.append(os.path.join(root, file))

    total_files = len(png_files)
    print(f"Found {total_files} PNG images. Starting parallel compression...")

    # 2. Process in parallel using ProcessPoolExecutor
    start_time = time.time()
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Map the list of files to the worker function
        results = executor.map(convert_single_image, png_files)
        
        # Process results as they complete
        processed_count = 0
        for result in results:
            if result: # If not None (skipped)
                processed_count += 1
                if processed_count % 10 == 0:
                    print(f"Progress: {processed_count}/{total_files}...", end='\r')
                # Uncomment the next line if you want to see every single filename (slower)
                # print(result)

    duration = time.time() - start_time
    print(f"\nDone! Processed {processed_count} images in {duration:.2f} seconds.")

if __name__ == "__main__":
    # Windows requires this guard for multiprocessing
    main()
    input("Press Enter to exit.")