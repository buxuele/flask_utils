import os
import io
import base64
import re
import uuid
from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Any
from flask import current_app
from werkzeug.utils import secure_filename

from app.common.utils import natural_sort_key, create_directory_if_not_exists, allowed_file as common_allowed_file

# --- Text Adding Utilities (from original app.py and image_utils.py) ---
def _get_font(font_name_or_path: str, size: int):
    """Helper to load a font, falling back to default."""
    try:
        return ImageFont.truetype(font_name_or_path, size)
    except IOError:
        return None

def add_text_to_image_pil(pil_image: Image.Image, text: str, position: Tuple[int, int], text_size: int,
                      font_color="black", bg_color=(255, 255, 255, 230), outline_color=(0,0,0,255), padding=10):
    """
    Adds text with a background to a PIL Image object.
    Uses common Chinese fonts if available, otherwise default.
    """
    draw = ImageDraw.Draw(pil_image)

    # Attempt to load a suitable font
    font = None
    # Common font paths/names (adjust as needed or make configurable)
    # These paths are OS-dependent and might not exist.
    # Consider bundling a font or using a more reliable font lookup.
    font_preferences = [
        "msyh.ttc", "simhei.ttf", "simsun.ttc", "arial.ttf", "DejaVuSans.ttf"
    ]
    if os.name == 'nt': # Windows specific common paths
        font_preferences.extend([
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/arial.ttf"
        ])

    for font_choice in font_preferences:
        font = _get_font(font_choice, text_size)
        if font:
            break
    if not font:
        font = ImageFont.load_default() # Fallback to Pillow's default font

    # Get text bounding box
    # For Pillow >= 10.0.0 textbbox takes four arguments, for older versions 2.
    # Using textbbox for better accuracy if available, else textsize.
    try:
        bbox = draw.textbbox(position, text, font=font) # xy, text, font, anchor, spacing, align, direction, features, language
    except AttributeError: # Older Pillow or if textbbox not found for some reason
         # Fallback for older Pillow versions if textbbox is not available or has different signature
        try:
            # Pillow < 10.0.0 textlength, textbbox has different signature or may not exist for all Draw instances
            text_width, text_height = draw.textsize(text, font=font)
            bbox = (position[0], position[1], position[0] + text_width, position[1] + text_height)
        except AttributeError: # even older, or problem with textsize
            # A very rough estimate if textsize also fails
            text_width = len(text) * text_size * 0.6
            text_height = text_size
            bbox = (position[0], position[1], position[0] + text_width, position[1] + text_height)


    # Define background rectangle with padding
    bg_bbox = (
        bbox[0] - padding,
        bbox[1] - padding,
        bbox[2] + padding,
        bbox[3] + padding
    )

    # Draw background and outline
    if bg_color:
        draw.rectangle(bg_bbox, fill=bg_color)
    if outline_color: # Assuming outline for the background box
        draw.rectangle(bg_bbox, outline=outline_color)

    # Draw text
    draw.text(position, text, fill=font_color, font=font)
    return pil_image


# --- Image Merging Utilities (from original app.py and utils/image_processor.py) ---

def _resize_images_to_common_dimension(images: List[Image.Image], dimension: str = 'height') -> List[Image.Image]:
    """
    Resizes a list of images to a common dimension (height or width), maintaining aspect ratio.
    """
    if not images:
        return []

    if dimension == 'height':
        target_dim = max(img.size[1] for img in images)
        resized_images = []
        for img in images:
            if img.size[1] == target_dim:
                resized_images.append(img)
                continue
            ratio = target_dim / img.size[1]
            new_width = int(img.size[0] * ratio)
            resized_images.append(img.resize((new_width, target_dim), Image.Resampling.LANCZOS))
    else: # dimension == 'width'
        target_dim = max(img.size[0] for img in images)
        resized_images = []
        for img in images:
            if img.size[0] == target_dim:
                resized_images.append(img)
                continue
            ratio = target_dim / img.size[0]
            new_height = int(img.size[1] * ratio)
            resized_images.append(img.resize((target_dim, new_height), Image.Resampling.LANCZOS))
    return resized_images

def merge_two_images_side_by_side(img1: Image.Image, img2: Image.Image, add_labels: bool = False, label_text_size_ratio: float = 0.05) -> Image.Image:
    """Merges two images horizontally, resizing them to the same height."""
    img1 = img1.convert('RGBA')
    img2 = img2.convert('RGBA')

    resized_images = _resize_images_to_common_dimension([img1, img2], dimension='height')
    r_img1, r_img2 = resized_images[0], resized_images[1]

    total_width = r_img1.width + r_img2.width
    max_height = r_img1.height # or r_img2.height, they are same

    merged_image = Image.new('RGBA', (total_width, max_height), (0, 0, 0, 0)) # Transparent background
    merged_image.paste(r_img1, (0, 0))
    merged_image.paste(r_img2, (r_img1.width, 0))

    if add_labels:
        text_size = int(max_height * label_text_size_ratio)
        add_text_to_image_pil(merged_image, "修改前", (20, 20), text_size)
        add_text_to_image_pil(merged_image, "修改后", (r_img1.width + 20, 20), text_size)

    return merged_image.convert('RGB') # Convert to RGB for saving as JPEG

def _merge_multiple_images_grid(image_files: List[Any], add_filenames: bool = False) -> Image.Image:
    """
    Merges multiple images (2-6) into a grid or strip.
    - 2 images: side-by-side horizontal strip.
    - 3 images: top-to-bottom vertical strip.
    - 4 images: 2x2 grid.
    - 5 or 6 images: 2 rows, 3 columns grid (6th image ignored if 5).
    File order is determined by natural sort of filenames if provided.
    """
    if not (2 <= len(image_files) <= 6):
        raise ValueError("Number of images must be between 2 and 6.")

    images_pil = []
    for f_obj in image_files:
        try:
            img = Image.open(f_obj).convert("RGBA")
            images_pil.append(img)
        except Exception as e:
            current_app.logger.error(f"Error opening image: {e}")
            # Skip corrupted images or raise error
            continue

    if not images_pil:
        raise ValueError("No valid images could be opened.")

    num_images = len(images_pil)
    merged_image = None

    if num_images == 2:
        # Resize to common height, then paste side-by-side
        images_pil = _resize_images_to_common_dimension(images_pil, 'height')
        total_width = sum(img.width for img in images_pil)
        max_height = images_pil[0].height
        merged_image = Image.new('RGBA', (total_width, max_height))
        current_x = 0
        for img in images_pil:
            merged_image.paste(img, (current_x, 0))
            current_x += img.width

    elif num_images == 3:
        # Resize to common width, then paste top-to-bottom
        images_pil = _resize_images_to_common_dimension(images_pil, 'width')
        max_width = images_pil[0].width
        total_height = sum(img.height for img in images_pil)
        merged_image = Image.new('RGBA', (max_width, total_height))
        current_y = 0
        for img in images_pil:
            merged_image.paste(img, (0, current_y))
            current_y += img.height

    else: # 4, 5, or 6 images - grid layout
        cols = 3 if num_images >= 5 else 2
        rows = 2 if num_images >= 4 else 1 # This logic needs refinement for 5,6
        if num_images == 4: cols, rows = 2, 2
        elif num_images == 5: cols, rows = 3, 2 # will leave one spot empty or handle differently
        elif num_images == 6: cols, rows = 3, 2

        # Resize all images to a common size (e.g., average or max dimensions)
        # For simplicity, let's resize to max width and max height found among images
        max_w = max(img.width for img in images_pil)
        max_h = max(img.height for img in images_pil)

        resized_imgs = [img.resize((max_w, max_h), Image.Resampling.LANCZOS) for img in images_pil]

        merged_width = cols * max_w
        merged_height = rows * max_h
        merged_image = Image.new('RGBA', (merged_width, merged_height))

        for i, img in enumerate(resized_imgs):
            if i >= cols * rows: break # For 5 images in 3x2 grid
            row_idx = i // cols
            col_idx = i % cols
            x_pos = col_idx * max_w
            y_pos = row_idx * max_h
            merged_image.paste(img, (x_pos, y_pos))
            if add_filenames and hasattr(image_files[i], 'filename'): # Check if original file object had filename
                 # Add filename label (optional, simple version)
                draw = ImageDraw.Draw(merged_image)
                try:
                    font = ImageFont.truetype("arial.ttf", 15)
                except IOError:
                    font = ImageFont.load_default()
                draw.text((x_pos + 5, y_pos + 5), os.path.basename(image_files[i].filename), fill="red", font=font)


    if merged_image:
        return merged_image.convert('RGB')
    return None


def process_multiple_images_for_merging(file_storage_list: List[Any]) -> str:
    """
    Opens images from FileStorage objects, merges them, and returns base64 encoded JPEG.
    Sorts files by natural sort key of their filenames.
    """

    # Decorate FileStorage objects with their filenames for sorting, then extract sorted FileStorage
    # The original app.py sorted (filename, file_storage_object) tuples.
    # We need to ensure file_storage_list items are sortable or contain filenames.
    # Assuming file_storage_list contains objects that have a 'filename' attribute and can be opened by PIL.

    # Sort based on filename
    # Check if items are FileStorage with filename attribute
    if not all(hasattr(f, 'filename') for f in file_storage_list):
        # If not, and they are already PIL Images or paths, this sorting might not be needed or done differently.
        # For now, assume they are FileStorage-like objects.
        # Log a warning if filenames are not available for sorting.
        current_app.logger.warning("Attempting to sort files for merging, but some items may lack 'filename'.")

    # Create a list of (filename, file_object) tuples for sorting
    files_to_sort = []
    for f_obj in file_storage_list:
        fname = getattr(f_obj, 'filename', f"unknown_file_{uuid.uuid4().hex[:6]}")
        files_to_sort.append((fname, f_obj))

    files_to_sort.sort(key=lambda x: natural_sort_key(x[0]))

    # Extract the sorted file objects (which can be read by PIL.Image.open())
    sorted_file_objects = [item[1] for item in files_to_sort]

    merged_pil_image = _merge_multiple_images_grid(sorted_file_objects)

    if merged_pil_image:
        img_bytes = io.BytesIO()
        merged_pil_image.save(img_bytes, format='JPEG', quality=95) # Good quality JPEG
        img_bytes.seek(0)
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
        return img_base64
    return None


# --- Image Cleaning Utilities (from original utils/clean_images.py) ---
def convert_images_to_jpg_in_folder(source_folder_path: str, output_base_dir: str = None) -> str:
    """
    Converts all images in a source folder to JPG format and saves them in a new unique subfolder
    within output_base_dir (e.g., configured 'cleaned_images_output' or desktop if None).
    Returns the path to the output subfolder.
    """
    if not os.path.isdir(source_folder_path):
        raise ValueError(f"Source path '{source_folder_path}' is not a valid directory.")

    if output_base_dir:
        create_directory_if_not_exists(output_base_dir)
    else: # Fallback to Desktop (as in original script), consider making this configurable
        output_base_dir = os.path.join(os.path.expanduser("~"), "Desktop")

    # Create a unique subfolder for this batch of cleaned images
    output_subfolder_name = f"cleaned_images_{uuid.uuid4().hex[:8]}"
    actual_output_dir = os.path.join(output_base_dir, output_subfolder_name)
    create_directory_if_not_exists(actual_output_dir)

    processed_count = 0
    error_count = 0

    for filename in os.listdir(source_folder_path):
        source_file_path = os.path.join(source_folder_path, filename)
        if not os.path.isfile(source_file_path):
            continue

        # Use common_allowed_file to check if it's a known image type
        # The original clean_images.py didn't explicitly check extensions before trying Image.open()
        # Adding a check can make it slightly more robust or faster by skipping obvious non-images.
        # However, PIL itself is quite good at determining image types.
        # For now, let PIL handle it.

        base, ext = os.path.splitext(filename)
        # Ensure output filename is secure if based on user input, though listdir is from server-side path.
        output_filename = f"{secure_filename(base)}.jpg"
        output_file_path = os.path.join(actual_output_dir, output_filename)

        try:
            with Image.open(source_file_path) as img:
                # Pillow-avif-plugin might be needed for AVIF, ensure it's imported if AVIF is common.
                # import pillow_avif # Ensure this is imported somewhere globally if used.

                rgb_img = img.convert('RGB') # Convert to RGB for JPEG compatibility
                rgb_img.save(output_file_path, 'JPEG', quality=90) # Good quality
            processed_count +=1
        except Exception as e:
            error_count +=1
            current_app.logger.error(f"Failed to convert '{filename}': {e}")
            # Optionally, copy problematic files to output dir as-is or log them.

    if processed_count == 0 and error_count > 0:
        # If all files failed, the output directory might be empty.
        # Consider removing it or returning a specific status.
        pass

    return actual_output_dir


def convert_uploaded_images_to_jpg(uploaded_files: List[Any], output_base_dir: str) -> Tuple[str, int, int]:
    """
    Saves uploaded image files to a temporary directory, converts them to JPG,
    and stores them in a new unique subfolder within output_base_dir.
    Returns the path to the output subfolder, processed count, and error count.
    """
    if not uploaded_files:
        raise ValueError("No files provided for conversion.")

    # Create a temporary directory to store uploaded files before processing
    # This temp dir should be within a configured server-side temporary location.
    # For simplicity, let's use a subfolder of the output_base_dir for staging.
    # A more robust solution would use Flask's instance path or a dedicated temp file area.

    staging_dir_name = f"staging_{uuid.uuid4().hex[:8]}"
    staging_dir_path = os.path.join(output_base_dir, staging_dir_name) # Or configured temp path
    create_directory_if_not_exists(staging_dir_path)

    try:
        for file_storage in uploaded_files:
            if file_storage and file_storage.filename and common_allowed_file(file_storage.filename):
                filename = secure_filename(file_storage.filename)
                file_path = os.path.join(staging_dir_path, filename)
                file_storage.save(file_path)
            else:
                current_app.logger.warning(f"Skipped non-allowed or empty file: {getattr(file_storage, 'filename', 'N/A')}")

        # Now convert images from the staging directory
        output_subfolder_path = convert_images_to_jpg_in_folder(staging_dir_path, output_base_dir)

        # Count processed/errors (convert_images_to_jpg_in_folder does not return this yet)
        # For now, assume all staged files were attempted.
        # A more detailed count would require modification of convert_images_to_jpg_in_folder.
        processed_count = len(os.listdir(output_subfolder_path)) # Rough estimate
        error_count = 0 # Needs better tracking from underlying function

    finally:
        # Clean up the staging directory
        if os.path.exists(staging_dir_path):
            try:
                import shutil
                shutil.rmtree(staging_dir_path)
            except Exception as e:
                current_app.logger.error(f"Failed to remove staging directory {staging_dir_path}: {e}")

    return output_subfolder_path, processed_count, error_count
