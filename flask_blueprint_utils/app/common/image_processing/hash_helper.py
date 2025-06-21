import imagehash
from PIL import Image
from typing import Dict # Retained for consistency, though not strictly needed for current return of Dict
import logging

# Using standard logger here; if app context is reliably available, current_app.logger could be used.
logger = logging.getLogger(__name__)

class HashProcessor:
    def compute_feature(self, image_path: str) -> Dict[str, str]: # More specific type hint
        """
        Extracts various hash features from an image.
        Renamed from extract_features for consistency with other processors if they adopt this naming.
        """
        try:
            img = Image.open(image_path)
            # Ensure image is in a suitable mode for hashing if necessary, though most hashes handle common modes.
            # img = img.convert("RGB") # Example: Convert to RGB

            phash_val = str(imagehash.phash(img))
            ahash_val = str(imagehash.average_hash(img))
            dhash_val = str(imagehash.dhash(img))
            # whash_val = str(imagehash.whash(img)) # Example: Wavelet hash, if desired

            return {
                'phash': phash_val,
                'ahash': ahash_val,
                'dhash': dhash_val,
            }
        except FileNotFoundError:
            logger.error(f"HashProcessor: Image file not found at {image_path}")
            return None
        except Exception as e:
            logger.error(f"HashProcessor: Error extracting hash features for {image_path}: {e}", exc_info=True)
            return None

    def compute_similarity(self, feat1: Dict[str, str], feat2: Dict[str, str]) -> float:
        """
        Calculates a weighted similarity score based on multiple hash types' Hamming distances.
        Renamed from calculate_similarity for consistency.
        """
        if feat1 is None or feat2 is None:
            return 0.0

        # Ensure all required hash keys are present
        required_keys = ['phash', 'ahash', 'dhash']
        if not all(key in feat1 and key in feat2 for key in required_keys):
            logger.warning("HashProcessor: Missing one or more hash keys in features for similarity calculation.")
            return 0.0

        # Hamming distance calculation (lower is more similar for raw distance)
        # Similarity = 1 - (normalized Hamming distance)
        # Assuming standard 64-bit hashes from imagehash, so max distance is 64.

        try:
            phash_dist = sum(c1 != c2 for c1, c2 in zip(feat1['phash'], feat2['phash']))
            ahash_dist = sum(c1 != c2 for c1, c2 in zip(feat1['ahash'], feat2['ahash']))
            dhash_dist = sum(c1 != c2 for c1, c2 in zip(feat1['dhash'], feat2['dhash']))

            # Normalize distance to 0-1 range (0 = identical, 1 = completely different)
            # Length of hash string can vary if not fixed (e.g. dhash default is 8 hex chars = 32 bits, phash is 16 hex = 64 bits)
            # For simplicity, assuming imagehash produces comparable length hex strings for these hashes (often 16 hex chars for 64-bit).
            # If hash lengths vary, normalization needs to use actual length.
            # phash, ahash, dhash from imagehash are typically 64-bit.
            max_bits = 64

            phash_sim = 1.0 - (phash_dist / max_bits)
            ahash_sim = 1.0 - (ahash_dist / max_bits)
            dhash_sim = 1.0 - (dhash_dist / max_bits)
        except TypeError as e: # Catch if zip fails or other issues with feature format
            logger.error(f"HashProcessor: Error calculating hash distances, features might be malformed: {e}", exc_info=True)
            return 0.0

        # Weighted average of similarities
        weights = {'phash': 0.5, 'ahash': 0.25, 'dhash': 0.25} # Adjusted weights, phash often most robust

        similarity = (
            weights['phash'] * phash_sim +
            weights['ahash'] * ahash_sim +
            weights['dhash'] * dhash_sim
        )

        return float(similarity)
