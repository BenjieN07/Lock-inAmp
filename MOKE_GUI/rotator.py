from QCL_interface import *
from cryostat import *


class Rotator(QFrame):
    def __init__(self):
        super().__init__()
        self.show()
        self.initUI()
        self.angle_data = []

    def initUI(self):
        # create main grid to organize layout
        main_grid = QGridLayout()
        main_grid.setSpacing(10)
        self.setLayout(main_grid)

        # create resource manager to connect to the instrument and store resources in a list
        instruments.rm = visa.ResourceManager()
        resources = instruments.rm.list_resources()

        # create a combo box to allow the user to connect with a given instrument then add all resources
        self.connection_box = QComboBox()
        self.connection_box.addItem('Connect to rotator...')
        self.connection_box.addItems(resources)
        self.connection_box.currentIndexChanged.connect(self.connectInstrument)
        main_grid.addWidget(self.connection_box, 0, 0)

        # create a label to show connection of the instrument with check or cross mark
        self.connection_indicator = QLabel(u'\u274c ')  # cross mark by default because not connected yet
        main_grid.addWidget(self.connection_indicator, 0, 1)

        # position labels
        curr_pos = QLabel('Current Position')  # above the slider
        rel_pos = QLabel('Relative Position')  # below slider
        main_grid.addWidget(curr_pos, 1, 0)
        main_grid.addWidget(rel_pos, 3, 0, 1, 1, Qt.AlignBottom)

        # enable/disable button
        self.enable_btn = QPushButton('Enable/Disable')
        self.enable_btn.setEnabled(False)
        self.enable_btn.clicked.connect(self.toggleEnabled)
        main_grid.addWidget(self.enable_btn, 1, 1, 1, 2, Qt.AlignCenter)

        # absolute position slider
        self.abs_pos_sld = QDoubleSlider(Qt.Horizontal)
        self.abs_pos_sld.setTickPosition(QSlider.TicksBelow)
        self.abs_pos_sld.setEnabled(False)
        self.abs_pos_sld.sliderReleased.connect(self.setSliderPos)
        self.abs_pos_sld.setTickInterval(500)
        self.min_pos = QLabel('Min')  # bottom left of slider
        self.max_pos = QLabel('Max')  # bottom right of slider
        slider_vbox = QVBoxLayout()
        slider_vbox.addWidget(self.abs_pos_sld)
        min_max_hbox = QHBoxLayout()
        min_max_hbox.addWidget(self.min_pos)
        min_max_hbox.addStretch()
        min_max_hbox.addWidget(self.max_pos)
        slider_vbox.addLayout(min_max_hbox)
        main_grid.addLayout(slider_vbox, 2, 0)

        # absolute position spin box
        self.abs_pos_sb = QDoubleSpinBox()  # right of slider
        self.abs_pos_sb.setDecimals(4)
        self.abs_pos_sb.setSingleStep(0.0001)
        self.abs_pos_sb.setEnabled(False)
        self.abs_pos_sb.editingFinished.connect(self.setSpinboxPos)
        main_grid.addWidget(self.abs_pos_sb, 2, 1)

        # led indicator
        self.rotr_ind = QLedIndicator('orange')
        main_grid.addWidget(self.rotr_ind, 2, 2)

        # relative position buttons and spinbox
        self.rel_left = QPushButton(u'\u25C0')  # left of relative position spinbox
        self.rel_left.setFixedWidth(20)
        self.rel_left.clicked.connect(self.moveRelLeft)
        self.rel_right = QPushButton(u'\u25B6')  # right of relative position spinbox
        self.rel_right.setFixedWidth(20)
        self.rel_right.clicked.connect(self.moveRelRight)
        self.rel_left.setEnabled(False)
        self.rel_right.setEnabled(False)
        self.rel_pos_sb = QDoubleSpinBox()  # below slider
        self.rel_pos_sb.setDecimals(4)
        self.rel_pos_sb.setSingleStep(0.0001)
        self.rel_pos_sb.setAlignment(Qt.AlignHCenter)
        rel_pos_hbox = QHBoxLayout()
        rel_pos_hbox.addWidget(self.rel_left)
        rel_pos_hbox.addWidget(self.rel_pos_sb)
        rel_pos_hbox.addWidget(self.rel_right)
        main_grid.addLayout(rel_pos_hbox, 4, 0, 2, 1)

        # led indicator and current state labels
        curr_state_head = QLabel('Current State')
        self.curr_state = QLineEdit('')
        self.curr_state.setAlignment(Qt.AlignHCenter)
        self.curr_state.setReadOnly(True)
        main_grid.addWidget(curr_state_head, 4, 1, 1, 2, Qt.AlignBottom | Qt.AlignHCenter)
        main_grid.addWidget(self.curr_state, 5, 1, 1, 2, Qt.AlignTop | Qt.AlignHCenter)

    def connectInstrument(self):
        # if a selection is chosen that is not just the default prompt
        if (self.connection_box.currentText() != 'Connect to rotator...'):
            # get the chopper name and connect the chopper
            rotr_name = self.connection_box.currentText()

            if rotr_name[:4] == 'GPIB':
                return  # rotator can't be a GPIB port, so exit function

            instruments.rotr = instruments.rm.open_resource(rotr_name)

            # set baud rate to 921600 by default
            instruments.rotr.baud_rate = 921600

            left_lim = float(instruments.rotr.query('1SL?')[3:])
            right_lim = float(instruments.rotr.query('1SR?')[3:])

            self.abs_pos_sb.setRange(left_lim, right_lim)
            self.rel_pos_sb.setRange(left_lim, right_lim)
            self.abs_pos_sld.setRange(left_lim, right_lim)

            self.min_pos.setText(str(left_lim))
            self.max_pos.setText(str(right_lim))

            self.updatePosDisplay()

            # store controller states to tell when rotator is moving, disabled, ready, etc.
            self.controller_states = {'0a': 'NOT REFERENCED from reset',
                                      '0b': 'NOT REFERENCED from HOMING',
                                      '0c': 'NOT REFERENCED from CONFIGURATION',
                                      '0d': 'NOT REFERENCED from DISABLE',
                                      '0e': 'NOT REFERENCED from READY',
                                      '0f': 'NOT REFERENCED from MOVING',
                                      '10': 'NOT REFERENCED no parameters',
                                      '14': 'CONFIGURATION',
                                      '1e': 'HOMING',
                                      '28': 'MOVING',
                                      '32': 'READY from HOMING',
                                      '33': 'READY from MOVING',
                                      '34': 'READY from DISABLE',
                                      '3c': 'DISABLE from READY',
                                      '3d': 'DISABLE from MOVING'}

            # change connection indicator to a check mark from a cross mark
            self.connection_indicator.setText(u'\u2705')

            # turn led indicator on and set appropriate color based on state
            ctrl_state = self.controller_states[instruments.rotr.query('1mm?')[3:].strip()]
            self.ready = (ctrl_state.split(' ')[0] == 'READY')

            if (self.ready):
                self.rotr_ind.changeColor('green')
                # enable position spinbox, slider, and buttons
                self.abs_pos_sb.setEnabled(True)
                self.abs_pos_sld.setEnabled(True)
                self.rel_left.setEnabled(True)
                self.rel_right.setEnabled(True)
                self.enable_btn.setText('Disable')
            else:
                self.enable_btn.setText('Enable')

            self.rotr_ind.setChecked(True)
            self.enable_btn.setEnabled(True)

            # update controller state every second (1000 ms)
            self.timer = QTimer()
            self.timer.timeout.connect(self.updateState)
            self.timer.start(1000)

    def moveRelLeft(self):
        val = self.rel_pos_sb.value() * (-1)
        instruments.rotr.write('1PR{}'.format(val))
        self.updatePosDisplay()

    def moveRelRight(self):
        val = self.rel_pos_sb.value()
        instruments.rotr.write('1PR{}'.format(val))
        self.updatePosDisplay()

    def setSpinboxPos(self):
        val = self.abs_pos_sb.value()
        self.abs_pos_sld.setValue(val)
        self.angle_data.append(val)
        instruments.rotr.write('1PA{}'.format(val))

    def setSliderPos(self):
        val = self.abs_pos_sld.value()
        self.abs_pos_sb.setValue(val)
        self.angle_data.append(val)
        instruments.rotr.write('1PA{}'.format(val))

    def updateState(self):
        ctrl_state = self.controller_states[instruments.rotr.query('1mm?')[3:].strip()]
        self.curr_state.setText(ctrl_state)
        self.ready = (ctrl_state.split(' ')[0] == 'READY')

        if (self.ready):
            # enable position spinbox, slider, and buttons
            self.abs_pos_sb.setEnabled(True)
            self.abs_pos_sld.setEnabled(True)
            self.rel_left.setEnabled(True)
            self.rel_right.setEnabled(True)
        else:
            # disable position spinbox, slider, and buttons
            self.abs_pos_sb.setEnabled(False)
            self.abs_pos_sld.setEnabled(False)
            self.rel_left.setEnabled(False)
            self.rel_right.setEnabled(False)

    def updatePosDisplay(self):
        abs_pos = float(instruments.rotr.query('1PA?')[3:])
        self.abs_pos_sb.setValue(abs_pos)
        self.abs_pos_sld.setValue(abs_pos)

    def toggleEnabled(self):
        ctrl_state = self.controller_states[instruments.rotr.query('1mm?')[3:].strip()]

        if (self.ready or ctrl_state == 'MOVING'):  # disable, then change text to enable
            instruments.rotr.write('1mm0')
            self.enable_btn.setText('Enable')
            self.rotr_ind.changeColor('orange')
        else:  # enable, then change text to disable
            instruments.rotr.write('1mm1')
            self.enable_btn.setText('Disable')
            self.rotr_ind.changeColor('green')


class QDoubleSlider(QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.decimals = 4
        self._max_int = 10 ** self.decimals

        super().setMinimum(0)
        super().setMaximum(self._max_int)

        self._min_value = 0.0
        self._max_value = 1.0

    @property
    def _value_range(self):
        return self._max_value - self._min_value

    def value(self):
        return float(super().value()) / self._max_int * self._value_range + self._min_value

    def setValue(self, value):
        super().setValue(int((value - self._min_value) / self._value_range * self._max_int))

    def setMinimum(self, value):
        if value > self._max_value:
            raise ValueError("Minimum limit cannot be higher than maximum")

        self._min_value = value
        self.setValue(self.value())

    def setMaximum(self, value):
        if value < self._min_value:
            raise ValueError("Minimum limit cannot be higher than maximum")

        self._max_value = value
        self.setValue(self.value())

    def setRange(self, minval, maxval):
        self.setMinimum(minval)
        self.setMaximum(maxval)

    def minimum(self):
        return self._min_value

    def maximum(self):
        return self._max_value

    def setDecimals(self, value):
        if type(value != int):
            raise ValueError('Number of decimals must be an int')
        else:
            self.decimals = value


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
    window = Rotator()
    sys.exit(app.exec_())