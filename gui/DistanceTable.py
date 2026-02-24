from PySide6 import QtWidgets
from geopy import distance as dist

class DistanceTable:
    def __init__(self, parent_window):
        self.parent = parent_window

    def populate_distance_table(self):
    # Clear the table first to avoid duplicates
        self.parent.tableWidget_distances.setRowCount(0)

        self.parent.tableWidget_distances.horizontalHeader().setStretchLastSection(False)
        self.parent.tableWidget_distances.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.parent.tableWidget_distances.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)  # Second column: 100px
 
        bue_ids = list(self.parent.base_station.bue_id_to_coords.keys())


        for i, b1 in enumerate(bue_ids, start=1):
            b1_hostname = self.parent.base_station.bue_id_to_hostname[b1]
            b1_coords = self.parent.base_station.bue_id_to_coords[b1]
            # b1_lat, b1_long = self.parent.base_station.bue_id_to_coords[b1]
            for b2 in bue_ids[i:]:
                b2_hostname = self.parent.base_station.bue_id_to_hostname[b2]
                b2_coords = self.parent.base_station.bue_id_to_coords[b2]
                # b2_lat, b2_long = self.parent.base_station.bue_id_to_coords[b2]
                distance = dist.great_circle(b1_coords, b2_coords).meters

                row = self.parent.tableWidget_distances.rowCount()
                self.parent.tableWidget_distances.insertRow(row)
                self.parent.tableWidget_distances.setItem(row, 0, QtWidgets.QTableWidgetItem(f"{b1_hostname} to {b2_hostname}"))
                self.parent.tableWidget_distances.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{float(distance):.2f} m"))
