import os
import json # For direct JSON manipulation if needed, though utils handle it
from flask import (
    Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for, send_from_directory
)
from werkzeug.utils import secure_filename
from pathlib import Path

from . import legacy_image_diff_bp
from .utils import (
    save_legacy_similar_pairs,
    load_legacy_similar_pairs,
    group_similar_images_for_legacy_display
)
# The refactored ImageProcessor will be in app.common.image_processing
# This import will be valid after Step 10.
from app.common.image_processing import ImageProcessor
from app.common.utils import allowed_file, create_directory_if_not_exists

# This legacy module will have its own set of folders defined in config.
# LEGACY_IMAGE_DIFF_UPLOAD_DIR, LEGACY_IMAGE_DIFF_THUMBNAIL_DIR, LEGACY_IMAGE_DIFF_DUPLICATES_DIR

def get_legacy_image_processor():
    """Helper to instantiate ImageProcessor for the legacy tool's specific paths."""
    # These config keys need to be added in config.py during Step 13
    upload_dir = Path(current_app.config['LEGACY_IMAGE_DIFF_UPLOAD_DIR'])
    thumb_dir = Path(current_app.config['LEGACY_IMAGE_DIFF_THUMBNAIL_DIR'])

    # Ensure directories exist (ImageProcessor constructor should also do this)
    create_directory_if_not_exists(upload_dir)
    create_directory_if_not_exists(thumb_dir)

    # Assuming ImageProcessor is refactored to take these paths
    return ImageProcessor(images_dir=upload_dir, thumbnails_dir=thumb_dir)


@legacy_image_diff_bp.route('/')
def index():
    """Main page for the legacy image diff tool."""
    return render_template('legacy_image_diff_form.html')

@legacy_image_diff_bp.route('/process', methods=['POST'])
def process_legacy_diff():
    """Handles image uploads, processing for similarities, and saving results."""
    try:
        threshold = float(request.form.get('threshold', 95)) / 100.0 # Original had 95
        method = request.form.get('method', 'hash') # Default to hash

        if method not in ['hash', 'hist', 'deep']:
            flash(f"Unsupported similarity method: {method}", 'danger')
            return redirect(url_for('.index'))

        uploaded_files = request.files.getlist('images')
        if not uploaded_files or not any(f.filename for f in uploaded_files):
            flash("No image files selected for processing.", 'warning')
            return redirect(url_for('.index'))

        processor = get_legacy_image_processor()

        # Save uploaded files to the legacy tool's specific upload directory
        # The ImageProcessor's `save_uploaded_files` method needs to handle this.
        # It should use its configured `images_dir`.

        # The original `ImageProcessor.save_uploaded_files` returned a list of filenames.
        # It saved them to `self.images_dir`.
        saved_filenames = []
        for file_storage in uploaded_files:
            if file_storage and file_storage.filename and allowed_file(file_storage.filename):
                # Secure filename before saving
                s_filename = secure_filename(file_storage.filename)
                try:
                    # Let processor handle saving to its configured dir
                    processor.save_single_uploaded_file(file_storage, s_filename)
                    saved_filenames.append(s_filename)
                except Exception as e_save:
                    current_app.logger.error(f"Legacy: Error saving {s_filename}: {e_save}")
                    flash(f"Error saving file {s_filename}.", "danger")

        if not saved_filenames:
            flash("No valid image files were successfully saved for processing.", 'danger')
            return redirect(url_for('.index'))

        current_app.logger.info(f"Legacy: Saved {len(saved_filenames)} files. Processing with method '{method}', threshold {threshold}.")

        # Create thumbnails (processor method should operate on its configured dirs)
        processor.create_thumbnails() # Assumes it processes all images in its images_dir

        # Find similar images (processor method operates on its configured dirs)
        # The method in original ImageProcessor was `find_similar_images`
        similar_pairs = processor.find_similar_images(
            similarity_threshold=threshold,
            method=method
            # It implicitly uses images from its self.images_dir
        )

        save_legacy_similar_pairs(similar_pairs) # Save to this module's specific JSON

        flash(f'Processing complete. Found {len(similar_pairs)} similar pairs using "{method}" method.', 'success')
        return redirect(url_for('.show_legacy_results'))

    except ValueError as ve: # e.g. bad threshold
        current_app.logger.error(f"Legacy image diff processing error: {ve}", exc_info=True)
        flash(str(ve), 'danger')
    except Exception as e:
        current_app.logger.error(f"Unexpected error in legacy image diff processing: {e}", exc_info=True)
        flash('An unexpected error occurred during processing.', 'danger')

    return redirect(url_for('.index'))


@legacy_image_diff_bp.route('/results')
def show_legacy_results():
    """Displays the results of the legacy image similarity processing."""
    similar_pairs_data = load_legacy_similar_pairs()

    # The original template for this used grouped images.
    image_groups = group_similar_images_for_legacy_display(similar_pairs_data)

    return render_template('legacy_image_diff_results.html',
                           image_groups=image_groups,
                           raw_pairs_count=len(similar_pairs_data)) # Pass raw count for info


@legacy_image_diff_bp.route('/remove-duplicates', methods=['POST'])
def remove_legacy_duplicates():
    """Moves identified duplicate images to the legacy tool's duplicates folder."""
    similar_pairs = load_legacy_similar_pairs()
    if not similar_pairs:
        flash('No similarity data found to process for removal.', 'warning')
        return redirect(url_for('.show_legacy_results'))

    processor = get_legacy_image_processor()
    duplicates_target_dir = Path(current_app.config['LEGACY_IMAGE_DIFF_DUPLICATES_DIR'])
    create_directory_if_not_exists(duplicates_target_dir)

    try:
        # The original ImageProcessor had a `remove_duplicates` method.
        # This method took similar_pairs, grouped them internally, and moved files
        # from its `self.images_dir` to a 'duplicates' subfolder within `self.images_dir`.
        # We need to ensure the refactored ImageProcessor's remove_duplicates
        # uses the configured LEGACY_IMAGE_DIFF_DUPLICATES_DIR as the *target*.

        # Let's assume the refactored ImageProcessor.remove_duplicates now takes an explicit target_dir.
        moved_count = processor.remove_duplicates(
            similar_pairs_list=similar_pairs,
            custom_duplicates_dir=duplicates_target_dir
        )

        flash(f'Successfully moved {moved_count} duplicate images to the designated duplicates folder.', 'success')
        save_legacy_similar_pairs([]) # Clear the pairs list after action
    except Exception as e:
        current_app.logger.error(f"Error during legacy duplicate removal: {e}", exc_info=True)
        flash('An error occurred while removing duplicates.', 'danger')

    return redirect(url_for('.show_legacy_results'))


# --- Routes for serving images (uploads and thumbnails) for this legacy module ---
# These need to serve from the legacy tool's specific directories.

@legacy_image_diff_bp.route('/img/<path:filename>')
def serve_legacy_image(filename):
    """Serves an original image from the LEGACY_IMAGE_DIFF_UPLOAD_DIR."""
    upload_dir = current_app.config['LEGACY_IMAGE_DIFF_UPLOAD_DIR']
    # Basic sanitization, though Path objects handle this better generally.
    # send_from_directory itself is relatively safe.
    s_filename = secure_filename(Path(filename).name)
    return send_from_directory(upload_dir, s_filename, as_attachment=False)

@legacy_image_diff_bp.route('/thumb/<path:filename>')
def serve_legacy_thumbnail(filename):
    """Serves a thumbnail from the LEGACY_IMAGE_DIFF_THUMBNAIL_DIR."""
    thumb_dir = current_app.config['LEGACY_IMAGE_DIFF_THUMBNAIL_DIR']
    s_filename = secure_filename(Path(filename).name)
    return send_from_directory(thumb_dir, s_filename, as_attachment=False)
