import os
import sqlite3
import json
import pytest
from unittest.mock import MagicMock, patch

# TEST DATA
TEST_DB = "test_building.db"
TEST_DATASET = "dataset.csv"
TEST_MODEL_PATH = "test_occupancy_model.pkl"

@pytest.fixture(autouse=True)
def cleanup():
    """Clean up test database and model files after tests."""
    yield
    for path in [TEST_DB, TEST_MODEL_PATH]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

def test_init_db():
    """Verify that init_db function creates database and table structure."""
    from init_db import init_db_file
    
    # Initialize the database file
    init_db_file(TEST_DB)
    
    assert os.path.exists(TEST_DB)
    
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lab_readings'")
    table = cursor.fetchone()
    assert table is not None
    assert table[0] == 'lab_readings'
    conn.close()

def test_train_model():
    """Verify RandomForest model training and serialization."""
    from train_model import train_model_file
    
    train_model_file(TEST_DATASET, TEST_MODEL_PATH)
    assert os.path.exists(TEST_MODEL_PATH)

def test_ml_model():
    """Verify prediction logic of trained model."""
    from train_model import train_model_file
    from ml_model import get_predictor, predict_occupancy
    
    # Train test model if not exists
    if not os.path.exists(TEST_MODEL_PATH):
        train_model_file(TEST_DATASET, TEST_MODEL_PATH)
        
    predictor = get_predictor(TEST_MODEL_PATH)
    
    # Test raw 2350 -> OCUPADO (occupied range in real dataset)
    pred_high = predictor(2350, 1057, 580.0)
    assert pred_high == "OCUPADO"
    
    # Test raw 3000 -> VACIO (empty range in real dataset)
    pred_low = predictor(3000, 1350, 0.0)
    assert pred_low == "VACIO"

    # Test prediction with default None arguments
    pred_none = predictor(3000)
    assert pred_none == "VACIO"

    # Test predict_occupancy function directly
    with patch.dict(os.environ, {"OCCUPANCY_MODEL_PATH": TEST_MODEL_PATH}):
        import ml_model
        ml_model._predictor = None
        p = predict_occupancy(2350)
        assert p == "OCUPADO"


def test_app_routes():
    """Verify Flask routes /, /history, /translations, and /latest_readings."""
    # Mock databases and models during flask app setup
    with patch("sqlite3.connect") as mock_connect, \
         patch("joblib.load") as mock_load, \
         patch("paho.mqtt.client.Client") as mock_mqtt_client:
         
        # Mock ML Model prediction
        mock_model = MagicMock()
        mock_model.predict.return_value = ["VACIO"]
        mock_load.return_value = mock_model
        
        # Mock database cursor fetch
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("2026-05-25 12:00:00", 120.0, 700, 315, "VACIO"),
            ("2026-05-25 12:05:00", 450.0, 600, 300, "PARCIAL")
        ]
        mock_cursor.fetchone.return_value = (120.0, 700, 315, "VACIO", "2026-05-25 12:00:00")
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        from app import app
        app.config["TESTING"] = True
        
        with app.test_client() as client:
            # Test Root Dashboard
            resp_index = client.get("/")
            assert resp_index.status_code == 200
            
            # Test History route
            resp_history = client.get("/history")
            assert resp_history.status_code == 200
            assert b"LAB1" in resp_history.data
            assert b"LAB2" in resp_history.data
            
            # Test Translations API
            resp_trans = client.get("/translations")
            assert resp_trans.status_code == 200
            data = json.loads(resp_trans.data.decode("utf-8"))
            assert "dashboard_title" in data["en"]
            assert "dashboard_title" in data["es"]

            # Test Latest Readings endpoint
            resp_latest = client.get("/latest_readings")
            assert resp_latest.status_code == 200
            latest_data = json.loads(resp_latest.data.decode("utf-8"))
            assert "LAB1" in latest_data
            assert latest_data["LAB1"]["estado"] == "VACIO"

def test_app_mqtt_handler():
    """Verify MQTT message callback parses topic and updates dashboard."""
    with patch("sqlite3.connect") as mock_connect, \
         patch("joblib.load") as mock_load, \
         patch("paho.mqtt.client.Client") as mock_mqtt, \
         patch("flask_socketio.SocketIO.emit") as mock_emit:
         
        mock_model = MagicMock()
        mock_model.predict.return_value = ["OCUPADO"]
        mock_load.return_value = mock_model
        
        # Reset predictor cache
        import ml_model
        ml_model._predictor = None
        
        from app import handle_mqtt_message
        
        # Simulating message to salon/LAB3/gases
        msg = MagicMock()
        msg.topic = "salon/LAB3/gases"
        msg.payload = json.dumps({
            "mq135": 1700,
            "mq8": 800,
            "co2_index": 750.0
        }).encode("utf-8")
        
        handle_mqtt_message(msg)
        
        # Verify db insert query was executed for LAB3
        mock_connect.assert_called()
        conn = mock_connect.return_value
        cursor = conn.cursor.return_value
        cursor.execute.assert_called()
        
        # Verify socket.io emission with predicted state and room
        mock_emit.assert_called_with("new_data", {
            "lab": "LAB3",
            "estado": "OCUPADO",
            "co2": 750.0,
            "mq135": 1700,
            "mq8": 800
        })

def test_init_db_script():
    """Verify executing init_db.py as a script."""
    import subprocess
    res = subprocess.run(["python", "init_db.py", TEST_DB], capture_output=True, text=True)
    assert res.returncode == 0
    assert os.path.exists(TEST_DB)

def test_train_model_script():
    """Verify executing train_model.py as a script."""
    import subprocess
    res = subprocess.run(["python", "train_model.py", TEST_DATASET, TEST_MODEL_PATH], capture_output=True, text=True)
    assert res.returncode == 0
    assert os.path.exists(TEST_MODEL_PATH)

def test_build_dataset():
    """Verify build_dataset compiles JSON lines to CSV."""
    import pandas as pd
    from train_model import build_dataset
    
    # Create temp JSON files
    n_temp = "test_normal.json"
    r_temp = "test_noise.json"
    csv_temp = "test_dataset_temp.csv"
    
    with open(n_temp, "w") as f:
        f.write('{"t_ms":1000,"raw":900,"v":1.0}\n')
    with open(r_temp, "w") as f:
        f.write('{"t_ms":1000,"raw":2300,"v":2.0}\n')
        
    build_dataset(n_temp, r_temp, csv_temp)
    
    assert os.path.exists(csv_temp)
    df = pd.read_csv(csv_temp)
    assert len(df) == 2
    assert df.iloc[0]["mq135"] == 900
    assert df.iloc[0]["estado"] == "VACIO"
    assert df.iloc[1]["mq135"] == 2300
    assert df.iloc[1]["estado"] == "OCUPADO"
    
    # Cleanup
    for p in [n_temp, r_temp, csv_temp]:
        if os.path.exists(p):
            os.remove(p)

def test_train_model_script_json():
    """Verify executing train_model.py with JSON path arguments."""
    import subprocess
    
    n_temp = "test_normal.json"
    r_temp = "test_noise.json"
    csv_temp = "test_dataset_temp.csv"
    model_temp = "test_model_temp.pkl"
    
    with open(n_temp, "w") as f:
        f.write('{"t_ms":1000,"raw":900,"v":1.0}\n')
        f.write('{"t_ms":2000,"raw":910,"v":1.0}\n')
        f.write('{"t_ms":3000,"raw":920,"v":1.0}\n')
    with open(r_temp, "w") as f:
        f.write('{"t_ms":1000,"raw":2300,"v":2.0}\n')
        f.write('{"t_ms":2000,"raw":2310,"v":2.0}\n')
        f.write('{"t_ms":3000,"raw":2320,"v":2.0}\n')
        
    res = subprocess.run([
        "python", "train_model.py", 
        n_temp, r_temp, csv_temp, model_temp
    ], capture_output=True, text=True)
    
    assert res.returncode == 0
    assert os.path.exists(model_temp)
    
    # Cleanup
    for p in [n_temp, r_temp, csv_temp, model_temp]:
        if os.path.exists(p):
            os.remove(p)

def test_esp32_simulator():
    """Verify ESP32 simulator loads data and behaves correctly."""
    from unittest.mock import patch, MagicMock
    import esp32_simulator
    
    # 1. Test load_dataset with valid and invalid paths
    dataset = esp32_simulator.load_dataset("datosMq135N.json")
    assert len(dataset) > 0
    invalid_dataset = esp32_simulator.load_dataset("non_existent.json")
    assert len(invalid_dataset) == 0
    
    # 2. Test main dataset failure path
    with patch("esp32_simulator.load_dataset", return_value=[]):
        esp32_simulator.main()
        
    # 3. Test main execution mock with transient connection failure and KeyboardInterrupt
    mock_mqtt = MagicMock()
    mock_mqtt.connect.side_effect = [Exception("Conn error"), None]
    
    sleep_calls = []
    def mock_sleep_handler(secs):
        sleep_calls.append(secs)
        if secs == 5:
            raise KeyboardInterrupt()
            
    with patch("paho.mqtt.client.Client", return_value=mock_mqtt), \
         patch("time.sleep", side_effect=mock_sleep_handler):
         
        esp32_simulator.main()
        
        assert mock_mqtt.connect.call_count == 2
        assert mock_mqtt.publish.call_count == 1
        assert 3 in sleep_calls





