import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib
import json
import os
import sys

def build_dataset(normal_path="datosMq135N.json", noise_path="datosMq135R.json", out_path="dataset.csv"):
    """Parse real MQ135 json data files and output dataset.csv."""
    records = []
    
    mq135_baseline = 3000
    mq8_baseline = 1350
    
    def process_raw(raw_val, estado):
        mq8_raw = int(raw_val * 0.45)
        mq135_delta = max(0, mq135_baseline - raw_val)
        mq8_delta = max(0, mq8_baseline - mq8_raw)
        co2 = float((mq135_delta * 0.9) + (mq8_delta * 0.1))
        return {
            "mq135": raw_val,
            "mq8": mq8_raw,
            "co2_index": co2,
            "estado": estado
        }

    # Load normal (VACIO) dataset
    if os.path.exists(normal_path):
        with open(normal_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    records.append(process_raw(int(data["raw"]), "VACIO"))
                except Exception:
                    pass
                    
    # Load noise (OCUPADO) dataset
    if os.path.exists(noise_path):
        with open(noise_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    records.append(process_raw(int(data["raw"]), "OCUPADO"))
                except Exception:
                    pass
                    
    if not records:
        print("WARNING: Real data files not found. Using default mock values.")
        records = [
            {"mq135": 800, "mq8": 360, "co2_index": 200.0, "estado": "VACIO"},
            {"mq135": 1800, "mq8": 810, "co2_index": 500.0, "estado": "OCUPADO"}
        ]
        
    df = pd.DataFrame(records)
    df.to_csv(out_path, index=False)
    print(f"Dataset generated at {out_path} with {len(df)} records")

def train_model_file(dataset_path="dataset.csv", model_path="occupancy_model.pkl"):
    """Load dataset, train RandomForestClassifier, and save model file."""
    df = pd.read_csv(dataset_path)
    X = df[["mq135", "mq8", "co2_index"]]
    y = df["estado"]
    
    # Train the Random Forest model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Evaluate model
    if len(df) >= 5:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        test_model = RandomForestClassifier(n_estimators=100, random_state=42)
        test_model.fit(X_train, y_train)
        predictions = test_model.predict(X_test)
        print(classification_report(y_test, predictions, zero_division=0))
        
    joblib.dump(model, model_path)
    print(f"Modelo guardado en {model_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].endswith(".csv"):
        # Train directly from CSV
        d_path = sys.argv[1]
        m_path = sys.argv[2] if len(sys.argv) > 2 else "occupancy_model.pkl"
        train_model_file(d_path, m_path)
    else:
        # Build dataset from JSON files first
        n_path = "datosMq135N.json"
        r_path = "datosMq135R.json"
        d_path = "dataset.csv"
        m_path = "occupancy_model.pkl"
        
        if len(sys.argv) > 1:
            n_path = sys.argv[1]
        if len(sys.argv) > 2:
            r_path = sys.argv[2]
        if len(sys.argv) > 3:
            d_path = sys.argv[3]
        if len(sys.argv) > 4:
            m_path = sys.argv[4]
            
        build_dataset(n_path, r_path, d_path)
        train_model_file(d_path, m_path)
