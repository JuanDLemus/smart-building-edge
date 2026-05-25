import time
import json
import random
import os
import paho.mqtt.client as mqtt

MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))
ROOM = os.environ.get("ROOM", "LAB1")

def load_dataset(file_path):
    """Load JSON lines dataset from file."""
    data = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    data.append(int(record["raw"]))
                except Exception:
                    pass
    return data

def main():
    # Load the datasets
    empty_data = load_dataset("datosMq135N.json")
    occupied_data = load_dataset("datosMq135R.json")
    
    if not empty_data or not occupied_data:
        print("ERROR: Failed to load raw MQ135 datasets")
        return
        
    client = mqtt.Client()
    connected = False
    
    # Try connecting until successful
    while not connected:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            connected = True
        except Exception as e:
            # LOGGING: Log errors only
            print(f"ERROR: ESP32 {ROOM} failed to connect to {MQTT_BROKER}:{MQTT_PORT} - {e}")
            time.sleep(3)
            
    client.loop_start()
    print(f"ESP32 simulator for {ROOM} started successfully")
    
    # Initialize state (randomly empty or occupied)
    state = random.choice(["VACIO", "OCUPADO"])
    cycle_count = 0
    
    mq135_baseline = 3000
    mq8_baseline = 1350
    
    while True:
        try:
            # Every 60 seconds (12 cycles * 5s), 20% chance to toggle state
            cycle_count += 1
            if cycle_count >= 12:
                cycle_count = 0
                if random.random() < 0.20:
                    state = "OCUPADO" if state == "VACIO" else "VACIO"
                    
            # Pick a raw MQ135 sensor value from the selected state dataset
            dataset = empty_data if state == "VACIO" else occupied_data
            raw_val = random.choice(dataset)
            
            # Simulate mq8 and co2_index
            mq8_raw = int(raw_val * 0.45 + random.randint(-5, 5))
            mq135_delta = max(0, mq135_baseline - raw_val)
            mq8_delta = max(0, mq8_baseline - mq8_raw)
            co2_index = float((mq135_delta * 0.9) + (mq8_delta * 0.1))
            
            # Publish payload matching ESP32 MQTT interface
            payload = {
                "mq135": raw_val,
                "mq8": mq8_raw,
                "co2_index": co2_index
            }
            topic = f"salon/{ROOM}/gases"
            client.publish(topic, json.dumps(payload))
            
            time.sleep(5)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"ERROR: ESP32 {ROOM} simulator loop error - {e}")
            time.sleep(5)
            
    client.loop_stop()

if __name__ == "__main__":
    main()
