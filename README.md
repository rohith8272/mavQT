# mavQT

**mavQT** is a lightweight tool to connect **MAVLink-enabled drones** to **IoT systems** via MQTT. It allows you to receive, display, and forward MAVLink messages in real time to an MQTT broker.

---

## Features

- Connect to **UDP/TCP MAVLink streams** from drones.
- Subscribe and publish MQTT topics with **custom QoS levels**.
---

## Setup

setup virtual env and install requirements.txt

- On mission planner, set UDP, outbound on port 14550.
- Subscribe and publish MQTT topics with **custom QoS levels**.
---


## Build 
pyinstaller --onefile --hidden-import=pymavlink --add-data "env/Lib/site-packages/pymavlink/message_definitions:pymavlink/message_definitions" mavQT.py
