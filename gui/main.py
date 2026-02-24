from PySide6 import QtUiTools, QtWidgets
from PySide6.QtCore import QTimer
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base_station_main import Base_Station_Main
from MapManager import MapManager

from gui.ui.MainWindowUi import Ui_MainWindow

from DialogRunTests import DialogRunTests
from gui.DialogCancelTests import DialogCancelTests

from DistanceTable import DistanceTable
from CoordsTable import CoordsTable
from LogViewerWidget import LogViewerWidget
from BueTable import Buetable

class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.base_station = Base_Station_Main("config_base.yaml")
        self.loader = QtUiTools.QUiLoader()

        self.map_manager = MapManager(self)
        self.distance_table = DistanceTable(self)
        self.coords_table = CoordsTable(self)
        self.bue_table = Buetable(self)

        log_viewer = LogViewerWidget(self.frame_base_station_log, "logs/last_run.log")
        layout = QtWidgets.QVBoxLayout()
        self.frame_base_station_log.setLayout(layout)
        layout.addWidget(log_viewer)

        self.dialog_run_tests = DialogRunTests(self)
        self.dialog_cancel_tests = DialogCancelTests(self)

        self.button_run_tests.clicked.connect(self.dialog_run_tests.open_dialog_run_tests)
        self.button_switch_map_type.clicked.connect(self.map_manager.swap_map_type)
        self.button_cancel_tests.clicked.connect(self.dialog_cancel_tests.open_dialog_cancel_tests)
        self.button_clear_messages.clicked.connect(lambda: self.base_station.bue_tout.clear())

        self.bue_table.setup_table()

        # Track previous state to detect changes
        self.prev_bue_state = {}
        self.prev_missed_pings = {}
        self.prev_bue_tout = {}
        self.prev_bue_id_to_coords = {}

        self.bue_checkboxes = {}

        self.map_manager.initialize_map()
        self.bue_table.populate_table()
        self.distance_table.populate_distance_table()
        self.coords_table.populate_coords_table()
        self.setup_timer()

    

    def setup_bue_checkboxes(self):
        """Create checkboxes for each connected BUE in the dialog."""
        # Clear any existing layout first
        if self.dialog_run_tests_ui.widget_bue_selection.layout():
            QtWidgets.QWidget().setLayout(
                self.dialog_run_tests.widget_bue_selection.layout()
            )

        # Create and set the layout
        layout = QtWidgets.QVBoxLayout()
        self.dialog_run_tests_ui.widget_bue_selection.setLayout(layout)

        # Dictionary to store checkbox references
        self.bue_checkboxes = {}

        # Create a checkbox for each connected BUE
        for bue_id in self.base_station.connected_bues:
            hostname = self.base_station.bue_id_to_hostname.get(bue_id, f"BUE_{bue_id}")

            checkbox = QtWidgets.QCheckBox(f"{hostname} (ID: {bue_id})")
            checkbox.setChecked(True)  # Default to checked

            # Store reference to checkbox with bue_id as key
            self.bue_checkboxes[bue_id] = checkbox

            # Add to layout (this is the key part!)
            layout.addWidget(checkbox)


    def setup_timer(self):
        """Set up a timer to refresh the table every second."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_for_changes)
        self.timer.start(1000)  # 1000 milliseconds = 1 second

    def check_for_changes(self):
        """Check if there are changes in state or missed pings, and update table if needed."""
        current_state = self.base_station.bue_id_to_state.copy()
        current_missed_pings = self.base_station.bue_missed_ping_counter.copy()
        current_bue_tout = self.base_station.bue_tout.copy()
        current_bue_id_to_coord = self.base_station.bue_id_to_coords.copy()

        # Check if there are any changes
        state_changed = current_state != self.prev_bue_state
        pings_changed = current_missed_pings != self.prev_missed_pings
        messages_changed = current_bue_tout != self.prev_bue_tout
        coords_changed = current_bue_id_to_coord != self.prev_bue_id_to_coords

        if state_changed or pings_changed:
            self.bue_table.populate_table()
            # Update our tracked state
            self.prev_bue_state = current_state
            self.prev_missed_pings = current_missed_pings

        if messages_changed:
            self.populate_messages()
            self.prev_bue_tout = current_bue_tout

        if coords_changed:
            self.prev_bue_id_to_coords = current_bue_id_to_coord
            self.map_manager.populate_map()
            self.distance_table.populate_distance_table()
            self.coords_table.populate_coords_table()
    

    def populate_messages(self):
        """Populate the text browser with messages from base_station.bue_tout."""
        # Save current scroll position
        scrollbar = self.textBrowser_messages.verticalScrollBar()
        current_position = scrollbar.value()
        max_position = scrollbar.maximum()
        
        # Check if user was at the bottom (auto-scroll) or somewhere else (manual scroll)
        was_at_bottom = current_position == max_position
        
        self.textBrowser_messages.clear()

        # Add messages without moving cursor
        for message in self.base_station.bue_tout:
            self.textBrowser_messages.append(message)
        
        # Only auto-scroll if user was previously at the bottom
        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())
        else:
            # Restore previous position (approximately)
            scrollbar.setValue(current_position)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
