import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import sqlite3
import paho.mqtt.client as mqtt
import json
import os
from ml_model import predict_occupancy


app = Flask(__name__)
# Enable CORS for security in different browser ports if needed
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
DB_PATH = os.environ.get("DB_PATH", "building.db")
MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))

# Route to fetch translations file
@app.route("/translations")
def translations():
    """Load and return translations JSON."""
    try:
        with open("translations.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        print(f"ERROR: Failed loading translations - {e}")
        return jsonify({"error": "Failed loading translations"}), 500

@app.route("/latest_readings")
def latest_readings():
    """Fetch the latest reading for each classroom from the database."""
    labs = ["LAB1", "LAB2", "LAB3", "LAB4"]
    result = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for lab in labs:
            cursor.execute("""
                SELECT co2_index, mq135, mq8, estado, timestamp
                FROM lab_readings
                WHERE lab = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (lab,))
            row = cursor.fetchone()
            if row:
                result[lab] = {
                    "co2": row[0],
                    "mq135": row[1],
                    "mq8": row[2],
                    "estado": row[3],
                    "timestamp": row[4]
                }
        conn.close()
    except Exception as e:
        print(f"ERROR: Failed fetching latest readings - {e}")
    return jsonify(result)

@app.route("/")
def index():
    """Render main interactive dashboard."""
    return render_template("index.html")

@app.route("/history")
def history():
    """Render readings history grouped per room."""
    labs = ["LAB1", "LAB2", "LAB3", "LAB4"]
    per_lab = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        for lab in labs:
            cursor.execute("""
                SELECT timestamp, co2_index, mq135, mq8, estado
                FROM lab_readings
                WHERE lab = ?
                ORDER BY timestamp DESC
                LIMIT 25
            """, (lab,))
            per_lab[lab] = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"ERROR: Database fetch failed - {e}")
        for lab in labs:
            per_lab[lab] = []
    return render_template("history.html", per_lab=per_lab)

def handle_mqtt_message(msg):
    """Callback when an MQTT message is received on salon/+/gases."""
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        mq135 = int(payload.get("mq135", 0))
        mq8 = int(payload.get("mq8", 0))
        co2_index = float(payload.get("co2_index", 0.0))
        
        # Parse topic: salon/<LAB_ID>/gases
        topic_parts = msg.topic.split("/")
        lab_name = topic_parts[1] if len(topic_parts) >= 2 else "UNKNOWN"
        
        # Predict occupancy using mq135, mq8, and co2_index
        estado = predict_occupancy(mq135, mq8, co2_index)
        
        # Save to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO lab_readings (lab, co2_index, mq135, mq8, estado)
            VALUES (?, ?, ?, ?, ?)
        """, (lab_name, co2_index, mq135, mq8, estado))
        conn.commit()
        conn.close()
        
        # SocketIO emit real-time updates
        socketio.emit("new_data", {
            "lab": lab_name,
            "estado": estado,
            "co2": co2_index,
            "mq135": mq135,
            "mq8": mq8
        })
    except Exception as e:
        print(f"ERROR: Failed handling MQTT message - {e}")


# MQTT Client Setup
def on_message(client, userdata, msg):
    handle_mqtt_message(msg)

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqtt_client.subscribe("salon/+/gases")
    mqtt_client.loop_start()
except Exception as e:
    print(f"ERROR: Could not connect to MQTT broker at {MQTT_BROKER}:{MQTT_PORT} - {e}")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
