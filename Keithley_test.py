from pymeasure.instruments.keithley.keithley2450 import *
from pymeasure.instruments.keithley.keithley2400 import *
import pyvisa
from QCL_interface import *

"""
rm = pyvisa.ResourceManager()
print(rm.list_resources())

keithley = Keithley2450("GPIB::18")

keithley.apply_current()
keithley.source_current_range = 10e-3
keithley.compliance_voltage = 10
keithley.source_current = 0
keithley.enable_source()

keithley.measure_voltage()
keithley.ramp_to_current(5e-3)
print(keithley.voltage)

keithley.shutdown()
"""

class Keithley(QFrame):
    def __init__(self):
        super().__init__()
        self.setGeometry(700, 400, 500, 450)
        # self.show()
        self.initUI()
        self.setWindowTitle("Keithley")
        self.enabled = False
        self.connected = False

    def initUI(self):
        # create main grid to organize layout
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)

        # create resource manager to connect to the instrument and store resources in a list
        instruments.rm = visa.ResourceManager()
        resources = instruments.rm.list_resources()
        resource = []
        for i in range(len(resources)):
            resource.append(resources[i])
            if resource[i] == "GPIB0::18::INSTR":
                resource[i] += " (default)"

        # create a combo box to allow the user to connect with a given instrument then add all resources
        self.connection_box = QComboBox()
        self.connection_box.addItem('Connect to keithley...')
        self.connection_box.addItems(resource)
        self.connection_box.currentIndexChanged.connect(self.connectInstrument)
        main_grid.addWidget(self.connection_box, 0, 0, 1, 1, Qt.AlignCenter)

        # create a label to show connection of the instrument with check or cross mark
        self.connection_indicator = QLabel(u'\u274c ')  # cross mark by default because not connected yet
        main_grid.addWidget(self.connection_indicator, 0, 1, 1, 1, Qt.AlignLeft)

        self.keitheley_selection_box = QComboBox()
        self.keitheley_selection_box.addItem("Keithley 2450")
        self.keitheley_selection_box.addItem("Keithley 2400")
        main_grid.addWidget(self.keitheley_selection_box, 0, 2, 1, 1, Qt.AlignCenter)

        I_lb = QLabel("Current")
        V_lb = QLabel("Voltage")
        # R_lb = QLabel("Resistance (ohm)")
        main_grid.addWidget(I_lb, 1, 0, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(V_lb, 1, 1, 1, 1, Qt.AlignCenter)
        # main_grid.addWidget(R_lb, 1, 2, 1, 1, Qt.AlignCenter)

        self.I_value_lb = QLabel("")
        self.V_value_lb = QLabel("")
        self.R_value_lb = QLabel("")
        main_grid.addWidget(self.I_value_lb, 2, 0, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.V_value_lb, 2, 1, 1, 1, Qt.AlignCenter)
        main_grid.addWidget(self.R_value_lb, 2, 2, 1, 1, Qt.AlignCenter)

        self.current_rb = QRadioButton("Apply current")
        self.current_rb.clicked.connect(self.select_mode)
        self.current_rb.setEnabled(False)
        main_grid.addWidget(self.current_rb, 3, 0, 1, 1, Qt.AlignCenter)

        source_current_hbox = QHBoxLayout()
        source_current_lb = QLabel("Source current ")
        self.source_current_sb = QDoubleSpinBox()
        self.source_current_sb.setDecimals(3)
        self.source_current_sb.setEnabled(False)
        source_current_unit_lb = QLabel("A")
        source_current_hbox.addWidget(source_current_lb)
        source_current_hbox.addWidget(self.source_current_sb)
        source_current_hbox.addWidget(source_current_unit_lb)
        main_grid.addLayout(source_current_hbox, 4, 0, 1, 2, Qt.AlignCenter)
        compliance_voltage_hbox = QHBoxLayout()
        compliance_voltage_lb = QLabel("Compliance voltage ")
        self.compliance_voltage_sb = QDoubleSpinBox()
        self.compliance_voltage_sb.setDecimals(3)
        self.compliance_voltage_sb.setEnabled(False)
        compliance_voltage_unit_lb = QLabel("V")
        compliance_voltage_hbox.addWidget(compliance_voltage_lb)
        compliance_voltage_hbox.addWidget(self.compliance_voltage_sb)
        compliance_voltage_hbox.addWidget(compliance_voltage_unit_lb)
        main_grid.addLayout(compliance_voltage_hbox, 4, 2, 1, 2, Qt.AlignCenter)

        source_current_range_hbox = QHBoxLayout()
        source_current_range_lb = QLabel("Source current range")
        self.source_current_range_sb = QDoubleSpinBox()
        self.source_current_range_sb.setDecimals(3)
        self.source_current_range_sb.setRange(0, 1.05)
        self.source_current_range_sb.setEnabled(False)
        source_current_range_unit_lb = QLabel("A")
        source_current_range_hbox.addWidget(source_current_range_lb)
        source_current_range_hbox.addWidget(self.source_current_range_sb)
        source_current_range_hbox.addWidget(source_current_range_unit_lb)
        main_grid.addLayout(source_current_range_hbox, 5, 0, 1, 4, Qt.AlignCenter)

        self.voltage_rb = QRadioButton("Apply voltage")
        self.voltage_rb.clicked.connect(self.select_mode)
        self.voltage_rb.setEnabled(False)
        main_grid.addWidget(self.voltage_rb, 6, 0, 1, 1, Qt.AlignCenter)

        source_voltage_hbox = QHBoxLayout()
        source_voltage_lb = QLabel("Source voltage ")
        self.source_voltage_sb = QDoubleSpinBox()
        self.source_voltage_sb.setDecimals(3)
        self.source_voltage_sb.setEnabled(False)
        source_voltage_unit_lb = QLabel("V")
        source_voltage_hbox.addWidget(source_voltage_lb)
        source_voltage_hbox.addWidget(self.source_voltage_sb)
        source_voltage_hbox.addWidget(source_voltage_unit_lb)
        main_grid.addLayout(source_voltage_hbox, 7, 0, 1, 2, Qt.AlignCenter)
        compliance_current_hbox = QHBoxLayout()
        compliance_current_lb = QLabel("Compliance current ")
        self.compliance_current_sb = QDoubleSpinBox()
        self.compliance_current_sb.setDecimals(3)
        self.compliance_current_sb.setEnabled(False)
        compliance_current_unit_lb = QLabel("A")
        compliance_current_hbox.addWidget(compliance_current_lb)
        compliance_current_hbox.addWidget(self.compliance_current_sb)
        compliance_current_hbox.addWidget(compliance_current_unit_lb)
        main_grid.addLayout(compliance_current_hbox, 7, 2, 1, 2, Qt.AlignCenter)

        source_voltage_range_hbox = QHBoxLayout()
        source_voltage_range_lb = QLabel("Source voltage range")
        self.source_voltage_range_sb = QDoubleSpinBox()
        self.source_voltage_range_sb.setDecimals(3)
        self.source_voltage_range_sb.setRange(0, 210)
        self.source_voltage_range_sb.setEnabled(False)
        source_voltage_range_unit_lb = QLabel("V")
        source_voltage_range_hbox.addWidget(source_voltage_range_lb)
        source_voltage_range_hbox.addWidget(self.source_voltage_range_sb)
        source_voltage_range_hbox.addWidget(source_voltage_range_unit_lb)
        main_grid.addLayout(source_voltage_range_hbox, 8, 0, 1, 4, Qt.AlignCenter)

        self.auto_range_btn = QPushButton("Auto source range")
        self.auto_range_btn.setEnabled(False)
        main_grid.addWidget(self.auto_range_btn, 9, 0, 1, 2, Qt.AlignCenter)

        enable_hbox = QHBoxLayout()
        self.enable_btn = QPushButton('Enable/Disable')
        self.enable_btn.setEnabled(False)
        self.enable_btn.clicked.connect(self.toggleEnabled)
        enable_hbox.addWidget(self.enable_btn)
        self.enable_ind = QLedIndicator('orange')
        enable_hbox.addWidget(self.enable_ind)
        main_grid.addLayout(enable_hbox, 9, 2, 1, 2, Qt.AlignCenter)

        ramp_lb = QLabel("Ramp")
        main_grid.addWidget(ramp_lb, 10, 0, 1, 1, Qt.AlignCenter)

        ramp_step_current_hbox = QHBoxLayout()
        ramp_step_current_lb = QLabel("Number of ramp steps ")
        self.ramp_step_current_sb = QSpinBox()
        self.ramp_step_current_sb.setEnabled(False)
        self.ramp_step_current_sb.setRange(1, 1000)
        self.ramp_step_current_sb.setValue(30)
        ramp_step_current_hbox.addWidget(ramp_step_current_lb)
        ramp_step_current_hbox.addWidget(self.ramp_step_current_sb)
        main_grid.addLayout(ramp_step_current_hbox, 11, 0, 1, 1, Qt.AlignCenter)
        ramp_to_current_hbox = QHBoxLayout()
        ramp_to_current_lb = QLabel("Ramp to current ")
        self.ramp_to_current_sb = QDoubleSpinBox()
        self.ramp_to_current_sb.setDecimals(3)
        self.ramp_to_current_sb.setEnabled(False)
        self.ramp_to_current_sb.editingFinished.connect(self.current_ramp)
        ramp_to_current_unit_lb = QLabel("A")
        ramp_to_current_hbox.addWidget(ramp_to_current_lb)
        ramp_to_current_hbox.addWidget(self.ramp_to_current_sb)
        ramp_to_current_hbox.addWidget(ramp_to_current_unit_lb)
        main_grid.addLayout(ramp_to_current_hbox, 11, 2, 1, 1, Qt.AlignCenter)
        ramp_pause_current_hbox = QHBoxLayout()
        ramp_pause_current_lb = QLabel("Pause ")
        self.ramp_pause_current_sb = QDoubleSpinBox()
        self.ramp_pause_current_sb.setDecimals(2)
        self.ramp_pause_current_sb.setValue(0.02)
        self.ramp_pause_current_sb.setEnabled(False)
        ramp_pause_current_unit_lb = QLabel("sec")
        ramp_pause_current_hbox.addWidget(ramp_pause_current_lb)
        ramp_pause_current_hbox.addWidget(self.ramp_pause_current_sb)
        ramp_pause_current_hbox.addWidget(ramp_pause_current_unit_lb)
        main_grid.addLayout(ramp_pause_current_hbox, 11, 1, 1, 1, Qt.AlignCenter)

        ramp_step_voltage_hbox = QHBoxLayout()
        ramp_step_voltage_lb = QLabel("Number of ramp steps ")
        self.ramp_step_voltage_sb = QSpinBox()
        self.ramp_step_voltage_sb.setEnabled(False)
        self.ramp_step_voltage_sb.setRange(1, 1000)
        self.ramp_step_voltage_sb.setValue(30)
        ramp_step_voltage_hbox.addWidget(ramp_step_voltage_lb)
        ramp_step_voltage_hbox.addWidget(self.ramp_step_voltage_sb)
        main_grid.addLayout(ramp_step_voltage_hbox, 12, 0, 1, 1, Qt.AlignCenter)
        ramp_to_voltage_hbox = QHBoxLayout()
        ramp_to_voltage_lb = QLabel("Ramp to voltage ")
        self.ramp_to_voltage_sb = QDoubleSpinBox()
        self.ramp_to_voltage_sb.setDecimals(3)
        self.ramp_to_voltage_sb.setEnabled(False)
        self.ramp_to_voltage_sb.editingFinished.connect(self.voltage_ramp)
        ramp_to_voltage_unit_lb = QLabel("V")
        ramp_to_voltage_hbox.addWidget(ramp_to_voltage_lb)
        ramp_to_voltage_hbox.addWidget(self.ramp_to_voltage_sb)
        ramp_to_voltage_hbox.addWidget(ramp_to_voltage_unit_lb)
        main_grid.addLayout(ramp_to_voltage_hbox, 12, 2, 1, 1, Qt.AlignCenter)
        ramp_pause_voltage_hbox = QHBoxLayout()
        ramp_pause_voltage_lb = QLabel("Pause ")
        self.ramp_pause_voltage_sb = QDoubleSpinBox()
        self.ramp_pause_voltage_sb.setDecimals(2)
        self.ramp_pause_voltage_sb.setValue(0.02)
        self.ramp_pause_voltage_sb.setEnabled(False)
        ramp_pause_voltage_unit_lb = QLabel("sec")
        ramp_pause_voltage_hbox.addWidget(ramp_pause_voltage_lb)
        ramp_pause_voltage_hbox.addWidget(self.ramp_pause_voltage_sb)
        ramp_pause_voltage_hbox.addWidget(ramp_pause_voltage_unit_lb)
        main_grid.addLayout(ramp_pause_voltage_hbox, 12, 1, 1, 1, Qt.AlignCenter)

    def connectInstrument(self):
        # if a selection is chosen that is not just the default prompt
        if (self.connection_box.currentText() != 'Connect to keithley...'):
            # get the chopper name and connect the chopper
            if self.connection_box.currentText()[-1] == ")":
                keithley_name = self.connection_box.currentText()[:-10]
            else:
                keithley_name = self.connection_box.currentText()

            try:
                if self.keitheley_selection_box.currentText() == "Keithley 2450":
                    self.keithley = Keithley2450(keithley_name)
                elif self.keitheley_selection_box.currentText() == "Keithley 2400":
                    self.keithley = Keithley2400(keithley_name)
                self.keithley.apply_current()
                self.connected = True
            except:
                self.connection_indicator.setText(u'\u274c ')
                self.connected = False
                #self.enable_ind.changeColor('orange')
                self.enable_btn.setText('Enable/Disable')
                self.enable_ind.setChecked(False)
                self.enable_btn.setEnabled(False)
                self.disable_all()
                self.connected = False
                return

            # change connection indicator to a check mark from a cross mark
            self.connection_indicator.setText(u'\u2705')
            self.connected = True

            self.enable_btn.setText('Enable')
            self.enable_ind.setChecked(True)
            self.enable_btn.setEnabled(True)
            self.current_rb.setEnabled(True)
            self.voltage_rb.setEnabled(True)
            self.auto_range_btn.setEnabled(True)

            self.keithley.auto_range_source()
            self.source_current_range_sb.setValue(self.keithley.source_current_range)
            self.source_voltage_range_sb.setValue(self.keithley.source_voltage_range)
            self.compliance_current_sb.setRange(-1.05, 1.05)
            self.compliance_voltage_sb.setRange(-210, 210)
            self.source_current_sb.setRange(-1.05, 1.05)
            self.source_voltage_sb.setRange(-210, 210)
            self.ramp_to_current_sb.setRange(-1.05, 1.05)
            self.ramp_to_voltage_sb.setRange(-210, 210)

            # self.keithley.measure_resistance()
            # self.R_value_lb.setText(str(self.keithley.resistance))

            # update I, V, R every second (1000 ms)
            self.timer = QTimer()
            self.timer.timeout.connect(self.updateIVR)
            self.timer.start(1500)

    def disable_all(self):
        self.current_rb.setEnabled(False)
        self.voltage_rb.setEnabled(False)
        self.source_current_sb.setEnabled(False)
        self.compliance_current_sb.setEnabled(False)
        self.ramp_step_current_sb.setEnabled(False)
        self.ramp_to_current_sb.setEnabled(False)
        self.ramp_pause_current_sb.setEnabled(False)
        self.source_current_range_sb.setEnabled(False)
        self.source_voltage_sb.setEnabled(False)
        self.compliance_voltage_sb.setEnabled(False)
        self.ramp_step_voltage_sb.setEnabled(False)
        self.ramp_to_voltage_sb.setEnabled(False)
        self.ramp_pause_voltage_sb.setEnabled(False)
        self.source_voltage_range_sb.setEnabled(False)
        self.auto_range_btn.setEnabled(False)

    def select_mode(self):
        if self.current_rb.isChecked():
            self.source_current_sb.setEnabled(True)
            self.compliance_voltage_sb.setEnabled(True)
            self.source_current_range_sb.setEnabled(True)
            self.source_voltage_sb.setEnabled(False)
            self.source_voltage_range_sb.setEnabled(False)
            self.compliance_current_sb.setEnabled(False)
        else:
            self.source_current_sb.setEnabled(False)
            self.compliance_voltage_sb.setEnabled(False)
            self.source_current_range_sb.setEnabled(False)
            self.source_voltage_sb.setEnabled(True)
            self.source_voltage_range_sb.setEnabled(True)
            self.compliance_current_sb.setEnabled(True)

    def enable_source(self):
        if not self.current_rb.isChecked() and not self.voltage_rb.isChecked():
            QMessageBox.warning(self, "mode", "You haven't selected to apply current or voltage!")
            return
        elif self.current_rb.isChecked():
            if abs(self.source_current_sb.value()) > self.source_current_range_sb.value():
                QMessageBox.warning(self, "Current overflow", "Input current is out of range!")
                return
            self.keithley.apply_current()
            self.keithley.source_current_range = self.source_current_range_sb.value()
            self.keithley.source_current = self.source_current_sb.value()
            self.keithley.compliance_voltage = self.compliance_voltage_sb.value()
        else:
            if abs(self.source_voltage_sb.value()) > self.source_voltage_range_sb.value():
                QMessageBox.warning(self, "Voltage overflow", "Input voltage is out of range!")
                return
            self.keithley.apply_voltage()
            self.keithley.source_voltage_range = self.source_voltage_range_sb.value()
            self.keithley.source_voltage = self.source_voltage_sb.value()
            self.keithley.compliance_current = self.compliance_current_sb.value()

    def toggleEnabled(self):
        if (self.enabled == True):  # disable, then change text to enable
            self.keithley.shutdown()
            self.enable_btn.setText('Enable')
            self.enable_ind.changeColor('orange')
            self.enabled = False
            self.ramp_step_current_sb.setEnabled(False)
            self.ramp_step_voltage_sb.setEnabled(False)
            self.ramp_to_voltage_sb.setEnabled(False)
            self.ramp_to_current_sb.setEnabled(False)
            self.ramp_pause_voltage_sb.setEnabled(False)
            self.ramp_pause_current_sb.setEnabled(False)
        else:  # enable, then change text to disable
            self.enable_source()
            self.keithley.enable_source()
            self.enable_btn.setText('Disable')
            self.enable_ind.changeColor('green')
            self.enabled = True
            self.ramp_step_current_sb.setEnabled(True)
            self.ramp_step_voltage_sb.setEnabled(True)
            self.ramp_to_voltage_sb.setEnabled(True)
            self.ramp_to_current_sb.setEnabled(True)
            self.ramp_pause_current_sb.setEnabled(True)
            self.ramp_pause_voltage_sb.setEnabled(True)
            self.ramp_to_current_sb.setRange(-self.keithley.source_current_range, self.keithley.source_current_range)
            self.ramp_to_voltage_sb.setRange(-self.keithley.source_voltage_range, self.keithley.source_voltage_range)

    def current_ramp(self):
        self.keithley.ramp_to_current(self.ramp_to_current_sb.value(), self.ramp_step_current_sb.value(), self.ramp_pause_current_sb.value())

    def voltage_ramp(self):
        self.keithley.ramp_to_voltage(self.ramp_to_voltage_sb.value(), self.ramp_step_voltage_sb.value(), self.ramp_pause_voltage_sb.value())

    def updateIVR(self):
        self.keithley.measure_current()
        if self.keithley.current < 1e-9:
            self.I_value_lb.setText(str(round(self.keithley.current*1e9, 6)) + " nA")
        elif self.keithley.current < 1e-6:
            self.I_value_lb.setText(str(round(self.keithley.current*1e6, 6)) + " uA")
        elif self.keithley.current < 1e-3:
            self.I_value_lb.setText(str(round(self.keithley.current*1e3, 6)) + " mA")
        else:
            self.I_value_lb.setText(str(round(self.keithley.current, 6)) + " A")
        self.keithley.measure_voltage()
        if self.keithley.voltage < 1e-9:
            self.V_value_lb.setText(str(round(self.keithley.voltage*1e9, 6)) + " nV")
        elif self.keithley.voltage < 1e-6:
            self.V_value_lb.setText(str(round(self.keithley.voltage*1e6, 6)) + " uV")
        elif self.keithley.voltage < 1e-3:
            self.V_value_lb.setText(str(round(self.keithley.voltage*1e3, 6)) + " mV")
        else:
            self.V_value_lb.setText(str(round(self.keithley.voltage, 6)) + " V")
        #self.keithley.measure_resistance()
        #self.R_value_lb.setText(str(self.keithley.resistance))

# from https://github.com/nlamprian/pyqt5-led-indicator-widget/blob/master/LedIndicatorWidget.py
class QLedIndicator(QAbstractButton):
    scaledSize = 1000.0

    def __init__(self, color='green', parent=None):  # added a color option to use red or orange
        QAbstractButton.__init__(self, parent)

        self.setMinimumSize(24, 24)
        self.setCheckable(True)

        # prevent user from changing indicator color by clicking
        self.setEnabled(False)

        if color.lower() == 'red':
            self.on_color_1 = QColor(255, 0, 0)
            self.on_color_2 = QColor(192, 0, 0)
            self.off_color_1 = QColor(28, 0, 0)
            self.off_color_2 = QColor(128, 0, 0)
        elif color.lower() == 'orange':
            self.on_color_1 = QColor(255, 175, 0)
            self.on_color_2 = QColor(170, 115, 0)
            self.off_color_1 = QColor(90, 60, 0)
            self.off_color_2 = QColor(150, 100, 0)
        else:  # default to green if user does not give valid option
            self.on_color_1 = QColor(0, 255, 0)
            self.on_color_2 = QColor(0, 192, 0)
            self.off_color_1 = QColor(0, 28, 0)
            self.off_color_2 = QColor(0, 128, 0)

    def changeColor(self, color):
        '''change color by inputting a string only for red, orange, and green'''
        if color.lower() == 'red':
            self.on_color_1 = QColor(255, 0, 0)
            self.on_color_2 = QColor(192, 0, 0)
            self.off_color_1 = QColor(28, 0, 0)
            self.off_color_2 = QColor(128, 0, 0)
        elif color.lower() == 'orange':
            self.on_color_1 = QColor(255, 175, 0)
            self.on_color_2 = QColor(170, 115, 0)
            self.off_color_1 = QColor(90, 60, 0)
            self.off_color_2 = QColor(150, 100, 0)
        elif color.lower() == 'green':
            self.on_color_1 = QColor(0, 255, 0)
            self.on_color_2 = QColor(0, 192, 0)
            self.off_color_1 = QColor(0, 28, 0)
            self.off_color_2 = QColor(0, 128, 0)

        self.update()

    def resizeEvent(self, QResizeEvent):
        self.update()

    def paintEvent(self, QPaintEvent):
        realSize = min(self.width(), self.height())

        painter = QPainter(self)
        pen = QPen(Qt.black)
        pen.setWidth(1)

        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(realSize / self.scaledSize, realSize / self.scaledSize)

        gradient = QRadialGradient(QPointF(-500, -500), 1500, QPointF(-500, -500))
        gradient.setColorAt(0, QColor(224, 224, 224))
        gradient.setColorAt(1, QColor(28, 28, 28))
        painter.setPen(pen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QPointF(0, 0), 500, 500)

        gradient = QRadialGradient(QPointF(500, 500), 1500, QPointF(500, 500))
        gradient.setColorAt(0, QColor(224, 224, 224))
        gradient.setColorAt(1, QColor(28, 28, 28))
        painter.setPen(pen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QPointF(0, 0), 450, 450)

        painter.setPen(pen)
        if self.isChecked():
            gradient = QRadialGradient(QPointF(-500, -500), 1500, QPointF(-500, -500))
            gradient.setColorAt(0, self.on_color_1)
            gradient.setColorAt(1, self.on_color_2)
        else:
            gradient = QRadialGradient(QPointF(500, 500), 1500, QPointF(500, 500))
            gradient.setColorAt(0, self.off_color_1)
            gradient.setColorAt(1, self.off_color_2)

        painter.setBrush(gradient)
        painter.drawEllipse(QPointF(0, 0), 400, 400)

    @pyqtProperty(QColor)
    def onColor1(self):
        return self.on_color_1

    @onColor1.setter
    def onColor1(self, color):
        self.on_color_1 = color

    @pyqtProperty(QColor)
    def onColor2(self):
        return self.on_color_2

    @onColor2.setter
    def onColor2(self, color):
        self.on_color_2 = color

    @pyqtProperty(QColor)
    def offColor1(self):
        return self.off_color_1

    @offColor1.setter
    def offColor1(self, color):
        self.off_color_1 = color

    @pyqtProperty(QColor)
    def offColor2(self):
        return self.off_color_2

    @offColor2.setter
    def offColor2(self, color):
        self.off_color_2 = color

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Keithley()
    sys.exit(app.exec_())
