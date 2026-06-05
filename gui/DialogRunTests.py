import os

from PySide6 import QtWidgets, QtCore
from gui.ui.DialogRunTestsUi import Ui_dialog_run_tests

from datetime import datetime, timedelta

from yaml import safe_load

# Get the cirrect directory

current_dir = os.path.dirname(os.path.abspath(__file__))

class DialogRunTests:
    def __init__(self, parent_window):
         self.parent = parent_window
         self.dialog_run_tests = None

    def open_dialog_run_tests(self):
            if self.dialog_run_tests is None:
                self.dialog_run_tests = QtWidgets.QDialog()
                self.ui = Ui_dialog_run_tests()
                self.ui.setupUi(self.dialog_run_tests)

                # Load test names from YAML config file and populate the combo box
                with open("utw_config.yaml", 'r') as f:
                    self.utw_test_config = safe_load(f)
                
                self.populate_comboBox_select_test()
                
                self.ui.comboBox_select_test.currentIndexChanged.connect(
                    lambda: self.populate_scrollArea_test_setup(self.ui.comboBox_select_test.currentText()))
                
                self.populate_scrollArea_test_setup(self.ui.comboBox_select_test.currentText())


            #     # Connect button signals to close handler
                self.ui.pushButton_run.clicked.connect(self.close_dialog_run_tests)
                self.ui.pushButton_cancel.clicked.connect(self.close_dialog_cancel_tests)

            # self.setup_bue_checkboxes()
            self.dialog_run_tests.show()

    def populate_comboBox_select_test(self):
        test_names = self.utw_test_config.keys()
        self.ui.comboBox_select_test.clear()
        self.ui.comboBox_select_test.addItems(['-- Select Test --'] + list(test_names))
         
    
    
    def populate_scrollArea_test_setup(self, test_name):
        old_widget = self.ui.scrollArea_test_setup.takeWidget()
        if old_widget is not None:
            old_widget.deleteLater()

        # self.ui.scrollArea_test_setup.setWidget(QtWidgets.QWidget())  # Set an empty widget as the new content
        # self.ui.scrollArea_test_setup.setWidgetResizable(True)  # Allow the scroll area to resize the content widget
        # self.ui.scrollArea_test_setup.widget().setGeometry(0, 0, self.ui.scrollArea_test_setup.width(), self.ui.scrollArea_test_setup.height())  # Set geometry of the new content widget

        frame = QtWidgets.QFrame()
        frame.resize(901, 551)

        def build_args_frame(test_name: str, role: str):
            args_frame = QtWidgets.QFrame(parent=frame)

            ui_args = self.utw_test_config[test_name][role]['ui_args']
            args_frame_x = x_margin

            bue_label = QtWidgets.QLabel("<bUE>:", parent=args_frame)
            bue_label.setObjectName("bue_label")
            bue_label.setGeometry(args_frame_x, 5, 100, 20)
            bue_label.setStyleSheet("color: black;")
            bue_label.show()
            args_frame_x += 60

            for arg_name, arg_value in ui_args.items():
                # Create a label and input field for each argument
                arg_label = QtWidgets.QLabel(f"{arg_name}:", parent=args_frame)
                arg_label.setGeometry(args_frame_x, 5, 100, 20)
                arg_label.setStyleSheet("color: black;")
                arg_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
                arg_label.show()

                arg_input = QtWidgets.QLineEdit(parent=args_frame)
                arg_input.setGeometry(args_frame_x + 110, 5, 100, 20)
                arg_input.setStyleSheet("color: black;")
                arg_input.setObjectName(f"{arg_name}_input")
                if arg_value is not None:
                    arg_input.setText(str(arg_value))
                arg_input.show()

                args_frame_x += 220  # Move to the right for the next argument

            return args_frame
        
        def set_args_frame(bue_name: str, args_frame: QtWidgets.QFrame):
            # Get first word in bue name
            parts = bue_name.split(maxsplit=1)
            enable = (parts[0] == "CB" and "Select BUE" not in bue_name) or (parts[0] == "T")

            if enable:
                # Set the text of thebue_label in args_frame to the bue_name without the status prefix
                args_frame.setEnabled(True)
                args_frame.setStyleSheet("background-color: white;")
                bue_label = args_frame.findChild(QtWidgets.QLabel, "bue_label")
                if bue_label:
                    bue_label.setText(f"{parts[1]}:")
            else:
                args_frame.setEnabled(False)
                args_frame.setStyleSheet("background-color: gray;")
                bue_label = args_frame.findChild(QtWidgets.QLabel, "bue_label")
                if bue_label:
                    bue_label.setText("<bUE>:")
        
        
        if test_name == '-- Select Test --':
            return
        elif test_name not in self.utw_test_config.keys():
            print(f"Error: Test '{test_name}' not found in configuration.")
            return

        current_y = 10
        x_margin = 10

        bue_widgets = []  # Keep track of BUE-related widgets to manage their visibility

        for role in self.utw_test_config[test_name].keys():
            current_x = x_margin
            
            # Add the role name label at explicit coordinates
            role_label = QtWidgets.QLabel(f"Role: {role}", parent=frame)
            role_label.setStyleSheet("font-weight: bold; color: black;")
            label_height = role_label.sizeHint().height() or 20
            role_label.setGeometry(x_margin, current_y, 400, label_height)
            role_label.show()
            current_y += 30

            # Now we provide a selection of BUEs for the user to choose from for this role, up to the max_per_test limit if specified
            max_per_test = self.utw_test_config[test_name][role].get('max_per_test', 0)

            if max_per_test > 0:
                instruction_label = QtWidgets.QLabel(f"Select up to {max_per_test} BUE(s) for this role:", parent=frame)
                instruction_label.setGeometry(x_margin, current_y, 300, 20)
                instruction_label.setStyleSheet("font-style: italic; color: gray;")
                instruction_label.show()
                current_y += 30

                combo_y = current_y
                combo_x = current_x

                for i in range(max_per_test):
                    bue_combo = QtWidgets.QComboBox(parent=frame)
                    bue_combo.setGeometry(combo_x, combo_y, 200, 20)
                    bue_combo.setStyleSheet("color: black;")
                    bue_combo.addItem("-- Select BUE --")
                    for bue_id in self.parent.base_station.connected_bues:
                        hostname = self.parent.base_station.bue_id_to_hostname.get(bue_id, f"BUE_{bue_id}")
                        bue_combo.addItem(f"{hostname} (ID: {bue_id})", userData=bue_id)
                    bue_combo.show()
                    combo_x += 210

                    # Now, we add the args frame for this role, which will be enabled/disabled based on whether 
                    #  a BUE is selected in the combo box
                    if 'ui_args' in self.utw_test_config[test_name][role].keys():
                        current_y += 40
                        
                        args_frame = build_args_frame(test_name, role)
                        args_frame.setGeometry(x_margin, current_y, 880, 40)
                        args_frame.show()

                        args_frame.setObjectName(f"{role}_args_frame_{i}")  # Set object name for later reference

                        bue_widgets.append([bue_combo, args_frame])  # Keep track of this args frame
                        set_args_frame("F init", args_frame)  # Initialize the args frame as disabled
                        
                current_y += 40

            # In the event that there is no limit, we create check boxes of all the other bUEs
            else:
                instruction_label = QtWidgets.QLabel(f"Select BUE(s) for this role:", parent=frame)
                instruction_label.setGeometry(x_margin, current_y, 300, 20)
                instruction_label.setStyleSheet("font-style: italic; color: gray;")
                instruction_label.show()
                current_y += 30

                check_x = current_x
                check_y = current_y

                i = 0
                for bue_id in self.parent.base_station.connected_bues:
                    hostname = self.parent.base_station.bue_id_to_hostname.get(bue_id, f"BUE_{bue_id}")
                    bue_checkbox = QtWidgets.QCheckBox(f"{hostname}", parent=frame)
                    bue_checkbox.setGeometry(check_x, check_y, 100, 20)
                    bue_checkbox.setStyleSheet("color: black; background-color: gray;")
                    bue_checkbox.show()
                    check_x += 110

                    # Now, we add the args frame for this role, which will be enabled/disabled based on whether 
                    #  a BUE is selected in the combo box
                    if 'ui_args' in self.utw_test_config[test_name][role].keys():
                        current_y += 30

                        args_frame = build_args_frame(test_name, role)
                        args_frame.setGeometry(x_margin, current_y, 880, 30)
                        args_frame.show()

                        args_frame.setObjectName(f"{role}_args_frame_{i}")  # Set object name for later reference

                        bue_widgets.append([bue_checkbox, args_frame])  # Keep track of this args frame
                        set_args_frame("F init", args_frame)  # Initialize the args frame as disabled

                    i += 1

            current_x = x_margin
            current_y += 40

            

            # Add a horizontal line separator at explicit coordinates
            line = QtWidgets.QFrame(parent=frame)
            line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
            line.setStyleSheet("background-color: gray;")
            line_height = 2
            line.setGeometry(x_margin, current_y, self.ui.scrollArea_test_setup.width() - 2 * x_margin, line_height)
            line.show()
            current_y += line_height + 10

        # # Ensure the content widget is tall enough to show all children and enable scrolling.
        # content.setMinimumSize(viewport_w, current_y + 10)
        self.ui.scrollArea_test_setup.setWidget(frame)

        for item in bue_widgets:
            widget = item[0]
            frame = item[1]
            if isinstance(widget, QtWidgets.QComboBox):
                widget.currentIndexChanged.connect(lambda _, w=widget, f=frame: set_args_frame("CB " + w.currentText().split()[0], f))
            elif isinstance(widget, QtWidgets.QCheckBox):
                widget.stateChanged.connect(lambda _, w=widget, f=frame: set_args_frame(("T " if w.isChecked() else "F ") + w.text(), f))
        

        


    def close_dialog_run_tests(self):
        if self.ui.comboBox_select_test.currentText() == '-- Select Test --':
            print("Error: Please select a test before running.")
            return
        
        execution_time = datetime.now().replace(microsecond=0) + timedelta(seconds=self.ui.spinBox_execution_time.value())
        start_time = int(execution_time.timestamp())

        setup_frame = self.ui.scrollArea_test_setup.takeWidget()

        for child_frame in setup_frame.findChildren(QtWidgets.QFrame):
            if "args_frame" in child_frame.objectName():
                bue_name = child_frame.findChild(QtWidgets.QLabel, "bue_label").text()[:-1]  # Get text without the colon
                # Make sure we have a valid bUE name before proceeding
                if bue_name == "<bUE>":
                    continue  # Skip frames that are not associated with a specific BUE
                rx_id = self.parent.base_station.hostname_to_bue_id.get(bue_name, None)
                if rx_id is None:
                    print(f"Error: Could not find BUE ID for hostname '{bue_name}'")
                    continue

                # Start building the TEST message for this BUE
                send_string = f"TEST:{start_time}:"

                # Add the test name
                send_string += f"{self.ui.comboBox_select_test.currentText()};"  # Add test name to the message

                # Add the role
                send_string += f"{child_frame.objectName().split('_args_frame_')[0]};"  # Extract role from object name
                
                
                # Load in the default args and see if any have changed in the UI, if so we update the send_string with the new args
                args = self.utw_test_config[self.ui.comboBox_select_test.currentText()][child_frame.objectName().split('_args_frame_')[0]].get('default_args', {}).copy()
                
                for arg_input in child_frame.findChildren(QtWidgets.QLineEdit):
                    arg_name = arg_input.objectName().replace("_input", "")
                    arg_value = arg_input.text()
                    if arg_name in args:
                        if str(args[arg_name]) != arg_value:
                            send_string += f"{arg_value},"
                        else:
                            send_string += ","  # If the value hasn't changed, we still need to add a comma 
                                                #  to maintain the correct position of args in the message
                    else:
                        print(f"Warning: Argument '{arg_name}' not found in default args for test '{self.ui.comboBox_select_test.currentText()}' and role '{child_frame.objectName().split('_args_frame_')[0]}'")

                # Trim any trailing commas from the send_string
                send_string = send_string.rstrip(',')
                
                # Final: send the TEST... message to the selected BUEs with the specified args
                self.parent.base_station.ota.send_ota_message(
                    rx_id,
                    send_string
                )

        """Reset dialog_run_tests to None when dialog is closed."""
        self.dialog_run_tests = None

    def close_dialog_cancel_tests(self):
        """Reset dialog_run_tests to None when dialog is closed."""
        self.dialog_run_tests = None

    def send_hello_world(self):
            execution_time = datetime.now().replace(microsecond=0) + timedelta(seconds=10)
            start_time = int(execution_time.timestamp())

            # Get only selected BUEs from checkboxes
            selected_bues = []
            for bue_id, checkbox in self.bue_checkboxes.items():
                if checkbox.isChecked():
                    selected_bues.append(bue_id)

            # Send to selected BUEs only
            for bue_id in selected_bues:
                self.parent.base_station.ota.send_ota_message(
                    bue_id,
                    f"TEST:Old/helloworld,{start_time},5 {self.parent.base_station.bue_id_to_hostname[bue_id]}",
                )

            print(f"Sent hello world to {len(selected_bues)} selected BUEs")


    def send_utw(self, type: str):
        execution_time = datetime.now().replace(microsecond=0) + timedelta(seconds=10)
        start_time = int(execution_time.timestamp())

        # Get only selected BUEs from checkboxes
        selected_bues = []
        for bue_id, checkbox in self.bue_checkboxes.items():
            if checkbox.isChecked():
                selected_bues.append(bue_id)

        

        # Send to selected BUEs only
        for bue_id in selected_bues:
            if(type == "init"):
                self.parent.base_station.ota.send_ota_message(
                    bue_id,
                    f"TEST:/home/admin/two_agent_osu/agent_main,{start_time},-a rtt_init",
                )
            elif(type == "resp"):
                self.parent.base_station.ota.send_ota_message(
                    bue_id,
                    f"TEST:/home/admin/two_agent_osu/agent_main,{start_time},-a rtt_resp",
                )

        print(f"Sent hello world to {len(selected_bues)} selected BUEs")

    def setup_bue_checkboxes(self):
        """Create checkboxes for each connected BUE in the dialog."""
        # Clear any existing layout first
        if self.ui.widget_bue_selection.layout():
            QtWidgets.QWidget().setLayout(
                self.ui.widget_bue_selection.layout()
            )

        # Create and set the layout
        layout = QtWidgets.QVBoxLayout()
        self.ui.widget_bue_selection.setLayout(layout)

        # Dictionary to store checkbox references
        self.bue_checkboxes = {}

        # Create a checkbox for each connected BUE
        for bue_id in self.parent.base_station.connected_bues:
            hostname = self.parent.base_station.bue_id_to_hostname.get(bue_id, f"BUE_{bue_id}")

            checkbox = QtWidgets.QCheckBox(f"{hostname} (ID: {bue_id})")
            checkbox.setChecked(True)  # Default to checked

            # Store reference to checkbox with bue_id as key
            self.bue_checkboxes[bue_id] = checkbox

            # Add to layout
            layout.addWidget(checkbox)