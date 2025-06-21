# Flask Utilities Toolkit (Blueprint Version)

This project is a refactored version of the original Flask Utilities Toolkit, now using Flask Blueprints for a more modular and organized structure. It provides a collection of web-based tools for image manipulation, file comparison, prompt management, and more.

## Original Project

For the original version of this toolkit, please see the `flask_utils` directory if this project is part of a larger repository, or refer to its original source. This `flask_blueprint_utils` directory contains the blueprint-refactored application.

## Features

This toolkit provides the following utilities, organized into modules:

*   **Image Tools (`/image-tools`):**
    *   Merge two images side-by-side (`/merge-two`).
    *   Merge multiple (2-6) images into a single image (`/merge-multiple`).
    *   Clean images by converting them to JPG format (`/clean-images`).
*   **Image Deduplication (`/img_duplicate`):**
    *   Find and manage similar/duplicate images using hash, histogram, or deep learning methods.
*   **Legacy Image Difference (`/legacy-image-diff`):**
    *   An older version of the image similarity tool.
*   **File Comparison (`/file-diff`):**
    *   Upload two text files and view a visual diff of their contents.
*   **Prompt Management (`/prompts`):**
    *   A CRUD interface to manage a list of text prompts, stored in a local SQLite database.
*   **Image Uploader (`/uploader`):**
    *   Upload images to the server and get a shareable link.

## Project Structure (`flask_blueprint_utils/`)

The project follows a structure based on Flask Blueprints and an application factory pattern:

```
flask_blueprint_utils/
├── run.py                 # Application entry point (use this to run the app)
├── config.py              # Configuration settings (database, upload paths, etc.)
├── requirements.txt       # Python dependencies
├── instance/              # Created automatically (e.g., for SQLite database)
│   └── prompts.db
├── uploads/               # Created automatically (for storing uploaded files by modules)
│   ├── general_uploads/
│   ├── image_dedup/
│   │   ├── uploads/
│   │   ├── thumbnails/
│   │   └── duplicates/
│   └── legacy_image_diff/
│       ├── uploads/
│       ├── thumbnails/
│       └── duplicates/
├── outputs/               # Created automatically (e.g., for cleaned images)
│   └── cleaned_images/
└── app/                   # Main application package
    ├── __init__.py        # Application factory (create_app)
    ├── extensions.py      # Flask extensions (e.g., SQLAlchemy db instance)
    ├── static/            # Global static files (CSS, JS, images like logo)
    ├── templates/         # Global templates (base.html, index.html, error pages)
    │   ├── base.html
    │   └── index.html
    ├── common/            # Shared utilities and code
    │   ├── __init__.py
    │   ├── utils.py
    │   └── image_processing/ # ImageProcessor and helpers
    │       ├── __init__.py
    │       ├── base_processor.py
    │       ├── hash_helper.py
    │       ├── hist_helper.py
    │       └── deep_helper.py
    └── modules/           # Feature modules (Blueprints)
        ├── prompts/
        │   ├── __init__.py
        │   ├── routes.py
        │   ├── models.py
        │   └── templates/
        │       └── prompts.html
        ├── image_tools/
        │   ├── __init__.py
        │   ├── routes.py
        │   ├── utils.py
        │   └── templates/
        │       ├── merge_two.html
        │       ├── merge_multiple.html
        │       └── clean_images.html
        ├── image_dedup/
        │   ├── __init__.py
        │   ├── routes.py
        │   ├── utils.py
        │   └── templates/
        │       ├── image_dedup.html
        │       └── image_dedup_results.html
        ├── legacy_image_diff/
        │   ├── __init__.py
        │   ├── routes.py
        │   ├── utils.py
        │   └── templates/
        │       ├── legacy_image_diff_form.html
        │       └── legacy_image_diff_results.html
        ├── file_diff/
        │   ├── __init__.py
        │   ├── routes.py
        │   └── templates/
        │       ├── file_diff_form.html
        │       └── file_diff_result.html
        └── uploader/
            ├── __init__.py
            ├── routes.py
            └── templates/
                └── upload_form.html
```

## Setup and Installation

1.  **Navigate to this project's directory:**
    ```bash
    cd path/to/flask_blueprint_utils
    ```

2.  **Create a Python virtual environment (recommended):**
    ```bash
    python -m venv venv
    # Activate the environment
    # On Windows:
    # venv\Scripts\activate
    # On macOS/Linux:
    # source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: The Deep Learning image comparison method (`deep`) requires PyTorch and torchvision. If you don't have these installed or don't need this specific method, the application will use dummy implementations for it. To enable it, install PyTorch appropriate for your system (see [pytorch.org](https://pytorch.org/)).*

4.  **Environment Variables (Optional):**
    *   You can set a `SECRET_KEY` environment variable for Flask session security. A default is provided in `config.py` for development.
    *   `FLASK_CONFIG`: Can be set to `development` or `production` if you define corresponding config classes in `config.py`. (Currently, only a default `Config` is used).

5.  **Run the application:**
    ```bash
    python run.py
    ```
    The application will typically be available at `http://localhost:5080` or `http://0.0.0.0:5080`.

## Usage

Once the application is running, open your web browser and navigate to the main URL (e.g., `http://localhost:5080`). The homepage provides an overview and links to the various tools. Navigation is also available in the top menu bar.

The tools are accessible via their respective URL prefixes:
*   Image Tools: `/image-tools/...`
*   Image Deduplication (New): `/img_duplicate/...`
*   Legacy Image Diff: `/legacy-image-diff/...`
*   File Compare: `/file-diff/...`
*   Prompts Manager: `/prompts/...`
*   Image Uploader: `/uploader/...`

## Notes

*   **Database:** The Prompts module uses an SQLite database (`instance/prompts.db`), which will be created automatically on first run.
*   **File Storage:** Uploaded images, thumbnails, duplicates, and cleaned images are stored in subdirectories within `flask_blueprint_utils/uploads/` and `flask_blueprint_utils/outputs/`. These are configured in `config.py`.
*   **Windows Auto-start:** If you wish to set this application to auto-start on Windows, you can adapt the `.bat` script method described in the original project's documentation, ensuring paths in the script point to this `flask_blueprint_utils` directory and `run.py`.

## Contributing

Contributions, issues, and feature requests are welcome. Please feel free to open an issue or submit a pull request if you have suggestions for improvements.

## License

This project does not currently have a specified license. Please refer to the repository owner for licensing information if applicable.
