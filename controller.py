import asyncio
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog
import os 
import websockets
import shutil
import http.server
import socketserver
import sys

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
SAVE_FILE = os.path.join(BASE_DIR, "deadlock_draft_state.json")

# Static list of Deadlock Heroes
HERO_LIST = [
    "None", "Abrams", "Apollo", "Baba", "Bebop", "Billy", "Calico", "Celeste", 
    "Deadman Danny", "The Doorman", "Drifter", "Dynamo", "Graves", "Grey Talon", "Haze", 
    "Holliday", "Infernus", "Ivy", "Kelvin", "Lady Geist", "Lash", "McGinnis", 
    "Mina", "Mirage", "Mo & Krill", "Nurse Harrow", "Paige", "Paradox", "Pocket", 
    "Rat King", "Rem", "Seven", "Shiv", "Silver", "Sinclair", "Solomon", "Venator",
    "Victor", "Vindicta", "Violet", "Viscous", "Vyper", "Warden", "Wraith", "Yamato"
]

default_state = {
    "patch": "Week 1",
    "sponsor": "College Deadlock",
    "blue": {
        "name": "PFW",
        "logo": "",
        "score": 0,
        "players": ["Player 1", "Player 2", "Player 3", "Player 4", "Player 5", "Player 6"],
        "picks": ["None", "None", "None", "None", "None", "None"]
    },
    "red": {
        "name": "OPP",
        "logo": "",
        "score": 0,
        "players": ["Player 1", "Player 2", "Player 3", "Player 4", "Player 5", "Player 6"],
        "picks": ["None", "None", "None", "None", "None", "None"]
    }
}

def load_state():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r") as f:
                saved_state = json.load(f)
                for key in default_state:
                    if key not in saved_state:
                        saved_state[key] = default_state[key]
                return saved_state
        except Exception as e:
            print(f"Error reading save file: {e}")
    return default_state

state = load_state()

connected_clients = set()
server_loop = None

async def handler(websocket):
    connected_clients.add(websocket)
    await websocket.send(json.dumps(state))
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)

async def broadcast_state():
    if connected_clients:
        message = json.dumps(state)
        await asyncio.gather(*[client.send(message) for client in connected_clients])

def trigger_broadcast():
    if server_loop and server_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_state(), server_loop)

async def run_server():
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future() 

def start_server():
    global server_loop
    server_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(server_loop)
    server_loop.run_until_complete(run_server())

def start_http_server():
    PORT = 8000
    os.chdir(BASE_DIR)
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("localhost", PORT), Handler) as httpd:
        print(f"Serving HTTP at http://localhost:{PORT}")
        httpd.serve_forever()

class SearchableDropdown(ttk.Frame):
    def __init__(self, parent, values, width=16, **kwargs):
        super().__init__(parent)
        self.values = values
        self.current_value = tk.StringVar(value="None")
        
        self.btn = ttk.Button(self, textvariable=self.current_value, width=width, command=self.open_popup)
        self.btn.pack(fill="both", expand=True)
        self.popup = None

    def set(self, value):
        self.current_value.set(value)

    def get(self):
        return self.current_value.get()
        
    def bind(self, sequence, func, add=None):
        self.btn.bind(sequence, func, add)
        
    def event_generate(self, sequence):
        self.btn.event_generate(sequence)

    def open_popup(self):
        if self.popup and self.popup.winfo_exists():
            return

        self.popup = tk.Toplevel(self)
        self.popup.wm_overrideredirect(True)
        self.popup.attributes('-topmost', True)
        
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self.popup.geometry(f"{self.winfo_width() + 40}x200+{x}+{y}")

        search_var = tk.StringVar()
        search_entry = ttk.Entry(self.popup, textvariable=search_var)
        search_entry.pack(fill="x", padx=1, pady=1)
        search_entry.focus_set()

        list_frame = ttk.Frame(self.popup)
        list_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, selectmode="browse")
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        def update_list(*args):
            typed = search_var.get().lower()
            listbox.delete(0, tk.END)
            for item in self.values:
                if typed in item.lower():
                    listbox.insert(tk.END, item)
            if listbox.size() > 0:
                listbox.selection_set(0)

        update_list()
        search_var.trace_add("write", update_list)

        def make_selection(event=None):
            if listbox.curselection():
                self.set(listbox.get(listbox.curselection()[0]))
                self.event_generate("<<ComboboxSelected>>")
            if self.popup:
                self.popup.destroy()

        def check_focus():
            if self.popup and self.popup.winfo_exists():
                focus = self.popup.focus_get()
                if not focus or not str(focus).startswith(str(self.popup)):
                    self.popup.destroy()

        listbox.bind("<ButtonRelease-1>", make_selection)
        search_entry.bind("<Return>", make_selection)
        search_entry.bind("<Escape>", lambda e: self.popup.destroy() if self.popup else None)
        
        if self.popup:
            self.popup.bind("<FocusOut>", lambda e: self.after(100, check_focus))

class OverlayController(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Deadlock Broadcast Controller")
        self.geometry("900x650")
        self.configure(padx=10, pady=10)

        # --- GUI LAYOUT ---
        meta_frame = ttk.LabelFrame(self, text="Broadcast Match Info", padding=8)
        meta_frame.pack(fill="x", pady=5)

        ttk.Label(meta_frame, text="League/Match:").grid(row=0, column=0, padx=4)
        self.patch_entry = ttk.Entry(meta_frame, width=20)
        self.patch_entry.insert(0, state["patch"])
        self.patch_entry.grid(row=0, column=1, padx=4)

        ttk.Label(meta_frame, text="Sponsor/Bottom Text:").grid(row=0, column=2, padx=4)
        self.sponsor_entry = ttk.Entry(meta_frame, width=25)
        self.sponsor_entry.insert(0, state["sponsor"])
        self.sponsor_entry.grid(row=0, column=3, padx=4)

        ttk.Button(
            meta_frame, text="Swap Teams ⇄", command=self.swap_teams
        ).grid(row=0, column=4, padx=(20, 0))

        teams_container = ttk.Frame(self)
        teams_container.pack(fill="both", expand=True, pady=5)

        self.blue_widgets = self._build_team_column(teams_container, "Blue Side", "blue", 0)
        self.red_widgets = self._build_team_column(teams_container, "Red Side", "red", 1)

        broadcast_btn = tk.Button(
            self, text="BROADCAST UPDATE TO OVERLAY", command=self.push_updates,
            font=("Segoe UI", 10, "bold"), pady=5
        )
        broadcast_btn.pack(fill="x", pady=10)

    def _build_team_column(self, parent, title, side_key, column_idx):
        frame = ttk.LabelFrame(parent, text=title, padding=10)
        frame.grid(row=0, column=column_idx, sticky="nsew", padx=5)
        parent.grid_columnconfigure(column_idx, weight=1)

        info_frame = ttk.Frame(frame)
        info_frame.pack(fill="x", pady=2)

        ttk.Label(info_frame, text="Team Tag:").grid(row=0, column=0, sticky="w")
        team_name_entry = ttk.Entry(info_frame, width=12)
        team_name_entry.insert(0, state[side_key]["name"])
        team_name_entry.grid(row=0, column=1, padx=4, pady=2)

        ttk.Label(info_frame, text="Score:").grid(row=1, column=0, sticky="w")
        score_entry = ttk.Entry(info_frame, width=12)
        score_entry.insert(0, str(state[side_key]["score"]))
        score_entry.grid(row=1, column=1, padx=4, pady=2)

        ttk.Label(info_frame, text="Logo:").grid(row=2, column=0, sticky="w")
        logo_path_var = tk.StringVar(value=state[side_key].get("logo", ""))
        
        def browse_logo():
            filename = filedialog.askopenfilename(
                title="Select Team Logo",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.svg")]
            )
            if filename:
                ext = os.path.splitext(filename)[1]
                local_name = f"{side_key}_logo{ext}"
                dest_path = os.path.join(BASE_DIR, local_name)
                
                try:
                    shutil.copy(filename, dest_path)
                    logo_path_var.set(local_name)  
                    self.push_updates()
                except Exception as e:
                    print(f"Failed to copy image: {e}")

        logo_btn = ttk.Button(info_frame, textvariable=logo_path_var, width=10, command=browse_logo)
        logo_btn.grid(row=2, column=1, padx=4, pady=2)

        pick_frame = ttk.LabelFrame(frame, text="Players & Hero Picks (6v6)", padding=6)
        pick_frame.pack(fill="x", pady=6)
        
        player_entries, pick_combos = [], []

        # Headers
        ttk.Label(pick_frame, text="Player Name").grid(row=0, column=1, pady=2)
        ttk.Label(pick_frame, text="Hero Pick").grid(row=0, column=2, pady=2)

        for i in range(6):
            r = i + 1
            ttk.Label(pick_frame, text=f"P{r}:").grid(row=r, column=0, sticky="w", pady=2)
            
            p_entry = ttk.Entry(pick_frame, width=18)
            p_entry.insert(0, state[side_key]["players"][i])
            p_entry.grid(row=r, column=1, padx=4, pady=4)
            player_entries.append(p_entry)

            cb = SearchableDropdown(pick_frame, values=HERO_LIST, width=16)
            cb.set(state[side_key]["picks"][i])
            cb.grid(row=r, column=2, padx=4, pady=4)
            cb.bind("<<ComboboxSelected>>", lambda e: self.push_updates())
            pick_combos.append(cb)

        def clear_picks():
            for cb in pick_combos:
                cb.set("None")
                cb.event_generate("<<ComboboxSelected>>") 
            self.push_updates()

        ttk.Button(pick_frame, text="Clear All Picks", command=clear_picks).grid(row=7, column=1, columnspan=2, pady=10, sticky="ew")

        return {
            "name": team_name_entry, 
            "score": score_entry,
            "logo": logo_path_var,
            "players": player_entries, 
            "picks": pick_combos
        }

    def swap_teams(self):
        blue_name = self.blue_widgets["name"].get()
        blue_score = self.blue_widgets["score"].get()
        blue_logo = self.blue_widgets["logo"].get()
        blue_players = [entry.get() for entry in self.blue_widgets["players"]]
        
        red_name = self.red_widgets["name"].get()
        red_score = self.red_widgets["score"].get()
        red_logo = self.red_widgets["logo"].get()
        red_players = [entry.get() for entry in self.red_widgets["players"]]
        
        self.blue_widgets["name"].delete(0, tk.END)
        self.blue_widgets["name"].insert(0, red_name)
        self.red_widgets["name"].delete(0, tk.END)
        self.red_widgets["name"].insert(0, blue_name)

        self.blue_widgets["score"].delete(0, tk.END)
        self.blue_widgets["score"].insert(0, red_score)
        self.red_widgets["score"].delete(0, tk.END)
        self.red_widgets["score"].insert(0, blue_score)
        
        self.blue_widgets["logo"].set(red_logo)
        self.red_widgets["logo"].set(blue_logo)

        for i in range(6):
            self.blue_widgets["players"][i].delete(0, tk.END)
            self.blue_widgets["players"][i].insert(0, red_players[i])
            self.red_widgets["players"][i].delete(0, tk.END)
            self.red_widgets["players"][i].insert(0, blue_players[i])
        
        self.push_updates()

    def push_updates(self):
        state["patch"] = self.patch_entry.get()
        state["sponsor"] = self.sponsor_entry.get()

        for side_key, widgets in [("blue", self.blue_widgets), ("red", self.red_widgets)]:
            state[side_key]["name"] = widgets["name"].get()
            
            try:
                state[side_key]["score"] = int(widgets["score"].get())
            except ValueError:
                state[side_key]["score"] = 0

            state[side_key]["logo"] = widgets["logo"].get()
            state[side_key]["players"] = [entry.get() for entry in widgets["players"]]
            state[side_key]["picks"] = [cb.get() for cb in widgets["picks"]]

        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"Error writing save file: {e}")

        trigger_broadcast()

if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    threading.Thread(target=start_http_server, daemon=True).start() 
    app = OverlayController()
    app.mainloop()