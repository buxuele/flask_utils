import os
import shutil
from flask import (
    Blueprint, render_template, request, jsonify, redirect, url_for, current_app, send_from_directory, flash
)
from werkzeug.utils import secure_filename # Already in common.utils but can be here too
from pathlib import Path

from . import image_dedup_bp
from .utils import (
    save_similar_pairs_to_instance,
    load_similar_pairs_from_instance,
    move_duplicate_images_from_groups,
    process_loaded_similar_pairs # Renamed from process_similar_pairs for clarity
)
# Assuming ImageProcessor will be in app.common.image_processing
# This import will be adjusted once ImageProcessor is refactored.
from app.common.image_processing import ImageProcessor # Placeholder
from app.common.utils import allowed_file, create_directory_if_not_exists


# Route for the main page of image deduplication
@image_dedup_bp.route('/')
def index():
    """Image deduplication main page."""
    # Ensure necessary directories exist (could also be done at app startup)
    # create_directory_if_not_exists(current_app.config['IMG_DUP_UPLOAD_FOLDER'])
    # create_directory_if_not_exists(current_app.config['THUMBNAIL_FOLDER']) # Thumbnails for this module
    # create_directory_if_not_exists(current_app.config['DUPLICATES_FOLDER']) # For duplicates from this module
    return render_template('image_dedup.html')

# Route to get the count of image files in the upload folder
@image_dedup_bp.route('/file_count')
def file_count():
    """Gets the current number of images in the deduplication upload folder."""
    upload_folder = Path(current_app.config['IMG_DUP_UPLOAD_FOLDER'])
    if not upload_folder.exists():
        return jsonify({'count': 0, 'error': 'Upload folder not found.'}), 500

    image_extensions = current_app.config.get('ALLOWED_IMAGE_EXTENSIONS', {'png', 'jpg', 'jpeg'})
    count = 0
    for ext in image_extensions:
        count += len(list(upload_folder.glob(f'*.{ext}')))
    return jsonify({'count': count})

# Route to handle image uploads (single or multiple files, or folders)
@image_dedup_bp.route('/upload', methods=['POST'])
def upload_files():
    """Handles uploading images or folders of images for deduplication."""
    upload_folder = current_app.config['IMG_DUP_UPLOAD_FOLDER']
    create_directory_if_not_exists(upload_folder) # Ensure it exists

    uploaded_file_names = []

    # Check for 'images' part for multiple file uploads
    if 'images' in request.files:
        files = request.files.getlist('images')
        for file_storage in files:
            if file_storage and file_storage.filename and allowed_file(file_storage.filename):
                filename = secure_filename(file_storage.filename)
                file_path = os.path.join(upload_folder, filename)
                try:
                    file_storage.save(file_path)
                    uploaded_file_names.append(filename)
                except Exception as e:
                    current_app.logger.error(f"Error saving uploaded file {filename}: {e}")
                    return jsonify({'error': f'Error saving file {filename}'}), 500
            elif file_storage and file_storage.filename:
                # File was provided but not allowed
                current_app.logger.warning(f"Disallowed file type uploaded: {file_storage.filename}")


    # Check for 'folder' part (typically a zip file or handled by frontend for directory uploads)
    # Note: HTML standard file input does not directly support folder uploads in a simple way.
    # Often this involves JS on the frontend to iterate through folder contents or upload a ZIP.
    # The original code had a 'folder' check; assuming it might receive a ZIP or similar.
    if 'folder' in request.files:
        folder_file = request.files['folder']
        if folder_file and folder_file.filename:
            filename = secure_filename(folder_file.filename)
            # If it's a zip file, extract it
            if filename.lower().endswith('.zip'):
                temp_zip_path = os.path.join(upload_folder, filename)
                temp_extract_dir = os.path.join(upload_folder, '_temp_extract_' + Path(filename).stem)

                try:
                    folder_file.save(temp_zip_path)
                    os.makedirs(temp_extract_dir, exist_ok=True)
                    with shutil.zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_extract_dir)

                    # Move images from extracted folder to the main upload folder
                    for root, _, files_in_zip in os.walk(temp_extract_dir):
                        for item_name in files_in_zip:
                            if allowed_file(item_name):
                                item_src_path = os.path.join(root, item_name)
                                item_dst_name = secure_filename(item_name) # Secure again if needed
                                item_dst_path = os.path.join(upload_folder, item_dst_name)
                                # Avoid overwriting if names clash, or implement renaming
                                if not os.path.exists(item_dst_path):
                                    shutil.move(item_src_path, item_dst_path)
                                    uploaded_file_names.append(item_dst_name)
                                else:
                                    current_app.logger.warning(f"File {item_dst_name} already exists, skipped.")
                except Exception as e:
                    current_app.logger.error(f"Error processing uploaded folder/zip {filename}: {e}")
                    return jsonify({'error': f'Error processing folder/zip {filename}'}), 500
                finally:
                    if os.path.exists(temp_zip_path):
                        os.remove(temp_zip_path)
                    if os.path.exists(temp_extract_dir):
                        shutil.rmtree(temp_extract_dir)
            else:
                # If not a zip, and it's a single file masquerading as 'folder', treat as 'images'
                if allowed_file(filename):
                    file_path = os.path.join(upload_folder, filename)
                    try:
                        folder_file.save(file_path)
                        uploaded_file_names.append(filename)
                    except Exception as e:
                        current_app.logger.error(f"Error saving uploaded 'folder' file {filename}: {e}")

    if not uploaded_file_names and not request.files.getlist('images'):
         # Check if any files were actually attempted or if it was an empty submission
        if any(f.filename for f in request.files.getlist('images')) or \
           (request.files.get('folder') and request.files.get('folder').filename):
            return jsonify({'error': 'No valid image files found or uploaded. Please check file types.'}), 400
        else:
            return jsonify({'error': 'No files selected for upload.'}), 400


    return jsonify({
        'message': f'Successfully uploaded {len(uploaded_file_names)} files.',
        'files': uploaded_file_names
    })

# Route to process images and find duplicates
@image_dedup_bp.route('/process', methods=['POST'])
def process_duplicates():
    """Processes images to find similarities and saves the pairs."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON data in request.'}), 400

    method = data.get('method', 'hash') # Default to 'hash'
    threshold = float(data.get('threshold', 0.95)) # Default threshold

    upload_folder_path = current_app.config['IMG_DUP_UPLOAD_FOLDER']
    thumbnail_folder_path = current_app.config['THUMBNAIL_FOLDER'] # For this module

    # Ensure ImageProcessor is instantiated correctly, possibly with config paths
    # This is a placeholder instantiation.
    try:
        # The ImageProcessor needs to be refactored to be initializable here.
        # It will need paths from current_app.config.
        # For now, we assume it can be instantiated and its methods called.
        # This part is dependent on Step 10 (Shared Utilities/Models) for ImageProcessor's final form.

        # Create an instance of the refactored ImageProcessor
        # It should be configured with the correct paths for this blueprint's context
        img_processor_instance = ImageProcessor(
            images_dir=Path(upload_folder_path),
            thumbnails_dir=Path(thumbnail_folder_path)
            # Adjust ImageProcessor __init__ if it needs more/different config
        )

    except Exception as e:
        current_app.logger.error(f"Failed to initialize ImageProcessor: {e}")
        return jsonify({'error': 'Image processing setup failed.'}), 500

    # Get list of image files from the specific upload folder for this blueprint
    image_files = [f.name for f in Path(upload_folder_path).glob('*')
                   if f.is_file() and allowed_file(f.name)]

    if not image_files:
        return jsonify({'error': 'No image files found in the upload directory to process.'}), 400

    try:
        # Create thumbnails for all images in the upload folder (if ImageProcessor handles this)
        # img_processor_instance.create_thumbnails_for_dir(Path(upload_folder_path), Path(thumbnail_folder_path))

        # The find_similar_pairs method in the original ImageProcessor took a list of full paths.
        # Adjust if the refactored ImageProcessor works differently (e.g., operates on its configured dir).
        full_image_paths = [os.path.join(upload_folder_path, f) for f in image_files]

        # The original ImageProcessor in app.py was a single instance.
        # The one from utils/image_processor.py had its own directory setup.
        # We need to ensure the refactored ImageProcessor uses the correct IMG_DUP_UPLOAD_FOLDER.
        # Let's assume `find_similar_images` is the method on the refactored processor.
        similar_pairs = img_processor_instance.find_similar_images(
            image_paths_to_scan=full_image_paths, # Or it uses its configured images_dir
            similarity_threshold=threshold,
            method=method
        )

        save_similar_pairs_to_instance(similar_pairs) # Save to instance folder

        # Instead of redirect, a JSON response is often better for XHR/fetch calls
        return jsonify({
            'status': 'success',
            'message': f'Processing complete. Found {len(similar_pairs)} similar pairs. Results are available.',
            'redirect_url': url_for('.show_results') # Provide URL for client to redirect if needed
        })

    except ValueError as ve: # e.g. invalid method
        current_app.logger.error(f"Processing error: {ve}")
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred during image processing: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred during processing.'}), 500


# Route to display the results of the deduplication process
@image_dedup_bp.route('/results')
def show_results():
    """Displays the list of similar image pairs found."""
    similar_pairs_data = load_similar_pairs_from_instance()

    # The template expects 'groups' of images, not just pairs.
    # Use the utility function to process pairs into groups.
    image_groups = process_loaded_similar_pairs(similar_pairs_data)

    # The template will need to know the base URL for images and thumbnails
    # These URLs should point to where the files are served from.
    # original_image_url_base = url_for('.serve_original_image', filename='') # filename will be appended by template
    # thumbnail_image_url_base = url_for('.serve_thumbnail_image', filename='')

    return render_template('image_dedup_results.html',
                           image_groups=image_groups,
                           similar_pairs_raw=similar_pairs_data # For debugging or alternative display
                           # original_image_url_base=original_image_url_base,
                           # thumbnail_image_url_base=thumbnail_image_url_base
                           )

# Route to handle the removal of selected duplicate images
@image_dedup_bp.route('/remove_duplicates', methods=['POST'])
def remove_duplicates_action():
    """Moves identified duplicate images to a separate 'duplicates' folder."""
    similar_pairs = load_similar_pairs_from_instance()
    if not similar_pairs:
        flash('No similarity data found to process for removal.', 'warning')
        return redirect(url_for('.index')) # Or back to results

    # The groups are what we need for removal logic (keep one, move others)
    image_groups = process_loaded_similar_pairs(similar_pairs)
    if not image_groups:
        flash('No groups of similar images to process for removal.', 'warning')
        return redirect(url_for('.show_results'))

    source_dir = current_app.config['IMG_DUP_UPLOAD_FOLDER']
    duplicates_target_dir = current_app.config['DUPLICATES_FOLDER'] # Specific to this module's duplicates

    create_directory_if_not_exists(duplicates_target_dir)

    try:
        moved_count = move_duplicate_images_from_groups(image_groups, source_dir, duplicates_target_dir)
        flash(f'Successfully moved {moved_count} duplicate images to the duplicates folder.', 'success')

        # Clear the similarity data as it's now acted upon (optional)
        # save_similar_pairs_to_instance([])

    except Exception as e:
        current_app.logger.error(f"Error during duplicate removal: {e}", exc_info=True)
        flash('An error occurred while removing duplicates.', 'danger')

    return redirect(url_for('.show_results')) # Refresh results page or go to index

# Route to serve original images from the deduplication upload folder
@image_dedup_bp.route('/img/<path:filename>')
def serve_original_image(filename):
    """Serves an original image from the IMG_DUP_UPLOAD_FOLDER."""
    # Ensure filename is safe and does not try to access files outside the intended directory
    safe_filename = secure_filename(Path(filename).name) # Basic sanitization
    if filename != safe_filename:
        # This might be too strict if filenames legitimately contain characters secure_filename strips,
        # but it's a safety measure.
        current_app.logger.warning(f"Potentially unsafe filename access attempted: {filename}")
        # return "Invalid filename", 400 # Or handle as not found

    return send_from_directory(
        current_app.config['IMG_DUP_UPLOAD_FOLDER'],
        safe_filename,
        as_attachment=False # Display inline
    )

# Route to serve thumbnail images from the thumbnail folder
@image_dedup_bp.route('/thumb/<path:filename>')
def serve_thumbnail_image(filename):
    """Serves a thumbnail image from the THUMBNAIL_FOLDER."""
    safe_filename = secure_filename(Path(filename).name)
    # Thumbnails might be in subdirectories or have modified names; adjust logic if so.
    # Assuming thumbnails are directly in THUMBNAIL_FOLDER with same/similar names.
    return send_from_directory(
        current_app.config['THUMBNAIL_FOLDER'], # Specific thumbnail folder for this module
        safe_filename,
        as_attachment=False
    )
