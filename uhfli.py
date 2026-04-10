"""
Lock-in Live Monitor (MFLI / UHFLI) - All Demods, R and Phase Only

What this version fixes:
- Keeps the simple device discovery logic that can already see both devices
- Works with either MFLI or UHFLI
- Does NOT fail startup just because one config command is unsupported
- Displays all readable demods
- Shows only amplitude (R) and phase for each demod

Install:
  pip install zhinst-toolkit PyQt5

Run:
  python lockin_all_demods_generic.py
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

    def set_values(self, r: float, phi: float):
        self.r_lbl.setText(f"R: {r:.6e}")
        self.phi_lbl.setText(f"Phase: {phi:+.3f} rad")
        self.state_lbl.setText("ok")
        self.state_lbl.setStyleSheet("color: green; font-size: 12px;")

    def set_error(self, msg: str = "no data"):
        self.r_lbl.setText("R: —")
        self.phi_lbl.setText("Phase: —")
        self.state_lbl.setText(msg)
        self.state_lbl.setStyleSheet("color: red; font-size: 12px;")

    def set_idle(self):
        self.r_lbl.setText("R: —")
        self.phi_lbl.setText("Phase: —")
        self.state_lbl.setText("idle")
        self.state_lbl.setStyleSheet("color: gray; font-size: 12px;")


class LockinLiveGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lock-in Live Monitor (MFLI / UHFLI)")
        self.setMinimumWidth(760)
        self.setMinimumHeight(520)

        # --- State ---
        self.session: Optional[Session] = None
        self.device_id: Optional[str] = None
        self.streaming: bool = False
        self.available_demods: List[int] = []
        self.demod_rows: Dict[int, DemodRow] = {}

        # --- UI widgets ---
        # Keep localhost because the uploaded version that sees both devices uses that.
        self.host_edit = QLineEdit("localhost")
        self.port_edit = QLineEdit("8004")
        self.connect_btn = QPushButton("Connect")
        self.refresh_btn = QPushButton("Refresh Devices")
        self.device_combo = QComboBox()

        # Optional settings. These are now best-effort only.
        self.freq_edit = QLineEdit("1000")
        self.tc_edit = QLineEdit("0.01")
        self.rate_edit = QLineEdit("200")

        self.start_btn = QPushButton("Start Live")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)

        self.status_lbl = QLabel("Status: Disconnected")
        self.status_lbl.setWordWrap(True)

        self.demod_count_lbl = QLabel("Readable demods: 0")

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

        cfg_box = QGroupBox("Optional Settings (best-effort)")
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
        self.demod_count_lbl.setText(f"Readable demods: {len(demod_indices)}")

    @staticmethod
    def safe_extract(value):
        if isinstance(value, (list, tuple)) and len(value) > 0:
            return float(value[0])
        return float(value)

    def try_get_double(self, path: str):
        try:
            return self.session.daq_server.getDouble(path)
        except Exception:
            return None

    def try_set_call(self, func, value=None):
        try:
            if value is None:
                func()
            else:
                func(value)
            return True
        except Exception:
            return False

    def detect_readable_demods(self, device_id: str, max_to_probe: int = 8) -> List[int]:
        """
        Detect demods conservatively:
        - probe demod rate node existence
        - then try reading a sample path
        This avoids assuming too much about MFLI vs UHFLI.
        """
        found = []

        for i in range(max_to_probe):
            base = f"/{device_id}/demods/{i}"
            rate_path = f"{base}/rate"
            sample_path = f"{base}/sample"

            # First check whether the demod node exists at all.
            try:
                _ = self.session.daq_server.getDouble(rate_path)
            except Exception:
                continue

            # If the node exists, count it as available.
            found.append(i)

            # We do not require sample read success at detection time,
            # because some demods may exist but not yet have live data.
            _ = sample_path

        return found

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
        except Exception:
            # One more fallback
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

    # ---------------- LabOne logic ----------------
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

    def apply_best_effort_settings(self, device_id: str, demod_indices: List[int]):
        """
        This is the key fix:
        do not let one setting failure abort MFLI startup.

        We try settings, but we do not require all of them to work.
        """
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

        # Best-effort input enable
        try:
            dev.sigins[0].on(1)
        except Exception:
            pass

        try:
            dev.sigins[0].autorange(1)
        except Exception:
            pass

        # Oscillator frequency best-effort
        try:
            dev.oscs[0].freq(freq)
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

            # These may exist on one setup and not another
            try:
                dev.demods[i].oscselect(0)
            except Exception:
                pass

            try:
                dev.demods[i].adcselect(0)
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
            demods = self.detect_readable_demods(device_id, max_to_probe=8)
            if not demods:
                raise RuntimeError("No demods detected on this device.")

            self.available_demods = demods
            self.build_demod_rows(demods)

            # Best-effort settings: no fatal failure here
            self.apply_best_effort_settings(device_id, demods)

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

        self.streaming = True
        self.timer.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.set_status(f"Reading R and phase from {len(demods)} demod(s) on {device_id}")

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


def main():
    app = QApplication(sys.argv)
    w = LockinLiveGUI()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()