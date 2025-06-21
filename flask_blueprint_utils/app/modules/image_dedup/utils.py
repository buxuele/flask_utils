import os
import shutil
import json
from pathlib import Path
from typing import List, Dict, Tuple
from flask import current_app # To access config like IMG_DUP_UPLOAD_FOLDER

# Assuming ImageProcessor class and its dependencies (HashProcessor, HistProcessor, DeepProcessor)
# will be moved to a shared location or within this module if only used here.
# For now, let's assume they might be in `app.common.image_processing` or similar.
# This part needs to be adjusted based on where ImageProcessor and its components are placed.
# from app.common.image_processing import ImageProcessor

# Placeholder for ImageProcessor until its final location is decided.
# If ImageProcessor is simple enough and specific to this blueprint, it can be defined here.
# Or, parts of it can be extracted.

# For `save_similar_pairs` and `load_similar_pairs`, the file path needs to be handled carefully.
# Storing it in a temporary or instance folder is better than the project root.

def get_similar_pairs_filepath():
    """Returns the path to the similar_pairs.json file within the instance folder."""
    instance_path = current_app.instance_path
    return os.path.join(instance_path, 'image_dedup_similar_pairs.json')

def save_similar_pairs_to_instance(similar_pairs: List[Dict]):
    """Saves similar image pairs to a JSON file in the instance folder."""
    filepath = get_similar_pairs_filepath()
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(similar_pairs, f, ensure_ascii=False, indent=2)
    except IOError as e:
        current_app.logger.error(f"Error saving similar pairs file: {e}")


def load_similar_pairs_from_instance() -> List[Dict]:
    """Loads similar image pairs from a JSON file in the instance folder."""
    filepath = get_similar_pairs_filepath()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except IOError as e:
        current_app.logger.error(f"Error loading similar pairs file: {e}")
        return []

def process_loaded_similar_pairs(similar_pairs: List[Dict]) -> List[List[str]]:
    """
    Processes a list of similar pair dictionaries into groups of similar images.
    Each group is a list of image filenames.
    Keeps the first image of a group as the original, others are potential duplicates.
    """
    groups = []
    # Keep track of images already assigned to a group to avoid redundant processing
    # and adding an image to multiple groups if it's part of multiple pairs.
    images_in_groups = set()

    for pair in similar_pairs:
        img1, img2 = pair['image1'], pair['image2']

        # Check if either image is already in a group
        group_for_img1 = None
        group_for_img2 = None

        for group in groups:
            if img1 in group:
                group_for_img1 = group
            if img2 in group:
                group_for_img2 = group

        if group_for_img1 and group_for_img2:
            # Both images are in groups. If different groups, merge them.
            if group_for_img1 != group_for_img2:
                group_for_img1.extend(g for g in group_for_img2 if g not in group_for_img1)
                groups.remove(group_for_img2)
        elif group_for_img1:
            # Only img1 is in a group, add img2 if not already present
            if img2 not in group_for_img1:
                group_for_img1.append(img2)
        elif group_for_img2:
            # Only img2 is in a group, add img1 if not already present
            if img1 not in group_for_img2:
                group_for_img2.append(img1)
        else:
            # Neither image is in any group, create a new group
            groups.append([img1, img2])

        images_in_groups.add(img1)
        images_in_groups.add(img2)

    # Ensure all images mentioned in pairs are captured, even if some are isolated pairs
    # not merged into larger groups by the logic above (e.g. A-B, C-D)
    # The current logic should handle this, but this is a check.

    # The original `process_similar_pairs` from image_utils.py had a slightly different grouping logic.
    # This revised version aims to create comprehensive groups.
    # Let's refine the grouping logic from image_utils.py to be more robust.

    # Simpler grouping: Iterate through pairs, extend existing groups or start new ones.
    # This is closer to the original logic in image_utils.py's process_similar_pairs

    final_groups = []
    processed_images = set()
    for p_outer in similar_pairs:
        img1_outer = p_outer['image1']
        img2_outer = p_outer['image2']

        if img1_outer in processed_images and img2_outer in processed_images:
            continue

        current_group = set()
        if img1_outer not in processed_images:
            current_group.add(img1_outer)
        if img2_outer not in processed_images:
            current_group.add(img2_outer)

        # Find all images connected to the current_group
        queue = list(current_group)
        head = 0
        while head < len(queue):
            img_to_check = queue[head]
            head += 1
            if img_to_check in processed_images and img_to_check in current_group : # already processed and part of this group
                 pass # continue to avoid adding duplicates from already processed items that are part of this group.

            processed_images.add(img_to_check) # Mark as processed in general
            current_group.add(img_to_check) # Ensure it's in current group

            for p_inner in similar_pairs:
                p_img1, p_img2 = p_inner['image1'], p_inner['image2']
                related_img = None
                if p_img1 == img_to_check and p_img2 not in current_group:
                    related_img = p_img2
                elif p_img2 == img_to_check and p_img1 not in current_group:
                    related_img = p_img1

                if related_img and related_img not in current_group :
                    current_group.add(related_img)
                    if related_img not in queue:
                         queue.append(related_img)

        if current_group: # only add if group is not empty
            # Check if this group is a subset of or overlaps with an existing final_group
            merged = False
            for fg_idx, fg in enumerate(final_groups):
                if not current_group.isdisjoint(fg): # if they overlap
                    final_groups[fg_idx] = list(current_group.union(fg))
                    merged = True
                    break
            if not merged:
                 final_groups.append(list(current_group))

    # Consolidate any groups that might have been merged creating duplicates or subsets
    # This is a simple way to do it, could be more efficient
    if not final_groups: return []

    consolidated_groups = []
    sorted_groups = sorted([sorted(list(g)) for g in final_groups]) # Sort for consistent comparison

    for group_list in sorted_groups:
        is_subset = False
        for cg_idx, cg in enumerate(consolidated_groups):
            if set(group_list).issubset(set(cg)):
                is_subset = True
                break
            if set(cg).issubset(set(group_list)): # current group is superset of an existing one
                consolidated_groups[cg_idx] = group_list # replace
                is_subset = True # Mark as handled
                break
        if not is_subset:
            consolidated_groups.append(group_list)

    return [list(g) for g in consolidated_groups if g] # Return list of lists, ensure no empty groups

def move_duplicate_images_from_groups(groups: List[List[str]], source_dir_str: str, target_dir_str: str) -> int:
    """
    Moves duplicate images to a target directory based on grouped image lists.
    The first image in each group is considered the original and is kept.
    All other images in the group are considered duplicates and moved.

    Args:
        groups: A list of lists, where each inner list contains filenames of similar images.
        source_dir_str: Path string to the directory containing the original images.
        target_dir_str: Path string to the directory where duplicates will be moved.

    Returns:
        The number of images successfully moved.
    """
    source_dir = Path(source_dir_str)
    target_dir = Path(target_dir_str)
    target_dir.mkdir(exist_ok=True)
    moved_count = 0

    if not groups:
        return 0

    for group in groups:
        if not group:  # Skip empty groups
            continue

        # The first image in the sorted group is kept (heuristic, could be based on other criteria)
        # Sorting ensures consistent "original" selection if order varies.
        # However, the grouping logic should ideally preserve an intended original if possible.
        # For now, let's assume the group is just a list of similar images and we keep one.

        # Keep the first image listed in the group, move the rest.
        # Ensure the group is not empty and has more than one image to have duplicates.
        if len(group) > 1:
            # Original is group[0], duplicates are group[1:]
            for img_filename in group[1:]:
                src_path = source_dir / img_filename
                dst_path = target_dir / img_filename

                if src_path.exists():
                    try:
                        # Ensure destination directory for the file exists (if moving to subfolders within target_dir)
                        # For now, moving directly into target_dir.
                        shutil.move(str(src_path), str(dst_path))
                        moved_count += 1
                        current_app.logger.info(f"Moved duplicate image {src_path} to {dst_path}")
                    except Exception as e:
                        current_app.logger.error(f"Error moving image {src_path} to {dst_path}: {e}")
                else:
                    current_app.logger.warning(f"Source image {src_path} not found for moving.")
    return moved_count

# Placeholder for allowed_file, assuming it will be a common utility
# from app.common.utils import allowed_file
def allowed_file(filename, allowed_extensions={'png', 'jpg', 'jpeg'}):
    """Checks if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# The ImageProcessor class itself, or its relevant parts for this blueprint,
# needs to be defined or imported.
# For now, we'll assume its methods like `find_similar_pairs` are available.
# This is a major dependency that needs to be correctly placed.
# Let's assume `ImageProcessor` will be in `app.common.image_processing`
# and its constructor/methods use `current_app.config` for paths.

# Example:
# from app.common.image_processing import ImageProcessor
# def get_image_processor():
#     upload_folder = current_app.config['IMG_DUP_UPLOAD_FOLDER']
#     # Modify ImageProcessor to take necessary paths from config or pass them
#     return ImageProcessor(upload_folder=upload_folder,
#                           thumbnail_folder=current_app.config['THUMBNAIL_FOLDER'])

# This utils.py will primarily hold helper functions specific to image_dedup logic,
# like saving/loading similarity data and processing these lists.
# Core image processing (feature extraction, comparison) should be in a shared class/module.
# The functions `save_similar_pairs` and `load_similar_pairs` in original `image_utils.py`
# are now `save_similar_pairs_to_instance` and `load_similar_pairs_from_instance`.
# The `move_duplicate_images` is now `move_duplicate_images_from_groups`.
# `process_similar_pairs` is now `process_loaded_similar_pairs`.

# The actual `ImageProcessor().find_similar_pairs` call will be in `routes.py`
# and will use an instance of the refactored `ImageProcessor`.
pass
