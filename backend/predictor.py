"""WheatVision ONNX Inference Engine.

Handles ONNX Runtime session management, verified 224x224 RGB image
preprocessing, two-stage inference (detector threshold 0.77, species threshold 0.93),
and model-unavailable handling.
"""
import io
import os
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import numpy as np
from PIL import Image

try:
    import onnxruntime as ort
except ImportError:
    ort = None

logger = logging.getLogger("wheatvision.predictor")

BASE_DIR = Path(__file__).resolve().parent

# Exact 4-class species mapping
SPECIES_CLASSES = [
    {
        "index": 0,
        "key": "aestivum",
        "common_name": "Common Wheat / Bread Wheat",
        "scientific_name": "Triticum aestivum"
    },
    {
        "index": 1,
        "key": "durum",
        "common_name": "Durum Wheat / Pasta Wheat",
        "scientific_name": "Triticum durum"
    },
    {
        "index": 2,
        "key": "dicoccum",
        "common_name": "Emmer Wheat / Farro Medio",
        "scientific_name": "Triticum dicoccum"
    },
    {
        "index": 3,
        "key": "polonicum",
        "common_name": "Polish Wheat",
        "scientific_name": "Triticum polonicum"
    }
]


class WheatPredictor:
    """Singleton inference manager for wheat detection and species classification."""

    def __init__(self,
                 detector_path: Optional[str] = None,
                 species_path: Optional[str] = None,
                 wheat_threshold: float = 0.77,
                 species_threshold: float = 0.93):
        self.detector_path = self._resolve_path(detector_path or "models/wheat_detector.onnx")
        self.species_path = self._resolve_path(species_path or "models/wheat_species.onnx")
        self.wheat_threshold = float(wheat_threshold)
        self.species_threshold = float(species_threshold)

        self.detector_session = None
        self.species_session = None
        self.is_available = False
        self.load_error = None

        self._initialize_sessions()

    def _resolve_path(self, path_str: str) -> Path:
        p = Path(path_str)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()

    def _initialize_sessions(self):
        """Load ONNX Runtime sessions once if valid .onnx files exist."""
        if ort is None:
            self.load_error = "onnxruntime is not installed in the environment."
            self.is_available = False
            logger.warning(self.load_error)
            return

        if not self.detector_path.is_file():
            self.load_error = f"Detector ONNX model not found at {self.detector_path}"
            self.is_available = False
            logger.info("ONNX detector model is not yet available; inference routes will return 503.")
            return

        if not self.species_path.is_file():
            self.load_error = f"Species ONNX model not found at {self.species_path}"
            self.is_available = False
            logger.info("ONNX species model is not yet available; inference routes will return 503.")
            return

        try:
            # CPUExecutionProvider is universally supported on Windows
            providers = ["CPUExecutionProvider"]
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            logger.info(f"Loading detector ONNX session from {self.detector_path}")
            self.detector_session = ort.InferenceSession(
                str(self.detector_path),
                sess_options=sess_options,
                providers=providers
            )

            logger.info(f"Loading species ONNX session from {self.species_path}")
            self.species_session = ort.InferenceSession(
                str(self.species_path),
                sess_options=sess_options,
                providers=providers
            )

            self.is_available = True
            self.load_error = None
            logger.info("Both ONNX models loaded successfully and are ready for inference.")

        except Exception as e:
            self.load_error = f"Failed to load ONNX models: {str(e)}"
            self.is_available = False
            logger.error(self.load_error)

    def preprocess_image(self, image_input) -> np.ndarray:
        """Preprocesses an image to 224x224 RGB float32 for EfficientNetB0.

        Note: EfficientNetB0 architecture includes internal Rescaling and
        Normalization layers, so raw pixel intensities [0.0, 255.0] must be preserved.
        """
        if isinstance(image_input, (bytes, bytearray)):
            image = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, Image.Image):
            image = image_input
        else:
            raise ValueError("Unsupported image input type; expected bytes or PIL.Image")

        # Convert to standard RGB (handles grayscale, RGBA, CMYK safely)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Resize to 224x224 using high-quality bilinear interpolation
        image = image.resize((224, 224), Image.Resampling.BILINEAR)

        # Convert to float32 NumPy array with shape (1, 224, 224, 3) in [0.0, 255.0]
        img_array = np.array(image, dtype=np.float32)
        tensor = np.expand_dims(img_array, axis=0)

        return tensor

    def predict(self, image_input) -> Dict[str, Any]:
        """Runs the two-stage classification pipeline on an input image.

        Stage 1: Wheat Detector (binary sigmoid, threshold 0.77).
        Stage 2: Species Classifier (4-class softmax, threshold 0.93).
        """
        if not self.is_available:
            return {
                "success": False,
                "status": "model_unavailable",
                "error": "Trained ONNX models are not yet deployed. Please convert the .keras models in Google Colab and place the .onnx files in backend/models/.",
                "details": self.load_error
            }

        try:
            tensor = self.preprocess_image(image_input)

            # -------------------------------------------------------------
            # Stage 1: Wheat Detection
            # -------------------------------------------------------------
            det_input_name = self.detector_session.get_inputs()[0].name
            det_outputs = self.detector_session.run(None, {det_input_name: tensor})
            raw_prob = det_outputs[0]
            detector_score = float(np.squeeze(raw_prob))

            # Evaluate detector score against 0.77 threshold
            if detector_score < 0.50:
                # Confidently not wheat
                return {
                    "success": True,
                    "status": "non_wheat",
                    "is_wheat": False,
                    "detector_confidence": round(1.0 - detector_score, 4),
                    "detector_raw_score": round(detector_score, 4),
                    "message": "The uploaded image does not appear to contain wheat grains.",
                    "species_analysis": None
                }
            elif detector_score < self.wheat_threshold:
                # Uncertain if wheat (0.50 <= score < 0.77)
                return {
                    "success": True,
                    "status": "uncertain_wheat",
                    "is_wheat": False,
                    "detector_confidence": round(detector_score, 4),
                    "detector_raw_score": round(detector_score, 4),
                    "threshold_applied": self.wheat_threshold,
                    "message": f"Detection confidence ({round(detector_score * 100, 2)}%) is below the {int(self.wheat_threshold * 100)}% verification threshold.",
                    "species_analysis": None
                }

            # -------------------------------------------------------------
            # Stage 2: Species Identification
            # -------------------------------------------------------------
            spec_input_name = self.species_session.get_inputs()[0].name
            spec_outputs = self.species_session.run(None, {spec_input_name: tensor})
            raw_probs = np.squeeze(spec_outputs[0])

            # Build probability map for all 4 species
            all_classes = []
            for spec in SPECIES_CLASSES:
                idx = spec["index"]
                conf = float(raw_probs[idx])
                all_classes.append({
                    "key": spec["key"],
                    "scientific_name": spec["scientific_name"],
                    "common_name": spec["common_name"],
                    "confidence": round(conf, 4)
                })

            top_idx = int(np.argmax(raw_probs))
            top_conf = float(raw_probs[top_idx])
            top_species = SPECIES_CLASSES[top_idx]

            is_confident = top_conf >= self.species_threshold

            return {
                "success": True,
                "status": "wheat_detected" if is_confident else "uncertain_species",
                "is_wheat": True,
                "detector_confidence": round(detector_score, 4),
                "predicted_species": top_species["key"],
                "scientific_name": top_species["scientific_name"],
                "common_name": top_species["common_name"],
                "species_confidence": round(top_conf, 4),
                "is_confident_species": is_confident,
                "species_threshold_applied": self.species_threshold,
                "all_species_probabilities": all_classes,
                "message": (
                    f"Identified as {top_species['scientific_name']} with {round(top_conf * 100, 2)}% confidence."
                    if is_confident else
                    f"Species prediction ({top_species['scientific_name']}) confidence ({round(top_conf * 100, 2)}%) is below the {int(self.species_threshold * 100)}% threshold."
                )
            }

        except Exception as e:
            logger.error(f"Inference error: {e}", exc_info=True)
            return {
                "success": False,
                "status": "inference_error",
                "error": "An error occurred while analyzing the image."
            }


# Global singleton predictor instance
_predictor = None


def get_predictor(app=None) -> WheatPredictor:
    """Retrieve or initialize the global WheatPredictor instance."""
    global _predictor
    if _predictor is None:
        if app:
            _predictor = WheatPredictor(
                detector_path=app.config.get("DETECTOR_MODEL_PATH"),
                species_path=app.config.get("SPECIES_MODEL_PATH"),
                wheat_threshold=app.config.get("WHEAT_THRESHOLD", 0.77),
                species_threshold=app.config.get("SPECIES_THRESHOLD", 0.93)
            )
        else:
            _predictor = WheatPredictor()
    return _predictor
