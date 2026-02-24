import math
import pyqtgraph as pg
from qgmap import QGoogleMap, QtWidgets
from qgmap.presets import base64DataUrl

class MapManager:
    def __init__(self, parent_window):
        self.parent = parent_window
        self.gmap_enabled = False
        self.satmap = None
        self.graphmap = None
        self.gmap_auto_fitted = False

    def initialize_map(self):
        if self.parent.frame_map.layout() is None:
            layout = QtWidgets.QVBoxLayout(self.parent.frame_map)
            layout.setContentsMargins(0, 0, 0, 0)
            self.parent.frame_map.setLayout(layout)

        self.setup_graph_map()

    def setup_gmap(self):
        self.satmap = QGoogleMap(None)
        self.satmap.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding,
        )
        
        self.parent.frame_map.layout().addWidget(self.satmap)
        self.satmap.waitUntilReady()

    def setup_graph_map(self):
        self.graphmap = pg.PlotWidget()
        self.graphmap.setLabel('left', 'Latitude')
        self.graphmap.setLabel('bottom', 'Longitude')
        self.graphmap.setTitle('GPS System Locations')
        self.graphmap.showGrid(x=True, y=True)
        self.graphmap.setAspectLocked(True, ratio=1.0)
        
        self.parent.frame_map.layout().addWidget(self.graphmap)

    def swap_map_type(self):
        self.gmap_enabled = not self.gmap_enabled
        
        if self.gmap_enabled:
            if self.graphmap is not None:
                self.parent.frame_map.layout().removeWidget(self.graphmap)
                self.graphmap.setParent(None)
                self.graphmap.deleteLater()
                self.graphmap = None
            
            self.setup_gmap()
        else:
            if self.satmap is not None:
                self.parent.frame_map.layout().removeWidget(self.satmap)
                self.satmap.setParent(None)
                self.satmap.deleteLater()
                self.satmap = None
            
            self.setup_graph_map()
        
        self.populate_map()

    def fit_markers_to_view(self, coords_list):
        if not coords_list:
            return
        
        self.gmap_auto_fitted = True
        
        lats = [coord[0] for coord in coords_list]
        lons = [coord[1] for coord in coords_list]
        
        # Calculate center
        center_lat = (max(lats) + min(lats)) / 2
        center_lon = (max(lons) + min(lons)) / 2
        
        # Calculate zoom
        lat_diff = max(lats) - min(lats)
        lon_diff = max(lons) - min(lons)
        max_diff = max(lat_diff, lon_diff)
        
        if max_diff == 0:
            zoom = 16
        else:
            zoom = int(math.log2(360 / max_diff)) - 1
            zoom = max(1, min(zoom, 18))
        
        # Set zoom first, then center (order matters!)
        self.satmap.setZoom(zoom)
        self.satmap.centerAt(center_lat, center_lon)

    def populate_map(self):
        if self.gmap_enabled and self.satmap is not None:
            for bue_id, coords in self.parent.base_station.bue_id_to_coords.items():
                self.satmap.addMarker(f"{bue_id}", *coords, 
                    icon=self.customPin('green', self.parent.base_station.bue_id_to_hostname[bue_id]),
                    draggable=0,
                )

            # Auto-fit bounds to show all markers
            if not self.gmap_auto_fitted and self.parent.base_station.bue_id_to_coords :
                coords_list = list(self.parent.base_station.bue_id_to_coords.values())
                if coords_list:
                    self.fit_markers_to_view(coords_list)
        else:
            if self.graphmap is not None:
                self.graphmap.clear()
                # Extract coordinates for plotting
                lats = []
                lons = []
                labels = []
                
                for bue_id, coords in self.parent.base_station.bue_id_to_coords.items():
                    lat, lon = coords
                    lats.append(lat)
                    lons.append(lon)
                    hostname = self.parent.base_station.bue_id_to_hostname[bue_id]
                    labels.append(f"{hostname}")
                
                if lats and lons:
                    # Plot scatter points
                    scatter = self.graphmap.plot(lons, lats, pen=None, symbol='o', 
                                            symbolBrush='green', symbolSize=10)
                    
                    # Add text labels for each point
                    for i, (lon, lat, label) in enumerate(zip(lons, lats, labels)):
                        text = pg.TextItem(label, color='green', anchor=(0.5, 1))
                        text.setPos(lon, lat)
                        self.graphmap.addItem(text)        

    def customPin(self, color, name, path=None):
            # Create a circle with text above it
            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="60" height="40" viewBox="0 0 60 40">
                <!-- Text above the circle -->
                <text x="30" y="12" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" fill="{color}">{name}</text>
                <!-- Circle marker -->
                <circle cx="30" cy="25" r="8" fill="{color}" stroke="#000000" stroke-width="2"/>
                <!-- Inner dot -->
                <circle cx="30" cy="25" r="3" fill="#ffffff"/>
            </svg>'''
            
            url = base64DataUrl(svg)
            return dict(
                iconUrl=url,
                iconAnchor=[30, 25],  # Anchor point at center of circle
                iconSize=[60, 40]     # Size of the entire icon
            )