import ctypes

from QCL_interface import *
from ctypes import *
import arrow_rc
from ctypes import*                         # import ctypes (used to call DLL functions)
import sys
import win32com.client
import psutil
import time
import os
from get_project_path import cwd_path

class Translator(QFrame):
    def __init__(self):
        super().__init__()
        self.Tango = windll.LoadLibrary(r"{}\Tango_DLL.dll".format(cwd_path))  # give location of dll (current directory)
        self.LSID = c_int()
        self.trans_name = ""
        self.in_Opus = False
        self.connected = False
        self.show()
        self.initUI()
        self.x = self.get_x_pos()
        self.y = self.get_y_pos()
        self.z = self.get_z_pos()
        self.x_home = self.get_x_pos()
        self.y_home = self.get_y_pos()
        self.z_home = self.get_z_pos()

    def initUI(self):
        # create main grid to organize layout
        main_grid = QGridLayout()
        main_grid.setSpacing(5)
        self.setLayout(main_grid)

        # create resource manager to connect to the instrument and store resources in a list
        instruments.rm = visa.ResourceManager()
        resources = instruments.rm.list_resources()

        # create a combo box to allow the user to connect with a given instrument then add all resources
        self.connection_box = QComboBox()
        self.connection_box.addItem('Connect to translator...')
        self.connection_box.addItems(resources)
        self.connection_box.currentIndexChanged.connect(self.connectInstrument)
        main_grid.addWidget(self.connection_box, 0, 2)

        # create a label to show connection of the instrument with check or cross mark
        self.connection_indicator = QLabel(u'\u274c ')  # cross mark by default because not connected yet
        main_grid.addWidget(self.connection_indicator, 0, 3)

        # reconnect/disconnect button
        self.connect_btn = QPushButton('Reconnect/Disconnect')
        self.connect_btn.setEnabled(False)
        self.connect_btn.clicked.connect(self.swicthConnection)
        main_grid.addWidget(self.connect_btn, 2, 2, Qt.AlignCenter)

        # set position label
        enter_pos = QLabel('Active / Position')  # above the slider
        main_grid.addWidget(enter_pos, 0, 0)

        # set xyz check boxes
        self.x_check_box = QCheckBox()
        self.x_check_box.setText(f"X ({chr(956)}m)")
        self.x_check_box.setEnabled(False)
        main_grid.addWidget(self.x_check_box, 1, 0, 1, 1, Qt.AlignCenter)
        self.y_check_box = QCheckBox()
        self.y_check_box.setText(f"Y ({chr(956)}m)")
        self.y_check_box.setEnabled(False)
        main_grid.addWidget(self.y_check_box, 2, 0, 1, 1, Qt.AlignCenter)
        self.z_check_box = QCheckBox()
        self.z_check_box.setText(f"Z ({chr(956)}m)")
        self.z_check_box.setEnabled(False)
        main_grid.addWidget(self.z_check_box, 3, 0, 1, 1, Qt.AlignCenter)

        # set xyz spin boxes
        self.x_sb = QDoubleSpinBox()
        self.x_sb.setDecimals(2)
        self.x_sb.setValue(0.00)
        self.x_sb.setEnabled(False)
        main_grid.addWidget(self.x_sb, 1, 1, Qt.AlignCenter)
        self.y_sb = QDoubleSpinBox()
        self.y_sb.setDecimals(2)
        self.y_sb.setValue(0.00)
        self.y_sb.setEnabled(False)
        main_grid.addWidget(self.y_sb, 2, 1, Qt.AlignCenter)
        self.z_sb = QDoubleSpinBox()
        self.z_sb.setDecimals(2)
        self.z_sb.setValue(0.00)
        self.z_sb.setEnabled(False)
        main_grid.addWidget(self.z_sb, 3, 1, Qt.AlignCenter)

        # enable/disable button
        self.enable_btn = QPushButton('Enable/Disable')
        self.enable_btn.setEnabled(False)
        self.enable_btn.clicked.connect(self.toggleEnabled)
        main_grid.addWidget(self.enable_btn, 3, 2, Qt.AlignCenter)

        # led indicator
        self.trans_ind = QLedIndicator('orange')
        main_grid.addWidget(self.trans_ind, 3, 3)

        # Move and Set / Get labels
        move = QLabel('Move')
        main_grid.addWidget(move, 4, 0)
        setget = QLabel('Set / Get')
        main_grid.addWidget(setget, 4, 1)

        # buttons under Move
        self.absolute_btn = QPushButton('Absolute')
        self.absolute_btn.setEnabled(False)
        self.absolute_btn.clicked.connect(self.absolute)
        main_grid.addWidget(self.absolute_btn, 5, 0, Qt.AlignCenter)
        self.relative_btn = QPushButton('Relative')
        self.relative_btn.setEnabled(False)
        self.relative_btn.clicked.connect(self.relative)
        main_grid.addWidget(self.relative_btn, 6, 0, Qt.AlignCenter)
        self.center_btn = QPushButton('Center')
        self.center_btn.setEnabled(False)
        self.center_btn.clicked.connect(self.center)
        main_grid.addWidget(self.center_btn, 7, 0, Qt.AlignCenter)
        self.home_btn = QPushButton('Home')
        self.home_btn.setEnabled(False)
        self.home_btn.clicked.connect(self.home)
        main_grid.addWidget(self.home_btn, 8, 0, Qt.AlignCenter)

        # buttons under Set/Get
        self.set_pos_btn = QPushButton('Set Pos')
        self.set_pos_btn.setEnabled(False)
        self.set_pos_btn.clicked.connect(self.set_pos)
        main_grid.addWidget(self.set_pos_btn, 5, 1, Qt.AlignCenter)
        self.set_zero_btn = QPushButton('Set Zero')
        self.set_zero_btn.setEnabled(False)
        self.set_zero_btn.clicked.connect(self.set_zero)
        main_grid.addWidget(self.set_zero_btn, 6, 1, Qt.AlignCenter)
        self.edit_home_btn = QPushButton('Edit Home')
        self.edit_home_btn.setEnabled(False)
        self.edit_home_btn.clicked.connect(self.edit_home)
        main_grid.addWidget(self.edit_home_btn, 7, 1, Qt.AlignCenter)
        self.pos_home_btn = QPushButton('Pos -> Home')
        self.pos_home_btn.setEnabled(False)
        self.pos_home_btn.clicked.connect(self.pos_home)
        main_grid.addWidget(self.pos_home_btn, 8, 1, Qt.AlignCenter)

        # Joystick control label
        joystick_control = QLabel('Joystick Control')
        main_grid.addWidget(joystick_control, 9, 0)

        # X/Y label and buttons
        xy_grid = QGridLayout()
        xy_grid.setSpacing(5)
        x_y = QLabel('X/Y')
        xy_grid.addWidget(x_y, 1, 1, Qt.AlignCenter)
        self.y_up_btn = QPushButton()
        self.y_up_btn.setEnabled(False)
        self.y_up_btn.pressed.connect(self.y_up)
        self.y_up_btn.released.connect(self.joystick_stop)
        self.y_up_btn.setStyleSheet("image: url(:/arrow/Up.png);")
        xy_grid.addWidget(self.y_up_btn, 0, 1, Qt.AlignCenter)
        self.y_down_btn = QPushButton()
        self.y_down_btn.setEnabled(False)
        self.y_down_btn.pressed.connect(self.y_down)
        self.y_down_btn.released.connect(self.joystick_stop)
        self.y_down_btn.setStyleSheet("image: url(:/arrow/Down.png);")
        xy_grid.addWidget(self.y_down_btn, 2, 1, Qt.AlignCenter)
        self.x_left_btn = QPushButton()
        self.x_left_btn.setEnabled(False)
        self.x_left_btn.pressed.connect(self.x_left)
        self.x_left_btn.released.connect(self.joystick_stop)
        self.x_left_btn.setStyleSheet("image: url(:/arrow/Left.png);")
        xy_grid.addWidget(self.x_left_btn, 1, 0, Qt.AlignCenter)
        self.x_right_btn = QPushButton()
        self.x_right_btn.setEnabled(False)
        self.x_right_btn.pressed.connect(self.x_right)
        self.x_right_btn.released.connect(self.joystick_stop)
        self.x_right_btn.setStyleSheet("image: url(:/arrow/Right.png);")
        xy_grid.addWidget(self.x_right_btn, 1, 2, Qt.AlignCenter)
        main_grid.addLayout(xy_grid, 10, 0)

        # Z label and buttons
        z_grid = QGridLayout()
        z_grid.setSpacing(5)
        z = QLabel('Z')
        z_grid.addWidget(z, 1, 0, Qt.AlignCenter)
        self.z_up_btn = QPushButton()
        self.z_up_btn.setEnabled(False)
        self.z_up_btn.pressed.connect(self.z_up)
        self.z_up_btn.released.connect(self.joystick_stop)
        self.z_up_btn.setStyleSheet("image: url(:/arrow/Up.png);")
        z_grid.addWidget(self.z_up_btn, 0, 0, Qt.AlignCenter)
        self.z_down_btn = QPushButton()
        self.z_down_btn.setEnabled(False)
        self.z_down_btn.pressed.connect(self.z_down)
        self.z_down_btn.released.connect(self.joystick_stop)
        self.z_down_btn.setStyleSheet("image: url(:/arrow/Down.png);")
        z_grid.addWidget(self.z_down_btn, 2, 0, Qt.AlignCenter)
        main_grid.addLayout(z_grid, 10, 1)

        # Current Position labels
        current_pos = QLabel('Current Position')
        main_grid.addWidget(current_pos, 4, 2)
        x_pos = QLabel(f"X ({chr(956)}m)")
        main_grid.addWidget(x_pos, 5, 2)
        y_pos = QLabel(f"Y ({chr(956)}m)")
        main_grid.addWidget(y_pos, 6, 2)
        z_pos = QLabel(f"Z ({chr(956)}m)")
        main_grid.addWidget(z_pos, 7, 2)

        # Actual position readings of xyz
        self.x_current_pos = QLabel("0.00")
        main_grid.addWidget(self.x_current_pos, 5, 3, Qt.AlignCenter)
        self.y_current_pos = QLabel("0.00")
        main_grid.addWidget(self.y_current_pos, 6, 3, Qt.AlignCenter)
        self.z_current_pos = QLabel("0.00")
        main_grid.addWidget(self.z_current_pos, 7, 3, Qt.AlignCenter)

        # Current state label and reading
        curr_state_head = QLabel('Current State')
        self.curr_state = QLineEdit('')
        self.curr_state.setAlignment(Qt.AlignHCenter)
        self.curr_state.setReadOnly(True)
        main_grid.addWidget(curr_state_head, 8, 2, 1, 2, Qt.AlignBottom | Qt.AlignHCenter)
        main_grid.addWidget(self.curr_state, 9, 2, 1, 2, Qt.AlignTop | Qt.AlignHCenter)

        # stop button
        self.stop_btn = QPushButton('Stop')
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop)
        main_grid.addWidget(self.stop_btn, 10, 3, 1, 1, Qt.AlignTop | Qt.AlignCenter)

        # start OPUS button
        self.start_OPUS_btn = QPushButton('Start OPUS')
        self.start_OPUS_btn.setEnabled(False)
        self.start_OPUS_btn.clicked.connect(self.start_OPUS)
        main_grid.addWidget(self.start_OPUS_btn, 10, 2, 1, 1, Qt.AlignTop | Qt.AlignCenter)


    def connectInstrument(self):

        if self.Tango == 0:
            print("Error: failed to load DLL")
            sys.exit(0)

        # Tango_DLL.dll loaded successfully

        if self.Tango.LSX_CreateLSID == 0:
            print("unexpected error. required DLL function CreateLSID() missing")
            sys.exit(0)
        # continue only if required function exists

        error = int     #value is either DLL or Tango error number if not zero
        error = self.Tango.LSX_CreateLSID(byref(self.LSID))
        if error > 0:
            print("Error: " + str(error))
            sys.exit(0)

        # OK: got communication ID from DLL (usually 1. may vary with multiple connections)
        # keep this LSID in mind during the whole session

        if self.Tango.LSX_ConnectSimple == 0:
            print("unexepcted error. required DLL function ConnectSimple() missing")
            sys.exit(0)
        # continue only if required function exists

        # if a selection is chosen that is not just the default prompt
        if (self.connection_box.currentText() != 'Connect to translator...'):
            # get the translator name and connect to the translator
            self.trans_name = "COM" + self.connection_box.currentText()[4]

            # set baud rate to 57600 by default
            baud_rate = 57600

            trans_name = ctypes.c_char_p(self.trans_name.encode())
            error = self.Tango.LSX_ConnectSimple(self.LSID, 1, trans_name, baud_rate, 0)
            if error > 0:
                print("Error: LSX_ConnectSimple " + str(error))
                sys.exit(0)
            print("TANGO is now successfully connected to DLL")

            # store controller states to tell when rotator is moving, disabled, ready, etc.
            self.controller_states = {'@': 'Axis stands still',
                                      'M': 'Axis is in motion',
                                      ' ': 'Axis is not enabled',
                                      'J': 'Joystick switched on',
                                      'C': 'Axis is in closed loop',
                                      'A': 'Return message after calibration',
                                      'E': 'Error when calibration',
                                      'D': 'Return message after measuring stage travel range (m)',
                                      'U': 'Setup mode',
                                      'T': 'Timeout'}
            # change connection indicator to a check mark from a cross mark
            self.connection_indicator.setText(u'\u2705')
            self.conncted = True
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Disconnect")

            # turn led indicator on and set appropriate color based on state
            self.Tango.LSX_SetActiveAxes(self.LSID, 7)
            ctrl_state = c_char()
            self.Tango.LSX_GetStatusAxis(self.LSID, byref(ctrl_state), 16)
            ctrl_state = str(ctrl_state.value)[2]
            self.ready = (ctrl_state != 'M')

            if (self.ready):
                self.trans_ind.changeColor('green')
                # enable every buttons
                self.x_check_box.setEnabled(True)
                self.y_check_box.setEnabled(True)
                self.z_check_box.setEnabled(True)
                self.absolute_btn.setEnabled(True)
                self.relative_btn.setEnabled(True)
                self.center_btn.setEnabled(True)
                self.home_btn.setEnabled(True)
                self.set_pos_btn.setEnabled(True)
                self.set_zero_btn.setEnabled(True)
                self.edit_home_btn.setEnabled(True)
                self.pos_home_btn.setEnabled(True)
                self.start_OPUS_btn.setEnabled(True)
                self.enable_btn.setText('Disable')
            else:
                self.enable_btn.setText('Enable')

            self.trans_ind.setChecked(True)
            self.enable_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)

            # update controller state every second (1000 ms)
            self.timer = QTimer()
            self.timer.timeout.connect(self.updateState)
            self.timer.start(1000)

            self.set_limit()

    def disconnect(self):
        self.Tango.LSX_Disconnect(self.LSID)
        self.connection_indicator.setText(u'\u274c')
        self.connected = False
        self.connect_btn.setText('Reconnect')
        self.timer.stop()

    def reconnect(self):
        baud_rate = 57600
        trans_name = ctypes.c_char_p(self.trans_name.encode())
        error = self.Tango.LSX_ConnectSimple(self.LSID, 1, trans_name, baud_rate, 0)
        if error > 0:
            QMessageBox.warning(self, "Tango Connection", "Tango fails to reconnect!")
            return
        self.connection_indicator.setText(u'\u2705')
        self.connected = True
        self.connect_btn.setText('Disconnect')
        self.timer.start(1000)

    def updateState(self):
        if not self.in_Opus:
            ctrl_state = c_char()
            self.Tango.LSX_GetStatusAxis(self.LSID, byref(ctrl_state), 16)
            ctrl_state = str(ctrl_state.value)[2]
            self.curr_state.setText(self.controller_states[ctrl_state])
            flag = c_int()
            self.Tango.LSX_GetActiveAxes(self.LSID, byref(flag))
            self.ready = (ctrl_state != 'M' and flag.value != 0)

            if (self.ready):
                # enable position spinbox, slider, and buttons
                self.x_check_box.setEnabled(True)
                self.y_check_box.setEnabled(True)
                self.z_check_box.setEnabled(True)
                self.x_sb.setEnabled(self.x_check_box.isChecked())
                self.y_sb.setEnabled(self.y_check_box.isChecked())
                self.z_sb.setEnabled(self.z_check_box.isChecked())
                self.absolute_btn.setEnabled(True)
                self.relative_btn.setEnabled(True)
                self.center_btn.setEnabled(True)
                self.home_btn.setEnabled(True)
                self.set_pos_btn.setEnabled(True)
                self.set_zero_btn.setEnabled(True)
                self.edit_home_btn.setEnabled(True)
                self.pos_home_btn.setEnabled(True)
                self.y_up_btn.setEnabled(self.y_check_box.isChecked())
                self.y_down_btn.setEnabled(self.y_check_box.isChecked())
                self.x_left_btn.setEnabled(self.x_check_box.isChecked())
                self.x_right_btn.setEnabled(self.x_check_box.isChecked())
                self.z_up_btn.setEnabled(self.z_check_box.isChecked())
                self.z_down_btn.setEnabled(self.z_check_box.isChecked())
                self.start_OPUS_btn.setEnabled(True)
            else:
                # disable position spinbox, slider, and buttons
                self.x_check_box.setEnabled(False)
                self.y_check_box.setEnabled(False)
                self.z_check_box.setEnabled(False)
                self.x_sb.setEnabled(False)
                self.y_sb.setEnabled(False)
                self.z_sb.setEnabled(False)
                self.absolute_btn.setEnabled(False)
                self.relative_btn.setEnabled(False)
                self.center_btn.setEnabled(False)
                self.home_btn.setEnabled(False)
                self.set_pos_btn.setEnabled(False)
                self.set_zero_btn.setEnabled(False)
                self.edit_home_btn.setEnabled(False)
                self.pos_home_btn.setEnabled(False)
                self.start_OPUS_btn.setEnabled(False)

        self.x = self.get_x_pos()
        self.y = self.get_y_pos()
        self.z = self.get_z_pos()
        self.x_current_pos.setText(f"{self.x}")
        self.y_current_pos.setText(f"{self.y}")
        self.z_current_pos.setText(f"{self.z}")

    def toggleEnabled(self):
        flag = c_int()
        self.Tango.LSX_GetActiveAxes(self.LSID, byref(flag))

        if (flag.value != 0):  # disable, then change text to enable
            self.Tango.LSX_SetActiveAxes(self.LSID, 0)
            self.enable_btn.setText('Enable')
            self.trans_ind.changeColor('orange')
        else:  # enable, then change text to disable
            self.Tango.LSX_SetActiveAxes(self.LSID, 7)
            self.enable_btn.setText('Disable')
            self.trans_ind.changeColor('green')

    def swicthConnection(self):
        if self.connected:
            self.disconnect()
        else:  # enable, then change text to disable
            self.reconnect()

    def get_pos(self):
        x = c_double()
        y = c_double()
        z = c_double()
        a = c_double()
        self.Tango.LSX_GetPos(self.LSID, byref(x), byref(y), byref(z), byref(a))
        return x.value, y.value, z.value

    def get_x_pos(self):
        x, _, _ = self.get_pos()
        return x

    def get_y_pos(self):
        _, y, _ = self.get_pos()
        return y

    def get_z_pos(self):
        _, _, z = self.get_pos()
        return z

    def absolute(self):
        x = c_double(self.x)
        y = c_double(self.y)
        z = c_double(self.z)
        if self.x_check_box.checkState() != 0:
            x = c_double(self.x_sb.value())
        if self.y_check_box.checkState() != 0:
            y = c_double(self.y_sb.value())
        if self.z_check_box.checkState() != 0:
            z = c_double(self.z_sb.value())
        self.Tango.LSX_MoveAbs(self.LSID, x, y, z, c_double(0), c_bool(False))

    def relative(self):
        x = c_double(0)
        y = c_double(0)
        z = c_double(0)
        if self.x_check_box.checkState() != 0:
            x = c_double(self.x_sb.value())
        if self.y_check_box.checkState() != 0:
            y = c_double(self.y_sb.value())
        if self.z_check_box.checkState() != 0:
            z = c_double(self.z_sb.value())
        self.Tango.LSX_MoveRel(self.LSID, x, y, z, c_double(0), c_bool(False))

    def center(self):
        self.Tango.LSX_MoveAbs(self.LSID, c_double(0), c_double(0), c_double(0), c_double(0), c_bool(False))

    def set_pos(self):
        x = c_double(self.x)
        y = c_double(self.y)
        z = c_double(self.z)
        if self.x_check_box.checkState() != 0:
            x = c_double(self.x_sb.value())
        if self.y_check_box.checkState() != 0:
            y = c_double(self.y_sb.value())
        if self.z_check_box.checkState() != 0:
            z = c_double(self.z_sb.value())
        self.Tango.LSX_SetPos(self.LSID, x, y, z, c_double(0))

    def set_zero(self):
        self.Tango.LSX_SetPos(self.LSID, c_double(0), c_double(0), c_double(0), c_double(0))

    def home(self):
        self.Tango.LSX_MoveAbs(self.LSID, c_double(self.x_home), c_double(self.y_home), c_double(self.z_home), c_double(0), False)

    def edit_home(self):
        self.Home = Home(self)

    def pos_home(self):
        if self.x_check_box.checkState() != 0:
            self.x_home = self.x_sb.value()
        if self.y_check_box.checkState() != 0:
            self.y_home = self.y_sb.value()
        if self.z_check_box.checkState() != 0:
            self.z_home = self.z_sb.value()

    def y_up(self):
        self.Tango.LSX_SetDigJoySpeed(self.LSID, c_double(0), c_double(5.0), c_double(0), c_double(0))

    def y_down(self):
        self.Tango.LSX_SetDigJoySpeed(self.LSID, c_double(0), c_double(-5.0), c_double(0), c_double(0))

    def x_left(self):
        self.Tango.LSX_SetDigJoySpeed(self.LSID, c_double(5.0), c_double(0), c_double(0), c_double(0))

    def x_right(self):
        self.Tango.LSX_SetDigJoySpeed(self.LSID, c_double(-5.0), c_double(0), c_double(0), c_double(0))

    def z_up(self):
        self.Tango.LSX_SetDigJoySpeed(self.LSID, c_double(0), c_double(0), c_double(5.0), c_double(0))

    def z_down(self):
        self.Tango.LSX_SetDigJoySpeed(self.LSID, c_double(0), c_double(0), c_double(-5.0), c_double(0))

    def joystick_stop(self):
        self.Tango.LSX_SetDigJoySpeed(self.LSID, c_double(0), c_double(0), c_double(0), c_double(0))

    def set_limit(self):
        min = c_double()
        max = c_double()
        self.Tango.LSX_GetLimit(self.LSID, 1, byref(min), byref(max))
        self.x_sb.setMinimum(min.value)
        self.x_sb.setMaximum(max.value)
        self.x_min = min.value
        self.x_max = max.value
        self.Tango.LSX_GetLimit(self.LSID, 2, byref(min), byref(max))
        self.y_sb.setMinimum(min.value)
        self.y_sb.setMaximum(max.value)
        self.y_min = min.value
        self.y_max = max.value
        self.Tango.LSX_GetLimit(self.LSID, 3, byref(min), byref(max))
        self.z_sb.setMinimum(min.value)
        self.z_sb.setMaximum(max.value)
        self.z_min = min.value
        self.z_max = max.value

    def wait_until(self, period=0.25):
        timeout = 300   # 5 minutes
        mustend = time.time() + timeout
        while time.time() < mustend:
            in_Opus = False
            for proc in psutil.process_iter(["pid", "name", "username"]):
                if proc.info["name"] == "opus.exe":
                    in_Opus = True
                    time.sleep(period)
            if not in_Opus:
                return True
        return False

    def start_OPUS(self):
        self.in_Opus = True
        self.disconnect()
        start = win32com.client.Dispatch("OpusCMD334.StartOpus")
        exePath = r"C:\Program Files\Bruker\OPUS_8.5.29\opus.exe"
        password = "OPUS"
        start.StartOpus(exePath, password)
        self.wait_until()
        self.reconnect()
        self.in_Opus = False

    def stop(self):
        self.Tango.LSX_StopAxes(self.LSID)

class Home(QFrame):
    def __init__(self, Translator):
        super().__init__()
        self.trans = Translator
        self.LSID = Translator.LSID
        self.x_home = Translator.x_home
        self.y_home = Translator.y_home
        self.z_home = Translator.z_home
        self.x_min = Translator.x_min
        self.x_max = Translator.x_max
        self.y_min = Translator.y_min
        self.y_max = Translator.y_max
        self.z_min = Translator.z_min
        self.z_max = Translator.z_max
        self.show()
        self.initUI()

    def initUI(self):
        main_grid = QGridLayout()
        main_grid.setSpacing(5)
        self.setLayout(main_grid)

         # set position label
        enter_pos = QLabel('Active / Position')  # above the slider
        main_grid.addWidget(enter_pos, 0, 0)

        # set xyz check boxes
        self.x_label = QLabel(f"X ({chr(956)}m)")
        main_grid.addWidget(self.x_label, 1, 0, 1, 1, Qt.AlignCenter)
        self.y_label = QLabel(f"Y ({chr(956)}m)")
        main_grid.addWidget(self.y_label, 2, 0, 1, 1, Qt.AlignCenter)
        self.z_label = QLabel(f"Z ({chr(956)}m)")
        main_grid.addWidget(self.z_label, 3, 0, 1, 1, Qt.AlignCenter)

        # set xyz spin boxes
        self.x_sb = QDoubleSpinBox()
        self.x_sb.setDecimals(2)
        self.x_sb.setValue(self.x_home)
        self.x_sb.setEnabled(True)
        self.x_sb.setMinimum(self.x_min)
        self.x_sb.setMaximum(self.x_max)
        main_grid.addWidget(self.x_sb, 1, 1, Qt.AlignCenter)
        self.y_sb = QDoubleSpinBox()
        self.y_sb.setDecimals(2)
        self.y_sb.setValue(self.y_home)
        self.y_sb.setEnabled(True)
        self.y_sb.setMinimum(self.y_min)
        self.y_sb.setMaximum(self.y_max)
        main_grid.addWidget(self.y_sb, 2, 1, Qt.AlignCenter)
        self.z_sb = QDoubleSpinBox()
        self.z_sb.setDecimals(2)
        self.z_sb.setValue(self.z_home)
        self.z_sb.setEnabled(True)
        self.z_sb.setMinimum(self.z_min)
        self.z_sb.setMaximum(self.z_max)
        main_grid.addWidget(self.z_sb, 3, 1, Qt.AlignCenter)

        self.submit_btn = QPushButton('Submit')
        self.submit_btn.clicked.connect(self.submit)
        main_grid.addWidget(self.submit_btn, 4, 1, Qt.AlignCenter)

    def submit(self):
        self.trans.x_home = self.x_sb.value()
        self.trans.y_home = self.y_sb.value()
        self.trans.z_home = self.z_sb.value()
        self.close()


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
    window = Translator()
    sys.exit(app.exec_())
