#!/usr/bin/env python3
"""
Simplified Test Dialog that matches main_ui.py workflow
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from loguru import logger
from constants import bUEs


class TestDialog:
    """Simplified test dialog that follows main_ui.py workflow"""

    def __init__(self, parent, base_station):
        self.parent = parent
        self.base_station = base_station

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Test Management")
        self.dialog.geometry("500x600")
        self.dialog.grab_set()

        # Available test files
        self.test_files = [
            "lora_td_ru",
            "lora_tu_rd",
            "helloworld",
            "gpstest",
            "gpstest2",
        ]

        # Selected bUEs and their configurations
        self.selected_bues = []
        self.bue_configs = {}  # {bue_id: {'file': str, 'params': str}}

        self.setup_dialog()

    def setup_dialog(self):
        """Setup the simplified test dialog like main_ui.py"""
        # Step 1: bUE Selection (like basket in main_ui)
        selection_frame = ttk.LabelFrame(
            self.dialog, text="Step 1: Select bUEs for Testing", padding="10"
        )
        selection_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(selection_frame, text="Choose which bUEs will run tests:").pack(
            anchor=tk.W, pady=(0, 10)
        )

        # Create checkboxes for connected bUEs
        self.bue_vars = {}
        checkbox_frame = ttk.Frame(selection_frame)
        checkbox_frame.pack(fill=tk.X)

        row = 0
        col = 0
        for i, bue_id in enumerate(self.base_station.connected_bues):
            bue_name = bUEs.get(str(bue_id), f"bUE {bue_id}")
            var = tk.BooleanVar()
            self.bue_vars[bue_id] = var

            cb = ttk.Checkbutton(
                checkbox_frame,
                text=bue_name,
                variable=var,
                command=self.update_selection,
            )
            cb.grid(row=row, column=col, sticky=tk.W, padx=20, pady=2)

            col += 1
            if col > 1:  # 2 columns
                col = 0
                row += 1

        # Selection summary
        self.selection_label = ttk.Label(
            selection_frame, text="No bUEs selected", foreground="gray"
        )
        self.selection_label.pack(anchor=tk.W, pady=(10, 0))

        # Step 2: Start Time (like main_ui datetime prompt)
        time_frame = ttk.LabelFrame(
            self.dialog, text="Step 2: Set Start Time", padding="10"
        )
        time_frame.pack(fill=tk.X, padx=10, pady=5)

        now = datetime.now()
        time_controls = ttk.Frame(time_frame)
        time_controls.pack()

        ttk.Label(time_controls, text="Hour:").grid(row=0, column=0, padx=5)
        self.hour_var = tk.StringVar(value=str(now.hour))
        ttk.Spinbox(
            time_controls, from_=0, to=23, textvariable=self.hour_var, width=5
        ).grid(row=0, column=1, padx=5)

        ttk.Label(time_controls, text="Minute:").grid(row=0, column=2, padx=5)
        self.minute_var = tk.StringVar(value=str(now.minute))
        ttk.Spinbox(
            time_controls, from_=0, to=59, textvariable=self.minute_var, width=5
        ).grid(row=0, column=3, padx=5)

        ttk.Label(time_controls, text="Second:").grid(row=0, column=4, padx=5)
        self.second_var = tk.StringVar(value=str(now.second))
        ttk.Spinbox(
            time_controls, from_=0, to=59, textvariable=self.second_var, width=5
        ).grid(row=0, column=5, padx=5)

        # Step 3: Configure Individual bUEs
        config_frame = ttk.LabelFrame(
            self.dialog, text="Step 3: Configure Selected bUEs", padding="10"
        )
        config_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        ttk.Label(
            config_frame,
            text="Click 'Configure bUEs' after selecting which ones to test",
        ).pack(anchor=tk.W)

        # Configuration display/status
        self.config_text = tk.Text(
            config_frame, height=10, wrap=tk.WORD, state=tk.DISABLED
        )
        config_scroll = ttk.Scrollbar(config_frame, command=self.config_text.yview)
        self.config_text.configure(yscrollcommand=config_scroll.set)

        self.config_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        config_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.config_btn = ttk.Button(
            button_frame,
            text="Configure bUEs",
            command=self.configure_selected_bues,
            state=tk.DISABLED,
        )
        self.config_btn.pack(side=tk.LEFT, padx=5)

        self.run_btn = ttk.Button(
            button_frame, text="Run Tests", command=self.run_tests, state=tk.DISABLED
        )
        self.run_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(
            side=tk.RIGHT, padx=5
        )

    def update_selection(self):
        """Update the selection when checkboxes change"""
        self.selected_bues = [
            bue_id for bue_id, var in self.bue_vars.items() if var.get()
        ]

        if self.selected_bues:
            bue_names = [bUEs.get(str(bid), f"bUE {bid}") for bid in self.selected_bues]
            self.selection_label.config(
                text=f"Selected: {', '.join(bue_names)}", foreground="blue"
            )
            self.config_btn.config(state=tk.NORMAL)

            # Clear previous configs if selection changed
            self.bue_configs = {}
            self.update_config_display()
        else:
            self.selection_label.config(text="No bUEs selected", foreground="gray")
            self.config_btn.config(state=tk.DISABLED)
            self.run_btn.config(state=tk.DISABLED)
            self.bue_configs = {}
            self.update_config_display()

    def configure_selected_bues(self):
        """Configure each selected bUE individually (like main_ui loop)"""
        if not self.selected_bues:
            return

        # Configure each bUE one by one (like main_ui.py does)
        for bue_id in self.selected_bues:
            if bue_id not in self.bue_configs:
                # Launch individual bUE configuration dialog
                config_dialog = IndividualBueConfigDialog(
                    self.dialog, bue_id, self.test_files, self.bue_configs
                )
                self.dialog.wait_window(config_dialog.dialog)

        self.update_config_display()

        # Enable run button if all bUEs are configured
        if len(self.bue_configs) == len(self.selected_bues):
            self.run_btn.config(state=tk.NORMAL)

    def update_config_display(self):
        """Update the configuration display"""
        self.config_text.config(state=tk.NORMAL)
        self.config_text.delete(1.0, tk.END)

        if self.bue_configs:
            self.config_text.insert(tk.END, "Test Configuration Summary:\n\n")
            for bue_id, config in self.bue_configs.items():
                bue_name = bUEs.get(str(bue_id), f"bUE {bue_id}")
                self.config_text.insert(tk.END, f"{bue_name}:\n")
                self.config_text.insert(tk.END, f"  File: {config['file']}\n")
                self.config_text.insert(tk.END, f"  Parameters: {config['params']}\n\n")
        else:
            self.config_text.insert(
                tk.END,
                "No bUEs configured yet.\n\nSelect bUEs above, then click 'Configure bUEs' to set up tests.",
            )

        self.config_text.config(state=tk.DISABLED)

    def run_tests(self):
        """Execute the configured tests (like main_ui send_test)"""
        if not self.bue_configs:
            messagebox.showwarning(
                "No Configuration", "Please configure at least one bUE for testing"
            )
            return

        # Calculate start time (like main_ui.py)
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            second = int(self.second_var.get())

            today = date.today()
            start_time = datetime.combine(
                today,
                datetime.min.time().replace(hour=hour, minute=minute, second=second),
            )
            unix_timestamp = int(start_time.timestamp())

            # Send test commands (like main_ui.py)
            for bue_id, config in self.bue_configs.items():
                command = f"TEST-{config['file']}-{unix_timestamp}-{config['params']}"
                self.base_station.ota.send_ota_message(bue_id, command)
                logger.info(f"Sent test command to bUE {bue_id}: {command}")

            bue_names = [
                bUEs.get(str(bue_id), str(bue_id)) for bue_id in self.bue_configs.keys()
            ]
            messagebox.showinfo(
                "Tests Started", f"Started tests on: {', '.join(bue_names)}"
            )
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start tests: {e}")


class IndividualBueConfigDialog:
    """Individual bUE configuration dialog (like main_ui.py prompts)"""

    def __init__(self, parent, bue_id, test_files, bue_configs):
        self.parent = parent
        self.bue_id = bue_id
        self.test_files = test_files
        self.bue_configs = bue_configs

        bue_name = bUEs.get(str(bue_id), f"bUE {bue_id}")

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Configure {bue_name}")
        self.dialog.geometry("400x300")
        self.dialog.wait_visibility()
        self.dialog.grab_set()

        self.setup_dialog()

    def setup_dialog(self):
        """Setup individual bUE configuration (like main_ui.py prompts)"""
        bue_name = bUEs.get(str(self.bue_id), f"bUE {self.bue_id}")

        # Header
        header_frame = ttk.Frame(self.dialog)
        header_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(
            header_frame,
            text=f"Configure test for {bue_name}",
            font=("TkDefaultFont", 12, "bold"),
        ).pack()

        # Test file selection (like main_ui.py select prompt)
        file_frame = ttk.LabelFrame(self.dialog, text="Select Test File", padding="10")
        file_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(file_frame, text="What file would you like to run?").pack(
            anchor=tk.W, pady=(0, 5)
        )

        self.file_var = tk.StringVar(value=self.test_files[0])
        for i, test_file in enumerate(self.test_files):
            ttk.Radiobutton(
                file_frame, text=test_file, variable=self.file_var, value=test_file
            ).pack(anchor=tk.W, padx=20)

        # Parameters (like main_ui.py input prompt)
        params_frame = ttk.LabelFrame(self.dialog, text="Parameters", padding="10")
        params_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Label(params_frame, text="Enter parameters separated by space:").pack(
            anchor=tk.W, pady=(0, 5)
        )
        self.params_var = tk.StringVar()
        ttk.Entry(params_frame, textvariable=self.params_var, width=40).pack(fill=tk.X)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=20)

        ttk.Button(
            button_frame, text="Save Configuration", command=self.save_config
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(
            side=tk.RIGHT, padx=5
        )

    def save_config(self):
        """Save the bUE configuration"""
        self.bue_configs[self.bue_id] = {
            "file": self.file_var.get(),
            "params": self.params_var.get(),
        }
        self.dialog.destroy()
