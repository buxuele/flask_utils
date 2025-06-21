import os
import difflib
from tempfile import NamedTemporaryFile # For temporary file handling
from flask import (
    Blueprint, render_template, request, current_app, flash, redirect, url_for
)
from werkzeug.utils import secure_filename # Though not strictly needed for temp files if not saving with original names

from . import file_diff_bp
# No specific utils or models for this simple module yet.

@file_diff_bp.route('/', methods=['GET', 'POST'])
def compare_files():
    if request.method == 'POST':
        # Check if the post request has the file parts
        if 'file1' not in request.files or 'file2' not in request.files:
            flash('Please select two files to compare.', 'warning')
            return redirect(request.url)

        file1 = request.files['file1']
        file2 = request.files['file2']

        if file1.filename == '' or file2.filename == '':
            flash('One or both files were not selected.', 'warning')
            return redirect(request.url)

        # Basic check for text-like files, although difflib handles binary differences too,
        # HtmlDiff output is best for text.
        # Consider adding more robust type checking if needed.
        # For now, assume user uploads text-comparable files.

        temp_files_paths = []
        try:
            # Save uploaded files to temporary locations to read them
            # Using NamedTemporaryFile to ensure they are cleaned up

            # It's good practice to handle potential character encoding issues.
            # The original app.py used 'utf-8'. We'll try that.
            # Browsers might not always send encoding, so this can be tricky.

            temp_file_objects = []

            with NamedTemporaryFile(delete=False, mode='wb') as temp1_wb, \
                 NamedTemporaryFile(delete=False, mode='wb') as temp2_wb:

                file1.save(temp1_wb) # Save file1 (binary mode)
                file2.save(temp2_wb) # Save file2 (binary mode)

                temp_files_paths.append(temp1_wb.name)
                temp_files_paths.append(temp2_wb.name)

            # Now read from the saved temp files with specified encoding
            try:
                with open(temp_files_paths[0], 'r', encoding='utf-8') as f1_content_file, \
                     open(temp_files_paths[1], 'r', encoding='utf-8') as f2_content_file:
                    fromlines = f1_content_file.readlines()
                    tolines = f2_content_file.readlines()
            except UnicodeDecodeError:
                # Fallback or error if UTF-8 fails. For simplicity, we'll flash an error.
                # A more robust solution might try other encodings or allow user to specify.
                flash('Could not decode one or both files as UTF-8. Please ensure files are UTF-8 encoded text.', 'danger')
                return redirect(request.url)


            diff_html = difflib.HtmlDiff(wrapcolumn=80).make_file(
                fromlines,
                tolines,
                fromdesc=secure_filename(file1.filename), # Use secure_filename for display
                todesc=secure_filename(file2.filename),
                context=True, # Show context lines
                numlines=5    # Number of context lines
            )

            # The diff_html can be very large. Passing it directly in render_template is fine.
            return render_template('file_diff_result.html', diff_content_html=diff_html)

        except Exception as e:
            current_app.logger.error(f"Error during file diff: {e}", exc_info=True)
            flash(f'An error occurred while comparing files: {str(e)}', 'danger')
            return redirect(request.url)
        finally:
            # Ensure temporary files are deleted
            for path in temp_files_paths:
                if os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception as e_unlink:
                        current_app.logger.error(f"Error deleting temp file {path}: {e_unlink}")

    # For GET request, just show the upload form
    return render_template('file_diff_form.html')
