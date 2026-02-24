from PySide6 import QtWidgets
from geopy import distance as dist

class CoordsTable:
    def __init__(self, parent_window):
        self.parent = parent_window

    def populate_coords_table(self):
    # Clear the table first to avoid duplicates
        self.parent.tableWidget_coords.setRowCount(0)
 
        for bue_id, coords in self.parent.base_station.bue_id_to_coords.items():
            hostname = self.parent.base_station.bue_id_to_hostname[bue_id]
            lat, long = coords

            row = self.parent.tableWidget_coords.rowCount()
            self.parent.tableWidget_coords.insertRow(row)
            self.parent.tableWidget_coords.setItem(row, 0, QtWidgets.QTableWidgetItem(f"{hostname}"))
            self.parent.tableWidget_coords.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{lat:.4f}, {long:.4f}"))
