import os
import sys
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QScrollBar, QApplication, QMainWindow, QHBoxLayout, QCheckBox
from PySide6.QtCore import QTimer, QFileSystemWatcher, Signal, QObject, Qt, QThread
from PySide6.QtGui import QFont, QTextCursor, QPalette, QColor


class LogViewerWidget(QWidget):
    """
    A custom PySide6 widget for viewing log files with real-time updates.

    Features:
    - Real-time file monitoring and updates
    - Scroll position preservation when not at bottom
    - Automatic scrolling to bottom for new content (only when already at bottom)
    - Proper spacing and parent handling
    - Non-blocking file operations
    """

    # Signal emitted when log content changes
    logUpdated = Signal(str)

    def __init__(self, parent=None, log_file_path="../logs/last_run.log"):
        super().__init__(parent)

        self.log_file_path = log_file_path
        self.full_log_path = os.path.abspath(log_file_path)
        self.last_file_size = 0
        self.was_at_bottom = True
        self.last_modification_time = 0
        self.is_paused = False  # Track pause state

        self.setup_ui()
        self.setup_file_monitoring()

    def setup_ui(self):
        """Set up the user interface with proper spacing and layout."""
        # Ensure widget has an object name so stylesheet can target it
        self.setObjectName("LogViewerWidget")

        # Ensure the widget background is filled from palette (fallback)
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor("#ffffff"))
        self.setPalette(pal)
        self.setAutoFillBackground(True)

        # Create main layout with appropriate margins
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)  # Add padding from edges
        layout.setSpacing(4)  # Small spacing between controls and text display

        # Create control panel
        control_layout = QHBoxLayout()

        # Create pause checkbox
        self.pause_checkbox = QCheckBox("Pause updates")
        self.pause_checkbox.setToolTip("Pause automatic log updates to read without interruption")
        self.pause_checkbox.toggled.connect(self.on_pause_toggled)
        # Use the application's standard font for the checkbox (not bold) and make indicator larger
        self.pause_checkbox.setFont(QApplication.font())
        self.pause_checkbox.setStyleSheet(
            """
            QCheckBox {
                color: #000000;
                font-size: 10pt;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #ffffff;
                border: 1px solid #5e5e5e;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #0e7490;
                border: 1px solid #0e7490;
                border-radius: 3px;
            }
        """
        )

        control_layout.addWidget(self.pause_checkbox)
        control_layout.addStretch()  # Push checkbox to the left

        layout.addLayout(control_layout)

        # Create text display widget
        self.text_display = QTextEdit(self)
        self.text_display.setReadOnly(True)
        self.text_display.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # Set up font for better readability and don't make it bold
        font = QFont("Consolas", 9)  # Monospace font
        if not font.exactMatch():
            font = QFont("Monaco", 9)
        if not font.exactMatch():
            font = QFont("Courier New", 9)
        # ensure it's not bold so it matches other UI text
        font.setBold(False)
        self.text_display.setFont(font)

        # Style the text display to match white app background and dark text
        self.text_display.setStyleSheet(
            """
            QTextEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #cfcfcf;
                selection-background-color: #cfe8ff;
            }
        """
        )

        # Connect scroll events to track position
        scrollbar = self.text_display.verticalScrollBar()
        scrollbar.valueChanged.connect(self.on_scroll_changed)

        layout.addWidget(self.text_display)

        # Load initial content
        self.load_initial_content()

    def setup_file_monitoring(self):
        """Set up file system monitoring for real-time updates."""
        # Create file system watcher
        self.file_watcher = QFileSystemWatcher(self)

        # Ensure the directory exists
        log_dir = os.path.dirname(self.full_log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Watch the log file and its directory
        if os.path.exists(self.full_log_path):
            self.file_watcher.addPath(self.full_log_path)
        self.file_watcher.addPath(log_dir)

        # Connect file change signals
        self.file_watcher.fileChanged.connect(self.on_file_changed)
        self.file_watcher.directoryChanged.connect(self.on_directory_changed)

        # Set up a timer for periodic checks (backup monitoring)
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.check_file_updates)
        self.update_timer.start(1000)  # Check every second

    def load_initial_content(self):
        """Load the initial content of the log file."""
        try:
            if os.path.exists(self.full_log_path):
                with open(self.full_log_path, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                    self.text_display.setPlainText(content)
                    self.last_file_size = len(content.encode("utf-8"))
                    self.last_modification_time = os.path.getmtime(self.full_log_path)

                    # Scroll to bottom initially
                    self.scroll_to_bottom()
        except Exception as e:
            self.text_display.setPlainText(f"Error loading log file: {str(e)}")

    def on_scroll_changed(self, value):
        """Track whether user is at the bottom of the log."""
        scrollbar = self.text_display.verticalScrollBar()
        # Consider "at bottom" if within 10 pixels of the bottom
        self.was_at_bottom = value >= scrollbar.maximum() - 10

    def on_pause_toggled(self, checked):
        """Handle pause checkbox toggle."""
        self.is_paused = checked
        if checked:
            # When pausing, stop the timer
            if hasattr(self, "update_timer"):
                self.update_timer.stop()
        else:
            # When resuming, restart the timer and do an immediate update
            if hasattr(self, "update_timer"):
                self.update_timer.start(1000)
            self.check_file_updates()  # Immediate check for any missed updates

    def on_file_changed(self, path):
        """Handle file change events."""
        if path == self.full_log_path and not self.is_paused:
            self.update_log_content()

    def on_directory_changed(self, path):
        """Handle directory change events (in case file is recreated)."""
        if not self.is_paused and os.path.exists(self.full_log_path):
            # Re-add the file to watcher if it was recreated
            if self.full_log_path not in self.file_watcher.files():
                self.file_watcher.addPath(self.full_log_path)
            self.update_log_content()

    def check_file_updates(self):
        """Periodic check for file updates (backup method)."""
        if self.is_paused:
            return

        try:
            if os.path.exists(self.full_log_path):
                current_mod_time = os.path.getmtime(self.full_log_path)
                if current_mod_time > self.last_modification_time:
                    self.update_log_content()
        except Exception:
            pass  # Silently handle any file system errors

    def update_log_content(self):
        """Update the log content while preserving scroll position."""
        if self.is_paused:
            return

        try:
            if not os.path.exists(self.full_log_path):
                return

            # Get current file size and modification time
            current_mod_time = os.path.getmtime(self.full_log_path)

            # Only update if file was actually modified
            if current_mod_time <= self.last_modification_time:
                return

            with open(self.full_log_path, "r", encoding="utf-8", errors="ignore") as file:
                new_content = file.read()

            current_content = self.text_display.toPlainText()

            # Only update if content actually changed
            if new_content != current_content:
                # Store scroll position before update
                scrollbar = self.text_display.verticalScrollBar()
                old_scroll_value = scrollbar.value()

                # Update content
                self.text_display.setPlainText(new_content)

                # Restore scroll position or scroll to bottom
                if self.was_at_bottom:
                    # User was at bottom, so scroll to new bottom
                    self.scroll_to_bottom()
                else:
                    # User was scrolled up, preserve their position
                    scrollbar.setValue(old_scroll_value)

                # Update tracking variables
                self.last_file_size = len(new_content.encode("utf-8"))
                self.last_modification_time = current_mod_time

                # Emit signal for any listeners
                self.logUpdated.emit(new_content)

        except Exception as e:
            # Handle errors gracefully - maybe show in status or just ignore
            pass

    def scroll_to_bottom(self):
        """Scroll the text display to the bottom."""
        scrollbar = self.text_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def clear_log(self):
        """Clear the log display."""
        self.text_display.clear()

    def get_log_content(self):
        """Get the current log content."""
        return self.text_display.toPlainText()

    def set_log_file_path(self, new_path):
        """Change the log file being monitored."""
        # Remove old file from watcher
        if self.full_log_path in self.file_watcher.files():
            self.file_watcher.removePath(self.full_log_path)

        # Update path and add to watcher
        self.log_file_path = new_path
        self.full_log_path = os.path.abspath(new_path)

        if os.path.exists(self.full_log_path):
            self.file_watcher.addPath(self.full_log_path)

        # Load new content
        self.load_initial_content()

    def closeEvent(self, event):
        """Clean up when widget is closed."""
        if hasattr(self, "update_timer"):
            self.update_timer.stop()
        if hasattr(self, "file_watcher"):
            self.file_watcher.deleteLater()
        super().closeEvent(event)


# Example usage and testing
if __name__ == "__main__":
    import tempfile
    import threading
    import time

    app = QApplication(sys.argv)

    # Create a test window
    window = QMainWindow()
    window.setWindowTitle("Log Viewer Widget Test")
    window.setGeometry(100, 100, 800, 600)

    # Create the log viewer widget
    log_viewer = LogViewerWidget(window, "logs/last_run.log")
    window.setCentralWidget(log_viewer)

    window.show()

    # Create a test function to write to the log file periodically
    def write_test_logs():
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        log_file = "logs/last_run.log"
        counter = 1

        while True:
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"Test log entry {counter} - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.flush()
                counter += 1
                time.sleep(2)  # Write new log every 2 seconds
            except Exception as e:
                print(f"Error writing to log: {e}")
                break

    # Start background thread to write test logs
    log_thread = threading.Thread(target=write_test_logs, daemon=True)
    log_thread.start()

    sys.exit(app.exec())
