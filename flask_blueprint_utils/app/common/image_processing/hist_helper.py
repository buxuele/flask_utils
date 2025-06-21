import cv2
import numpy as np
from typing import Dict # Retained for consistency
import logging

logger = logging.getLogger(__name__)

class HistProcessor:
    def compute_feature(self, image_path: str) -> Dict[str, np.ndarray]: # More specific type hint
        """
        Extracts a color histogram feature from an image using OpenCV.
        Renamed from extract_features for consistency.
        """
        try:
            img = cv2.imread(str(image_path)) # cv2.imread needs string path
            if img is None:
                logger.error(f"HistProcessor: Failed to load image at {image_path}")
                return None

            # Calculate histogram for B, G, R channels
            # Using 8 bins per channel, range [0, 256]
            hist = cv2.calcHist([img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])

            # Normalize the histogram
            cv2.normalize(hist, hist) # In-place normalization

            return {
                'histogram': hist.flatten() # Flatten to a 1D array
            }
        except FileNotFoundError: # Though cv2.imread returns None for not found, this is defensive
            logger.error(f"HistProcessor: Image file not found at {image_path}")
            return None
        except Exception as e:
            logger.error(f"HistProcessor: Error extracting histogram features for {image_path}: {e}", exc_info=True)
            return None

    def compute_similarity(self, feat1: Dict[str, np.ndarray], feat2: Dict[str, np.ndarray]) -> float:
        """
        Calculates similarity between two histogram features using a specified comparison method.
        Renamed from calculate_similarity for consistency.
        """
        if feat1 is None or feat2 is None or 'histogram' not in feat1 or 'histogram' not in feat2:
            logger.warning("HistProcessor: Missing histogram features for similarity calculation.")
            return 0.0

        hist1 = feat1['histogram']
        hist2 = feat2['histogram']

        # Ensure histograms are suitable for comparison (e.g., float32)
        if not isinstance(hist1, np.ndarray) or not isinstance(hist2, np.ndarray):
            logger.warning("HistProcessor: Histogram features are not numpy arrays.")
            return 0.0

        if hist1.dtype != np.float32:
            hist1 = hist1.astype(np.float32)
        if hist2.dtype != np.float32:
            hist2 = hist2.astype(np.float32)

        try:
            # OpenCV's compareHist offers several methods:
            # - cv2.HISTCMP_CORREL: Correlation (higher is more similar, range -1 to 1, often 0 to 1 for positive correlations)
            # - cv2.HISTCMP_CHISQR: Chi-Square (lower is more similar, 0 for identical)
            # - cv2.HISTCMP_INTERSECT: Intersection (higher is more similar, sum of min values at each bin)
            # - cv2.HISTCMP_BHATTACHARYYA: Bhattacharyya distance (lower is more similar, 0 for identical)

            # Correlation is a good general choice, as used in original.
            similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

            # Ensure similarity is within a typical range [0, 1] if needed, though CORREL can be -1 to 1.
            # If it's [-1, 1], you might want to normalize it: (similarity + 1) / 2
            # For positive correlations (common with images), it's often [0,1]
            if similarity < 0: # If negative correlation is possible and undesirable as "similarity"
                similarity = 0.0

            return float(similarity)
        except Exception as e:
            logger.error(f"HistProcessor: Error calculating histogram similarity: {e}", exc_info=True)
            return 0.0
