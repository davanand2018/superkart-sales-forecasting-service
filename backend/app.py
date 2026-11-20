"""SuperKart sales forecasting API (Flask)."""
import joblib
import pandas as pd
from flask import Flask, jsonify, request

MODEL_PATH = "superkart_model.joblib"
FEATURES = [
    "Product_Weight", "Product_Sugar_Content", "Product_Allocated_Area", "Product_MRP",
    "Store_Size", "Store_Location_City_Type", "Store_Type",
    "Product_Id_char", "Store_Age_Years", "Product_Type_Category",
]
NUMERIC_FEATURES = ["Product_Weight", "Product_Allocated_Area", "Product_MRP", "Store_Age_Years"]

superkart_api = Flask("SuperKart Sales Forecasting API")
superkart_api.json.sort_keys = False  # keep batch predictions in row order

# Load the trained pipeline (preprocessing + model) once, when the worker starts
model = joblib.load(MODEL_PATH)


def build_feature_frame(records):
    """Validate the incoming records and return them as a DataFrame in the training column order."""
    frame = pd.DataFrame(records)
    missing = [col for col in FEATURES if col not in frame.columns]
    if missing:
        raise ValueError(f"Missing required feature(s): {missing}")
    frame = frame[FEATURES].copy()
    for col in NUMERIC_FEATURES:
        frame[col] = pd.to_numeric(frame[col], errors="raise")
    return frame


@superkart_api.get("/")
def home():
    return "Welcome to the SuperKart Sales Forecasting API. POST product data to /v1/predict or a CSV to /v1/predictbatch."


@superkart_api.get("/health")
def health():
    return jsonify(status="ok", model=type(model.named_steps["regressor"]).__name__)


@superkart_api.post("/v1/predict")
def predict_sales():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="The request body must be a JSON object with the product and store features."), 400
    try:
        features = build_feature_frame([payload])
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400
    prediction = float(model.predict(features)[0])
    return jsonify({"Predicted_Sales": round(prediction, 2)})


@superkart_api.post("/v1/predictbatch")
def predict_sales_batch():
    uploaded_file = request.files.get("file")
    if uploaded_file is None:
        return jsonify(error="Upload a CSV file in the 'file' form field."), 400
    try:
        features = build_feature_frame(pd.read_csv(uploaded_file))
    except (ValueError, TypeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        return jsonify(error=str(exc)), 400
    predictions = model.predict(features)
    return jsonify({str(idx): round(float(pred), 2) for idx, pred in enumerate(predictions)})


if __name__ == "__main__":
    # Local debugging only; in the container the app is served by Gunicorn (see Dockerfile)
    superkart_api.run(host="0.0.0.0", port=7860)
