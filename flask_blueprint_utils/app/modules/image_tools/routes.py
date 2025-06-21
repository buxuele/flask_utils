import os
import io
import base64
import shutil # For removing temp dirs if used in clean_images

from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
)
from PIL import Image # Used directly for opening images from request files

from . import image_tools_bp
from .utils import (
    merge_two_images_side_by_side,
    process_multiple_images_for_merging,
    convert_images_to_jpg_in_folder,
    convert_uploaded_images_to_jpg
)
from app.common.utils import (
    natural_sort_key,
    allowed_file as common_allowed_file, # General file type check
    create_directory_if_not_exists,
    get_secure_filename
)

# Define allowed extensions specifically for image tools if different from common
IMAGE_TOOLS_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tiff', 'tif', 'avif'}


# Helper to check allowed file types for this blueprint
def _is_allowed_image_tool_file(filename):
    return common_allowed_file(filename, IMAGE_TOOLS_ALLOWED_EXTENSIONS)


@image_tools_bp.route('/')
def index():
    """Main page for image tools, could redirect to a specific tool or be a dashboard."""
    # For now, let's make the 2-image merge the default page for this blueprint's root.
    return redirect(url_for('.merge_two_images_get'))


# --- Route for merging two images ---
@image_tools_bp.route('/merge-two', methods=['GET', 'POST'])
def merge_two_images_get():
    if request.method == 'POST':
        if 'image1' not in request.files or 'image2' not in request.files:
            flash('Please select two image files.', 'warning')
            return redirect(request.url)

        file1 = request.files['image1']
        file2 = request.files['image2']

        if file1.filename == '' or file2.filename == '':
            flash('One or both files were not selected.', 'warning')
            return redirect(request.url)

        if not (_is_allowed_image_tool_file(file1.filename) and _is_allowed_image_tool_file(file2.filename)):
            flash('Invalid file type. Please upload supported image formats.', 'danger')
            return redirect(request.url)

        add_text_labels = 'add_text' in request.form

        try:
            img1_pil = Image.open(file1.stream)
            img2_pil = Image.open(file2.stream)

            # Sort images by filename using natural sort before merging
            # This ensures consistent "left" and "right" if filenames imply order (e.g., "img_before.png", "img_after.png")
            files_data = [(file1.filename, img1_pil), (file2.filename, img2_pil)]
            files_data.sort(key=lambda x: natural_sort_key(x[0]))

            # The merge function expects PIL images
            merged_pil_image = merge_two_images_side_by_side(
                files_data[0][1], # First PIL image after sort
                files_data[1][1], # Second PIL image after sort
                add_labels=add_text_labels
            )

            img_byte_arr = io.BytesIO()
            merged_pil_image.save(img_byte_arr, format='JPEG', quality=95)
            img_byte_arr.seek(0)
            img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

            flash('Images merged successfully!', 'success')
            return render_template('merge_two.html', merged_image_data=img_base64)

        except Exception as e:
            current_app.logger.error(f"Error merging two images: {e}", exc_info=True)
            flash(f'An error occurred during image merging: {str(e)}', 'danger')
            return redirect(request.url)

    return render_template('merge_two.html')


# --- Route for merging multiple images (2-6 images) ---
@image_tools_bp.route('/merge-multiple', methods=['GET', 'POST'])
def merge_multiple_images():
    if request.method == 'POST':
        uploaded_files = request.files.getlist('images') # Expecting 'images' as field name

        if not uploaded_files or len(uploaded_files) == 0:
            flash('No files selected.', 'warning')
            return redirect(request.url)

        # Filter out empty filenames and check types
        valid_files = []
        for f_storage in uploaded_files:
            if f_storage and f_storage.filename and _is_allowed_image_tool_file(f_storage.filename):
                valid_files.append(f_storage)
            elif f_storage and f_storage.filename: # File provided but not allowed type
                flash(f"File '{f_storage.filename}' has an unsupported type.", 'warning')
                # Continue to process other valid files or redirect

        if not (2 <= len(valid_files) <= 6):
            flash(f'Please upload between 2 and 6 valid image files. You provided {len(valid_files)}.', 'danger')
            return redirect(request.url)

        try:
            # The utility function process_multiple_images_for_merging expects FileStorage-like objects
            # It handles opening, sorting by filename, merging, and base64 encoding.
            merged_base64_string = process_multiple_images_for_merging(valid_files)

            if merged_base64_string:
                flash('Images merged successfully!', 'success')
                return render_template('merge_multiple.html', merged_image_data=merged_base64_string)
            else:
                flash('Failed to merge images. Please ensure files are valid images.', 'danger')

        except ValueError as ve: # From _merge_multiple_images_grid if count is wrong (should be caught above) or no valid images
             flash(str(ve), 'danger')
        except Exception as e:
            current_app.logger.error(f"Error merging multiple images: {e}", exc_info=True)
            flash(f'An error occurred: {str(e)}', 'danger')

        return redirect(request.url) # On error, redirect back to the GET page

    return render_template('merge_multiple.html')


# --- Route for cleaning images (convert to JPG) ---
@image_tools_bp.route('/clean-images', methods=['GET', 'POST'])
def clean_images_route():
    if request.method == 'POST':
        source_folder_path = request.form.get('folder_path', '').strip()
        uploaded_image_files = request.files.getlist('images')

        # Config key for where cleaned images should be stored (base directory)
        # This should be an absolute path defined in config.py
        cleaned_output_base_dir = current_app.config.get('CLEANED_IMAGES_OUTPUT_DIR')
        if not cleaned_output_base_dir:
            flash('Output directory for cleaned images is not configured.', 'danger')
            return redirect(request.url)
        create_directory_if_not_exists(cleaned_output_base_dir) # Ensure base output dir exists

        output_subdir_path = None
        processed_count = 0
        error_count = 0

        try:
            if source_folder_path: # User provided a server-side folder path
                if not os.path.isdir(source_folder_path): # Basic validation
                    flash('The provided folder path is not a valid directory.', 'danger')
                    return redirect(request.url)
                # Security: Ensure this path is safe and within allowed areas if this feature is exposed.
                # For a local tool, it's less critical but for a web app, be very careful.
                # Consider restricting access to only specific pre-approved directories.
                current_app.logger.info(f"Cleaning images from folder: {source_folder_path}")
                output_subdir_path = convert_images_to_jpg_in_folder(source_folder_path, cleaned_output_base_dir)
                # TODO: convert_images_to_jpg_in_folder should return counts
                # For now, we can only confirm it ran.
                flash(f'Images from folder processed. Output at: {output_subdir_path}', 'success')

            elif uploaded_image_files and any(f.filename for f in uploaded_image_files):
                valid_uploads = [f for f in uploaded_image_files if f.filename and _is_allowed_image_tool_file(f.filename)]
                if not valid_uploads:
                    flash('No valid image files were uploaded for cleaning.', 'warning')
                    return redirect(request.url)

                current_app.logger.info(f"Cleaning {len(valid_uploads)} uploaded images.")
                output_subdir_path, processed_count, error_count = convert_uploaded_images_to_jpg(
                    valid_uploads,
                    cleaned_output_base_dir
                )
                msg = f'Uploaded images processed: {processed_count} converted, {error_count} errors. Output at: {output_subdir_path}'
                flash(msg, 'success' if error_count == 0 else 'warning')

            else: # Neither folder path nor uploaded files
                flash('Please provide a folder path or upload image files to clean.', 'warning')
                return redirect(request.url)

            if output_subdir_path:
                 # Provide a way for the user to know where the files are.
                 # If it's a web server, direct download or listing isn't straightforward unless these are web-accessible.
                 # For now, just showing the server path.
                return render_template('clean_images.html', output_directory=output_subdir_path)

        except ValueError as ve:
            flash(str(ve), 'danger')
        except Exception as e:
            current_app.logger.error(f"Error cleaning images: {e}", exc_info=True)
            flash(f'An error occurred during image cleaning: {str(e)}', 'danger')

        return redirect(request.url)

    return render_template('clean_images.html')

# Note: The original app.py had a root route '/' that rendered 'merge.html'.
# This is now handled by merge_two_images_get or the blueprint's index.
# The original '/multi_merge' is now '/merge-multiple'.
# The original '/clean_images' is now '/clean-images'.
# URL prefixes are handled by the blueprint.
# Ensure templates are renamed/moved to 'merge_two.html', 'merge_multiple.html', 'clean_images.html'
# within the image_tools/templates/ directory.

# A route to serve images from the cleaned_output_base_dir might be needed if users
# should be able to download or view them via the web app.
# This depends on whether CLEANED_IMAGES_OUTPUT_DIR is within a static serving path
# or needs a dedicated route. For security, a dedicated route with path validation is better.
# Example:
# @image_tools_bp.route('/cleaned_files/<path:subfolder>/<path:filename>')
# def serve_cleaned_image(subfolder, filename):
#     base_dir = current_app.config.get('CLEANED_IMAGES_OUTPUT_DIR')
#     if not base_dir: return "Configuration error", 500
#     # IMPORTANT: Validate subfolder and filename to prevent directory traversal
#     safe_subfolder = get_secure_filename(subfolder) # Basic check
#     safe_filename = get_secure_filename(filename)
#     if subfolder != safe_subfolder or filename != safe_filename:
#         return "Invalid path", 400
#     file_dir = os.path.join(base_dir, safe_subfolder)
#     return send_from_directory(file_dir, safe_filename)
