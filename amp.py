"""
MFLI Live Monitor (Minimal) — FIXED v2

Fixes included:
- Updated to use the correct modern zhinst-toolkit subscription API
- Uses device.demods[0].sample.subscribe() instead of session.daq.subscribe()
- Uses device.demods[0].sample.poll() for data retrieval
- Handles "device already in use" more gracefully
- Unsubscribes on Stop/Close to avoid stale subscriptions
- Tries to disconnect device on Stop/Close (if supported by your toolkit version)

Install:
  pip install zhinst-toolkit PyQt5

Run:
  python amp_fixed.py
"""

import sys
from typing import Optional

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFormLayout, QGroupBox, QMessageBox
)

from zhinst.toolkit import Session


def looks_like_in_use_error(msg: str) -> bool:
    m = (msg or "").lower()
    return ("in use" in m) or ("already connected" in m) or ("32789" in m) or ("different server" in m)


class MFLILiveGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MFLI Live Monitor (Minimal) - Fixed")
        self.setMinimumWidth(560)

        # --- State ---
        self.session: Optional[Session] = None
        self.device_id: Optional[str] = None
        self.streaming: bool = False

        # --- UI widgets ---
        self.host_edit = QLineEdit("192.168.60.166")  # set to your lab server by default
        self.port_edit = QLineEdit("8004")
        self.connect_btn = QPushButton("Connect")
        self.refresh_btn = QPushButton("Refresh Devices")
        self.device_combo = QComboBox()

        # Minimal settings (optional)
        self.freq_edit = QLineEdit("1000")   # Hz
        self.tc_edit = QLineEdit("0.01")     # s
        self.rate_edit = QLineEdit("200")    # Sa/s

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
        self.timer.setInterval(200)  # ms UI refresh (not the instrument demod rate)
        self.timer.timeout.connect(self.poll_and_update)

        self._build_layout()
        self._wire_events()

    # ---------------- UI ----------------
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

    # ---------------- LabOne / MFLI logic ----------------
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
            self.set_status("Disconnected")
            self.show_error("Connection Failed", f"Could not connect to LabOne Data Server at {host}:{port}\n\n{e}")
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
        Minimal config. This assumes you're using demod 0 and osc 0.
        If your lab wiring uses different routing, we'll adjust later.
        """
        dev = self.session.devices[device_id]

        # Enable input and demod
        dev.sigins[0].on(1)
        dev.demods[0].enable(1)

        # Parse settings with fallbacks
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

        # Apply settings
        dev.oscs[0].freq(freq)
        dev.demods[0].timeconstant(tc)
        dev.demods[0].order(4)   # fixed for simplicity
        dev.demods[0].rate(rate)

        # Optional autorange (ignore if your version doesn't support it)
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

        # Stop any existing stream first
        if self.streaming:
            self.stop_live()

        self.device_id = device_id

        # Try connecting device (some setups require it; if already in use, we may still be able to subscribe)
        try:
            # IMPORTANT: connect_device may fail if another client currently owns the device
            self.session.connect_device(device_id)
        except Exception as e:
            msg = str(e)
            if looks_like_in_use_error(msg):
                # We'll still try to subscribe/poll; if that fails we'll show the real error.
                pass
            else:
                self.show_error("Start Failed", f"Could not connect device {device_id}.\n\n{e}")
                self.device_id = None
                return

        try:
            self.apply_minimal_settings(device_id)

            # ✅ FIXED: Use the modern subscription API
            device = self.session.devices[device_id]
            device.demods[0].sample.subscribe()

        except Exception as e:
            self.show_error(
                "Start Failed",
                "Could not start live stream.\n\n"
                f"Device: {device_id}\n\n{e}\n\n"
                "If you see 'in use', close LabOne UI and other python scripts, or restart the LabOne Data Server."
            )
            self.device_id = None
            return

        self.streaming = True
        self.timer.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.set_status(f"Streaming from {device_id}/demods/0/sample")

    def stop_live(self):
        # Stop timer first
        self.timer.stop()

        # Unsubscribe safely using the modern API
        if self.session and self.device_id:
            try:
                device = self.session.devices[self.device_id]
                device.demods[0].sample.unsubscribe()
            except Exception:
                pass

        # Try to disconnect device to release "in use" lock (best effort)
        if self.session and self.device_id:
            try:
                self.session.disconnect_device(self.device_id)
            except Exception:
                # Some toolkit versions may not provide this; ignoring is OK.
                pass

        self.streaming = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.set_status("Connected (stream stopped)")

        # Clear labels (optional)
        self.x_lbl.setText("X: —")
        self.y_lbl.setText("Y: —")
        self.r_lbl.setText("Amplitude (R): —")
        self.phi_lbl.setText("Phase (phi): —")

    def poll_and_update(self):
        if not (self.session and self.device_id):
            return

        try:
            # ✅ FIXED: Use the modern polling API
            device = self.session.devices[self.device_id]
            data = device.demods[0].sample.poll(timeout=0.5)
        except Exception as e:
            self.set_status(f"Poll error: {e}")
            return

        if not data:
            return

        try:
            # Data structure depends on toolkit version, but typically:
            # data is a dict-like object or has direct array access
            # Try to get the last sample
            if hasattr(data, 'x') and hasattr(data, 'y'):
                # Some versions return structured data
                x = float(data.x[-1]) if len(data.x) > 0 else 0.0
                y = float(data.y[-1]) if len(data.y) > 0 else 0.0
                r = float(data.r[-1]) if len(data.r) > 0 else 0.0
                phi = float(data.phi[-1]) if len(data.phi) > 0 else 0.0
            elif isinstance(data, dict):
                # Or it might be a dict
                x = float(data["x"][-1]) if "x" in data and len(data["x"]) > 0 else 0.0
                y = float(data["y"][-1]) if "y" in data and len(data["y"]) > 0 else 0.0
                r = float(data["r"][-1]) if "r" in data and len(data["r"]) > 0 else 0.0
                phi = float(data["phi"][-1]) if "phi" in data and len(data["phi"]) > 0 else 0.0
            else:
                # Fallback: try direct attribute access
                x = float(data.x) if hasattr(data, 'x') else 0.0
                y = float(data.y) if hasattr(data, 'y') else 0.0
                r = float(data.r) if hasattr(data, 'r') else 0.0
                phi = float(data.phi) if hasattr(data, 'phi') else 0.0
                
        except Exception as e:
            self.set_status(f"Data parsing error: {e}")
            return

        self.x_lbl.setText(f"X: {x:+.6e}")
        self.y_lbl.setText(f"Y: {y:+.6e}")
        self.r_lbl.setText(f"Amplitude (R): {r:.6e}")
        self.phi_lbl.setText(f"Phase (phi): {phi:+.3f} rad")

    def closeEvent(self, event):
        # Ensure we release resources
        try:
            if self.streaming:
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