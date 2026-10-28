
from pathlib import Path
import tensorflow as tf

# Paths to the trained models
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"

detector_path = MODEL_DIR / "wheat_detector.keras"
species_path = MODEL_DIR / "wheat_species.keras"

print("TensorFlow version:", tf.__version__)
print("\nChecking model files...")

for path in (detector_path, species_path):
    if not path.exists():
        raise FileNotFoundError(
            f"Model not found: {path}\n"
            "Copy the downloaded .keras file into backend/models/"
        )
    print(f"Found: {path.name} ({path.stat().st_size / (1024 * 1024):.2f} MB)")

print("\nLoading wheat detector...")
detector = tf.keras.models.load_model(
    detector_path,
    compile=False
)
print("Wheat detector loaded successfully!")
print("Input shape:", detector.input_shape)
print("Output shape:", detector.output_shape)

print("\nLoading wheat species classifier...")
species_model = tf.keras.models.load_model(
    species_path,
    compile=False
)
print("Wheat species classifier loaded successfully!")
print("Input shape:", species_model.input_shape)
print("Output shape:", species_model.output_shape)

print("\nSUCCESS: Both trained models are ready for inference.")
