# Flask Utilities Toolkit

A collection of web-based tools built with Flask for image manipulation, file comparison, and more.

![Example Screenshot](效果图/a1.jpg)
_Example: Merging two images with "Before" and "After" labels._

## Features

This toolkit provides the following utilities:

*   **Image Merging:**
    *   Merge two images side-by-side, with an option to add "Before" and "After" labels.
    *   Merge multiple (2-6) images into a single image.
*   **File Comparison:**
    *   Upload two text files and view a visual diff of their contents.
*   **Image Uploading:**
    *   Upload images to the server and get a shareable link.
*   **Prompt Management:**
    *   A simple CRUD interface to manage a list of text prompts, stored in a local SQLite database.
*   **Image Cleaning:**
    *   Convert images in a specified folder or uploaded images to JPG format.
*   **Image Deduplication:**
    *   **Method 1 (Legacy):** Find and remove similar/duplicate images from an uploaded set. Uses hash, histogram, or deep learning methods for comparison. Results are displayed, and duplicates can be moved to a separate folder.
    *   **Method 2 (New):** An alternative image deduplication tool. Upload images or a folder, choose a comparison method (hash, hist, deep) and threshold, and identify similar pairs. Duplicates can then be moved.

## Project Structure

*   `app.py`: The main Flask application file containing all routes and core logic.
*   `requirements.txt`: A list of Python dependencies required to run the project.
*   `config.py`: Configuration settings for the Flask application.
*   `templates/`: HTML templates used for rendering the web pages.
*   `processors/`: Modules for different image processing algorithms (e.g., `hash_processor.py`, `hist_processor.py`, `deep_processor.py`).
*   `utils/`: Utility scripts and helper functions (e.g., `image_utils.py`, `clean_images.py`).
*   `instance/`: Typically used for instance-specific data; here it stores `prompts.db`.
*   `static/`: Static files like CSS, JavaScript, and uploaded images (though uploads are configured to specific subdirectories like `user_uploads`, `image_diff`, etc.).
*   `效果图/`: Directory containing example images/screenshots.

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/buxuele/flask_utils.git
    cd flask_utils
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    python app.py
    ```
    The application will typically be available at `http://localhost:5080` or `http://0.0.0.0:5080`.

## Usage

Once the application is running, open your web browser and navigate to the appropriate URL (e.g., `http://localhost:5080`). You will see a menu or links to the different tools:

*   **Merge Images:** Access via `/` or `/merge`. Upload two images to combine them.
*   **Multi-Merge Images:** Access via `/multi_merge`. Upload 2 to 6 images to combine them.
*   **File Diff:** Access via `/file_diff`. Upload two text files to see their differences.
*   **Upload Image:** Access via `/upload`. Upload an image and get a link.
*   **Prompts:** Access via `/prompts`. Manage your text prompts.
*   **Clean Images:** Access via `/clean_images`. Convert images to JPG.
*   **Image Deduplication (Legacy):** Access via `/image_diff`. Find and manage duplicate images.
*   **Image Deduplication (New):** Access via `/img_duplicate`. Another tool to find and manage duplicate images.

### Running on Windows (Auto-start)

The `项目介绍.md` file (in Chinese) provides instructions for setting up the application to auto-start on Windows:

1.  Create a `.bat` file (e.g., `run_flask_utils.bat`) with the following content, adjusting paths as necessary:
    ```bat
    @echo off
    cd /d "C:\path\to\your\flask_utils"  REM Change this to your project path
    call .\venv\Scripts\activate.bat     REM Assuming your venv is named 'venv'
    python app.py
    ```
2.  Place this `.bat` file in the Windows Startup folder:
    `C:\Users\YourUserName\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`

## Contributing

Contributions are welcome! If you have suggestions for improvements or new features, feel free to open an issue or submit a pull request.

## License

This project does not currently have a specified license. Please refer to the repository owner for licensing information.
