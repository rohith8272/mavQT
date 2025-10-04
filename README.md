# mavQT

**mavQT** is a lightweight tool to connect **MAVLink-enabled drones** to **IoT systems** via MQTT. It allows you to receive, display, and forward MAVLink messages in real time to an MQTT broker.

---

## Features

- Connect to **UDP/TCP MAVLink streams** from drones.
- Subscribe and publish MQTT topics with **custom QoS levels**.
---

## Setup

setup virtual env and install requirements.txt
```
python -m mavQT
```


### Mavlink stream
- On mission planner, set UDP, outbound on port 14550.
- On mavproxy, forwards stream 

```
mavproxy --master=tcp:127.0.0.1:5760 --out 127.0.0.1:14550
```

- connect to your MQTT broker IP/port
- Subscribe and publish MQTT topics with **custom QoS levels**.
---



