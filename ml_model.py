import joblib
import pandas as pd
import os

def get_predictor(model_path="occupancy_model.pkl"):
    """Load model and return a prediction function."""
    model = joblib.load(model_path)
    def predictor(mq135, mq8=None, co2_index=None):
        if mq8 is None:
            mq8 = int(mq135 * 0.45)
        if co2_index is None:
            mq135_baseline = 3000
            mq8_baseline = 1350
            mq135_delta = max(0, mq135_baseline - mq135)
            mq8_delta = max(0, mq8_baseline - mq8)
            co2_index = float((mq135_delta * 0.9) + (mq8_delta * 0.1))
        data = pd.DataFrame([{
            "mq135": mq135,
            "mq8": mq8,
            "co2_index": co2_index
        }])
        prediction = model.predict(data)
        return prediction[0]
    return predictor

# Lazy load default predictor
_predictor = None

def predict_occupancy(mq135, mq8=None, co2_index=None):
    """Predict occupancy using the default model path."""
    global _predictor
    if _predictor is None:
        model_path = os.environ.get("OCCUPANCY_MODEL_PATH", "occupancy_model.pkl")
        _predictor = get_predictor(model_path)
    return _predictor(mq135, mq8, co2_index)
