import numpy as np
from PIL import Image # Kept for consistency if uncommented parts use it
import logging

# Try to import PyTorch, but make it optional so the app doesn't break if not installed.
try:
    import torch
    import torchvision.transforms as transforms
    from torchvision.models import resnet50, ResNet50_Weights # Or other models
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    # print("PyTorch or torchvision not found. DeepProcessor will use dummy implementations.")

logger = logging.getLogger(__name__)

class DeepProcessor:
    def __init__(self, use_dummy=False):
        self.model = None
        self.transform = None
        self.device = None
        self.use_dummy = use_dummy or not TORCH_AVAILABLE

        if not self.use_dummy:
            try:
                self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                # Using default pre-trained weights
                self.model = resnet50(weights=ResNet50_Weights.DEFAULT)
                self.model = self.model.to(self.device)
                self.model.eval() # Set to evaluation mode

                self.transform = transforms.Compose([
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
                ])
                logger.info(f"DeepProcessor initialized with ResNet50 on {self.device}.")
            except Exception as e:
                logger.error(f"DeepProcessor: Error initializing PyTorch model: {e}. Falling back to dummy implementation.", exc_info=True)
                self.use_dummy = True

        if self.use_dummy:
            logger.warning("DeepProcessor: Using DUMMY implementation as PyTorch is not available or failed to initialize.")


    def compute_feature(self, image_path: str) -> np.ndarray:
        """
        Extracts deep learning features from an image.
        Returns a NumPy array representing the feature vector.
        """
        if self.use_dummy or not self.model:
            # logger.debug(f"DeepProcessor (Dummy): Computing dummy feature for {image_path}")
            return np.random.rand(1000).astype(np.float32) # Dummy feature vector (e.g. ResNet50 output size before FC layer)

        try:
            image = Image.open(image_path).convert('RGB')
            image_tensor = self.transform(image).unsqueeze(0).to(self.device)

            with torch.no_grad():
                features = self.model(image_tensor)
                # features = features.squeeze().cpu().numpy() # Original approach
                # Using flatten after cpu for robustness, ensure it's a 1D array
                features_np = features.cpu().numpy().flatten()
            return features_np
        except FileNotFoundError:
            logger.error(f"DeepProcessor: Image file not found at {image_path}")
            return np.zeros(1000, dtype=np.float32) # Return zero vector on error
        except Exception as e:
            logger.error(f"DeepProcessor: Error extracting deep features for {image_path}: {e}", exc_info=True)
            return np.zeros(1000, dtype=np.float32) # Return zero vector on error

    def compute_similarity(self, feat1: np.ndarray, feat2: np.ndarray) -> float:
        """
        Computes cosine similarity between two feature vectors (NumPy arrays).
        """
        if self.use_dummy:
            # logger.debug("DeepProcessor (Dummy): Computing dummy similarity.")
            # For dummy, return a random similarity or fixed value if features are also dummy
            if np.all(feat1 == 0) or np.all(feat2 == 0): # If one is a zero vector from error
                return 0.0
            # Could return random for testing, but consistent 0.0 for dummy is also fine
            # return np.random.rand()
            # Let's try a simple dot product for dummy random features - not meaningful but consistent
            # Cosine similarity for random vectors will be somewhat random.
            # If dummy features are always the same, similarity will be 1.0.
            # If dummy features are always random, similarity will be random.
            # Let's make dummy similarity slightly more deterministic if features are the dummy random ones.
            # This is mostly for testing the pipeline. A fixed low value might be better.
            # return 0.1 # Fixed low dummy similarity

        if not isinstance(feat1, np.ndarray) or not isinstance(feat2, np.ndarray):
            logger.warning("DeepProcessor: Features for similarity calculation are not numpy arrays.")
            return 0.0
        if feat1.shape != feat2.shape:
            logger.warning(f"DeepProcessor: Feature shapes mismatch for similarity calculation: {feat1.shape} vs {feat2.shape}")
            return 0.0
        if np.all(feat1 == 0) or np.all(feat2 == 0): # Handle zero vectors (e.g. from errors)
            return 0.0

        try:
            # Cosine similarity: (A . B) / (||A|| * ||B||)
            dot_product = np.dot(feat1, feat2)
            norm_feat1 = np.linalg.norm(feat1)
            norm_feat2 = np.linalg.norm(feat2)

            if norm_feat1 == 0 or norm_feat2 == 0: # Avoid division by zero
                return 0.0

            similarity = dot_product / (norm_feat1 * norm_feat2)

            # Clip to [0, 1] as similarity should ideally be positive. Cosine can be [-1, 1].
            # For image features, usually we expect positive similarity.
            return float(max(0, similarity))
        except Exception as e:
            logger.error(f"DeepProcessor: Error calculating deep feature similarity: {e}", exc_info=True)
            return 0.0

# The original file also had `get_image_features` and `find_similar_pairs` methods.
# These are more like orchestrator methods that would belong in the main `ImageProcessor` class,
# which would *use* this `DeepProcessor` for the "deep" method.
# So, those methods are not included here. This class focuses on providing
# `compute_feature` and `compute_similarity` for deep learning features.
