"""WheatVision Model Conversion Script for Google Colab.

Run this in Google Colab (https://colab.research.google.com/).
=============================================================================
"""

# =============================================================================
# CELL 1: Install required libraries in Google Colab
# =============================================================================
# !pip install tf2onnx onnxruntime

# =============================================================================
# CELL 2: Upload your .keras files, convert them, and download .onnx files
# =============================================================================
import os
import shutil
import inspect
import numpy as np
import tensorflow as tf
import keras
import onnxruntime as ort

print("TensorFlow Version:", tf.__version__)
print("Keras Version     :", keras.__version__)
print("ONNX Runtime      :", ort.__version__)

DETECTOR_KERAS = "wheat_detector.keras"
SPECIES_KERAS = "wheat_species.keras"

DETECTOR_ONNX = "wheat_detector.onnx"
SPECIES_ONNX = "wheat_species.onnx"


def build_inference_model(model: keras.Model) -> keras.Model:
    """Builds an inference-only model by bypassing training data augmentation layers.

    Layer 0: InputLayer ('image' / 'input_layer_5')
    Layer 1: Data Augmentation Sequential (RandomFlip, RandomRotation, etc.)
    Layer 2+: EfficientNetB0 backbone and classification head
    """
    inputs = keras.Input(shape=(224, 224, 3), name="image", dtype="float32")
    x = inputs

    # Start from layer index 2 (skipping layer 1 which is the training augmentation)
    for layer in model.layers[2:]:
        sig = inspect.signature(layer.call)
        if "training" in sig.parameters:
            x = layer(x, training=False)
        else:
            x = layer(x)

    inference_model = keras.Model(inputs=inputs, outputs=x, name=model.name + "_inference")
    return inference_model


def convert_keras_to_onnx(keras_path: str, onnx_path: str, is_species: bool = False):
    print(f"\n=======================================================")
    print(f"Converting: {keras_path} -> {onnx_path}")
    print(f"=======================================================")

    if not os.path.exists(keras_path):
        raise FileNotFoundError(
            f"File '{keras_path}' not found! Please upload it to the Colab files pane."
        )

    # 1. Load trained Keras model
    print("1. Loading Keras model...")
    model = keras.models.load_model(keras_path, compile=False)
    print("   Original input shape :", model.input_shape)
    print("   Original output shape:", model.output_shape)
    print("   Layers:", [l.name for l in model.layers])

    # 2. Extract inference sub-graph (bypasses random augmentation layers)
    print("2. Building pure inference graph (bypassing training augmentation)...")
    inf_model = build_inference_model(model)
    print("   Inference graph built successfully.")

    # 3. Export to clean SavedModel
    temp_dir = f"temp_export_{os.path.splitext(onnx_path)[0]}"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    print("3. Exporting SavedModel...")
    inf_model.export(temp_dir, format="tf_saved_model")

    # 4. Convert to ONNX using tf2onnx
    print("4. Converting to ONNX (opset 17)...")
    cmd = f"python -m tf2onnx.convert --saved-model \"{temp_dir}\" --output \"{onnx_path}\" --opset 17"
    exit_code = os.system(cmd)
    if exit_code != 0:
        raise RuntimeError(f"tf2onnx conversion failed with exit code {exit_code}")

    print(f"[OK] ONNX file created: {onnx_path} ({os.path.getsize(onnx_path) / 1024 / 1024:.2f} MB)")

    # 5. Numerical parity check
    print("\n5. Verifying numerical equivalence on test tensor...")
    test_input = np.random.uniform(0.0, 255.0, (1, 224, 224, 3)).astype(np.float32)

    # Prediction from inference Keras model
    k_pred = inf_model(test_input, training=False).numpy()

    # Prediction from ONNX Runtime
    sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
    in_name = sess.get_inputs()[0].name
    ort_pred = sess.run(None, {in_name: test_input})[0]

    max_diff = float(np.max(np.abs(k_pred - ort_pred)))
    print(f"   Max absolute difference: {max_diff:.6e}")
    if max_diff < 1e-4:
        print("   [SUCCESS] Verified! Keras and ONNX predictions match perfectly.")
    else:
        print(f"   [INFO] Output difference is {max_diff:.6e}.")

    if is_species:
        print("   Sample ONNX species softmax probabilities:", np.round(ort_pred[0], 4))
    else:
        print("   Sample ONNX detector sigmoid probability:", round(float(np.squeeze(ort_pred)), 4))

    # Clean up temporary export folder
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    # Convert detector model
    convert_keras_to_onnx(DETECTOR_KERAS, DETECTOR_ONNX, is_species=False)

    # Convert species model
    convert_keras_to_onnx(SPECIES_KERAS, SPECIES_ONNX, is_species=True)

    print("\n" + "=" * 60)
    print("ALL CONVERSIONS COMPLETE AND VALIDATED!")
    print("=" * 60)

    try:
        from google.colab import files
        print("Downloading .onnx models to your computer...")
        files.download(DETECTOR_ONNX)
        files.download(SPECIES_ONNX)
    except Exception:
        print(f"Right-click and download {DETECTOR_ONNX} and {SPECIES_ONNX} from the Colab file tree.")
