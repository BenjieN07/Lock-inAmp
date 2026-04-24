"""
Simplified UHF‑LI live monitor
==============================

This module is a pared‑down version of the original ``uhfli.py`` from the
Hyperlist/Lock‑inAmp project.  It removes all user‑controllable knobs
(frequency, time constant, rate) so that the program functions strictly as
a read‑only monitor.  Demodulator amplitudes (R) and phases are displayed
for each available demod, and phase values are converted to degrees.

The LabOne server and web GUI remain responsible for configuring the
instrument.  Changes made via the LabOne interface propagate
automatically to this GUI.

Requires
--------
* Python 3.7 or later
* PyQt5
* zhinst‑toolkit (available via ``pip install zhinst‑toolkit``)

Run this module with::

    python uhfli_modified.py
"""

import sys
import math
from typing import Optional, Dict, List

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QFormLayout,
    QGroupBox,
    QMessageBox,
    QScrollArea,
    QFrame,
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
    """Widget that displays amplitude and phase for a single demodulator."""

    def __init__(self, demod_index: int):
        super().__init__()
        self.demod_index = demod_index
        self.setFrameShape(QFrame.StyledPanel)

        layout = QHBoxLayout()

        self.name_lbl = QLabel(f"Demod {demod_index}")
        self.name_lbl.setMinimumWidth(90)
        self.name_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.r_lbl = QLabel("R: —")
        self.r_lbl.setMinimumWidth(180)
        self.r_lbl.setStyleSheet("font-size: 14px;")

        self.phi_lbl = QLabel("Phase: —")
        self.phi_lbl.setMinimumWidth(180)
        self.phi_lbl.setStyleSheet("font-size: 14px;")

        self.state_lbl = QLabel("idle")
        self.state_lbl.setStyleSheet("color: gray; font-size: 12px;")

        layout.addWidget(self.name_lbl)
        layout.addWidget(self.r_lbl)
        layout.addWidget(self.phi_lbl)
        layout.addWidget(self.state_lbl)
        layout.addStretch()

        self.setLayout(layout)

    def set_values(self, r: float, phi: float) -> None:
        """Set the amplitude and phase.

        Phase is expected in radians and will be displayed in degrees.
        """
        self.r_lbl.setText(f"R: {r:.6e}")
        # Convert radian to degrees
        phi_deg = phi * 180.0 / math.pi
        self.phi_lbl.setText(f"Phase: {phi_deg:+.3f}°")
        self.state_lbl.setText("ok")
        self.state_lbl.setStyleSheet("color: green; font-size: 12px;")

    def set_error(self, msg: str = "no data") -> None:
        self.r_lbl.setText("R: —")
        self.phi_lbl.setText("Phase: —")
        self.state_lbl.setText(msg)
        self.state_lbl.setStyleSheet("color: red; font-size: 12px;")

    def set_idle(self) -> None:
        self.r_lbl.setText("R: —")
        self.phi_lbl.setText("Phase: —")
        self.state_lbl.setText("idle")
        self.state_lbl.setStyleSheet("color: gray; font-size: 12px;")


class LockinLiveGUI(QWidget):
    """Main widget for live monitoring of UHF/MF lock‑in demodulators."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Lock‑in Live Monitor (UHF/MF)")
        self.setMinimumWidth(760)
        self.setMinimumHeight(520)

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

        # Start/Stop controls
        self.start_btn = QPushButton("Start Live")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)

        self.status_lbl = QLabel("Status: Disconnected")
        self.status_lbl.setWordWrap(True)

        self.demod_count_lbl = QLabel("Readable demods: 0")

        # Timer for periodic updates
        self.timer = QTimer(self)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.poll_and_update)

        # Build UI and wire up signals
        self._build_layout()
        self._wire_events()

    # ---------------- UI ----------------
    def _build_layout(self) -> None:
        root = QVBoxLayout()

        # Connection group
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

        # Control row (Start/Stop and demod count)
        ctl = QHBoxLayout()
        ctl.addWidget(self.start_btn)
        ctl.addWidget(self.stop_btn)
        ctl.addStretch()
        ctl.addWidget(self.demod_count_lbl)
        root.addLayout(ctl)

        # Live output
        live_box = QGroupBox("Live Output (All Readable Demods)")
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

    def _wire_events(self) -> None:
        self.connect_btn.clicked.connect(self.connect_to_server)
        self.refresh_btn.clicked.connect(self.refresh_devices)
        self.start_btn.clicked.connect(self.start_live)
        self.stop_btn.clicked.connect(self.stop_live)

    # ---------------- utility ----------------
    def set_status(self, msg: str) -> None:
        self.status_lbl.setText(f"Status: {msg}")

    def show_error(self, title: str, msg: str) -> None:
        QMessageBox.critical(self, title, msg)

    def clear_demod_rows(self) -> None:
        while self.demod_layout.count():
            item = self.demod_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.demod_rows = {}

    def build_demod_rows(self, demod_indices: List[int]) -> None:
        self.clear_demod_rows()
        for idx in demod_indices:
            row = DemodRow(idx)
            self.demod_layout.addWidget(row)
            self.demod_rows[idx] = row
        self.demod_layout.addStretch()
        self.demod_count_lbl.setText(f"Readable demods: {len(demod_indices)}")

    @staticmethod
    def safe_extract(value) -> float:
        if isinstance(value, (list, tuple)) and len(value) > 0:
            return float(value[0])
        return float(value)

    def read_demod_sample(self, device_id: str, demod_index: int):
        sample_path = f"/{device_id}/demods/{demod_index}/sample"
        try:
            sample = self.session.daq_server.getSample(sample_path)
        except AttributeError:
            # Fallback to older API methods
            try:
                sample = self.session.daq_server.getAsEvent(sample_path)
            except AttributeError:
                result = self.session.daq_server.get(sample_path)
                if result and sample_path in result:
                    sample = result[sample_path]
                else:
                    raise RuntimeError("Unsupported API version or empty sample result")
        except Exception:
            # Fallback again
            result = self.session.daq_server.get(sample_path)
            if result and sample_path in result:
                sample = result[sample_path]
            else:
                raise

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
            # Newer API may nest values under 'value'
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
        # If r is missing, compute from x and y
        if (x != 0.0 or y != 0.0) and r == 0.0:
            r = math.hypot(x, y)
            phi = math.atan2(y, x)
        return r, phi

    # ---------------- LabOne logic ----------------
    def connect_to_server(self) -> None:
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

    def refresh_devices(self) -> None:
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

    def detect_readable_demods(self, device_id: str, max_to_probe: int = 8) -> List[int]:
        """Probe up to ``max_to_probe`` demodulators for availability."""
        found: List[int] = []
        for i in range(max_to_probe):
            base = f"/{device_id}/demods/{i}"
            rate_path = f"{base}/rate"
            # First check whether the demod node exists
            try:
                _ = self.session.daq_server.getDouble(rate_path)
            except Exception:
                continue
            found.append(i)
        return found

    def start_live(self) -> None:
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
            demods = self.detect_readable_demods(device_id, max_to_probe=8)
            if not demods:
                raise RuntimeError("No demods detected on this device.")
            self.available_demods = demods
            self.build_demod_rows(demods)
        except Exception as e:
            self.show_error(
                "Start Failed",
                "Could not prepare live monitor.\n\n"
                f"Device: {device_id}\n\n{e}"
            )
            self.device_id = None
            self.available_demods = []
            self.clear_demod_rows()
            self.demod_count_lbl.setText("Readable demods: 0")
            return
        # Start polling
        self.streaming = True
        self.timer.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.set_status(f"Reading R and phase from {len(demods)} demod(s) on {device_id}")

    def stop_live(self) -> None:
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

    def poll_and_update(self) -> None:
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
            except Exception:
                row.set_error("no data")
        self.set_status(
            f"Reading R and phase from {ok_count}/{len(self.available_demods)} demod(s) on {self.device_id}"
        )

    def closeEvent(self, event):
        try:
            if self.streaming:
                self.stop_live()
        finally:
            event.accept()


def main() -> None:
    app = QApplication(sys.argv)
    w = LockinLiveGUI()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()