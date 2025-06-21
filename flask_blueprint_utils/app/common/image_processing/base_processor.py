import os
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Any
from PIL import Image, UnidentifiedImageError
from flask import current_app # For logging and config access

from .hash_helper import HashProcessor
from .hist_helper import HistProcessor
from .deep_helper import DeepProcessor
from app.common.utils import create_directory_if_not_exists, get_secure_filename # For secure filenames

class ImageProcessor:
    def __init__(self, images_dir: Path, thumbnails_dir: Path, duplicates_dir: Path = None):
        """
        Initializes the ImageProcessor with specific directories for its operations.
        Args:
            images_dir: Path to the directory where primary images are stored/uploaded.
            thumbnails_dir: Path to the directory where thumbnails will be stored.
            duplicates_dir: Path to the directory where identified duplicates will be moved (optional, can be set later).
        """
        self.images_dir = Path(images_dir)
        self.thumbnails_dir = Path(thumbnails_dir)
        self.duplicates_dir = Path(duplicates_dir) if duplicates_dir else None

        create_directory_if_not_exists(self.images_dir)
        create_directory_if_not_exists(self.thumbnails_dir)
        if self.duplicates_dir:
            create_directory_if_not_exists(self.duplicates_dir)

        # Instantiate helper processors
        self.hash_proc = HashProcessor()
        self.hist_proc = HistProcessor()
        self.deep_proc = DeepProcessor() # Will use dummy if PyTorch not available

        self.logger = current_app.logger if current_app else logging.getLogger(__name__)


    def _get_processor_by_method(self, method: str):
        """Returns the appropriate helper processor based on the method string."""
        if method == 'hash':
            return self.hash_proc
        elif method == 'hist':
            return self.hist_proc
        elif method == 'deep':
            return self.deep_proc
        else:
            self.logger.error(f"Invalid similarity method specified: {method}")
            raise ValueError(f"Unsupported similarity method: {method}")

    def save_single_uploaded_file(self, file_storage, filename: str) -> bool:
        """
        Saves a single FileStorage object to the processor's images_dir.
        Args:
            file_storage: The FileStorage object from Flask request.
            filename: The (preferably secured) filename to save as.
        Returns:
            True if save was successful, False otherwise.
        """
        if not file_storage or not filename:
            self.logger.warning("ImageProcessor: Attempted to save file with no FileStorage or filename.")
            return False

        save_path = self.images_dir / get_secure_filename(filename) # Ensure filename is secured
        try:
            file_storage.save(str(save_path))
            self.logger.info(f"ImageProcessor: Saved uploaded file to {save_path}")
            return True
        except Exception as e:
            self.logger.error(f"ImageProcessor: Failed to save uploaded file {filename} to {save_path}: {e}", exc_info=True)
            return False

    def create_thumbnails(self, target_size: Tuple[int, int] = (200, 200), quality: int = 85):
        """
        Creates thumbnails for all valid images in self.images_dir, storing them in self.thumbnails_dir.
        """
        self.logger.info(f"ImageProcessor: Starting thumbnail creation in {self.thumbnails_dir} for images in {self.images_dir}")
        created_count = 0
        for img_file in self.images_dir.iterdir():
            if img_file.is_file():
                thumb_path = self.thumbnails_dir / img_file.name # Use the same filename for thumbnail
                if thumb_path.exists(): # Optionally, skip if thumbnail already exists
                    # self.logger.debug(f"Thumbnail already exists for {img_file.name}, skipping.")
                    continue
                try:
                    with Image.open(img_file) as img:
                        img.thumbnail(target_size, Image.Resampling.LANCZOS)
                        # Ensure thumbnail is RGB if saving as JPEG
                        if img.mode != 'RGB' and thumb_path.suffix.lower() in ['.jpg', '.jpeg']:
                             img = img.convert('RGB')
                        img.save(str(thumb_path), quality=quality)
                        created_count += 1
                except UnidentifiedImageError:
                    self.logger.warning(f"ImageProcessor: Cannot identify image file {img_file.name}, skipping thumbnail.")
                except Exception as e:
                    self.logger.error(f"ImageProcessor: Failed to create thumbnail for {img_file.name}: {e}", exc_info=True)
        self.logger.info(f"ImageProcessor: Thumbnail creation complete. Created {created_count} new thumbnails.")


    def find_similar_images(self, image_paths_to_scan: List[Path] = None,
                             similarity_threshold: float = 0.95, method: str = 'hash') -> List[Dict[str, Any]]:
        """
        Finds similar image pairs from a list of image paths or all images in self.images_dir.
        Args:
            image_paths_to_scan: Optional list of specific image Paths to process. If None, scans self.images_dir.
            similarity_threshold: The threshold above which images are considered similar.
            method: The method to use for feature extraction and similarity ('hash', 'hist', 'deep').
        Returns:
            A list of dictionaries, where each dictionary represents a similar pair:
            {'image1': filename1, 'image2': filename2, 'similarity': score}
        """
        helper_processor = self._get_processor_by_method(method)

        if image_paths_to_scan is None:
            image_files = [f for f in self.images_dir.iterdir() if f.is_file()]
            self.logger.info(f"ImageProcessor: Scanning all {len(image_files)} files in {self.images_dir} for similarity using '{method}'.")
        else:
            image_files = [Path(p) for p in image_paths_to_scan] # Ensure they are Path objects
            self.logger.info(f"ImageProcessor: Scanning {len(image_files)} provided image paths for similarity using '{method}'.")

        if not image_files:
            self.logger.info("ImageProcessor: No image files to process for similarity.")
            return []

        features_cache = {} # Cache features: {filename: feature_data}
        for img_path in image_files:
            if not img_path.is_file():
                self.logger.warning(f"ImageProcessor: Path {img_path} is not a file, skipping.")
                continue
            try:
                # Use absolute path for feature computation for clarity
                feature = helper_processor.compute_feature(str(img_path.resolve()))
                if feature:
                    features_cache[img_path.name] = feature # Store feature by filename
                else:
                    self.logger.warning(f"ImageProcessor: Could not compute feature for {img_path.name} using method '{method}'.")
            except Exception as e:
                self.logger.error(f"ImageProcessor: Error computing feature for {img_path.name}: {e}", exc_info=True)

        self.logger.info(f"ImageProcessor: Computed features for {len(features_cache)} images.")
        if not features_cache: return []

        similar_pairs = []
        processed_for_pairs = set() # To avoid (imgA, imgB) and (imgB, imgA) duplicates if comparing all-to-all naively

        filenames = list(features_cache.keys()) # List of filenames for which features were computed

        for i in range(len(filenames)):
            img1_name = filenames[i]
            feat1 = features_cache[img1_name]

            for j in range(i + 1, len(filenames)):
                img2_name = filenames[j]
                feat2 = features_cache[img2_name]

                try:
                    similarity = helper_processor.compute_similarity(feat1, feat2)
                    if similarity >= similarity_threshold:
                        similar_pairs.append({
                            'image1': img1_name,
                            'image2': img2_name,
                            'similarity': float(similarity) # Ensure it's a standard float
                        })
                except Exception as e:
                    self.logger.error(f"ImageProcessor: Error computing similarity between {img1_name} and {img2_name}: {e}", exc_info=True)

        self.logger.info(f"ImageProcessor: Found {len(similar_pairs)} similar pairs with threshold {similarity_threshold} using '{method}'.")
        return similar_pairs

    def remove_duplicates(self, similar_pairs_list: List[Dict[str, Any]],
                          custom_duplicates_dir: Path = None, keep_strategy='first') -> int:
        """
        Moves duplicate images to a specified duplicates directory.
        Args:
            similar_pairs_list: A list of similar pair dicts, as returned by find_similar_images.
            custom_duplicates_dir: Optional. If provided, duplicates are moved here. Otherwise, uses self.duplicates_dir.
            keep_strategy: Currently supports 'first' (keeps the first image in a group).
        Returns:
            The number of files successfully moved.
        """
        target_duplicates_dir = custom_duplicates_dir or self.duplicates_dir
        if not target_duplicates_dir:
            self.logger.error("ImageProcessor: Duplicates directory not specified for remove_duplicates.")
            return 0
        create_directory_if_not_exists(target_duplicates_dir)

        if not similar_pairs_list:
            self.logger.info("ImageProcessor: No similar pairs provided for duplicate removal.")
            return 0

        # Group images based on similarity pairs (simple connected components)
        image_groups = self._group_images_from_pairs(similar_pairs_list)

        moved_count = 0
        for group in image_groups:
            if len(group) <= 1: # No duplicates in a group of one or zero
                continue

            # Decide which image to keep based on strategy
            # For 'first', assuming the list `group` is somewhat ordered (e.g., by processing order or name if sorted before grouping)
            # A more robust 'keep' strategy might involve sorting by name, date, size, etc.
            # For now, keep the one at index 0 of the list `group`.

            # Ensure filenames in group are unique before deciding which to keep/move
            unique_images_in_group = sorted(list(set(g for g in group if g))) # Remove None/empty and sort for consistency
            if not unique_images_in_group or len(unique_images_in_group) <=1:
                continue

            image_to_keep = unique_images_in_group[0]
            self.logger.debug(f"ImageProcessor: In group {unique_images_in_group}, keeping {image_to_keep}.")

            for img_filename_to_move in unique_images_in_group[1:]:
                source_path = self.images_dir / img_filename_to_move
                dest_path = target_duplicates_dir / img_filename_to_move

                if source_path.exists():
                    try:
                        shutil.move(str(source_path), str(dest_path))
                        self.logger.info(f"ImageProcessor: Moved duplicate {img_filename_to_move} to {dest_path}")
                        moved_count += 1
                    except Exception as e:
                        self.logger.error(f"ImageProcessor: Failed to move {img_filename_to_move} to {dest_path}: {e}", exc_info=True)
                else:
                    self.logger.warning(f"ImageProcessor: Source file {source_path} for duplicate removal not found (might have been moved already or was a typo in pairs list).")

        self.logger.info(f"ImageProcessor: Duplicate removal complete. Moved {moved_count} files.")
        return moved_count

    def _group_images_from_pairs(self, similar_pairs: List[Dict[str, Any]]) -> List[List[str]]:
        """Helper to group images based on a list of similarity pairs."""
        adj = {} # Adjacency list for graph
        all_images_in_pairs = set()

        for pair in similar_pairs:
            img1, img2 = pair.get('image1'), pair.get('image2')
            if not img1 or not img2: continue # Skip malformed pairs

            all_images_in_pairs.add(img1)
            all_images_in_pairs.add(img2)
            adj.setdefault(img1, []).append(img2)
            adj.setdefault(img2, []).append(img1)

        groups = []
        visited = set()
        for img_node in all_images_in_pairs:
            if img_node not in visited:
                current_group = []
                q = [img_node]
                visited.add(img_node)
                head = 0
                while head < len(q):
                    u = q[head]
                    head += 1
                    current_group.append(u)
                    for v_neighbor in adj.get(u, []):
                        if v_neighbor not in visited:
                            visited.add(v_neighbor)
                            q.append(v_neighbor)
                if current_group:
                    groups.append(sorted(list(set(current_group)))) # Sort for consistent output
        return groups

    # Other methods from original ImageProcessor (like the one in utils/image_processor.py)
    # - create_thumbnails: Implemented above.
    # - save_uploaded_files (plural): The new processor expects to be told which files to process or scans its dir.
    #   Individual file saving is handled by `save_single_uploaded_file`.
    #   Batch saving can be a loop calling the single save, handled in routes.

    # The original ImageProcessor in app.py was a global instance.
    # This refactored version is designed to be instantiated per-blueprint or per-task
    # with specific directories, making it more flexible.

    # The `find_similar_pairs` method from the old `ImageProcessor` class in `utils/image_processor.py`
    # is essentially what `find_similar_images` does here.
    # The old `ImageProcessor` in `app.py` was different and simpler.
    # This new `base_processor.ImageProcessor` aims to be a comprehensive version.
    pass
