"""
UHFLI Live Monitor (Minimal)
Adapted from working MFLI structure.

Notes:
- Same overall logic as MFLI:
  Session -> visible devices -> connect -> configure demod -> poll sample
- Assumes demod 0, osc 0, sigin 0
- Uses getSample() first for compatibility with older toolkit/LabOne versions
"""

import sys
import math
from typing import Optional

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFormLayout, QGroupBox, QMessageBox
)

from zhinst.toolkit import Session


def looks_like_in_use_error(msg: str) -> bool:
    m = (msg or "").lower()
    return (
        ("in use" in m)
        or ("already connected" in m)
        or ("32789" in m)
        or ("different server" in m)
    )


class UHFLILiveGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UHFLI Live Monitor (Minimal)")
        self.setMinimumWidth(560)

        # --- State ---
        self.session: Optional[Session] = None
        self.device_id: Optional[str] = None
        self.streaming: bool = False

        # --- UI widgets ---
        self.host_edit = QLineEdit("localhost")
        self.port_edit = QLineEdit("8004")
        self.connect_btn = QPushButton("Connect")
        self.refresh_btn = QPushButton("Refresh Devices")
        self.device_combo = QComboBox()

        # Minimal settings
        self.freq_edit = QLineEdit("1000000")   # 1 MHz default for UHFLI example
        self.tc_edit = QLineEdit("0.001")       # 1 ms
        self.rate_edit = QLineEdit("1000")      # Sa/s

        self.start_btn = QPushButton("Start Live")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)

        self.status_lbl = QLabel("Status: Disconnected")
        self.status_lbl.setWordWrap(True)

        self.x_lbl = QLabel("X: —")
        self.y_lbl = QLabel("Y: —")
        self.r_lbl = QLabel("Amplitude (R): —")
        self.phi_lbl = QLabel("Phase (phi): —")

        for lab in (self.x_lbl, self.y_lbl, self.r_lbl, self.phi_lbl):
            lab.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lab.setStyleSheet("font-size: 16px;")

        # Poll timer
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.poll_and_update)

        self._build_layout()
        self._wire_events()

    def _build_layout(self):
        root = QVBoxLayout()

        conn_box = QGroupBox("Connection")
        conn_form = QFormLayout()
        conn_form.addRow("Host:", self.host_edit)
        conn_form.addRow("Port:", self.port_edit)

        conn_row = QHBoxLayout()
        conn_row.addWidget(self.connect_btn)
        conn_row.addWidget(self.refresh_btn)
        conn_form.addRow(conn_row)

        conn_form.addRow("Device:", self.device_combo)
        conn_box.setLayout(conn_form)
        root.addWidget(conn_box)

        cfg_box = QGroupBox("Minimal Settings (optional)")
        cfg_form = QFormLayout()
        cfg_form.addRow("Osc0 Frequency (Hz):", self.freq_edit)
        cfg_form.addRow("Demod0 Time Constant (s):", self.tc_edit)
        cfg_form.addRow("Demod0 Rate (Sa/s):", self.rate_edit)
        cfg_box.setLayout(cfg_form)
        root.addWidget(cfg_box)

        ctl = QHBoxLayout()
        ctl.addWidget(self.start_btn)
        ctl.addWidget(self.stop_btn)
        root.addLayout(ctl)

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

    def _wire_events(self):
        self.connect_btn.clicked.connect(self.connect_to_server)
        self.refresh_btn.clicked.connect(self.refresh_devices)
        self.start_btn.clicked.connect(self.start_live)
        self.stop_btn.clicked.connect(self.stop_live)

    def set_status(self, msg: str):
        self.status_lbl.setText(f"Status: {msg}")

    def show_error(self, title: str, msg: str):
        QMessageBox.critical(self, title, msg)

    def show_info(self, title: str, msg: str):
        QMessageBox.information(self, title, msg)

    def connect_to_server(self):
        host = self.host_edit.text().strip()
        try:
            port = int(self.port_edit.text().strip())
        except ValueError:
            self.show_error("Bad Port", "Port must be an integer, e.g. 8004.")
            return

        try:
            self.session = Session(host, port)
        except Exception as e:
            self.session = None
            self.set_status("Disconnected")
            self.show_error(
                "Connection Failed",
                f"Could not connect to LabOne Data Server at {host}:{port}\n\n{e}"
            )
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
            self.show_error("Device Query Failed", f"Could not query visible devices.\n\n{e}")
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
        Basic UHFLI configuration using same style as MFLI.
        Assumes:
          - sigin 0
          - demod 0
          - osc 0
        """

        dev = self.session.devices[device_id]

        try:
            freq = float(self.freq_edit.text().strip())
        except ValueError:
            freq = 1e6

        try:
            tc = float(self.tc_edit.text().strip())
        except ValueError:
            tc = 0.001

        try:
            rate = float(self.rate_edit.text().strip())
        except ValueError:
            rate = 1000.0

        # Enable input and demod
        dev.sigins[0].on(1)
        dev.demods[0].enable(1)

        # Oscillator and demod settings
        dev.oscs[0].freq(freq)
        dev.demods[0].timeconstant(tc)
        dev.demods[0].order(4)
        dev.demods[0].rate(rate)

        # Common demod source settings
        # These sometimes matter depending on lab setup
        try:
            dev.demods[0].oscselect(0)
        except Exception:
            pass

        try:
            dev.demods[0].adcselect(0)
        except Exception:
            pass

        # Optional autorange
        try:
            dev.sigins[0].autorange(1)
        except Exception:
            pass

    def start_live(self):
        if not self.session:
            self.show_error("Not Connected", "Connect to the LabOne Data Server first.")
            return

        device_id = self.device_combo.currentText().strip()
        if not device_id or device_id.startswith("("):
            self.show_error("No Device", "No valid device selected.")
            return

        if self.streaming:
            self.stop_live()

        self.device_id = device_id

        try:
            self.session.connect_device(device_id)
        except Exception as e:
            msg = str(e)
            if not looks_like_in_use_error(msg):
                self.show_error("Start Failed", f"Could not connect device {device_id}.\n\n{e}")
                self.device_id = None
                return

        try:
            self.apply_minimal_settings(device_id)
        except Exception as e:
            self.show_error(
                "Start Failed",
                "Could not configure device.\n\n"
                f"Device: {device_id}\n\n{e}\n\n"
                "Check whether another LabOne session is using the device, "
                "or whether the input/demod routing must be adjusted."
            )
            self.device_id = None
            return

        self.streaming = True
        self.timer.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.set_status(f"Reading from {device_id}/demods/0/sample")

    def stop_live(self):
        self.timer.stop()

        if self.session and self.device_id:
            try:
                self.session.disconnect_device(self.device_id)
            except Exception:
                pass

        self.streaming = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.set_status("Connected (stream stopped)")

        self.x_lbl.setText("X: —")
        self.y_lbl.setText("Y: —")
        self.r_lbl.setText("Amplitude (R): —")
        self.phi_lbl.setText("Phase (phi): —")

    def poll_and_update(self):
        if not (self.session and self.device_id):
            return

        try:
            sample_path = f"/{self.device_id}/demods/0/sample"

            try:
                sample = self.session.daq_server.getSample(sample_path)
            except AttributeError:
                try:
                    sample = self.session.daq_server.getAsEvent(sample_path)
                except AttributeError:
                    result = self.session.daq_server.get(sample_path)
                    if result and sample_path in result:
                        sample = result[sample_path]
                    else:
                        self.set_status("Could not read sample - unsupported API version")
                        return

            x = 0.0
            y = 0.0
            r = 0.0
            phi = 0.0

            def safe_extract(value):
                if isinstance(value, (list, tuple)) and len(value) > 0:
                    return float(value[0])
                return float(value)

            if isinstance(sample, dict):
                if "x" in sample:
                    x = safe_extract(sample["x"])
                if "y" in sample:
                    y = safe_extract(sample["y"])
                if "r" in sample:
                    r = safe_extract(sample["r"])
                if "theta" in sample:
                    phi = safe_extract(sample["theta"])
                elif "phi" in sample:
                    phi = safe_extract(sample["phi"])

                if "value" in sample and isinstance(sample["value"], dict):
                    val = sample["value"]
                    if "x" in val:
                        x = safe_extract(val["x"])
                    if "y" in val:
                        y = safe_extract(val["y"])
                    if "r" in val:
                        r = safe_extract(val["r"])
                    if "theta" in val:
                        phi = safe_extract(val["theta"])
                    elif "phi" in val:
                        phi = safe_extract(val["phi"])

            if (x != 0.0 or y != 0.0) and r == 0.0:
                r = math.sqrt(x * x + y * y)
                phi = math.atan2(y, x)

        except Exception as e:
            self.set_status(f"Read error: {e}")
            return

        self.x_lbl.setText(f"X: {x:+.6e}")
        self.y_lbl.setText(f"Y: {y:+.6e}")
        self.r_lbl.setText(f"Amplitude (R): {r:.6e}")
        self.phi_lbl.setText(f"Phase (phi): {phi:+.3f} rad")

    def closeEvent(self, event):
        try:
            if self.streaming:
                self.stop_live()
        finally:
            event.accept()


def main():
    app = QApplication(sys.argv)
    w = UHFLILiveGUI()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()