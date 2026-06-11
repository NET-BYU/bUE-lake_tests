from PySide6 import QtWidgets
from PySide6.QtCore import Qt


class Buetable:
    def __init__(self, parent_window):
        self.parent = parent_window

    def setup_table(self):
        self.parent.tableWidget_bue.setRowCount(0)
        self.parent.tableWidget_bue.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.parent.tableWidget_bue.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.parent.tableWidget_bue.customContextMenuRequested.connect(
            self.show_context_menu
        )

    def populate_table(self):
        # Clear the table first to avoid duplicates
        self.parent.tableWidget_bue.setRowCount(0)

        for bue_id, hostname in self.parent.base_station.bue_id_to_hostname.items():
            if bue_id not in self.parent.base_station.bue_id_to_state:
                continue

            if bue_id not in self.parent.base_station.bue_missed_ping_counter:
                continue

            row = self.parent.tableWidget_bue.rowCount()
            self.parent.tableWidget_bue.insertRow(row)

            state = self.parent.base_station.bue_id_to_state[bue_id]
            missed_pings = self.parent.base_station.bue_missed_ping_counter[bue_id]

            hostname_item = QtWidgets.QTableWidgetItem(hostname)
            # Store bue_id as user data (hidden from display)
            hostname_item.setData(Qt.ItemDataRole.UserRole, bue_id)

            self.parent.tableWidget_bue.setItem(row, 0, hostname_item)
            self.parent.tableWidget_bue.setItem(
                row, 1, QtWidgets.QTableWidgetItem(str(state)[6:])
            )
            self.parent.tableWidget_bue.setItem(
                row, 2, QtWidgets.QTableWidgetItem(str(missed_pings))
            )

    def show_context_menu(self, position):
        """Show context menu when right-clicking on table."""
        # Check if click was on a valid item
        item = self.parent.tableWidget_bue.itemAt(position)
        if item is None:
            return

        # Get the bue_id from the first column of the current row
        row = item.row()
        hostname_item = self.parent.tableWidget_bue.item(row, 0)
        bue_id = hostname_item.data(Qt.ItemDataRole.UserRole)
        hostname = hostname_item.text()

        # Create context menu
        context_menu = QtWidgets.QMenu(self.parent.tableWidget_bue)

        # Add actions
        restart_action = context_menu.addAction(f"Restart {hostname}")
        reboot_action = context_menu.addAction(f"Reboot {hostname}")
        context_menu.addSeparator()
        ping_action = context_menu.addAction(f"Send Ping to {hostname}")
        debug_action = context_menu.addAction(f"Debug {hostname}")

        # Show menu and get selected action
        action = context_menu.exec_(self.parent.tableWidget_bue.mapToGlobal(position))

        # Handle selected action
        if action == restart_action:
            print(f"restart {bue_id} : {hostname}")
        elif action == reboot_action:
            print(f"Reboot {bue_id} : {hostname}")
        elif action == ping_action:
            print(f"Action {bue_id} : {hostname}")
        elif action == debug_action:
            print(f"Debug {bue_id} : {hostname}")
