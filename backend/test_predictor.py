"""WheatVision Phase 4 Predictor Test Suite.

Verifies:
1. Predictor initialization without TensorFlow.
2. Graceful model-unavailable handling when .onnx models are not yet deployed.
3. Preprocessing image pipeline (224x224 RGB, float32, [0, 255] value preservation).
4. Thresholds and exact 4-class species mapping.
"""
import sys
import io
import numpy as np
from PIL import Image
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from predictor import WheatPredictor, SPECIES_CLASSES


def test_missing_onnx_handling():
    """Verify that absent ONNX files do not crash the engine and report model_unavailable."""
    predictor = WheatPredictor(
        detector_path="models/nonexistent_detector.onnx",
        species_path="models/nonexistent_species.onnx"
    )
    assert not predictor.is_available, "Predictor should not be available when models are missing"
    assert predictor.load_error is not None

    # Dummy image bytes
    img = Image.new("RGB", (300, 300), color=(128, 128, 128))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format="JPEG")

    result = predictor.predict(img_byte_arr.getvalue())
    assert result["success"] is False
    assert result["status"] == "model_unavailable"
    assert "not yet deployed" in result["error"]
    print("[PASS] Missing ONNX files handled safely with status 'model_unavailable'.")


def test_image_preprocessing():
    """Verify image preprocessing retains raw pixel scale [0, 255], 224x224, and RGB channels."""
    predictor = WheatPredictor(
        detector_path="models/wheat_detector.onnx",
        species_path="models/wheat_species.onnx"
    )

    # Test RGBA image to RGB conversion
    rgba_img = Image.new("RGBA", (500, 400), color=(200, 150, 100, 255))
    tensor = predictor.preprocess_image(rgba_img)

    assert tensor.shape == (1, 224, 224, 3), f"Expected shape (1, 224, 224, 3), got {tensor.shape}"
    assert tensor.dtype == np.float32, f"Expected float32, got {tensor.dtype}"
    # Ensure values were not divided by 255
    assert np.max(tensor) > 1.0, f"Pixel values unexpectedly divided by 255: max={np.max(tensor)}"
    print("[PASS] Image preprocessing preserves RGB shape (1, 224, 224, 3) and raw [0, 255] float32 scale.")


def test_species_mapping_and_thresholds():
    """Verify the exact species classes and configured thresholds."""
    expected_species = [
        (0, "aestivum", "Triticum aestivum"),
        (1, "durum", "Triticum durum"),
        (2, "dicoccum", "Triticum dicoccum"),
        (3, "polonicum", "Triticum polonicum")
    ]

    assert len(SPECIES_CLASSES) == 4, "Must have exactly 4 species classes"
    for idx, key, scientific in expected_species:
        entry = SPECIES_CLASSES[idx]
        assert entry["key"] == key, f"Expected key {key}, got {entry['key']}"
        assert entry["scientific_name"] == scientific, f"Expected {scientific}, got {entry['scientific_name']}"

    predictor = WheatPredictor(wheat_threshold=0.77, species_threshold=0.93)
    assert predictor.wheat_threshold == 0.77
    assert predictor.species_threshold == 0.93
    print("[PASS] Species mapping and decision thresholds (0.77 / 0.93) verified.")


if __name__ == "__main__":
    print("\n=== Running WheatVision Phase 4 Predictor Tests ===")
    test_missing_onnx_handling()
    test_image_preprocessing()
    test_species_mapping_and_thresholds()
    print("\nALL PHASE 4 PREDICTOR TESTS PASSED!\n")
