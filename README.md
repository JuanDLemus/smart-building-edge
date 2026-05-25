# Smart Building Edge - Floor B Blueprint & Occupancy Predictor

An Edge Computing system designed to monitor and predict classroom occupancy in real-time. The system processes gas sensor readings (MQ-135 and MQ-8) using a Random Forest machine learning model on the edge, presenting insights on an interactive building floor blueprint dashboard with instant hover details and localization support.

## System Architecture

```
                                  +-----------------------+
                                  |    ESP32 Simulators   | (Publish sensor readings
                                  |  (LAB 1, 2, 3, & 4)   |  to MQTT broker)
                                  +-----------+-----------+
                                              |
                                              | MQTT publish: salon/<LAB>/gases
                                              v
                                  +-----------------------+
                                  |      MQTT Broker      | (eclipse-mosquitto)
                                  +-----------+-----------+
                                              |
                                              | MQTT subscribe
                                              v
+------------------+              +-----------+-----------+              +-------------------+
|   SQLite DB      | <----------> |     Flask Server      | <----------> |   Web Dashboard   |
|  (building.db)   |              |  (Random Forest ML)   | (Socket.IO)  | (Sabana Blue UI)  |
+------------------+              +-----------------------+              +-------------------+
```

- **ESP32 Simulators / MCU Core**: Publishes simulated real-time data (`mq135` raw, `mq8` raw, calculated `co2_index`) from classrooms to the MQTT broker.
- **MQTT Broker**: Handles message distribution using topic boundaries: `salon/<LAB_ID>/gases`.
- **Flask Server**: Listens for sensor readings, applies a local pre-trained Random Forest model (`occupancy_model.pkl`) to classify the state (`VACIO`, `PARCIAL`, or `OCUPADO`), writes to SQLite database, and pushes live updates using Flask-SocketIO.
- **Web Dashboard**: An interactive, modern, light-themed vector blueprint representing the floor plan of Building B (including Oficina, Entrada Principal, Corridor, and 4 Labs: Automatización, Procesos, Lux, Física). Features a per-room historical readings visualization page with live-generated CO₂ trend sparklines.

---

## Directory Structure

```
smart-building-edge/
├── app.py                # Main Flask & Socket.IO server, listens to MQTT messages
├── init_db.py            # SQLite database schema initializer
├── ml_model.py           # Machine learning predictor module
├── train_model.py        # Dataset compiler & model training script
├── requirements.txt      # Python dependencies
├── dataset.csv           # Model training dataset compiled from logs
├── occupancy_model.pkl   # Serialized Random Forest model binary
├── building.db           # SQLite database storing readings history
├── esp32_simulator.py    # Simulated ESP32 room publisher
├── esp32_mqtt.ino        # Arduino/ESP32 firmware code for physical sensors
├── translations.json     # Localization dictionary for English/Spanish language switching
├── docker-compose.yml    # Service orchestration manifest
├── Dockerfile            # Container image builder specification
├── templates/
│   ├── index.html        # Main interactive vector blueprint dashboard
│   └── history.html      # Historical log card layout with trend sparklines
└── test_smart_building.py# Autonomous pytest integration suite
```

---

## Prerequisites

- **Docker** and **Docker Compose** (Recommended method)
- Or a local **Python 3.13** setup with a local MQTT Broker (e.g., Mosquitto) installed

---

## Getting Started

### Option 1: Running with Docker Compose (Recommended)

All services (MQTT, Web Backend, and the 4 ESP32 simulators) are orchestrated under Docker.

1. **Build and start the services**:
   ```bash
   docker compose up --build -d
   ```
2. **Verify that the containers are running**:
   ```bash
   docker compose ps
   ```
3. **Access the Applications**:
   - **Interactive Blueprint Dashboard**: [http://localhost:5001](http://localhost:5001)
   - **Historical Readings View**: [http://localhost:5001/history](http://localhost:5001/history)

---

### Option 2: Running Locally (Manual Setup)

#### 1. Setup the MQTT Broker
Ensure a local MQTT broker is running on port `1883`. On Debian/Ubuntu:
```bash
sudo apt update && sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable mosquitto && sudo systemctl start mosquitto
```
On macOS (using Homebrew):
```bash
brew install mosquitto
brew services start mosquitto
```

#### 2. Install Python Dependencies
It is recommended to run inside a virtual environment:
```bash
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

#### 3. Initialize the Database and Model
Run the setup scripts in order:
```bash
# Initialize SQLite database file (building.db)
python init_db.py

# Build dataset and train the Random Forest classification model
python train_model.py
```

#### 4. Start the Application components
In separate terminals (with the virtual environment activated):

- **Start the Flask Backend**:
  ```bash
  python app.py
  ```
- **Start the ESP32 Simulators** (Run as many as desired by changing the `ROOM` environment variable):
  ```bash
  # Windows CMD / PowerShell
  $env:ROOM="LAB1"; python esp32_simulator.py
  $env:ROOM="LAB2"; python esp32_simulator.py

  # Unix/macOS
  ROOM=LAB1 python esp32_simulator.py
  ROOM=LAB2 python esp32_simulator.py
  ```

---

## Running Verification Tests

To execute the test suite validating database integration, model inference, translations, and simulator logic:
```bash
python -m pytest -v
```

---

## UI Customizations & Details

- **Blueprint Palette**: Designed using the official **Sabana Blue** colorway (`#003d8f`) on a clean light theme.
- **Entrada Principal**: Labeled vertically on the left-side wall featuring an inward swinging door arc indicating the entry path.
- **Oficina**: Placed top-left (with horizontal zebra striping) and a matching lower-left utility area.
- **Interactive Tooltips**: Hovering over any active Lab highlights the room and displays the live sensor telemetry (CO₂, MQ-135, MQ-8) and occupancy status inside a styled tooltip.
- **Language Switcher**: Toggle dynamically between **EN** (English) and **ES** (Spanish) across the entire application interface.
