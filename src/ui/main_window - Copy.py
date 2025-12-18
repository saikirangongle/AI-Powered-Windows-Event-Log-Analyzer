# src/ui/main_window.py
"""
Main UI Window for Win Log Interpreter (Gemini-only)

Modified: left column now displays only the Log Table (Event Log viewer removed).
If LogsTable component is not available, a simple Treeview fallback is created.
"""

import os
import platform
import re
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Optional, List

from src.main.logger import logger
from src.main.config import load_config, save_app_settings
from src.api.api_client_gemini import GeminiClient
from src.api.event_analyzer import analyze
from src.api.ai_explainer import get_explanation
from src.utils.file_loader import load_file
from src.utils.parser import parse_log
from src.utils.validators import is_valid_api_key

# Windows event log reader (may be None if not available)
try:
    from src.utils.win_event_reader import read_windows_event_log
except Exception:
    read_windows_event_log = None

# Optional UI components
try:
    from src.ui.components.explanation_panel import ExplanationPanel
    from src.ui.components.timeline_panel import TimelinePanel
    from src.ui.components.logs_table import LogsTable
except Exception:
    ExplanationPanel = None
    TimelinePanel = None
    LogsTable = None


LOG_TYPES = ["System", "Application", "Security"]


class SimpleLogsTable(ttk.Frame):
    """
    Fallback logs table implemented with ttk.Treeview when LogsTable component is absent.
    Exposes:
      - load_rows(rows: List[dict])
      - get_selected() -> dict | None
      - on_double_click(callback)
    """
    def __init__(self, master=None):
        super().__init__(master)
        self.tree = ttk.Treeview(self, columns=("timestamp", "severity", "summary"), show="headings", height=20)
        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("severity", text="Severity")
        self.tree.heading("summary", text="Summary")
        self.tree.column("timestamp", width=160, anchor="w")
        self.tree.column("severity", width=80, anchor="w")
        self.tree.column("summary", width=400, anchor="w")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.config(yscrollcommand=scrollbar.set)

        self._double_click_cb = None
        self.tree.bind("<Double-1>", self._on_double)

        # store rows so we can return raw_event on selection
        self._rows = []

    def load_rows(self, rows: List[dict]):
        self._rows = rows or []
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(rows):
            ts = r.get("timestamp", "")
            sev = r.get("severity", "")
            summ = r.get("summary", "")[:400]
            self.tree.insert("", "end", iid=str(i), values=(ts, sev, summ))

    def get_selected(self) -> Optional[dict]:
        sel = self.tree.selection()
        if not sel:
            return None
        idx = int(sel[0])
        if 0 <= idx < len(self._rows):
            return self._rows[idx]
        return None

    def on_double_click(self, cb):
        self._double_click_cb = cb

    def _on_double(self, _event):
        if self._double_click_cb:
            row = self.get_selected()
            try:
                self._double_click_cb(row)
            except Exception:
                logger.exception("LogsTable double-click handler failed")


class MainWindow:
    def __init__(self, root, gemini_client: Optional[GeminiClient] = None):
        self.root = root
        self.root.title("Win Log Interpreter (Gemini-only)")
        self.root.geometry("1200x700")
        self.gemini = gemini_client

        # Events storage
        self._loaded_events: List[str] = []
        self._filtered_events: List[str] = []
        self._last_loaded_winlog_type: Optional[str] = None
        self._loaded_from_file: bool = False  # True when events come from a user-opened file

        # Build UI
        self._build_menu()
        self._build_ui_layout()
        self._update_ui_state_on_key()

        if not self.gemini:
            messagebox.showwarning(
                "Gemini API key required",
                "You can still view logs and run local analysis, but AI features require a Gemini API key.\n"
                "Open Settings → Settings to add your Gemini API key."
            )

        # Auto-load Windows System log on startup
        self._auto_load_windows_logs()

    # ---------------------------
    # Auto-load Windows logs
    # ---------------------------
    def _auto_load_windows_logs(self):
        if platform.system().lower() != "windows":
            logger.info("Not on Windows — skipping Windows Event Log auto-load.")
            return
        if not read_windows_event_log:
            logger.info("Windows Event Log reader not available; ensure pywin32 or wevtutil is usable.")
            return

        try:
            logger.info("Auto-loading Windows 'System' event log...")
            events = read_windows_event_log("System", max_records=500)
            if events:
                self._loaded_events = events
                self._last_loaded_winlog_type = "System"
                self._loaded_from_file = False
                self.log_type_var.set("System")
                self._apply_log_type_filter()
                logger.info("Loaded %d system events", len(events))
            else:
                logger.info("No system events found during auto-load.")
        except Exception:
            logger.exception("Failed to auto-load Windows System log.")

    # ---------------------------
    # Menu
    # ---------------------------
    def _build_menu(self):
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open Log File...", command=self.open_file)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        settingsmenu = tk.Menu(menubar, tearoff=0)
        settingsmenu.add_command(label="Settings", command=self.open_settings_dialog)
        menubar.add_cascade(label="Settings", menu=settingsmenu)

        debugmenu = tk.Menu(menubar, tearoff=0)
        debugmenu.add_command(label="Debug: Show Counts", command=self._debug_show_counts)
        menubar.add_cascade(label="Debug", menu=debugmenu)

        self.root.config(menu=menubar)

    # ---------------------------
    # UI layout: three columns (left now only contains Log Table)
    # ---------------------------
    def _build_ui_layout(self):
        main_frame = ttk.Frame(self.root, padding=8)
        main_frame.pack(fill=tk.BOTH, expand=True)

        paned = ttk.Panedwindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # LEFT: Only Log Table (removing Event Log viewer)
        left_frame = ttk.Frame(paned, width=380)
        paned.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Log Table", font=("Arial", 12, "bold")).pack(anchor="w", pady=(2, 6))

        # Controls above the table
        ctrl_frame = ttk.Frame(left_frame)
        ctrl_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(ctrl_frame, text="Log Type:").pack(side=tk.LEFT, padx=(0, 6))
        self.log_type_var = tk.StringVar(value=LOG_TYPES[0])
        self.log_type_cb = ttk.Combobox(ctrl_frame, textvariable=self.log_type_var, values=LOG_TYPES, state="readonly", width=12)
        self.log_type_cb.pack(side=tk.LEFT)
        self.log_type_cb.bind("<<ComboboxSelected>>", lambda e: self._apply_log_type_filter())

        ttk.Button(ctrl_frame, text="Refresh", command=self._apply_log_type_filter).pack(side=tk.LEFT, padx=6)

        # Logs table: prefer LogsTable component, else fallback
        if LogsTable:
            try:
                self.logs_table = LogsTable(left_frame)
                # ensure it fills available area
                try:
                    self.logs_table.pack(fill=tk.BOTH, expand=True)
                except Exception:
                    if hasattr(self.logs_table, "frame"):
                        self.logs_table.frame.pack(fill=tk.BOTH, expand=True)
                try:
                    self.logs_table.on_double_click(self._on_logs_table_double_click)
                except Exception:
                    pass
            except Exception:
                logger.exception("Failed to instantiate LogsTable component; using fallback.")
                self.logs_table = SimpleLogsTable(left_frame)
                self.logs_table.pack(fill=tk.BOTH, expand=True)
                self.logs_table.on_double_click(self._on_logs_table_double_click)
        else:
            self.logs_table = SimpleLogsTable(left_frame)
            self.logs_table.pack(fill=tk.BOTH, expand=True)
            self.logs_table.on_double_click(self._on_logs_table_double_click)

        # MIDDLE: Single-log AI Explainer
        mid_frame = ttk.Frame(paned, width=420)
        paned.add(mid_frame, weight=1)

        ttk.Label(mid_frame, text="Single Log AI Explainer", font=("Arial", 12, "bold")).pack(anchor="w", pady=(2, 6))

        if ExplanationPanel:
            try:
                self.single_explainer = ExplanationPanel(mid_frame, height=20)
                try:
                    self.single_explainer.pack(fill=tk.BOTH, expand=True)
                except Exception:
                    if hasattr(self.single_explainer, "frame"):
                        self.single_explainer.frame.pack(fill=tk.BOTH, expand=True)
            except Exception:
                logger.exception("Failed to instantiate ExplanationPanel; using Text fallback.")
                self.single_explainer = scrolledtext.ScrolledText(mid_frame, wrap=tk.WORD, height=20)
                self.single_explainer.pack(fill=tk.BOTH, expand=True)
        else:
            self.single_explainer = scrolledtext.ScrolledText(mid_frame, wrap=tk.WORD, height=20)
            self.single_explainer.pack(fill=tk.BOTH, expand=True)

        single_btn_frame = ttk.Frame(mid_frame)
        single_btn_frame.pack(fill=tk.X, pady=(6, 0))
        self.btn_explain_selected = ttk.Button(single_btn_frame, text="Explain Selected", command=self.explain_selected_event)
        self.btn_explain_selected.pack(side=tk.LEFT, padx=4)
        self.btn_explain_and_analyze = ttk.Button(single_btn_frame, text="Explain & Show Analysis", command=self.explain_and_analyze_selected)
        self.btn_explain_and_analyze.pack(side=tk.LEFT, padx=4)

        # RIGHT: Time-range explainer (datetime-based, responsive layout + presets)
        right_frame = ttk.Frame(paned, width=420)
        paned.add(right_frame, weight=1)

        ttk.Label(right_frame, text="Time-Range AI Explainer", font=("Arial", 12, "bold")).pack(anchor="w", pady=(2, 6))

        # Grid frame so controls stack cleanly
        range_frame = ttk.Frame(right_frame)
        range_frame.pack(fill=tk.X, pady=(0, 6), padx=4)

        ttk.Label(range_frame, text="Preset range:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 4))
        self.range_preset_var = tk.StringVar(value="Custom")
        presets = ["Custom", "Last 5 minutes", "Last 15 minutes", "Last 1 hour", "Last 24 hours", "Today"]
        self.range_preset_cb = ttk.Combobox(range_frame, textvariable=self.range_preset_var, values=presets, state="readonly", width=22)
        self.range_preset_cb.grid(row=0, column=1, sticky="w", pady=(0, 4))
        self.range_preset_cb.bind("<<ComboboxSelected>>", lambda e: self._on_preset_selected())

        ttk.Label(range_frame, text="Start time (e.g. 2024-01-25 10:00:00):").grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 2))
        self.range_start_time_var = tk.StringVar(value="")
        self.range_start_entry = ttk.Entry(range_frame, textvariable=self.range_start_time_var, width=30)
        self.range_start_entry.grid(row=2, column=0, columnspan=2, sticky="we", pady=(0, 6))

        ttk.Label(range_frame, text="End time:").grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 2))
        self.range_end_time_var = tk.StringVar(value="")
        self.range_end_entry = ttk.Entry(range_frame, textvariable=self.range_end_time_var, width=30)
        self.range_end_entry.grid(row=4, column=0, columnspan=2, sticky="we", pady=(0, 6))

        self.btn_explain_range = ttk.Button(range_frame, text="Explain Range", command=self.explain_time_range)
        self.btn_explain_range.grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

        range_frame.columnconfigure(0, weight=1)
        range_frame.columnconfigure(1, weight=1)

        if ExplanationPanel:
            try:
                self.range_explainer = ExplanationPanel(right_frame, height=12)
                self.range_explainer.pack(fill=tk.BOTH, expand=True)
            except Exception:
                logger.exception("Range ExplanationPanel instantiation failed; using Text fallback.")
                self.range_explainer = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, height=12)
                self.range_explainer.pack(fill=tk.BOTH, expand=True)
        else:
            self.range_explainer = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, height=12)
            self.range_explainer.pack(fill=tk.BOTH, expand=True)

        if TimelinePanel:
            try:
                self.timeline = TimelinePanel(right_frame)
                self.timeline.pack(fill=tk.BOTH, expand=False, pady=(6, 0))
            except Exception:
                logger.exception("Failed to instantiate TimelinePanel")
                self.timeline = None
        else:
            self.timeline = None

    # ---------------------------
    # Apply log type filter & auto-load Windows logs if appropriate
    # ---------------------------
    def _apply_log_type_filter(self):
        t = self.log_type_var.get() or LOG_TYPES[0]

        # If events were loaded from a user file, do not override them by auto-fetching Windows logs
        if platform.system().lower() == "windows" and read_windows_event_log and not self._loaded_from_file:
            if self._last_loaded_winlog_type != t:
                try:
                    logger.info("Loading Windows '%s' event log...", t)
                    evts = read_windows_event_log(t, max_records=500)
                    if evts:
                        self._loaded_events = evts
                        self._last_loaded_winlog_type = t
                    else:
                        logger.info("Windows '%s' log returned 0 events.", t)
                except Exception:
                    logger.exception("Failed to read Windows %s log", t)

        # For Windows logs we consider loaded_events already appropriate for the type; just set filtered list
        self._filtered_events = list(self._loaded_events)

        # Populate table & timeline
        self._populate_table_and_timeline()

    # ---------------------------
    # Populate events into primary view (now the logs table)
    # ---------------------------
    def _populate_events_into_viewer(self, events: List[str]):
        # store filtered events and repopulate the table & timeline
        self._filtered_events = events or []
        self._populate_table_and_timeline()

    # ---------------------------
    # Table & timeline population
    # ---------------------------
    def _populate_table_and_timeline(self):
        # Logs table
        if self.logs_table:
            try:
                rows = []
                for ev in self._filtered_events:
                    parts = str(ev).split("\t")
                    timestamp = parts[0] if parts else ""
                    summary = (str(ev).splitlines()[0])[:120]
                    rows.append({"timestamp": timestamp, "severity": "", "summary": summary, "raw_event": ev})
                # prefer component API
                if hasattr(self.logs_table, "load_rows"):
                    self.logs_table.load_rows(rows)
                elif hasattr(self.logs_table, "set_rows"):
                    self.logs_table.set_rows(rows)
                else:
                    # fallback Treeview has load_rows
                    try:
                        self.logs_table.load_rows(rows)
                    except Exception:
                        logger.exception("Failed to load rows into logs_table fallback")
            except Exception:
                logger.exception("Failed to populate logs_table")
        # Timeline population
        if self.timeline:
            try:
                if hasattr(self.timeline, "load_events"):
                    self.timeline.load_events(self._filtered_events)
                elif hasattr(self.timeline, "set_events"):
                    self.timeline.set_events(self._filtered_events)
                logger.info("Timeline loaded with %d events", len(self._filtered_events))
            except Exception:
                logger.exception("Failed to populate timeline")

    # ---------------------------
    # Timestamp helpers & filtering (unchanged)
    # ---------------------------
    def _try_parse_datetime(self, s: str) -> Optional[datetime]:
        if not s:
            return None
        s = s.strip()
        s = s.replace("T", " ").replace("Z", "")
        fmts = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%m/%d/%Y %I:%M:%S %p",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%d-%m-%Y %H:%M:%S",
            "%H:%M:%S",
        ]
        for fmt in fmts:
            try:
                dt = datetime.strptime(s, fmt)
                return dt
            except Exception:
                continue
        iso_re = re.search(r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}", s)
        if iso_re:
            try:
                return datetime.fromisoformat(iso_re.group(0).replace("T", " "))
            except Exception:
                pass
        return None

    def _extract_event_timestamp(self, event_text: str) -> Optional[datetime]:
        if not event_text:
            return None
        snippet = event_text[:300]
        patterns = [
            r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}",
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}",
            r"\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}(?::\d{2})?\s?(?:AM|PM|am|pm)?",
            r"\d{1,2}-\d{1,2}-\d{4} \d{2}:\d{2}:\d{2}",
            r"^\d{2}:\d{2}:\d{2}"
        ]
        for p in patterns:
            m = re.search(p, snippet)
            if m:
                dt = self._try_parse_datetime(m.group(0))
                if dt:
                    return dt
        tokens = re.split(r"\s+", snippet)
        for t in tokens:
            dt = self._try_parse_datetime(t)
            if dt:
                return dt
        return None

    def _filter_events_by_time(self, start_dt: Optional[datetime], end_dt: Optional[datetime]) -> List[str]:
        matched = []
        for ev in self._filtered_events:
            try:
                ev_dt = self._extract_event_timestamp(ev)
                if not ev_dt:
                    continue
                if start_dt and ev_dt < start_dt:
                    continue
                if end_dt and ev_dt > end_dt:
                    continue
                matched.append(ev)
            except Exception:
                continue
        return matched

    # ---------------------------
    # Selection helpers & explainers (logs_table is primary source)
    # ---------------------------
    def _get_selected_event_text(self) -> Optional[str]:
        # Try logs_table selection first
        try:
            if self.logs_table and hasattr(self.logs_table, "get_selected"):
                row = self.logs_table.get_selected()
                if row and "raw_event" in row:
                    return row.get("raw_event")
        except Exception:
            logger.exception("Error fetching selection from logs_table")

        # fallback to first filtered event
        if self._filtered_events:
            return self._filtered_events[0]
        return None

    def explain_selected_event(self):
        if not self.gemini:
            messagebox.showerror("Gemini Missing", "Gemini API key not configured.")
            return
        ev = self._get_selected_event_text()
        if not ev:
            messagebox.showwarning("No event", "No event selected.")
            return
        try:
            explanation = get_explanation(self.gemini, ev, context=None, retries=1)
            if isinstance(self.single_explainer, tk.Text):
                self.single_explainer.delete(1.0, tk.END)
                self.single_explainer.insert(tk.END, explanation)
            else:
                try:
                    self.single_explainer.set_text(explanation)
                except Exception:
                    logger.exception("Failed to set text in ExplanationPanel")
        except Exception as exc:
            logger.exception("Explain failed: %s", exc)
            messagebox.showerror("Gemini Error", str(exc))

    def explain_and_analyze_selected(self):
        ev = self._get_selected_event_text()
        if not ev:
            messagebox.showwarning("No event", "No event selected.")
            return
        try:
            analysis = analyze([ev])
        except Exception:
            logger.exception("Local analysis failed")
            analysis = "Local analysis error"
        try:
            explanation = get_explanation(self.gemini, ev, context={"analysis": analysis}, retries=1) if self.gemini else "No Gemini key"
        except Exception as exc:
            explanation = f"Failed to get explanation: {exc}"
        output = f"=== Local Analysis ===\n{analysis}\n\n=== Gemini Explanation ===\n{explanation}"
        if isinstance(self.single_explainer, tk.Text):
            self.single_explainer.delete(1.0, tk.END)
            self.single_explainer.insert(tk.END, output)
        else:
            try:
                self.single_explainer.set_text(output)
            except Exception:
                logger.exception("Failed to set text in ExplanationPanel")

    # ---------------------------
    # Time-range explanation (datetime-based)
    # ---------------------------
    def _on_preset_selected(self):
        preset = (self.range_preset_var.get() or "Custom").strip()
        if preset == "Custom":
            return
        now = datetime.now()
        if preset == "Last 5 minutes":
            start = now - timedelta(minutes=5)
            end = now
        elif preset == "Last 15 minutes":
            start = now - timedelta(minutes=15)
            end = now
        elif preset == "Last 1 hour":
            start = now - timedelta(hours=1)
            end = now
        elif preset == "Last 24 hours":
            start = now - timedelta(hours=24)
            end = now
        elif preset == "Today":
            start = datetime(now.year, now.month, now.day, 0, 0, 0)
            end = now
        else:
            return

        self.range_start_time_var.set(start.strftime("%Y-%m-%d %H:%M:%S"))
        self.range_end_time_var.set(end.strftime("%Y-%m-%d %H:%M:%S"))

    def explain_time_range(self):
        if not self.gemini:
            messagebox.showerror("Gemini Missing", "Gemini API client not initialized.")
            return

        start_input = self.range_start_time_var.get().strip()
        end_input = self.range_end_time_var.get().strip()

        start_dt = self._try_parse_datetime(start_input) if start_input else None
        end_dt = self._try_parse_datetime(end_input) if end_input else None

        if start_input and not start_dt:
            messagebox.showerror("Invalid start time", "Could not parse the Start time. Use format YYYY-MM-DD HH:MM:SS or MM/DD/YYYY H:MM AM/PM.")
            return
        if end_input and not end_dt:
            messagebox.showerror("Invalid end time", "Could not parse the End time.")
            return

        if start_dt and end_dt and start_dt > end_dt:
            messagebox.showerror("Invalid range", "Start time must be <= End time.")
            return

        selected_events = self._filter_events_by_time(start_dt, end_dt)
        if not selected_events:
            messagebox.showinfo("No events", "No events found in that time range.")
            return

        prompt_body = "\n\n".join(selected_events[:20])  # cap size
        try:
            explanation = get_explanation(self.gemini, prompt_body, context={"range_count": len(selected_events)}, retries=1)
            if isinstance(self.range_explainer, tk.Text):
                self.range_explainer.delete(1.0, tk.END)
                self.range_explainer.insert(tk.END, explanation)
            else:
                try:
                    self.range_explainer.set_text(explanation)
                except Exception:
                    logger.exception("Failed to set text in Range ExplanationPanel")
        except Exception as exc:
            logger.exception("Failed to get range explanation: %s", exc)
            messagebox.showerror("Gemini Error", f"Failed to get range explanation: {exc}")

    # ---------------------------
    # File open + load (user files)
    # ---------------------------
    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open Event Log",
            filetypes=[("Log Files", "*.evtx *.xml *.log *.txt"), ("All Files", "*.*")]
        )
        if not path:
            return
        self._loaded_from_file = True
        try:
            self._load_file(path)
        except Exception:
            logger.exception("open_file failed for %s", path)
            messagebox.showerror("Error", f"Failed to open file: {path}")

    def _load_file(self, path: str):
        try:
            raw = load_file(path)
            events = parse_log(raw)
            if events is None:
                events = []
            self._loaded_events = events
            self._loaded_from_file = True
            self._last_loaded_winlog_type = None
            # Apply current filter (dropdown) to user-loaded events
            self._apply_log_type_filter()
            logger.info("Loaded %d events from file %s", len(events), path)
            try:
                cfg = load_config() or {}
                cfg["last_opened"] = path
                save_app_settings(cfg)
            except Exception:
                logger.exception("Failed to persist last_opened to app_settings.json")
        except FileNotFoundError:
            logger.exception("File not found: %s", path)
            messagebox.showerror("File not found", f"File not found: {path}")
        except Exception as exc:
            logger.exception("Failed to load file %s: %s", path, exc)
            messagebox.showerror("Error", f"Failed to load file: {exc}")

    # ---------------------------
    # Settings & API key handling
    # ---------------------------
    def open_settings_dialog(self):
        try:
            from src.ui.settings_dialog import SettingsDialog
        except Exception as exc:
            logger.exception("Failed to import SettingsDialog: %s", exc)
            messagebox.showerror("Error", f"Cannot open settings dialog: {exc}")
            return
        dialog = SettingsDialog(self.root, on_save_callback=self._on_api_key_changed)
        dialog.grab_set()

    def _on_api_key_changed(self, new_key: str):
        if new_key:
            if not is_valid_api_key(new_key):
                messagebox.showerror("Invalid Key", "Saved key seems invalid.")
                self.gemini = None
                self._update_ui_state_on_key()
                return
            try:
                self.gemini = GeminiClient(api_key=new_key)
                logger.info("Gemini client initialized dynamically from Settings.")
                messagebox.showinfo("Gemini Ready", "Gemini API key saved. Analysis/Explanation features are now enabled.")
            except Exception as exc:
                logger.exception("Failed to initialize Gemini client with new key: %s", exc)
                messagebox.showerror("Initialization Error", f"Saved key but failed to initialize Gemini client: {exc}")
                self.gemini = None
        else:
            self.gemini = None
            messagebox.showinfo("Gemini Key Cleared", "Gemini API key removed. Analysis/Explanation will be disabled.")

        self._update_ui_state_on_key()

    # ---------------------------
    # UI state updates
    # ---------------------------
    def _update_ui_state_on_key(self):
        has_key = bool(self.gemini)
        try:
            if hasattr(self, "btn_explain_selected") and self.btn_explain_selected:
                self.btn_explain_selected.config(state="normal" if has_key else "disabled")
            if hasattr(self, "btn_explain_and_analyze") and self.btn_explain_and_analyze:
                self.btn_explain_and_analyze.config(state="normal" if has_key else "disabled")
            if hasattr(self, "btn_explain_range") and self.btn_explain_range:
                self.btn_explain_range.config(state="normal" if has_key else "disabled")
        except Exception:
            logger.exception("Failed to update button states in _update_ui_state_on_key")

    # ---------------------------
    # Debug helper
    # ---------------------------
    def _debug_show_counts(self):
        try:
            msg = (
                f"Loaded events: {len(self._loaded_events)}\n"
                f"Filtered events: {len(self._filtered_events)}\n"
                f"Loaded from file: {self._loaded_from_file}\n"
                f"Last WinLog type: {self._last_loaded_winlog_type}"
            )
            messagebox.showinfo("Debug Counts", msg)
            logger.info("Debug Counts: %s", msg)
        except Exception:
            logger.exception("Failed to show debug counts")

    # ---------------------------
    # Logs table double-click handler
    # ---------------------------
    def _on_logs_table_double_click(self, row):
        if row and "raw_event" in row:
            try:
                # Show in single explainer and auto-explain
                if isinstance(self.single_explainer, tk.Text):
                    self.single_explainer.delete(1.0, tk.END)
                    self.single_explainer.insert(tk.END, row["raw_event"])
                else:
                    try:
                        self.single_explainer.set_text(row["raw_event"])
                    except Exception:
                        logger.exception("Failed to set text in ExplanationPanel")
                if self.gemini:
                    self.explain_selected_event()
            except Exception:
                logger.exception("Failed in table double-click handler")


# ---------------------------
# Public entry point
# ---------------------------
def start_ui(gemini_client: Optional[GeminiClient] = None):
    root = tk.Tk()
    app = MainWindow(root, gemini_client=gemini_client)
    root.mainloop()


if __name__ == "__main__":
    start_ui()
