import os
from PySide6 import QtWidgets, QtGui
from gui.ui.DialogCancelTestsUi import Ui_dialog_cancel_tests

class DialogCancelTests:
    def __init__(self, parent_window):
        self.parent = parent_window
        self.dialog_cancel_tests = None

    def open_dialog_cancel_tests(self):
            if self.dialog_cancel_tests is None:
                self.dialog_cancel_tests = QtWidgets.QDialog()
                self.dialog_cancel_tests_ui = Ui_dialog_cancel_tests()
                self.dialog_cancel_tests_ui.setupUi(self.dialog_cancel_tests)

                # Set the correct image path
                image_path = os.path.join(os.path.dirname(__file__), "ui", "image.png")
                if os.path.exists(image_path):
                    pixmap = QtGui.QPixmap(image_path)
                    if not pixmap.isNull():
                        self.dialog_cancel_tests_ui.label.setPixmap(pixmap)

                # Connect button box signals to close handler
                self.dialog_cancel_tests_ui.button_exit.clicked.connect(lambda: self.close_dialog_cancel_tests(send_cancels=False))
                self.dialog_cancel_tests_ui.button_send_cancel.clicked.connect(lambda: self.close_dialog_cancel_tests(send_cancels=True))

            self.setup_bue_checkboxes()
            self.dialog_cancel_tests.show()

    def close_dialog_cancel_tests(self, send_cancels: bool):
        """Reset dialog_canel_tests to None when dialog is closed."""
        if send_cancels:
            self.send_cancels()
        self.dialog_cancel_tests = None

    def setup_bue_checkboxes(self):
        """Create checkboxes for each connected BUE in the dialog."""
        # Clear any existing layout first
        if self.dialog_cancel_tests_ui.widget_bue_selection.layout():
            QtWidgets.QWidget().setLayout(
                self.dialog_cancel_tests_ui.widget_bue_selection.layout()
            )

        # Create and set the layout
        layout = QtWidgets.QVBoxLayout()
        self.dialog_cancel_tests_ui.widget_bue_selection.setLayout(layout)

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

    def send_cancels(self):
        # Get only selected BUEs from checkboxes
        selected_bues = []
        for bue_id, checkbox in self.bue_checkboxes.items():
            if checkbox.isChecked():
                selected_bues.append(bue_id)

        # Send to selected BUEs only
        for bue_id in selected_bues:
            self.parent.base_station.ota.send_ota_message(bue_id, "CANC")

        print(f"Sent hello world to {len(selected_bues)} selected BUEs")