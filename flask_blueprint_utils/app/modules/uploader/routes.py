import os
import uuid # For generating unique filenames
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, current_app, send_from_directory
)
from werkzeug.utils import secure_filename

from . import uploader_bp
from app.common.utils import allowed_file as common_allowed_file, create_directory_if_not_exists

# Define allowed extensions specifically for this uploader if different from common,
# or use the common one directly. For a general uploader, it might be broader or configurable.
# For this module, let's stick to the common image extensions.
UPLOADER_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg', 'ico', 'tif', 'tiff'}

def _is_uploader_allowed_file(filename):
    return common_allowed_file(filename, UPLOADER_ALLOWED_EXTENSIONS)

@uploader_bp.route('/', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        if 'image_file' not in request.files: # Check for the specific input name
            flash('No file part selected in the form.', 'warning')
            return redirect(request.url)

        file = request.files['image_file']

        if file.filename == '':
            flash('No file selected for uploading.', 'warning')
            return redirect(request.url)

        if file and _is_uploader_allowed_file(file.filename):
            # Secure the filename and make it unique to prevent overwrites and conflicts
            original_filename = secure_filename(file.filename)
            extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
            # Using UUID for filename uniqueness
            unique_filename = f"{uuid.uuid4().hex}.{extension}"

            # Get the upload folder path from app config (needs to be defined in config.py)
            # Example: current_app.config['GENERAL_UPLOADS_DIR']
            # For now, using 'USER_UPLOAD_FOLDER' from original config, but this should be specific.
            # Let's assume a config var: `UPLOADER_STORAGE_DIR`
            upload_dir = current_app.config.get('UPLOADER_STORAGE_DIR')
            if not upload_dir:
                current_app.logger.error("UPLOADER_STORAGE_DIR is not configured.")
                flash('File upload directory is not configured on the server.', 'danger')
                return redirect(request.url)

            create_directory_if_not_exists(upload_dir) # Ensure directory exists

            file_path = os.path.join(upload_dir, unique_filename)

            try:
                file.save(file_path)

                # Generate a URL to access the uploaded file.
                # This requires a route to serve files from UPLOADER_STORAGE_DIR.
                # The URL should be relative to this blueprint or a global static serving route.
                # Let's assume a '/uploads/<filename>' route within this blueprint.
                image_access_url = url_for('.serve_uploaded_file', filename=unique_filename, _external=True)

                flash(f'Image "{original_filename}" uploaded successfully!', 'success')
                return render_template('upload_form.html', uploaded_filename=original_filename, image_url=image_access_url)

            except Exception as e:
                current_app.logger.error(f"Error saving uploaded file '{original_filename}': {e}", exc_info=True)
                flash(f'An error occurred while saving the file: {str(e)}', 'danger')
                return redirect(request.url)
        else:
            flash('Unsupported file type. Please upload a valid image.', 'danger')
            return redirect(request.url)

    return render_template('upload_form.html')


@uploader_bp.route('/uploads/<path:filename>')
def serve_uploaded_file(filename):
    """Serves files uploaded via the uploader module."""
    upload_dir = current_app.config.get('UPLOADER_STORAGE_DIR')
    if not upload_dir:
        current_app.logger.error("UPLOADER_STORAGE_DIR is not configured for serving.")
        return "File serving misconfigured.", 404 # Or appropriate error

    # Secure filename again before serving, though filename here should be the UUID-generated one
    # Path(filename).name ensures we only get the filename part if a path was somehow passed.
    # However, UUIDs are generally safe.
    safe_filename = secure_filename(os.path.basename(filename))

    # Check if the originally generated filename (which might contain UUID) is being requested.
    # This is important if unique_filename wasn't further sanitized by secure_filename (UUIDs are safe).
    # For simplicity, we assume `filename` is the one stored (e.g., the UUID.ext).

    return send_from_directory(upload_dir, safe_filename, as_attachment=False)

# The original app.py had a route `/my_files` that redirected to index.
# This seems unrelated to the uploader functionality directly, unless it was meant
# to list uploaded files. For now, I'll omit it as its purpose within the uploader is unclear.
# If a "list my uploads" feature is desired, it would need more logic (e.g., user sessions, database of uploads).
