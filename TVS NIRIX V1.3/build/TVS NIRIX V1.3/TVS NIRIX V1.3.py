# -*- coding: utf-8 -*-
"""
Created on Wed Apr 30 09:43:08 2025

@author: A.Harshitha
"""

import os
import sys
import configparser
import importlib
import io
import json
import requests
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QProgressBar, QMessageBox, QWidget, QPushButton, QRadioButton, QGroupBox, QButtonGroup
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QGuiApplication
from datetime import datetime
import time
import re
import can
import threading

# Path to your ini file
INI_PATH = "api.ini"

# Function to read selected API URL based on the mode (prd or EJO)
def get_api_url(api_mode):
    config = configparser.ConfigParser()
    config.read(INI_PATH)
    return config["API"][api_mode]

def load_scanner_config(config_file='scanner.ini'):
    config_path = resource_path(config_file)
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        return 'SocketCAN', 'can0', 500000
    config = configparser.ConfigParser()
    config.read(config_path)
    if 'ScannerConfig' not in config:
        print(f"Missing 'ScannerConfig' section in {config_path}")
        return 'SocketCAN', 'can0', 500000
    connection_mode = config.get('ScannerConfig', 'connection_mode', fallback='SocketCAN').upper()
    interface = config.get('ScannerConfig', 'interface', fallback='can0')
    bitrate = config.getint('ScannerConfig', 'bitrate', fallback=500000)
    return connection_mode, interface, bitrate

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_active_library():
    config = configparser.ConfigParser()
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        ini_path = os.path.join(base_path, "station.ini")
        if not os.path.exists(ini_path):
            raise FileNotFoundError(f"station.ini not found at {ini_path}")
        config.read(ini_path)
        active_library = config.get("SETTINGS", "active_library", fallback="test_library")
        return active_library
    except Exception as e:
        print(f"Error reading station.ini: {e}")
        return "test_library"

class ScannerSignalEmitter(QObject):
    vin_scanned = pyqtSignal(str)

class InputValidatorApp(QMainWindow):
    API_URL = "http://10.121.2.107:3000/vehicles/processParams/updateProcessParams"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TVS NIRIX V1.3")
        self.active_library = load_active_library()

        log_folder = r"D:\Python\ModularApp\test_results_V1.3"
        try:
            log_cleanup_module = importlib.import_module("log_cleanup")
            log_cleanup_module.cleanup_old_logs(log_folder)
        except ImportError as e:
            print(f"Failed to import log_cleanup.py: {e}")
        except AttributeError as e:
            print(f"Failed to call cleanup_old_logs in log_cleanup.py: {e}")
        except Exception as e:
            print(f"Error executing log_cleanup.py: {e}")

        self.front_mac = ""
        self.rear_mac = ""

        self.test_cases = [
            ("01_API_CALL", "API_CALL"),
            ("02_WRITE_TPMS_FRONT", "WRITE_TPMS_FRONT"),
            ("03_WRITE_TPMS_REAR", "WRITE_TPMS_REAR")
        ]

        self.current_test_index = 0
        self.test_results = []
        self.final_status = "OK"
        self.api_mode = "prd"
        self.json_response = None
        self.url = None

        # Detect screen dimensions and set window size
        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        self.setGeometry(0, 0, screen_width, screen_height)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        vin_row_layout = QHBoxLayout()
        self.vin_label = QLabel("Enter VIN Number:")
        self.vin_label.setStyleSheet("font-size: 45px; font-weight: bold;")
        self.vin_input = QLineEdit()
        self.vin_input.setMaxLength(17)
        self.vin_input.setPlaceholderText("Eg :MD612345678912345")
        self.vin_input.setStyleSheet("font-size: 40px; padding: 5px;")
        self.vin_input.setFixedWidth(800)
        self.vin_input.installEventFilter(self)
        self.vin_input.returnPressed.connect(self.start_test_cases)

        vin_row_layout.addWidget(self.vin_label)
        vin_row_layout.addWidget(self.vin_input)

        self.radio_prd = QRadioButton("PRD")
        self.radio_prd.setChecked(True)
        self.radio_prd.setStyleSheet("font-size: 40px; font-weight: normal; padding-left: 50px;")
        self.radio_ejo = QRadioButton("EJO")
        self.radio_ejo.setStyleSheet("font-size: 40px; font-weight: normal; padding-right: 25px;")

        self.api_group = QButtonGroup(self)
        self.api_group.addButton(self.radio_prd)
        self.api_group.addButton(self.radio_ejo)

        self.radio_prd.toggled.connect(self.set_api_mode)
        self.radio_ejo.toggled.connect(self.set_api_mode)

        self.select_api_label = QLabel("Select API:")
        self.select_api_label.setStyleSheet("font-size: 45px; font-weight: normal; padding-left: 25px;")
        vin_row_layout.addWidget(self.select_api_label)
        vin_row_layout.addWidget(self.radio_prd)
        vin_row_layout.addWidget(self.radio_ejo)
        vin_row_layout.addStretch()

        self.active_library_label = QLabel(f"Active Library: {self.active_library}")
        self.active_library_label.setStyleSheet("font-size: 45px; font-weight: normal;")

        main_layout.addLayout(vin_row_layout)
        main_layout.addWidget(self.active_library_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                color: blue;
                border: 1px solid black;
                text-align: center;
                height: 30px;
                font-size: 40px;
                width: 100%;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        test_layout = QHBoxLayout()

        self.test_boxes = []
        for i in range(0, len(self.test_cases), 1):
            row_layout = QVBoxLayout()
            for j in range(1):
                if i + j < len(self.test_cases):
                    module, function = self.test_cases[i + j]
                    test_box = QLabel(f"{function}")
                    test_box.setStyleSheet("""
                        font-size: 45px;
                        border: 2px solid black;
                        padding: 10px;
                        min-width: 200px;
                        min-height: 75px;
                        text-align: center;
                    """)
                    test_box.setAlignment(Qt.AlignCenter)
                    self.test_boxes.append(test_box)
                    row_layout.addWidget(test_box)
            test_layout.addLayout(row_layout)

        main_layout.addLayout(test_layout)

        bottom_layout = QHBoxLayout()
        self.instructions_label = QLabel("Instructions:")
        self.instructions_label.setStyleSheet("font-size: 45px; font-weight: bold; border: 1px solid black; padding: 10px;")
        self.instructions_label.setAlignment(Qt.AlignTop)
        bottom_layout.addWidget(self.instructions_label, stretch=1)

        self.result_label = QLabel("Result:")
        self.result_label.setStyleSheet("font-size: 45px; font-weight: bold; border: 1px solid black; padding: 10px;")
        self.result_label.setAlignment(Qt.AlignTop)
        bottom_layout.addWidget(self.result_label, stretch=1)

        main_layout.addLayout(bottom_layout)

        self.scanner_signals = ScannerSignalEmitter()
        self.scanner_signals.vin_scanned.connect(self.handle_scanned_vin)

        connection_mode, interface, bitrate = load_scanner_config()
        self.connection_mode = connection_mode
        self.interface = interface
        self.bitrate = bitrate

        if connection_mode == "SocketCAN" and interface:
            self.start_socketcan_listener(interface, bitrate)

    def set_api_mode(self):
        if self.radio_prd.isChecked():
            self.api_mode = 'PRD'
        elif self.radio_ejo.isChecked():
            self.api_mode = 'EJO'

    def eventFilter(self, source, event):
        if source == self.vin_input and event.type() == event.FocusIn:
            QTimer.singleShot(100, lambda: self.start_socketcan_listener(self.interface, self.bitrate))
        return super().eventFilter(source, event)

    '''def start_socketcan_listener(self, interface=None, bitrate=500000):
        if not interface:
            print("No SocketCAN interface specified. Available interfaces: can0, can1, etc.")
            return

        try:
            bus = can.interface.Bus(channel=interface, bustype='socketcan', bitrate=bitrate)
            print(f"Connected to SocketCAN interface {interface} at {bitrate} kbps.")

            def read_from_socketcan():
                while True:
                    message = bus.recv(timeout=1.0)
                    if message:
                        vin = message.data[:17].decode('utf-8', errors='ignore').strip()
                        if vin and vin.startswith("MD6") and len(vin) == 17:
                            print(f"Scanned VIN from CAN: {vin}")
                            self.scanner_signals.vin_scanned.emit(vin)
                            break
                    time.sleep(0.1)
                bus.shutdown()
            threading.Thread(target=read_from_socketcan, daemon=True).start()

        except Exception as e:
            print(f"Failed to connect to SocketCAN interface {interface}: {e}")'''

    def handle_scanned_vin(self, vin):
        self.vin_input.setText(vin)
        self.start_test_cases()

    def reset_for_next_cycle(self):
        print("Resetting for next cycle...")
        self.current_test_index = 0
        self.front_mac = ""
        self.rear_mac = ""
        self.test_results.clear()
        self.final_status = "OK"

        self.vin_input.clear()
        self.progress_bar.setValue(0)

        self.vin_input.clearFocus()
        self.vin_input.setFocus()

        for i, test_box in enumerate(self.test_boxes):
            _, function = self.test_cases[i]
            test_box.setText(function)
            test_box.setStyleSheet("""
                font-size: 45px;
                border: 2px solid black;
                padding: 10px;
                min-width: 200px;
                min-height: 75px;
                text-align: center;
                background-color: none;
            """)

        self.instructions_label.setText("Instructions:")
        self.result_label.setText("Result:")

        importlib.invalidate_caches()

    def start_test_cases(self):
        vin_number = self.vin_input.text().strip()
        if not (vin_number.startswith("MD6") and len(vin_number) == 17):
            self.instructions_label.setText(
                'Instructions:<br><span style="font-weight: normal;">Invalid VIN number.</span>'
            )
            return
        self.current_test_index = 0
        self.test_results = []
        self.final_status = "OK"
        self.run_next_test()

    def run_next_test(self):
        if self.current_test_index < len(self.test_cases):
            module, function = self.test_cases[self.current_test_index]
            label = self.test_boxes[self.current_test_index]

            result = self.run_test(self.active_library, module, function)
            status = "PASSED" if result else "FAILED"
            color = "green" if result else "red"

            label.setStyleSheet(f"""
                font-size: 45px;
                border: 2px solid black;
                background-color: {color};
                padding: 10px;
                min-width: 200px;
                min-height: 75px;
                text-align: center;
            """)
            label.setText(f"{function}\n{status}")

            progress_value = (self.current_test_index + 1) * (100 // len(self.test_cases))
            self.progress_bar.setValue(progress_value)
            self.result_label.setText(
                f'Result:<br> <span style="color:{color}; font-weight:bold; font-size:48px;">{function} - {status}</span>'
            )

            self.test_results.append(f"{function}: {status}")

            if not result:
                self.final_status = "NOK"
                self.progress_bar.setValue(100)
                self.instructions_label.setText(
                    f'Instructions:<br><span style="font-weight: normal;">{function} failed.<br>Please check.</span>'
                )
                self.result_label.setText(
                    f'Result:<br> <span style="color:red; font-weight:bold; font-size:48px;">{function} - FAILED</span>'
                )
                self.show_popup("Test Failed", f"{function} failed. Process stopped.")
                self.save_results_to_log()
                self.send_api_status()
                QTimer.singleShot(15000, lambda: self.reset_for_next_cycle())
                return

            QTimer.singleShot(1000, lambda: self._proceed_to_next_test())

        else:
            self.progress_bar.setValue(100)
            QTimer.singleShot(1000, lambda: print("1 second passed"))
            self.result_label.setText(
                f'Result:<br> <span style="color:green; font-weight:bold; font-size:48px;">All tests passed successfully!</span>'
            )
            self.instructions_label.setText(
                'Instructions:<br><span style="font-weight: normal;">System ready for next VIN number.</span>'
            )
            self.save_results_to_log()
            self.send_api_status()

            QTimer.singleShot(10000, lambda: self.reset_for_next_cycle())

    def _proceed_to_next_test(self):
        self.current_test_index += 1
        self.run_next_test()

    def send_api_status(self):
        print("Sending API request...")
        vin_number = self.vin_input.text().strip()
        headers = {'Content-Type': 'application/json'}
        data = {
            "vin": vin_number,
            "status": self.final_status,
            "front_mac": self.front_mac,
            "rear_mac": self.rear_mac
        }
        response = requests.post(self.API_URL, headers=headers, data=json.dumps(data))
        print(f"API Response: {response.status_code}, {response.text}")

    def is_valid_hex_mac(self, mac):
        return isinstance(mac, str) and re.fullmatch(r"[0-9A-Fa-f]{12}", mac) is not None

    def run_test(self, library_name, module_name, function_name):
        log_capture = io.StringIO()
        sys.stdout = log_capture
        try:
            module = importlib.import_module(f"{library_name}.{module_name}")
            test_function = getattr(module, function_name)
            vin_number = self.vin_input.text().strip()
    
            if function_name == "API_CALL":
                self.front_mac, self.rear_mac, result, self.json_response, self.url = test_function(vin_number, self.api_mode)
                result = self.is_valid_hex_mac(self.front_mac) and self.is_valid_hex_mac(self.rear_mac)
            elif function_name == "WRITE_TPMS_FRONT":
                if self.is_valid_hex_mac(self.front_mac):
                    result = test_function(self.front_mac)
                else:
                    print(f"Invalid MAC ID: {self.front_mac}")
                    result = False
            elif function_name == "WRITE_TPMS_REAR":
                if self.is_valid_hex_mac(self.rear_mac):
                    result = test_function(self.rear_mac)
                else:
                    print(f"Invalid MAC ID: {self.rear_mac}")
                    result = False
            else:
                result = test_function()
        except (ImportError, AttributeError, TypeError) as e:
            print(f"Error running test case: {function_name} - {e}")
            result = False
        finally:
            sys.stdout = sys.__stdout__
    
        log_output = log_capture.getvalue()
        log_capture.close()
    
        self.test_results.append(log_output.strip())
    
        return result

    def save_results_to_log(self):
        vin_number = self.vin_input.text().strip()
        timestamp_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        rear_wheel = getattr(self, 'rear_mac', '')
        front_wheel = getattr(self, 'front_mac', '')

        log_folder = r"D:\Python\ModularApp\test_results_V1.3"
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

        txt_filename = f"{vin_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        txt_path = os.path.join(log_folder, txt_filename)

        with open(txt_path, 'w') as file:
            file.write("VIN NUMBER      : {}\n".format(vin_number))
            file.write("REAR WHEEL MAC  : {}\n".format(rear_wheel))
            file.write("FRONT WHEEL MAC : {}\n".format(front_wheel))
            file.write("TEST STATUS     : {}\n".format(self.final_status))
            file.write("DATE            : {}\n".format(timestamp_now))
            file.write("API Request:\n")
            file.write(getattr(self, 'url', 'No request sent'))
            file.write("\nAPI Response:\n")
            file.write(getattr(self, 'json_response', 'No response available'))
            file.write("\n=== RAW LOGS WITH TIMESTAMP ===\n")

            for raw_log in self.test_results:
                timestamp_log = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                for line in raw_log.strip().split('\n'):
                    file.write(f"[{timestamp_log}] {line}\n")

        print(f"Results and logs saved to TXT: {txt_path}")

    def show_popup(self, title, message):
        msg = QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Information)
        #msg.setStandardButtons(QMessageBox.Ok)
        #msg.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = InputValidatorApp()
    window.show()
    sys.exit(app.exec())