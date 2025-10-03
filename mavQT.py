import sys
import os
import subprocess
import threading
import json
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QLabel, QLineEdit, QMessageBox, QSpinBox, QComboBox, QListWidgetItem, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, QObject, QTimer, Qt
import paho.mqtt.client as mqtt
from pymavlink import mavutil

MAX_TOPIC_ITEMS = 20  # Limit for topics 

# ------------------- MAVLink Receiver ------------------- #
class MAVLinkReceiver(QObject):
    message_received = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.running = False
        self.master = None

    def start_listening(self, ip, port):
        self.running = True
        threading.Thread(target=self._listen, args=(ip, port), daemon=True).start()

    def _listen(self, ip, port):
        self.master = mavutil.mavlink_connection(f'udp:{ip}:{port}')
        while self.running:
            try:
                msg = self.master.recv_match(blocking=True, timeout=1)
                if msg:
                    msg_dict = msg.to_dict()
                    msg_dict["_type"] = msg.get_type()
                    self.message_received.emit(msg_dict)
            except Exception as e:
                print("Error receiving MAVLink:", e)
                break

    def stop(self):
        self.running = False
        if self.master:
            self.master.close()

# ------------------- PyQt UI ------------------- #
class MAVMQTTUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("mavQT : MAVlink to MQTT bridge")
        self.setGeometry(200, 200, 1000, 700)

        self.mav_receiver = MAVLinkReceiver()
        self.mav_receiver.message_received.connect(self.update_mav_messages)

        self.mqtt_client = None
        self.broker_process = None
        self.latest_messages = {}   
        self.send_enabled = {}           
        self.continuous_timer = QTimer()
        self.continuous_timer.timeout.connect(self.send_continuous_messages)
        self.continuous_timer.start(100)  # Check every 100ms

        self.setup_ui()
        self.apply_dark_theme()

    def setup_ui(self):
        layout = QVBoxLayout()

        # ---- UDP Setup ----
        udp_layout = QHBoxLayout()
        self.udp_ip_input = QLineEdit("0.0.0.0")
        self.udp_port_input = QLineEdit("14550")
        self.start_udp_btn = QPushButton("Start UDP Listener")
        self.start_udp_btn.clicked.connect(self.toggle_udp)
        udp_layout.addWidget(QLabel("UDP IP:"))
        udp_layout.addWidget(self.udp_ip_input)
        udp_layout.addWidget(QLabel("Port:"))
        udp_layout.addWidget(self.udp_port_input)
        udp_layout.addWidget(self.start_udp_btn)
        layout.addLayout(udp_layout)

        # ---- Latest MAVLink messages ----
        layout.addWidget(QLabel("Latest MAVLink Messages (check to send):"))
        self.mav_list = QListWidget()
        layout.addWidget(self.mav_list)

        #self.uncheck_btn = QPushButton("Uncheck All")
        #self.uncheck_btn.clicked.connect(self.uncheck_all_messages)
        #layout.addWidget(self.uncheck_btn)

        # ---- MQTT Broker ----
        broker_layout = QHBoxLayout()
        #self.broker_ip_input = QLineEdit("127.0.0.1")
        #self.broker_port_input = QLineEdit("1883")
        #self.start_broker_btn = QPushButton("Start Local Broker")
        #self.start_broker_btn.clicked.connect(self.toggle_broker)
        #broker_layout.addWidget(QLabel("Broker IP:"))
        #broker_layout.addWidget(self.broker_ip_input)
        #broker_layout.addWidget(QLabel("Port:"))
        #broker_layout.addWidget(self.broker_port_input)
        #broker_layout.addWidget(self.start_broker_btn)
        #layout.addLayout(broker_layout)

        # ---- External Broker ----
        ext_layout = QHBoxLayout()
        self.ext_broker_ip_input = QLineEdit("127.0.0.1")
        self.ext_broker_port_input = QLineEdit("1883")
        self.connect_ext_btn = QPushButton("Connect External Broker")
        self.connect_ext_btn.clicked.connect(self.connect_external_broker)
        ext_layout.addWidget(QLabel("External Broker IP:"))
        ext_layout.addWidget(self.ext_broker_ip_input)
        ext_layout.addWidget(QLabel("Port:"))
        ext_layout.addWidget(self.ext_broker_port_input)
        ext_layout.addWidget(self.connect_ext_btn)
        layout.addLayout(ext_layout)

        # ---- Send Settings ----
        send_layout = QHBoxLayout()
        self.topic_input = QLineEdit("mavlink/msg")
        self.interval_input = QSpinBox()
        self.interval_input.setRange(50, 5000)
        self.interval_input.setValue(500)
        self.qos_combo = QComboBox()
        self.qos_combo.addItems(["0", "1", "2"])
        send_layout.addWidget(QLabel("Topic:"))
        send_layout.addWidget(self.topic_input)
        send_layout.addWidget(QLabel("Interval ms:"))
        send_layout.addWidget(self.interval_input)
        send_layout.addWidget(QLabel("QoS:"))
        send_layout.addWidget(self.qos_combo)
        layout.addLayout(send_layout)

        # ---- MQTT Topics Display ----
        layout.addWidget(QLabel("MQTT Sent Messages:"))
        self.topics_list = QListWidget()
        layout.addWidget(self.topics_list)

        self.setLayout(layout)

        author_label = QLabel("V 0.1 GitHub: https://github.com/rohith8272/mavQT")
        author_label.setStyleSheet("color: gray; font-size: 10pt;")
        layout.addWidget(author_label)

    # ---- Dark Theme ----
    def apply_dark_theme(self):
        dark_stylesheet = """
        QWidget { background-color: #2e2e2e; color: #f0f0f0; font-family: Arial; }
        QLineEdit, QSpinBox, QComboBox, QListWidget { background-color: #3e3e3e; color: #f0f0f0; border: 1px solid #555; }
        QPushButton { background-color: #555; color: #f0f0f0; border: 1px solid #777; padding: 5px; }
        QPushButton:hover { background-color: #777; }
        QLabel { color: #f0f0f0; }
        QListWidget { selection-background-color: #555; selection-color: #fff; }
        """
        self.setStyleSheet(dark_stylesheet)

    # ---- UDP ----
    def toggle_udp(self):
        if self.mav_receiver.running:
            self.mav_receiver.stop()
            self.start_udp_btn.setText("Start UDP Listener")
        else:
            ip = self.udp_ip_input.text()
            port = int(self.udp_port_input.text())
            self.mav_receiver.start_listening(ip, port)
            self.start_udp_btn.setText("Stop UDP Listener")

    def update_mav_messages(self, msg):
        msg_type = msg["_type"]

        # Skip UNKNOWN message types
        if msg_type.startswith("UNKNOWN"):
            return

        # Convert bytes/bytearray to hex
        serializable_msg = {k: (v.hex() if isinstance(v, (bytes, bytearray)) else v)
                            for k, v in msg.items()}

        self.latest_messages[msg_type] = serializable_msg

        # Update or add checkbox item
        for i in range(self.mav_list.count()):
            item = self.mav_list.item(i)
            if item.text().startswith(msg_type):
                item.setText(f"{msg_type}: {json.dumps(serializable_msg)}")
                break
        else:
            # Create new checkbox item
            item = QListWidgetItem(f"{msg_type}: {json.dumps(serializable_msg)}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)  # default unchecked
            self.mav_list.addItem(item)
            self.send_enabled[msg_type] = True

        # Update send_enabled map based on checkbox state
        for i in range(self.mav_list.count()):
            item = self.mav_list.item(i)
            state = item.checkState() == Qt.CheckState.Checked
            key = item.text().split(":")[0]
            self.send_enabled[key] = state

    # ---- MQTT Broker ----
    def toggle_broker(self):
        if self.broker_process:
            self.broker_process.terminate()
            self.broker_process = None
            self.start_broker_btn.setText("Start Local Broker")
        else:
            if not os.path.exists("mosquitto.exe"):
                QMessageBox.warning(self, "Error", "mosquitto.exe not found!")
                return
            port = self.broker_port_input.text()
            self.broker_process = subprocess.Popen(["mosquitto.exe", "-p", port])
            self.start_broker_btn.setText("Stop Local Broker")

    def connect_external_broker(self):
        ip = self.ext_broker_ip_input.text()
        port = int(self.ext_broker_port_input.text())
        try:
            if self.mqtt_client:
                self.mqtt_client.disconnect()
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.connect(ip, port)
            QMessageBox.information(self, "Connected", f"Connected to broker {ip}:{port}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Cannot connect MQTT: {e}")
    
    #def uncheck_all_messages(self):
        #for i in range(self.mav_list.count()):
            #item = self.mav_list.item(i)
            #item.setCheckState(Qt.CheckState.Unchecked)

    # ---- Send Continuous Messages ----
    def send_continuous_messages(self):
        if not self.mqtt_client:
            return
        topic = self.topic_input.text()
        qos = int(self.qos_combo.currentText())
        interval = self.interval_input.value()

        for msg_type, enabled in self.send_enabled.items():
            if enabled:
                msg = self.latest_messages.get(msg_type)
                if msg:
                    msg_str = json.dumps(msg)
                    self.mqtt_client.publish(topic, msg_str, qos=qos)
                    # Add to topics list with timestamp
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    self.topics_list.addItem(f"[{timestamp}] {topic}: {msg_str}")
                    # Limit list size
                    while self.topics_list.count() > MAX_TOPIC_ITEMS:
                        self.topics_list.takeItem(0)

# ---- Run App ----
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MAVMQTTUI()
    window.show()
    sys.exit(app.exec())
