"""
MFLI / UHFLI Live Monitor - All Demods
Based on the working minimal GUI structure.

What changed:
- Detects all demods available on the selected device
- Displays only Amplitude (R) and Phase (phi) for each demod
- Uses a scrollable live panel
- Polls each demod sample path individually
- Keeps older zhinst-toolkit / LabOne compatibility style

Install:
  pip install zhinst-toolkit PyQt5

Run:
  python amp_all_demods.py
"""

import sys
import math
from typing import Optional, Dict, List

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFormLayout, QGroupBox,
    QMessageBox, QScrollArea, QFrame
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


class DemodRow(QFrame):
    def __init__(self, demod_index: int):
        super().__init__()
        self.demod_index = demod_index
        self.setFrameShape(QFrame.StyledPanel)

        layout = QHBoxLayout()

        self.title_lbl = QLabel(f"Demod {demod_index}")
        self.title_lbl.setMinimumWidth(90)
        self.title_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.r_lbl = QLabel("R: —")
        self.r_lbl.setMinimumWidth(180)
        self.r_lbl.setStyleSheet("font-size: 14px;")

        self.phi_lbl = QLabel("Phase: —")
        self.phi_lbl.setMinimumWidth(180)
        self.phi_lbl.setStyleSheet("font-size: 14px;")

        self.status_lbl = QLabel("idle")
        self.status_lbl.setStyleSheet("color: gray; font-size: 12px;")

        layout.addWidget(self.title_lbl)
        layout.addWidget(self.r_lbl)
        layout.addWidget(self.phi_lbl)
        layout.addWidget(self.status_lbl)
        layout.addStretch()

        self.setLayout(layout)

    def set_values(self, r: float, phi: float):
        self.r_lbl.setText(f"R: {r:.6e}")
        self.phi_lbl.setText(f"Phase: {phi:+.3f} rad")
        self.status_lbl.setText("ok")
        self.status_lbl.setStyleSheet("color: green; font-size: 12px;")

    def set_error(self, msg: str = "no data"):
        self.r_lbl.setText("R: —")
        self.phi_lbl.setText("Phase: —")
        self.status_lbl.setText(msg)
        self.status_lbl.setStyleSheet("color: red; font-size: 12px;")

    def set_idle(self):
        self.r_lbl.setText("R: —")
        self.phi_lbl.setText("Phase: —")
        self.status_lbl.setText("idle")
        self.status_lbl.setStyleSheet("color: gray; font-size: 12px;")


class LockinAllDemodsGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lock-in Live Monitor - All Demods")
        self.setMinimumWidth(760)
        self.setMinimumHeight(500)

        # --- State ---
        self.session: Optional[Session] = None
        self.device_id: Optional[str] = None
        self.streaming: bool = False
        self.available_demods: List[int] = []
        self.demod_rows: Dict[int, DemodRow] = {}

        # --- UI widgets ---
        self.host_edit = QLineEdit("192.168.60.166")
        self.port_edit = QLineEdit("8004")
        self.connect_btn = QPushButton("Connect")
        self.refresh_btn = QPushButton("Refresh Devices")
        self.device_combo = QComboBox()

        # Optional global settings applied to detected demods
        self.freq_edit = QLineEdit("1000")
        self.tc_edit = QLineEdit("0.01")
        self.rate_edit = QLineEdit("200")

        self.start_btn = QPushButton("Start Live")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)

        self.status_lbl = QLabel("Status: Disconnected")
        self.status_lbl.setWordWrap(True)

        self.demod_count_lbl = QLabel("Detected demods: 0")

        self.timer = QTimer(self)
        self.timer.setInterval(250)
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

        cfg_box = QGroupBox("Minimal Settings (applied to detected demods)")
        cfg_form = QFormLayout()
        cfg_form.addRow("Osc0 Frequency (Hz):", self.freq_edit)
        cfg_form.addRow("Demod Time Constant (s):", self.tc_edit)
        cfg_form.addRow("Demod Rate (Sa/s):", self.rate_edit)
        cfg_box.setLayout(cfg_form)
        root.addWidget(cfg_box)

        ctl = QHBoxLayout()
        ctl.addWidget(self.start_btn)
        ctl.addWidget(self.stop_btn)
        ctl.addStretch()
        ctl.addWidget(self.demod_count_lbl)
        root.addLayout(ctl)

        live_box = QGroupBox("Live Output (All Demods)")
        live_layout = QVBoxLayout()
        live_layout.addWidget(self.status_lbl)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.demod_container = QWidget()
        self.demod_layout = QVBoxLayout()
        self.demod_layout.setAlignment(Qt.AlignTop)
        self.demod_container.setLayout(self.demod_layout)

        self.scroll.setWidget(self.demod_container)
        live_layout.addWidget(self.scroll)

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

    # ---------------- utility ----------------
    def clear_demod_rows(self):
        while self.demod_layout.count():
            item = self.demod_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.demod_rows = {}

    def build_demod_rows(self, demod_indices: List[int]):
        self.clear_demod_rows()
        self.demod_rows = {}

        for idx in demod_indices:
            row = DemodRow(idx)
            self.demod_layout.addWidget(row)
            self.demod_rows[idx] = row

        self.demod_layout.addStretch()
        self.demod_count_lbl.setText(f"Detected demods: {len(demod_indices)}")

    def safe_extract(self, value):
        if isinstance(value, (list, tuple)) and len(value) > 0:
            return float(value[0])
        return float(value)

    def read_demod_sample(self, device_id: str, demod_index: int):
        sample_path = f"/{device_id}/demods/{demod_index}/sample"

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
                    raise RuntimeError("Unsupported API version or empty sample result")

        x = 0.0
        y = 0.0
        r = 0.0
        phi = 0.0

        if isinstance(sample, dict):
            if "x" in sample:
                x = self.safe_extract(sample["x"])
            if "y" in sample:
                y = self.safe_extract(sample["y"])
            if "r" in sample:
                r = self.safe_extract(sample["r"])
            if "theta" in sample:
                phi = self.safe_extract(sample["theta"])
            elif "phi" in sample:
                phi = self.safe_extract(sample["phi"])

            if "value" in sample and isinstance(sample["value"], dict):
                val = sample["value"]
                if "x" in val:
                    x = self.safe_extract(val["x"])
                if "y" in val:
                    y = self.safe_extract(val["y"])
                if "r" in val:
                    r = self.safe_extract(val["r"])
                if "theta" in val:
                    phi = self.safe_extract(val["theta"])
                elif "phi" in val:
                    phi = self.safe_extract(val["phi"])

        if (x != 0.0 or y != 0.0) and r == 0.0:
            r = math.sqrt(x * x + y * y)
            phi = math.atan2(y, x)

        return r, phi

    def detect_available_demods(self, device_id: str, max_to_probe: int = 8) -> List[int]:
        """
        Robust demod detection for older toolkit/server combinations.
        We probe demod indices and keep the ones that respond to basic node access.
        """

        found = []

        for i in range(max_to_probe):
            base = f"/{device_id}/demods/{i}"
            try:
                # Try reading a simple node to see if this demod exists.
                # rate is a good choice for probing.
                _ = self.session.daq_server.getDouble(f"{base}/rate")
                found.append(i)
            except Exception:
                continue

        return found

    # ---------------- LabOne logic ----------------
    def connect_to_server(self):
        host = self.host_edit.text().strip()
        try:
            port = int(self.port_edit.text().strip())
        except ValueError:
            self.show_error("Bad Port", "Port must be an integer (e.g. 8004).")
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

    def apply_minimal_settings(self, device_id: str, demod_indices: List[int]):
        dev = self.session.devices[device_id]

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

        # Keep same spirit as your original code
        dev.sigins[0].on(1)

        try:
            dev.oscs[0].freq(freq)
        except Exception:
            pass

        try:
            dev.sigins[0].autorange(1)
        except Exception:
            pass

        for i in demod_indices:
            try:
                dev.demods[i].enable(1)
            except Exception:
                pass

            try:
                dev.demods[i].timeconstant(tc)
            except Exception:
                pass

            try:
                dev.demods[i].order(4)
            except Exception:
                pass

            try:
                dev.demods[i].rate(rate)
            except Exception:
                pass

            try:
                dev.demods[i].oscselect(0)
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
            if looks_like_in_use_error(msg):
                pass
            else:
                self.show_error("Start Failed", f"Could not connect device {device_id}.\n\n{e}")
                self.device_id = None
                return

        try:
            demods = self.detect_available_demods(device_id, max_to_probe=8)
            if not demods:
                raise RuntimeError("No demods detected on this device.")

            self.available_demods = demods
            self.build_demod_rows(demods)
            self.apply_minimal_settings(device_id, demods)

        except Exception as e:
            self.show_error(
                "Start Failed",
                "Could not configure/detect demods.\n\n"
                f"Device: {device_id}\n\n{e}\n\n"
                "If needed, increase max_to_probe or adjust routing/settings."
            )
            self.device_id = None
            self.available_demods = []
            self.clear_demod_rows()
            self.demod_count_lbl.setText("Detected demods: 0")
            return

        self.streaming = True
        self.timer.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.set_status(f"Reading amplitude and phase from {len(demods)} demod(s) on {device_id}")

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

        for row in self.demod_rows.values():
            row.set_idle()

    def poll_and_update(self):
        if not (self.session and self.device_id and self.available_demods):
            return

        ok_count = 0

        for i in self.available_demods:
            row = self.demod_rows.get(i)
            if row is None:
                continue

            try:
                r, phi = self.read_demod_sample(self.device_id, i)
                row.set_values(r, phi)
                ok_count += 1
            except Exception as e:
                row.set_error("no data")

        self.set_status(
            f"Reading amplitude and phase from {ok_count}/{len(self.available_demods)} demod(s) on {self.device_id}"
        )

    def closeEvent(self, event):
        try:
            if self.streaming:
                self.stop_live()
        finally:
            event.accept()


def main():
    app = QApplication(sys.argv)
    w = LockinAllDemodsGUI()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()