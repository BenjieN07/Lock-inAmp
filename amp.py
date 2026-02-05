"""
Simple MFLI Live Monitor (LabOne-style minimal GUI)

What it does:
- Connects to LabOne Data Server (localhost:8004 by default)
- Lets you choose a visible device
- Starts/stops a live stream of demod 0 sample (/demods/0/sample)
- Displays live X, Y, R, Phi values updating in real time

Requirements:
  pip install zhinst-toolkit PyQt5

Run:
  python mfli_live_gui.py
"""

import sys
import time
from typing import Optional

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFormLayout, QMessageBox, QGroupBox
)

from zhinst.toolkit import Session


class MFLILiveGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MFLI Live Monitor (Minimal)")
        self.setMinimumWidth(520)

        # --- LabOne session/device state ---
        self.session: Optional[Session] = None
        self.device_id: Optional[str] = None
        self.demod_path: Optional[str] = None
        self.streaming: bool = False

        # --- UI ---
        self.host_edit = QLineEdit("localhost")
        self.port_edit = QLineEdit("8004")
        self.refresh_btn = QPushButton("Refresh Devices")
        self.device_combo = QComboBox()

        # Basic "foundational" settings (keep minimal)
        self.freq_edit = QLineEdit("1000")     # Hz
        self.tc_edit = QLineEdit("0.01")       # s
        self.rate_edit = QLineEdit("200")      # Sa/s

        self.connect_btn = QPushButton("Connect")
        self.start_btn = QPushButton("Start Live")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)

        # Live readout labels
        self.status_lbl = QLabel("Status: Disconnected")
        self.status_lbl.setWordWrap(True)

        self.x_lbl = QLabel("x: —")
        self.y_lbl = QLabel("y: —")
        self.r_lbl = QLabel("r: —")
        self.phi_lbl = QLabel("phi: —")
        for lab in (self.x_lbl, self.y_lbl, self.r_lbl, self.phi_lbl):
            lab.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lab.setStyleSheet("font-size: 16px;")

        # Poll timer (live update)
        self.timer = QTimer(self)
        self.timer.setInterval(200)  # ms UI update rate (not necessarily device demod rate)
        self.timer.timeout.connect(self.poll_and_update)

        self.build_layout()
        self.wire_events()

    def build_layout(self):
        root = QVBoxLayout()

        # Connection box
        conn_box = QGroupBox("Connection")
        conn_layout = QFormLayout()
        conn_layout.addRow("Host:", self.host_edit)
        conn_layout.addRow("Port:", self.port_edit)

        row = QHBoxLayout()
        row.addWidget(self.connect_btn)
        row.addWidget(self.refresh_btn)
        conn_layout.addRow(row)

        conn_layout.addRow("Device:", self.device_combo)
        conn_box.setLayout(conn_layout)
        root.addWidget(conn_box)

        # Minimal config box
        cfg_box = QGroupBox("Minimal Settings (optional)")
        cfg_layout = QFormLayout()
        cfg_layout.addRow("Osc0 Frequency (Hz):", self.freq_edit)
        cfg_layout.addRow("Demod0 Time Constant (s):", self.tc_edit)
        cfg_layout.addRow("Demod0 Rate (Sa/s):", self.rate_edit)
        cfg_box.setLayout(cfg_layout)
        root.addWidget(cfg_box)

        # Controls
        ctl = QHBoxLayout()
        ctl.addWidget(self.start_btn)
        ctl.addWidget(self.stop_btn)
        root.addLayout(ctl)

        # Live display
        live_box = QGroupBox("Live Output (Demod 0 Sample)")
        live_layout = QVBoxLayout()
        live_layout.addWidget(self.status_lbl)
        live_layout.addWidget(self.x_lbl)
        live_layout.addWidget(self.y_lbl)
        live_layout.addWidget(self.r_lbl)
        live_layout.addWidget(self.phi_lbl)
        live_box.setLayout(live_layout)
        root.addWidget(live_box)

        self.setLayout(root)

    def wire_events(self):
        self.connect_btn.clicked.connect(self.connect_to_server)
        self.refresh_btn.clicked.connect(self.refresh_devices)
        self.start_btn.clicked.connect(self.start_live)
        self.stop_btn.clicked.connect(self.stop_live)

    def set_status(self, msg: str):
        self.status_lbl.setText(f"Status: {msg}")

    def show_error(self, title: str, msg: str):
        QMessageBox.critical(self, title, msg)

    def connect_to_server(self):
        host = self.host_edit.text().strip()
        try:
            port = int(self.port_edit.text().strip())
        except ValueError:
            self.show_error("Bad Port", "Port must be an integer (e.g., 8004).")
            return

        try:
            self.session = Session(host, port)
        except Exception as e:
            self.session = None
            self.show_error("Connection Failed", f"Could not connect to LabOne Data Server:\n\n{e}")
            self.set_status("Disconnected")
            return

        self.set_status(f"Connected to LabOne Data Server at {host}:{port}")
        self.refresh_devices()

    def refresh_devices(self):
        if not self.session:
            self.show_error("Not Connected", "Click Connect first.")
            return
        try:
            devs = self.session.devices.visible()
        except Exception as e:
            self.show_error("Device Query Failed", f"Could not query visible devices:\n\n{e}")
            return

        self.device_combo.clear()
        if not devs:
            self.device_combo.addItem("(none found)")
            self.set_status("Connected, but no devices visible.")
            return

        for d in devs:
            self.device_combo.addItem(d)

        self.set_status(f"Connected. Found {len(devs)} device(s). Select one, then Start Live.")

    def apply_minimal_settings(self, device_id: str):
        """
        Keeps it simple:
        - Enable sigin 1 and demod 0
        - Set osc0 freq, demod0 tc, order, rate
        """
        dev = self.session.devices[device_id]

        # Enable input and demod
        dev.sigins[0].on(1)
        dev.demods[0].enable(1)

        # User-chosen settings (fallback to safe defaults on parse errors)
        try:
            freq = float(self.freq_edit.text().strip())
        except ValueError:
            freq = 1000.0

        try:
            tc = float(self.tc_edit.text().strip())
        except ValueError:
            tc = 0.01

        try:
            rate = float(self.rate_edit.text().strip())
        except ValueError:
            rate = 200.0

        dev.oscs[0].freq(freq)
        dev.demods[0].timeconstant(tc)
        dev.demods[0].order(4)      # fixed for simplicity
        dev.demods[0].rate(rate)

    def start_live(self):
        if not self.session:
            self.show_error("Not Connected", "Connect to the LabOne Data Server first.")
            return

        device_id = self.device_combo.currentText().strip()
        if not device_id or device_id.startswith("("):
            self.show_error("No Device", "No valid device selected.")
            return

        # If already streaming, stop first
        if self.streaming:
            self.stop_live()

        self.device_id = device_id
        self.demod_path = f"/{device_id}/demods/0/sample"

        try:
            self.apply_minimal_settings(device_id)
            self.session.daq.subscribe(self.demod_path)
        except Exception as e:
            self.show_error("Start Failed", f"Could not start live stream:\n\n{e}")
            self.device_id = None
            self.demod_path = None
            return

        self.streaming = True
        self.timer.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.set_status(f"Streaming {self.demod_path}")

    def stop_live(self):
        if not self.session or not self.demod_path:
            return

        try:
            self.timer.stop()
            # Unsubscribe to stop data flow
            self.session.daq.unsubscribe(self.demod_path)
        except Exception:
            pass

        self.streaming = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.set_status("Connected (stream stopped)")

    def poll_and_update(self):
        """
        Polls the subscribed demod sample node and updates the UI.
        """
        if not (self.session and self.demod_path):
            return

        try:
            data = self.session.daq.poll(duration=0.1, timeout=0.5)
        except Exception as e:
            self.set_status(f"Poll error: {e}")
            return

        if self.demod_path not in data:
            # No new data this poll interval
            return

        samples = data[self.demod_path]
        if not samples:
            return

        # Most common format: dict of arrays with keys x,y,r,phi,timestamp
        try:
            x = float(samples["x"][-1])
            y = float(samples["y"][-1])
            r = float(samples["r"][-1])
            phi = float(samples["phi"][-1])
        except Exception:
            # If your server returns a different structure, you’ll see it here.
            self.set_status("Data format unexpected for demod sample.")
            return

        self.x_lbl.setText(f"x: {x:+.6e}")
        self.y_lbl.setText(f"y: {y:+.6e}")
        self.r_lbl.setText(f"r: {r:.6e}")
        self.phi_lbl.setText(f"phi: {phi:+.3f} rad")

    def closeEvent(self, event):
        # Ensure clean unsubscribe on close
        try:
            self.stop_live()
        finally:
            event.accept()


def main():
    app = QApplication(sys.argv)
    w = MFLILiveGUI()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
