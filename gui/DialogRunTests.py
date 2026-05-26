from PySide6 import QtWidgets
from gui.ui.DialogRunTestsUi import Ui_dialog_run_tests

from datetime import datetime, timedelta

class DialogRunTests:
    def __init__(self, parent_window):
         self.parent = parent_window
         self.dialog_run_tests = None

    def open_dialog_run_tests(self):
            if self.dialog_run_tests is None:
                self.dialog_run_tests = QtWidgets.QDialog()
                self.dialog_run_tests_ui = Ui_dialog_run_tests()
                self.dialog_run_tests_ui.setupUi(self.dialog_run_tests)

                self.dialog_run_tests_ui.button_hello_world.clicked.connect(self.send_hello_world)

                self.dialog_run_tests_ui.pushButton_init.clicked.connect(lambda: self.send_utw("init"))
                self.dialog_run_tests_ui.pushButton_resp.clicked.connect(lambda: self.send_utw("resp"))

                # Connect button box signals to close handler
                self.dialog_run_tests_ui.buttonBox.accepted.connect(self.close_dialog_run_tests)
                self.dialog_run_tests_ui.buttonBox.rejected.connect(self.close_dialog_run_tests)

            self.setup_bue_checkboxes()
            self.dialog_run_tests.show()

    def close_dialog_run_tests(self):
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
        if self.dialog_run_tests_ui.widget_bue_selection.layout():
            QtWidgets.QWidget().setLayout(
                self.dialog_run_tests_ui.widget_bue_selection.layout()
            )

        # Create and set the layout
        layout = QtWidgets.QVBoxLayout()
        self.dialog_run_tests_ui.widget_bue_selection.setLayout(layout)

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