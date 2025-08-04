import json
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from tkcalendar import DateEntry


class TimePicker(ttk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Hour selection
        self.hour_var = tk.StringVar(value="12")
        self.hour_combo = ttk.Combobox(
            self,
            textvariable=self.hour_var,
            values=[f"{i:02d}" for i in range(1, 13)],
            width=3,
        )
        self.hour_combo.pack(side=tk.LEFT, padx=2)

        # Minute selection
        self.minute_var = tk.StringVar(value="00")
        self.minute_combo = ttk.Combobox(
            self,
            textvariable=self.minute_var,
            values=[f"{i:02d}" for i in range(0, 60, 5)],
            width=3,
        )
        self.minute_combo.pack(side=tk.LEFT, padx=2)

        # AM/PM selection
        self.ampm_var = tk.StringVar(value="AM")
        self.ampm_combo = ttk.Combobox(
            self, textvariable=self.ampm_var, values=["AM", "PM"], width=3
        )
        self.ampm_combo.pack(side=tk.LEFT, padx=2)

    def get_time(self):
        return f"{self.hour_var.get()}:{self.minute_var.get()} {self.ampm_var.get()}"

    def set_time(self, time_str):
        try:
            time = datetime.strptime(time_str, "%I:%M %p")
            self.hour_var.set(f"{time.hour:02d}")
            self.minute_var.set(f"{time.minute:02d}")
            self.ampm_var.set(time.strftime("%p"))
        except:
            pass


class ConfigGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ForeUp Bot Configuration")
        self.root.geometry("400x700")

        # Load existing config if it exists
        try:
            with open("foreup_bot/foreup_config.json", "r") as f:
                self.config = json.load(f)
        except:
            self.config = {
                "target_date": "",
                "num_players": 4,
                "start_time": "",
                "window_start_time": "",
                "window_end_time": "",
            }

        self.create_widgets()

    def create_widgets(self):
        # Date selection
        ttk.Label(self.root, text="Target Date:").pack(pady=5)
        self.date_picker = DateEntry(
            self.root,
            width=12,
            background="darkblue",
            foreground="white",
            borderwidth=2,
            firstweekday="sunday",  # Start week on Sunday
            showweeknumbers=False,  # Hide week numbers
            selectmode="day",  # Only allow day selection
            year=datetime.now().year,
            month=datetime.now().month,
            day=datetime.now().day,
            selectbackground="red",  # Highlight selected day
            normalbackground="white",
            normalforeground="black",
            weekendbackground="white",
            weekendforeground="black",
            othermonthbackground="gray90",
            othermonthforeground="gray50",
            othermonthwebackground="gray90",
            othermonthweforeground="gray50",
            disableddaybackground="gray90",
            disableddayforeground="gray50",
            disabledselectbackground="gray90",
            disabledselectforeground="gray50",
        )
        if self.config.get("target_date"):
            try:
                date = datetime.strptime(self.config["target_date"], "%m-%d-%Y")
                self.date_picker.set_date(date)
            except:
                pass
        self.date_picker.pack(pady=5)

        # Number of players
        ttk.Label(self.root, text="Number of Players:").pack(pady=5)
        self.players_var = tk.StringVar(value=str(self.config.get("num_players", 4)))
        players_frame = ttk.Frame(self.root)
        players_frame.pack(pady=5)
        for i in range(1, 5):
            ttk.Radiobutton(
                players_frame, text=str(i), value=str(i), variable=self.players_var
            ).pack(side=tk.LEFT, padx=5)

        # Target time
        ttk.Label(self.root, text="Target Time:").pack(pady=5)
        self.target_time_picker = TimePicker(self.root)
        self.target_time_picker.pack(pady=5)
        if self.config.get("start_time"):
            self.target_time_picker.set_time(self.config["start_time"])

        # Window start time
        ttk.Label(self.root, text="Window Start Time:").pack(pady=5)
        self.window_start_picker = TimePicker(self.root)
        self.window_start_picker.pack(pady=5)
        if self.config.get("window_start_time"):
            self.window_start_picker.set_time(self.config["window_start_time"])

        # Window end time
        ttk.Label(self.root, text="Window End Time:").pack(pady=5)
        self.window_end_picker = TimePicker(self.root)
        self.window_end_picker.pack(pady=5)
        if self.config.get("window_end_time"):
            self.window_end_picker.set_time(self.config["window_end_time"])

        # Save button
        ttk.Button(self.root, text="Save Configuration", command=self.save_config).pack(
            pady=20
        )

    def save_config(self):
        config = {
            "target_date": self.date_picker.get_date().strftime("%m-%d-%Y"),
            "num_players": int(self.players_var.get()),
            "start_time": self.target_time_picker.get_time(),
            "window_start_time": self.window_start_picker.get_time(),
            "window_end_time": self.window_end_picker.get_time(),
        }

        with open("foreup_bot/foreup_config.json", "w") as f:
            json.dump(config, f, indent=4)

        self.root.destroy()  # Close the window instead of just quitting

    def run(self):
        self.root.mainloop()
        return self.config


if __name__ == "__main__":
    gui = ConfigGUI()
    gui.run()
