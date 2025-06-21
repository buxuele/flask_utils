import json
import os
from pathlib import Path
from flask import current_app

# This utils file will be for helpers specific to the legacy_image_diff module.
# The core ImageProcessor class and its sub-processors (Hash, Hist, Deep)
# will be refactored into app/common/image_processing.py in Step 10.

def get_legacy_similar_pairs_filepath():
    """Returns the path to the similar_pairs.json file for the legacy tool, stored in the instance folder."""
    instance_path = current_app.instance_path
    # Use a distinct name to avoid conflict with the newer image_dedup tool's JSON file
    return os.path.join(instance_path, 'legacy_image_diff_similar_pairs.json')

def save_legacy_similar_pairs(similar_pairs: list):
    """Saves similar image pairs to a JSON file in the instance folder for the legacy tool."""
    filepath = get_legacy_similar_pairs_filepath()
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(similar_pairs, f, ensure_ascii=False, indent=2)
        current_app.logger.info(f"Legacy similar pairs saved to {filepath}")
    except IOError as e:
        current_app.logger.error(f"Error saving legacy similar pairs file to {filepath}: {e}")

def load_legacy_similar_pairs() -> list:
    """Loads similar image pairs from a JSON file in the instance folder for the legacy tool."""
    filepath = get_legacy_similar_pairs_filepath()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            current_app.logger.info(f"Legacy similar pairs loaded from {filepath}")
            return data
    except FileNotFoundError:
        current_app.logger.info(f"Legacy similar pairs file not found at {filepath}. Returning empty list.")
        return []
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error decoding JSON from legacy similar pairs file {filepath}: {e}")
        return []
    except IOError as e:
        current_app.logger.error(f"Error loading legacy similar pairs file from {filepath}: {e}")
        return []

def group_similar_images_for_legacy_display(similar_pairs: list) -> list:
    """
    Groups images based on similarity pairs for display.
    Each group is a list of filenames.
    This logic is taken from the original app.py's show_image_diff_results.
    """
    groups = []
    used_images = set()

    for pair in similar_pairs:
        img1 = pair.get('image1')
        img2 = pair.get('image2')

        if not img1 or not img2: # Skip pairs with missing image names
            current_app.logger.warning(f"Skipping invalid pair in legacy_image_diff: {pair}")
            continue

        # If both images in the pair are already in some group, they might belong to the same conceptual group.
        # This logic tries to merge or extend groups.

        # Check if either image is already part of an existing group
        img1_in_group = None
        img2_in_group = None
        for group_idx, grp in enumerate(groups):
            if img1 in grp:
                img1_in_group = group_idx
            if img2 in grp:
                img2_in_group = group_idx
            if img1_in_group is not None and img2_in_group is not None:
                break # Both found

        if img1_in_group is not None and img2_in_group is not None:
            # Both images are already in groups.
            if img1_in_group != img2_in_group:
                # They are in different groups, merge the second group into the first.
                groups[img1_in_group].extend(g for g in groups[img2_in_group] if g not in groups[img1_in_group])
                groups.pop(img2_in_group) # Remove the merged group
        elif img1_in_group is not None:
            # Only img1 is in a group, add img2 to it if not already present.
            if img2 not in groups[img1_in_group]:
                groups[img1_in_group].append(img2)
        elif img2_in_group is not None:
            # Only img2 is in a group, add img1 to it if not already present.
            if img1 not in groups[img2_in_group]:
                groups[img2_in_group].append(img1)
        else:
            # Neither image is in any group, start a new group with this pair.
            groups.append([img1, img2])

        # The original logic used `used_images` set to prevent processing images multiple times
        # when forming initial groups. The above iterative merging might be an alternative.
        # Let's stick to the original logic for grouping more closely:

    # Reset for original grouping logic:
    groups = []
    used_images_for_grouping = set()

    for pair in similar_pairs:
        img1 = pair.get('image1')
        img2 = pair.get('image2')
        if not img1 or not img2: continue

        if img1 in used_images_for_grouping or img2 in used_images_for_grouping:
            # If one image of the pair is already in a group, try to add the other one to that group.
            # This part is a bit tricky with the original logic. Let's simplify:
            # If an image is already part of ANY group, we assume its connections are captured.
            # The goal is to form distinct sets of connected images.
            continue
            # The original logic was more about finding a starting pair and then expanding.
            # If pair['image1'] in used_images or pair['image2'] in used_images: continue
            # This implies that if one image of a pair is already "used", the pair is skipped.
            # This might lead to some images not being grouped if they appear later.

        # Start a new group with this pair
        current_group = {img1, img2}

        # Iteratively find other images connected to this group
        # This is a simplified connected components approach
        queue = list(current_group)
        head = 0
        while head < len(queue):
            img_to_check = queue[head]
            head += 1
            for other_pair in similar_pairs:
                op_img1 = other_pair.get('image1')
                op_img2 = other_pair.get('image2')
                if not op_img1 or not op_img2: continue

                related_img = None
                if op_img1 == img_to_check and op_img2 not in current_group:
                    related_img = op_img2
                elif op_img2 == img_to_check and op_img1 not in current_group:
                    related_img = op_img1

                if related_img:
                    current_group.add(related_img)
                    if related_img not in queue:
                        queue.append(related_img)

        if current_group:
            groups.append(list(current_group))
            for img_in_group in current_group:
                used_images_for_grouping.add(img_in_group)

    return groups


# The ImageProcessor class from the original `utils/image_processor.py` (which was also used by app.py)
# will be moved to `app/common/image_processing.py`.
# This legacy module will then use that common ImageProcessor.
# Functions like `save_uploaded_files` and `remove_duplicates` (from the old ImageProcessor class)
# will be part of the refactored ImageProcessor or specific utility functions there.
# This `utils.py` is for helpers tied *specifically* to the `legacy_image_diff` blueprint's behavior,
# like its distinct JSON file handling or unique grouping logic if it differs from the new one.

# Placeholder for where uploaded files for this legacy tool will be stored.
# This should be a distinct path from the new image_dedup tool.
# Example: current_app.config['LEGACY_IMAGE_DIFF_UPLOAD_DIR']
# Example: current_app.config['LEGACY_IMAGE_DIFF_THUMBNAIL_DIR']
# Example: current_app.config['LEGACY_IMAGE_DIFF_DUPLICATES_DIR']
# These need to be defined in config.py and directories created.

pass
