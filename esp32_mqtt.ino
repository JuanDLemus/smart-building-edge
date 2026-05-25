#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid = "TU_WIFI";
const char* password = "TU_PASSWORD";
const char* mqtt_server = "192.168.1.100";

WiFiClient espClient;
PubSubClient client(espClient);

#define MQ135_PIN 34
#define MQ8_PIN 35

float mq135_baseline = 0;
float mq8_baseline = 0;

void setup_wifi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
  }
}

void reconnect() {
  while (!client.connected()) {
    client.connect("ESP32Client");
  }
}

void calibrateSensors() {
  long mq135_total = 0;
  long mq8_total = 0;
  for (int i = 0; i < 100; i++) {
    mq135_total += analogRead(MQ135_PIN);
    mq8_total += analogRead(MQ8_PIN);
    delay(100);
  }
  mq135_baseline = mq135_total / 100.0;
  mq8_baseline = mq8_total / 100.0;
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  delay(30000);
  calibrateSensors();
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  int mq135_raw = analogRead(MQ135_PIN);
  int mq8_raw = analogRead(MQ8_PIN);
  
  float mq135_delta = mq135_raw - mq135_baseline;
  float mq8_delta = mq8_raw - mq8_baseline;
  
  float co2_index = (mq135_delta * 0.9) + (mq8_delta * 0.1);
  if (co2_index < 0) {
    co2_index = 0;
  }
  
  String payload = "{";
  payload += "\"mq135\":";
  payload += mq135_raw;
  payload += ",";
  payload += "\"mq8\":";
  payload += mq8_raw;
  payload += ",";
  payload += "\"co2_index\":";
  payload += co2_index;
  payload += "}";
  
  client.publish("salon/LAB1/gases", payload.c_str());
  delay(2000);
}
