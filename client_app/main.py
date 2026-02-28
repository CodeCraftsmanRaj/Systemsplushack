"""
Systemss Plus | AI Support Bot
Run via:  ./run.sh          (Linux/macOS — sets XCB-safe env vars first)
          uv run main.py    (Windows — no XCB issues there)
"""
import os
import sys

# Numeric thread limits — safe to set here on all platforms.
# On Linux these are also set by run.sh before Python starts, which is
# what actually prevents the XCB crash; these lines are a Windows fallback.
os.environ.setdefault("OMP_NUM_THREADS",        "1")
os.environ.setdefault("MKL_NUM_THREADS",        "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS",   "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS",    "1")
os.environ.setdefault("LOKY_MAX_CPU_COUNT",     "1")

# FIX #1: Ensure the client_app directory is on sys.path so system_utils
# can always be found regardless of the working directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import customtkinter as ctk
import threading
import requests
import joblib
import queue
import system_utils

# FIX #2: Resolve the model path relative to THIS file, not the CWD.
_DATA_ENGINE = os.path.join(_HERE, "..", "data_engine")
MODEL_PATH = os.path.abspath(os.path.join(_DATA_ENGINE, "ticket_classifier.pkl"))
VEC_PATH   = os.path.abspath(os.path.join(_DATA_ENGINE, "vectorizer.pkl"))

# Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class TicketBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Systemss Plus | AI Support Bot")
        self.geometry("600x750")

        # UI State
        self.selected_category = ctk.StringVar()
        self.selected_issue    = ctk.StringVar()
        self.ticket_log        = []

        # AI loaded lazily (Just-In-Time) to prevent startup crashes
        self.ai_model   = None
        self.vectorizer = None

        # Queue for Ollama background thread → main thread communication
        self.msg_queue = queue.Queue()
        self.monitor_queue()

        # Build UI
        self.start_screen()

    # ------------------------------------------------------------------
    # QUEUE MONITOR
    # ------------------------------------------------------------------

    def monitor_queue(self):
        """Drain the inter-thread message queue safely on the main thread."""
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                if msg["action"] == "log_ai":
                    if hasattr(self, "ai_response"):
                        self.ai_response.delete("1.0", "end")
                        self.ai_response.insert("end", msg["content"])
                elif msg["action"] == "error_ai":
                    if hasattr(self, "ai_response"):
                        self.ai_response.delete("1.0", "end")   # FIX #3: clear first
                        self.ai_response.insert("end", f"⚠ {msg['content']}")
        except queue.Empty:
            pass
        self.after(100, self.monitor_queue)

    # ------------------------------------------------------------------
    # UI HELPERS
    # ------------------------------------------------------------------

    def clear_frame(self):
        for widget in self.winfo_children():
            widget.destroy()

    # ------------------------------------------------------------------
    # START SCREEN
    # ------------------------------------------------------------------

    def start_screen(self):
        self.clear_frame()
        self.ticket_log = []  # reset log on returning home

        ctk.CTkLabel(self, text="Systemss Plus Support",   font=("Arial", 24, "bold")).pack(pady=20)
        ctk.CTkLabel(self, text="Automated IT Assistant",  font=("Arial", 14)).pack(pady=5)

        # FIX #4: Complete category → issues mapping (added "Peripheral")
        self._issue_map = {
            "Network":        ["Internet not working", "WiFi connected no internet"],
            "Performance":    ["Computer Slow", "App Frozen"],
            "Software":       ["Teams Cache", "Outlook not opening"],
            "Peripheral":     ["Printer not working", "Mouse / Keyboard unresponsive",
                               "Monitor no signal", "Headset no sound"],
            "Other / Ask AI": ["Describe Issue to AI"],
        }
        categories = list(self._issue_map.keys())

        self.cat_menu = ctk.CTkOptionMenu(
            self, values=categories, command=self.update_issues, width=300
        )
        self.cat_menu.set("Select Category")
        self.cat_menu.pack(pady=10)

        # FIX #5: Populate issue menu with first category's issues by default
        # so it's never empty when the user hasn't touched it yet.
        self.issue_menu = ctk.CTkOptionMenu(self, values=["— select a category first —"], width=300)
        self.issue_menu.set("— select a category first —")
        self.issue_menu.pack(pady=10)

        ctk.CTkButton(self, text="Start Diagnosis", command=self.process_selection).pack(pady=30)

    def update_issues(self, choice):
        options = self._issue_map.get(choice, [])
        if options:
            self.issue_menu.configure(values=options)
            self.issue_menu.set(options[0])
        else:
            self.issue_menu.configure(values=["— no options —"])
            self.issue_menu.set("— no options —")

    def process_selection(self):
        cat   = self.cat_menu.get()
        issue = self.issue_menu.get()

        # FIX #6: Guard – ensure user actually made a real selection
        if cat not in self._issue_map:
            self._show_warning("Please select a category first.")
            return
        if issue in ("— select a category first —", "— no options —", "Select Issue"):
            self._show_warning("Please select an issue first.")
            return

        if cat == "Other / Ask AI":
            self.ask_ai_screen()
        else:
            self.run_fix_screen(cat, issue)

    def _show_warning(self, message: str):
        """Display a non-blocking warning label under the buttons."""
        # Remove any pre-existing warning
        for w in self.winfo_children():
            if getattr(w, "_is_warning", False):
                w.destroy()
        lbl = ctk.CTkLabel(self, text=f"⚠  {message}", text_color="orange", font=("Arial", 12))
        lbl._is_warning = True
        lbl.pack(pady=4)

    # ------------------------------------------------------------------
    # AUTO-FIX FLOW
    # ------------------------------------------------------------------

    def run_fix_screen(self, category, issue):
        self.clear_frame()
        ctk.CTkLabel(self, text=f"Running Auto-Fix: {issue}", font=("Arial", 18)).pack(pady=20)

        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(pady=20)
        self.progress.set(0)

        self.log_box = ctk.CTkTextbox(self, width=500, height=150)
        self.log_box.pack(pady=10)
        self.log_box.insert("end", "Initialising diagnostics…\n")

        self.after(1000, lambda: self.step_2_execute(category, issue))

    def step_2_execute(self, category, issue):
        self.progress.set(0.5)

        # FIX #7: Extended action map to cover all mapped issues
        action_map = {
            "Internet not working":            "flush_dns",
            "WiFi connected no internet":      "flush_dns",
            "App Frozen":                      "restart_explorer",
            "Computer Slow":                   "clear_temp_files",
            "Teams Cache":                     "clear_teams_cache",
            "Outlook not opening":             "restart_outlook",
            "Printer not working":             "restart_print_spooler",
            "Mouse / Keyboard unresponsive":   "reinstall_hid_drivers",
            "Monitor no signal":               "restart_display_driver",
            "Headset no sound":                "restart_audio_service",
        }
        script_key = action_map.get(issue)

        if script_key:
            self.log_box.insert("end", f"Executing script: {script_key}…\n")
            result = system_utils.run_fix(script_key)
            self.log_box.insert("end", result + "\n")
            self.ticket_log.append(f"AutoFix: {script_key} → {result}")
        else:
            self.log_box.insert("end", "No specific script available. Collecting diagnostics…\n")
            self.ticket_log.append("No AutoFix available.")

        self.after(1000, self.step_3_finish)

    def step_3_finish(self):
        self.progress.set(1.0)
        self.log_box.insert("end", "Done.\n")
        self.verification_screen()

    def verification_screen(self):
        ctk.CTkLabel(
            self, text="Please test now. Is it working?",
            font=("Arial", 16, "bold"), text_color="yellow"
        ).pack(pady=10)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="YES – Fixed",        fg_color="green",
                      command=self.close_success).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="NO – Still Broken",  fg_color="red",
                      command=self.create_ticket_screen).pack(side="left", padx=10)

    def close_success(self):
        self.clear_frame()
        ctk.CTkLabel(self, text="Awesome!\nTicket closed automatically.",
                     font=("Arial", 20), text_color="green").pack(pady=50)
        ctk.CTkButton(self, text="Home", command=self.start_screen).pack(pady=20)

    # ------------------------------------------------------------------
    # AI / OLLAMA CHAT
    # ------------------------------------------------------------------

    def ask_ai_screen(self):
        self.clear_frame()
        ctk.CTkLabel(self, text="Describe your issue for the AI Agent:",
                     font=("Arial", 16)).pack(pady=10)

        self.ai_input = ctk.CTkTextbox(self, width=500, height=100)
        self.ai_input.pack(pady=10)

        ctk.CTkButton(self, text="Ask AI", command=self.trigger_ollama).pack(pady=10)

        self.ai_response = ctk.CTkTextbox(self, width=500, height=200)
        self.ai_response.pack(pady=10)

        ctk.CTkButton(
            self, text="Result Didn't Help? Create Ticket",
            fg_color="red", command=self.create_ticket_screen
        ).pack(pady=10)

    def trigger_ollama(self):
        # FIX #8: Strip whitespace/newlines from the prompt
        prompt = self.ai_input.get("1.0", "end").strip()
        if not prompt:
            self.ai_response.delete("1.0", "end")
            self.ai_response.insert("end", "⚠ Please describe your issue before clicking Ask AI.")
            return

        self.ai_response.delete("1.0", "end")
        self.ai_response.insert("end", "Thinking (Local LLM)… Please wait.\n")
        threading.Thread(target=self.ollama_worker, args=(prompt,), daemon=True).start()

    def ollama_worker(self, prompt: str):
        # FIX #9: Specific exception handling instead of bare except
        try:
            url  = "http://localhost:11434/api/generate"
            data = {
                "model":  "llama3",
                "prompt": f"Tech Support: Provide 3 steps to fix: {prompt}",
                "stream": False,
            }
            response = requests.post(url, json=data, timeout=60)
            if response.status_code == 200:
                ans = response.json().get("response", "").strip()
                self.msg_queue.put({"action": "log_ai", "content": ans})
                self.ticket_log.append(f"AI: {ans[:50]}…")
            else:
                self.msg_queue.put({
                    "action":  "error_ai",
                    "content": f"Ollama returned HTTP {response.status_code}.",
                })
        except requests.exceptions.ConnectionError:
            self.msg_queue.put({
                "action":  "error_ai",
                "content": "Cannot reach Ollama. Is it running? (ollama serve)",
            })
        except requests.exceptions.Timeout:
            self.msg_queue.put({
                "action":  "error_ai",
                "content": "Ollama timed out. The model may still be loading.",
            })
        except Exception as exc:  # noqa: BLE001
            self.msg_queue.put({"action": "error_ai", "content": f"Unexpected error: {exc}"})

    # ------------------------------------------------------------------
    # TICKET CREATION
    # ------------------------------------------------------------------

    def create_ticket_screen(self):
        self.clear_frame()
        ctk.CTkLabel(self, text="Escalating to IT Support",
                     font=("Arial", 20, "bold")).pack(pady=10)

        sys_info = system_utils.get_system_info()

        self.desc_entry = ctk.CTkTextbox(self, width=500, height=100)
        self.desc_entry.insert("1.0", "Describe the error…")
        self.desc_entry.pack(pady=5)

        grid = ctk.CTkFrame(self)
        grid.pack(pady=5)

        ctk.CTkLabel(grid, text="Urgency (1=High):").pack(side="left")
        # FIX #10: Set a safe default value so int() never receives an empty string
        self.urg_var = ctk.CTkComboBox(grid, values=["1", "2", "3"])
        self.urg_var.set("2")
        self.urg_var.pack(side="left", padx=5)

        ctk.CTkLabel(grid, text="Impact (1=High):").pack(side="left")
        self.imp_var = ctk.CTkComboBox(grid, values=["1", "2", "3"])
        self.imp_var.set("2")
        self.imp_var.pack(side="left", padx=5)

        ctk.CTkButton(
            self, text="Submit Ticket",
            command=lambda: self.submit_ticket(sys_info)
        ).pack(pady=20)

    def submit_ticket(self, sys_info: dict):
        description = self.desc_entry.get("1.0", "end").strip()

        # FIX #11: Safely parse urgency/impact with a fallback
        try:
            urgency = int(self.urg_var.get())
        except ValueError:
            urgency = 2
        try:
            impact = int(self.imp_var.get())
        except ValueError:
            impact = 2

        priority = system_utils.calculate_priority(urgency, impact)

        # --- LAZY LOADING AI (PREVENTS CRASH) ---
        predicted_level = "Unknown"
        try:
            if os.path.exists(MODEL_PATH) and os.path.exists(VEC_PATH):
                clf = joblib.load(MODEL_PATH)
                vec = joblib.load(VEC_PATH)
                predicted_level = clf.predict(vec.transform([description]))[0]
            else:
                predicted_level = "Model not found – run data_engine/train_model.py first"
        except Exception as exc:
            predicted_level = f"Prediction error: {exc}"
            print(f"[AI] Prediction skipped: {exc}")
        # ----------------------------------------

        ticket_data = (
            "\n*** SYSTEMSS PLUS TICKET ***\n"
            "---------------------------\n"
            f"User : {sys_info.get('Username')}  |  IP: {sys_info.get('IP Address')}\n"
            f"Desc : {description}\n"
            f"Logs : {self.ticket_log}\n"
            "---------------------------\n"
            "[AI ANALYSIS]\n"
            f"Predicted Level : {predicted_level}\n"
            f"Priority        : {priority}\n"
            "---------------------------\n"
        )

        self.clear_frame()
        ctk.CTkLabel(self, text="Ticket Submitted Successfully!",
                     font=("Arial", 20), text_color="green").pack(pady=10)

        res_box = ctk.CTkTextbox(self, width=550, height=400)
        res_box.insert("1.0", ticket_data)
        res_box.pack(pady=10)

        # FIX #12: Give visible feedback that the ticket was copied to clipboard
        self.clipboard_clear()
        self.clipboard_append(ticket_data)
        ctk.CTkLabel(self, text="📋 Ticket details copied to clipboard.",
                     font=("Arial", 11), text_color="gray").pack(pady=2)

        ctk.CTkButton(self, text="🏠 Home", command=self.start_screen).pack(pady=10)


if __name__ == "__main__":
    app = TicketBotApp()
    app.mainloop()