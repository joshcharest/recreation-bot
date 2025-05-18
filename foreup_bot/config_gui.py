import json
import tkinter as tk
from tkinter import ttk


class ConfigGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ForeUp Bot Configuration")
        self.root.geometry("400x600")

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
        ttk.Label(self.root, text="Target Date (MM-DD-YYYY):").pack(pady=5)
        self.date_entry = ttk.Entry(self.root)
        self.date_entry.insert(0, self.config.get("target_date", ""))
        self.date_entry.pack(pady=5)

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
        ttk.Label(self.root, text="Target Time (HH:MM AM/PM):").pack(pady=5)
        self.target_time_entry = ttk.Entry(self.root)
        self.target_time_entry.insert(0, self.config.get("start_time", ""))
        self.target_time_entry.pack(pady=5)

        # Window start time
        ttk.Label(self.root, text="Window Start Time (HH:MM AM/PM):").pack(pady=5)
        self.window_start_entry = ttk.Entry(self.root)
        self.window_start_entry.insert(0, self.config.get("window_start_time", ""))
        self.window_start_entry.pack(pady=5)

        # Window end time
        ttk.Label(self.root, text="Window End Time (HH:MM AM/PM):").pack(pady=5)
        self.window_end_entry = ttk.Entry(self.root)
        self.window_end_entry.insert(0, self.config.get("window_end_time", ""))
        self.window_end_entry.pack(pady=5)

        # Save button
        ttk.Button(self.root, text="Save Configuration", command=self.save_config).pack(
            pady=20
        )

    def save_config(self):
        config = {
            "target_date": self.date_entry.get(),
            "num_players": int(self.players_var.get()),
            "start_time": self.target_time_entry.get(),
            "window_start_time": self.window_start_entry.get(),
            "window_end_time": self.window_end_entry.get(),
        }

        with open("foreup_bot/foreup_config.json", "w") as f:
            json.dump(config, f, indent=4)

        self.root.quit()

    def run(self):
        self.root.mainloop()
        return self.config


if __name__ == "__main__":
    gui = ConfigGUI()
    gui.run()
