"""Módulo de resolución de captchas usando ONNX Runtime.

Reemplaza la dependencia de captchapass (TensorFlow) con un modelo ONNX ligero.
"""

from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

# Caracteres válidos del captcha CMF (sin K ni O)
CARACTERES = list("123456789ABCDEFGHIJLMNPQRSTUVWXYZ")

# Vocabulario: [UNK] en índice 0, luego los 33 caracteres, luego tokens internos
# El modelo tiene 38 clases de salida; blank CTC = 37
VOCAB = ["[UNK]"] + CARACTERES
BLANK_INDEX = 37

# Dimensiones de imagen esperadas por el modelo (width x height)
IMG_WIDTH, IMG_HEIGHT = 132, 46

# Cargar modelo ONNX a nivel de módulo
_MODEL_PATH = Path(__file__).parent / "modelo" / "ocr_model.onnx"
_session = ort.InferenceSession(str(_MODEL_PATH))
_INPUT_NAME = _session.get_inputs()[0].name


def preprocess_image(img_path: str | Path) -> np.ndarray:
    """Preprocesa una imagen de captcha para inferencia."""
    img = Image.open(img_path).convert("L")
    img = img.resize((IMG_WIDTH, IMG_HEIGHT), Image.BILINEAR)

    arr = np.array(img, dtype=np.float32) / 255.0
    # Normalizar a [-1, 1] (mismo que (x - 0.5) * 2)
    arr = (arr - 0.5) * 2
    # Transponer (H, W) -> (W, H) y añadir canal -> (W, H, 1)
    arr = arr.T[:, :, np.newaxis]
    # Añadir batch -> (1, W, H, 1)
    return arr[np.newaxis]


def ctc_greedy_decode(pred: np.ndarray) -> str:
    """Decodifica predicciones CTC con greedy search."""
    # pred shape: (timesteps, num_classes)
    indices = np.argmax(pred, axis=-1)

    # Colapsar repetidos y filtrar blanks
    chars = []
    prev = -1
    for idx in indices:
        if idx != prev and idx != BLANK_INDEX:
            if 0 <= idx < len(VOCAB):
                char = VOCAB[idx]
                if char != "[UNK]":
                    chars.append(char)
        prev = idx

    return "".join(chars)


def predict(img_path: str | Path) -> str:
    """Predice el texto de un captcha. Misma API que captchapass.predict."""
    batch = preprocess_image(img_path)
    output = _session.run(None, {_INPUT_NAME: batch})[0]
    return ctc_greedy_decode(output[0])
