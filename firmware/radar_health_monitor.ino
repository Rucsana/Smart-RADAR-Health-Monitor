#include <Wire.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <DHT.h>
#include <math.h>

// ---------- SENSOR OBJECTS ----------
Adafruit_MPU6050 mpu;

#define LM35_PIN   34
#define DHT_PIN    4
#define DHT_TYPE   DHT22

// ---------- OUTPUT PINS ----------
#define RED_LED    18
#define GREEN_LED  19
#define BLUE_LED   23
#define BUZZER_PIN 25

DHT dht(DHT_PIN, DHT_TYPE);

// ---------- DEMO SETTINGS ----------
const int SAMPLE_COUNT = 100;
const unsigned long SAMPLE_DELAY_MS = 5;
const unsigned long DHT_INTERVAL_MS = 2500;

// These are demonstration thresholds, NOT certified
// radar equipment limits. Calibrate before interpreting.
const float VIBRATION_LIMIT = 1.5f;  // m/s^2 RMSa
const float EQUIPMENT_TEMP_LIMIT = 40.0f; // degrees C
const float AMBIENT_TEMP_LIMIT = 40.0f;  // degrees C

float dhtTempC = NAN;
float humidity = NAN;
unsigned long lastDHTRead = 0;

bool mpuReady = false;

void setLEDs(bool red, bool green, bool blue) {
  digitalWrite(RED_LED, red);
  digitalWrite(GREEN_LED, green);
  digitalWrite(BLUE_LED, blue);
}

void buzzerOn() {
  ledcWriteTone(BUZZER_PIN, 2000);
}

void buzzerOff() {
  ledcWriteTone(BUZZER_PIN, 0);
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(RED_LED, OUTPUT);
  pinMode(GREEN_LED, OUTPUT);
  pinMode(BLUE_LED, OUTPUT);

  setLEDs(false, false, true);
  buzzerOff();

  // ESP32 Arduino core 3.x LEDC API.
  if (!ledcAttach(BUZZER_PIN, 2000, 8)) {
    Serial.println("ERROR: Buzzer PWM setup failed.");
  }

  Wire.begin(21, 22);
  analogReadResolution(12);

  dht.begin();

  Serial.println("Smart Radar Equipment Health Monitor");
  Serial.println("Initializing MPU6050...");

  if (!mpu.begin()) {
    Serial.println("ERROR: MPU6050 not detected.");
    setLEDs(true, false, false);

    while (true) {
      delay(100);
    }
  }

  mpu.setAccelerometerRange(MPU6050_RANGE_4_G);
  mpu.setFilterBandwidth(MPU6050_BAND_44_HZ);

  mpuReady = true;

  Serial.println("MPU6050 detected.");
  Serial.println(
    "time_ms,ax,ay,az,lm35_C,dht_C,humidity,"
    "vibration_rms,status"
  );

  setLEDs(false, true, false);
}

void loop() {
  if (!mpuReady) {
    delay(100);
    return;
  }

  float axValues[SAMPLE_COUNT];
  float ayValues[SAMPLE_COUNT];
  float azValues[SAMPLE_COUNT];

  float meanX = 0.0f;
  float meanY = 0.0f;
  float meanZ = 0.0f;

  // ---------- 1. COLLECT ACCELERATION ----------
  for (int i = 0; i < SAMPLE_COUNT; i++) {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    axValues[i] = a.acceleration.x;
    ayValues[i] = a.acceleration.y;
    azValues[i] = a.acceleration.z;

    meanX += axValues[i];
    meanY += ayValues[i];
    meanZ += azValues[i];

    delay(SAMPLE_DELAY_MS);
  }

  meanX /= SAMPLE_COUNT;
  meanY /= SAMPLE_COUNT;
  meanZ /= SAMPLE_COUNT;

  // Remove the average acceleration vector, including
  // the approximate gravity component, over this window.
  float sumSquared = 0.0f;

  for (int i = 0; i < SAMPLE_COUNT; i++) {
    float dx = axValues[i] - meanX;
    float dy = ayValues[i] - meanY;
    float dz = azValues[i] - meanZ;

    sumSquared += dx * dx + dy * dy + dz * dz;
  }

  float vibrationRMS = sqrtf(sumSquared / SAMPLE_COUNT);

  // Last sample for display only.
  float ax = axValues[SAMPLE_COUNT - 1];
  float ay = ayValues[SAMPLE_COUNT - 1];
  float az = azValues[SAMPLE_COUNT - 1];

  // ---------- 2. READ LM35 ----------
  // Approximate conversion. ADC calibration is still needed.
  int raw = analogRead(LM35_PIN);
  float voltage = raw * (3.3f / 4095.0f);
  float equipmentTempC = voltage * 100.0f;

  // ---------- 3. READ DHT22 PERIODICALLY ----------
  unsigned long now = millis();

  if (lastDHTRead == 0 ||
      now - lastDHTRead >= DHT_INTERVAL_MS) {

    float newTemp = dht.readTemperature();
    float newHumidity = dht.readHumidity();

    if (!isnan(newTemp) && !isnan(newHumidity)) {
      dhtTempC = newTemp;
      humidity = newHumidity;
    }

    lastDHTRead = now;
  }

  // ---------- 4. CLASSIFY DEMO STATUS ----------
  bool vibrationHigh = vibrationRMS > VIBRATION_LIMIT;
  bool equipmentTempHigh =
      equipmentTempC > EQUIPMENT_TEMP_LIMIT;

  bool ambientTempHigh =
      !isnan(dhtTempC) &&
      dhtTempC > AMBIENT_TEMP_LIMIT;

  bool degraded =
      vibrationHigh || equipmentTempHigh || ambientTempHigh;

  // Blue = normal monitoring, red = threshold exceeded.
  setLEDs(degraded, !degraded, false);

  if (degraded) {
    buzzerOn();
  } else {
    buzzerOff();
  }

  // ---------- 5. SEND DATA TO LAPTOP ----------
  Serial.print(now);
  Serial.print(",");
  Serial.print(ax, 2);
  Serial.print(",");
  Serial.print(ay, 2);
  Serial.print(",");
  Serial.print(az, 2);
  Serial.print(",");
  Serial.print(equipmentTempC, 1);
  Serial.print(",");

  if (isnan(dhtTempC)) Serial.print("NaN");
  else Serial.print(dhtTempC, 1);

  Serial.print(",");

  if (isnan(humidity)) Serial.print("NaN");
  else Serial.print(humidity, 1);

  Serial.print(",");
  Serial.print(vibrationRMS, 3);
  Serial.print(",");
  Serial.println(degraded ? "DEGRADED" : "NORMAL");

  delay(1000);
}