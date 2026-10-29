Smart RADAR Equipment Health Monitoring

Project Overview

A sensor-based equipment condition-monitoring prototype built using an ESP32 and a Python Streamlit dashboard.

The system monitors selected physical indicators, displays live readings, plots sensor trends, and provides configurable demonstration alerts.

Note: This is an educational monitoring prototype, not a working RADAR system or a certified industrial fault-detection system.

Hardware Components

- ESP32 development board
- MPU6050 accelerometer and gyroscope
- LM35 temperature sensor
- DHT22 temperature and humidity sensor
- LEDs and optional buzzer
- USB cable
- Laptop running the dashboard

Software and Technologies

- Arduino IDE
- ESP32 Arduino framework
- Python
- Streamlit
- Plotly
- PySerial
- Pandas

Project Structure

- "app.py" — Live monitoring dashboard
- "requirements.txt" — Python dependencies
- "firmware/radar_health_monitor.ino" — ESP32 firmware
- ".gitignore" — Files excluded from version control

Running the Dashboard

1. Install Python and Git.

2. Clone or download this repository.

3. Create and activate a Python virtual environment.

4. Install the dependencies:
   
   "python -m pip install -r requirements.txt"

5. Connect the ESP32 over USB.

6. Close any other application using its serial port.

7. Run:
   
   "python -m streamlit run app.py"

8. Select the correct COM port and baud rate in the dashboard.

Data and Limitations

The dashboard reads sensor data transmitted by the ESP32 over USB serial. Thresholds are demonstration settings and must not be treated as validated industrial safety limits.

Future Improvements

- Equipment health indicator
- Improved alert and event history
- Sensor calibration
- Exportable monitoring reports