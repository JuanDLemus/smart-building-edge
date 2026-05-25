
# SMART BUILDING EDGE COMPUTING PROJECT



## PROJECT STRUCTURE


smart-building/│├── app.py├── init_db.py├── ml_model.py├── train_model.py├── requirements.txt├── dataset.csv├── occupancy_model.pkl├── building.db│├── templates/│   ├── index.html│   └── history.html│└── esp32_mqtt.ino


# FILE: requirements.txt


flaskflask-socketioeventletpaho-mqttpandasscikit-learnjoblib


# FILE: init_db.py


import sqlite3conn = sqlite3.connect("building.db")cursor = conn.cursor()cursor.execute("""CREATE TABLE IF NOT EXISTS lab_readings (    id INTEGER PRIMARY KEY AUTOINCREMENT,    lab TEXT,    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,    co2_index REAL,    mq135 INTEGER,    mq8 INTEGER,    estado TEXT)""")conn.commit()conn.close()print("Database creada")


# FILE: train_model.py


import pandas as pdfrom sklearn.model_selection import train_test_splitfrom sklearn.ensemble import RandomForestClassifierfrom sklearn.metrics import classification_reportimport joblib# =========================# LOAD DATASET# =========================df = pd.read_csv("dataset.csv")# =========================# FEATURES# =========================X = df[[    "mq135",    "mq8",    "co2_index"]]# =========================# LABEL# =========================y = df["estado"]# =========================# SPLIT# =========================X_train, X_test, y_train, y_test = train_test_split(    X,    y,    test_size=0.2,    random_state=42)# =========================# MODEL# =========================model = RandomForestClassifier(    n_estimators=100,    random_state=42)model.fit(X_train, y_train)# =========================# EVALUATION# =========================predictions = model.predict(X_test)print(classification_report(    y_test,    predictions))# =========================# SAVE MODEL# =========================joblib.dump(    model,    "occupancy_model.pkl")print("Modelo guardado")


# FILE: ml_model.py


import joblibimport pandas as pdmodel = joblib.load(    "occupancy_model.pkl")def predict_occupancy(    mq135,    mq8,    co2_index):    data = pd.DataFrame([{        "mq135": mq135,        "mq8": mq8,        "co2_index": co2_index    }])    prediction = model.predict(data)    return prediction[0]


# FILE: app.py


from flask import Flask, render_templatefrom flask_socketio import SocketIOimport sqlite3import paho.mqtt.client as mqttimport jsonfrom ml_model import predict_occupancy# =========================# FLASK# =========================app = Flask(__name__)socketio = SocketIO(app)# =========================# DATABASE# =========================def guardar_datos(    lab,    co2,    mq135,    mq8,    estado):    conn = sqlite3.connect("building.db")    cursor = conn.cursor()    cursor.execute("""        INSERT INTO lab_readings        (            lab,            co2_index,            mq135,            mq8,            estado        )        VALUES (?, ?, ?, ?, ?)    """, (        lab,        co2,        mq135,        mq8,        estado    ))    conn.commit()    conn.close()# =========================# ROUTES# =========================@app.route("/")def index():    return render_template("index.html")@app.route("/history")def history():    conn = sqlite3.connect("building.db")    cursor = conn.cursor()    cursor.execute("""        SELECT            lab,            timestamp,            co2_index,            estado        FROM lab_readings        ORDER BY timestamp DESC        LIMIT 100    """)    rows = cursor.fetchall()    conn.close()    return render_template(        "history.html",        rows=rows    )# =========================# MQTT# =========================def on_message(client, userdata, msg):    payload = json.loads(        msg.payload.decode()    )    mq135 = payload["mq135"]    mq8 = payload["mq8"]    co2_index = payload["co2_index"]    estado = predict_occupancy(        mq135,        mq8,        co2_index    )    guardar_datos(        "LAB1",        co2_index,        mq135,        mq8,        estado    )    socketio.emit("new_data", {        "lab1":{            "estado": estado,            "co2": co2_index,            "mq135": mq135,            "mq8": mq8        },        "lab2":{            "estado":"VACIO",            "co2":120,            "mq135":700,            "mq8":100        },        "lab3":{            "estado":"PARCIAL",            "co2":400,            "mq135":1200,            "mq8":300        },        "lab4":{            "estado":"OCUPADO",            "co2":900,            "mq135":2100,            "mq8":900        }    })# =========================# MQTT CLIENT# =========================mqtt_client = mqtt.Client()mqtt_client.on_message = on_messagemqtt_client.connect(    "localhost",    1883)mqtt_client.subscribe(    "salon/gases")mqtt_client.loop_start()# =========================# MAIN# =========================if __name__ == "__main__":    socketio.run(        app,        host="0.0.0.0",        port=5000    )


# FILE: templates/history.html


<!DOCTYPE html><html><head><title>History</title><style>body{    background:#0f172a;    color:white;    font-family:Arial;}table{    width:90%;    margin:auto;    margin-top:40px;    border-collapse:collapse;}th, td{    padding:15px;    border:1px solid rgba(255,255,255,0.1);    text-align:center;}th{    background:#1e293b;}tr:nth-child(even){    background:#111827;}h1{    text-align:center;}</style></head><body><h1>    HISTORICAL DATA</h1><table><tr>    <th>LAB</th>    <th>TIME</th>    <th>CO₂ INDEX</th>    <th>STATE</th></tr>{% for row in rows %}<tr>    <td>{{ row[0] }}</td>    <td>{{ row[1] }}</td>    <td>{{ row[2] }}</td>    <td>{{ row[3] }}</td></tr>{% endfor %}</table></body></html>


# FILE: dataset.csv


mq135,mq8,co2_index,estado1800,900,850,OCUPADO1700,850,790,OCUPADO1600,800,740,OCUPADO1400,500,450,PARCIAL1200,400,350,PARCIAL900,300,220,VACIO800,250,180,VACIO700,200,120,VACIO


# FILE: esp32_mqtt.ino


#include <WiFi.h>#include <PubSubClient.h>const char* ssid = "TU_WIFI";const char* password = "TU_PASSWORD";const char* mqtt_server = "192.168.1.100";WiFiClient espClient;PubSubClient client(espClient);#define MQ135_PIN 34#define MQ8_PIN 35float mq135_baseline = 0;float mq8_baseline = 0;void setup_wifi() {  WiFi.begin(ssid, password);  while (WiFi.status() != WL_CONNECTED) {    delay(500);  }}void reconnect() {  while (!client.connected()) {    client.connect("ESP32Client");  }}void calibrateSensors() {  long mq135_total = 0;  long mq8_total = 0;  for (int i = 0; i < 100; i++) {    mq135_total += analogRead(MQ135_PIN);    mq8_total += analogRead(MQ8_PIN);    delay(100);  }  mq135_baseline = mq135_total / 100.0;  mq8_baseline = mq8_total / 100.0;}void setup() {  Serial.begin(115200);  setup_wifi();  client.setServer(mqtt_server, 1883);  delay(30000);  calibrateSensors();}void loop() {  if (!client.connected()) {    reconnect();  }  client.loop();  int mq135_raw = analogRead(MQ135_PIN);  int mq8_raw = analogRead(MQ8_PIN);  float mq135_delta = mq135_raw - mq135_baseline;  float mq8_delta = mq8_raw - mq8_baseline;  float co2_index = (mq135_delta * 0.9) + (mq8_delta * 0.1);  if (co2_index < 0) {    co2_index = 0;  }  String payload = "{";  payload += "\"mq135\":";  payload += mq135_raw;  payload += ",";  payload += "\"mq8\":";  payload += mq8_raw;  payload += ",";  payload += "\"co2_index\":";  payload += co2_index;  payload += "}";  client.publish("salon/gases", payload.c_str());  delay(2000);}


# FILE: templates/index.html


PASTE THE FULL BIG DASHBOARD HTML FILE HERE (the one with the blueprint, hover cards, labs, glow effects and SocketIO updates)


# HOW TO RUN EVERYTHING



## 1. INSTALL MQTT


sudo apt updatesudo apt install mosquitto mosquitto-clients


## 2. INSTALL PYTHON DEPENDENCIES


pip install -r requirements.txt


## 3. CREATE DATABASE


python init_db.py


## 4. TRAIN MODEL


python train_model.py


## 5. RUN BACKEND


python app.py


# DASHBOARD URL


http://IP_RASPBERRY:5000


# HISTORY URL


http://IP_RASPBERRY:5000/history


# WHAT YOUR PROJECT DOES


Reads MQ135 and MQ8 sensors

Sends sensor data using MQTT

Runs Machine Learning locally on Raspberry Pi

Predicts occupancy in real time

Saves historical data into SQLite

Displays a live smart building dashboard

Uses edge computing architecture