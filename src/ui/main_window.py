# src/ui/main_window.py
"""
Main UI Window for Win Log Interpreter (Gemini-only)

Left column displays only the Log Table. Right column time-range controls
use a date picker + time spinboxes (when tkcalendar is available) or fallback
to text entries if not installed.

Features:
- DateEntry (calendar popup) + Spinboxes for time (HH:MM:SS)
- Presets populate both date and time controls
- Backwards-compatible fallback if tkcalendar is missing
- Load-count dropdown to control how many events to fetch/display
"""

import os
import platform
import re
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Optional, List, Tuple

from src.main.logger import logger
from src.main.config import load_config, save_app_settings
from src.api.api_client_gemini import GeminiClient
from src.api.event_analyzer import analyze
from src.api.ai_explainer import get_explanation
from src.utils.file_loader import load_file
from src.utils.parser import parse_log
from src.utils.validators import is_valid_api_key

# Attempt to import tkcalendar DateEntry for date picker
try:
    from tkcalendar import DateEntry
except Exception:
    DateEntry = None

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
        try:
            idx = int(sel[0])
        except Exception:
            return None
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

        # Maximum events to load/display (default 100). None means "All".
        self._max_events: Optional[int] = 100

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
            maxrec = self._max_events or 1000
            events = read_windows_event_log("System", max_records=maxrec)
            if events:
                # If the reader returned more than desired and _max_events is set, slice
                if self._max_events:
                    events = events[: self._max_events]
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
    # UI layout: three columns (left: Log Table only)
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

        # Load count dropdown (how many events to fetch/display)
        ttk.Label(ctrl_frame, text="Load:").pack(side=tk.LEFT, padx=(8, 6))
        self.load_count_var = tk.StringVar(value=(str(self._max_events) if self._max_events else "All"))
        load_options = ["50", "100", "200", "500", "All"]
        self.load_count_cb = ttk.Combobox(ctrl_frame, textvariable=self.load_count_var,
                                          values=load_options, state="readonly", width=8)
        self.load_count_cb.pack(side=tk.LEFT)
        self.load_count_cb.bind("<<ComboboxSelected>>", lambda e: self._on_max_events_changed())

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

        # Start: Date picker + time spinboxes (or fallback to single Entry)
        ttk.Label(range_frame, text="Start time (date + time):").grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 2))

        # Container for start controls
        self.start_ctrl = ttk.Frame(range_frame)
        self.start_ctrl.grid(row=2, column=0, columnspan=2, sticky="we", pady=(0, 6))

        # If DateEntry available use it
        if DateEntry:
            self.start_date = DateEntry(self.start_ctrl, width=12, date_pattern="yyyy-mm-dd")
            self.start_date.pack(side=tk.LEFT, padx=(0, 6))
        else:
            self.start_date_text = ttk.Entry(self.start_ctrl, width=14)
            self.start_date_text.pack(side=tk.LEFT, padx=(0, 6))

        # Time spinboxes for hour:minute:second (24-hour format)
        self.start_hour = tk.Spinbox(self.start_ctrl, from_=0, to=23, width=3, format="%02.0f")
        self.start_hour.pack(side=tk.LEFT)
        ttk.Label(self.start_ctrl, text=":").pack(side=tk.LEFT)
        self.start_min = tk.Spinbox(self.start_ctrl, from_=0, to=59, width=3, format="%02.0f")
        self.start_min.pack(side=tk.LEFT)
        ttk.Label(self.start_ctrl, text=":").pack(side=tk.LEFT)
        self.start_sec = tk.Spinbox(self.start_ctrl, from_=0, to=59, width=3, format="%02.0f")
        self.start_sec.pack(side=tk.LEFT, padx=(0, 6))
        # removed AM/PM control (24-hour mode)


        # End: Date picker + time spinboxes (or fallback)
        ttk.Label(range_frame, text="End time (date + time):").grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 2))

        self.end_ctrl = ttk.Frame(range_frame)
        self.end_ctrl.grid(row=4, column=0, columnspan=2, sticky="we", pady=(0, 6))

        if DateEntry:
            self.end_date = DateEntry(self.end_ctrl, width=12, date_pattern="yyyy-mm-dd")
            self.end_date.pack(side=tk.LEFT, padx=(0, 6))
        else:
            self.end_date_text = ttk.Entry(self.end_ctrl, width=14)
            self.end_date_text.pack(side=tk.LEFT, padx=(0, 6))

        self.end_hour = tk.Spinbox(self.end_ctrl, from_=0, to=23, width=3, format="%02.0f")
        self.end_hour.pack(side=tk.LEFT)
        ttk.Label(self.end_ctrl, text=":").pack(side=tk.LEFT)
        self.end_min = tk.Spinbox(self.end_ctrl, from_=0, to=59, width=3, format="%02.0f")
        self.end_min.pack(side=tk.LEFT)
        ttk.Label(self.end_ctrl, text=":").pack(side=tk.LEFT)
        self.end_sec = tk.Spinbox(self.end_ctrl, from_=0, to=59, width=3, format="%02.0f")
        self.end_sec.pack(side=tk.LEFT, padx=(0, 6))
        # removed AM/PM control (24-hour mode)


        # Explain button below entries (always visible)
        self.btn_explain_range = ttk.Button(range_frame, text="Explain Range", command=self.explain_time_range)
        self.btn_explain_range.grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

        range_frame.columnconfigure(0, weight=1)
        range_frame.columnconfigure(1, weight=1)

        # Range explanation panel
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

        # Timeline (optional)
        if TimelinePanel:
            try:
                self.timeline = TimelinePanel(right_frame)
                self.timeline.pack(fill=tk.BOTH, expand=False, pady=(6, 0))
            except Exception:
                logger.exception("Failed to instantiate TimelinePanel")
                self.timeline = None
        else:
            self.timeline = None

        # Initialize time widgets to reasonable defaults (now / now - 15m)
        self._set_default_time_widgets()

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
                    maxrec = self._max_events or 1000
                    evts = read_windows_event_log(t, max_records=maxrec)
                    if evts:
                        if self._max_events:
                            evts = evts[: self._max_events]
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
    # Populate events into primary view (logs table)
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
    # Timestamp helpers & filtering
    # ---------------------------
    def _try_parse_datetime(self, s: str) -> Optional[datetime]:
        """Try several common datetime formats and return a datetime (naive)."""
        if not s:
            return None
        s = s.strip()
        # normalize basic ISO Z and remove stray dots
        s = s.replace("T", " ").replace("Z", "").replace(".", "")
        fmts = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%m/%d/%Y %I:%M:%S %p",
            "%m/%d/%Y %I:%M %p",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%d-%m-%Y %H:%M:%S",
            "%d/%m/%Y %I:%M:%S %p",
            "%d/%m/%Y %I:%M %p",
            "%H:%M:%S",
            "%I:%M:%S %p",
            "%I:%M %p",
            # Month name formats (English): "Wed Dec 10 16:36:41 2025"
            "%a %b %d %H:%M:%S %Y",
            "%b %d %H:%M:%S %Y",
            "%a %b %d %H:%M:%S",   # without year
            "%b %d %H:%M:%S",      # without year
            "%d %b %Y %H:%M:%S",
            "%d %b %H:%M:%S",
        ]
        for fmt in fmts:
            try:
                dt = datetime.strptime(s, fmt)
                return dt
            except Exception:
                continue
        # try to extract iso-like substring
        iso_re = re.search(r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}", s)
        if iso_re:
            try:
                return datetime.fromisoformat(iso_re.group(0).replace("T", " "))
            except Exception:
                pass
        return None


    def _extract_event_timestamp(self, event_text: str) -> Optional[datetime]:
        """Attempt to extract a datetime from an event text snippet."""
        if not event_text:
            return None
        snippet = event_text[:400]  # scan a bit further for verbose lines
        # Add regex patterns that include month names / weekday names
        patterns = [
            r"\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}",
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}",
            r"\d{1,2}/\d{1,2}/\d{4} \d{1,2}:\d{2}(?::\d{2})?\s?(?:AM|PM|am|pm)?",
            r"\d{1,2}-\d{1,2}-\d{4} \d{2}:\d{2}:\d{2}",
            r"^\d{2}:\d{2}:\d{2}",
            # weekday + month name e.g. "Wed Dec 10 16:36:41 2025"
            r"[A-Za-z]{3}\s+[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\d{4}",
            # month name e.g. "Dec 10 16:36:41 2025" or "Dec 10 16:36:41"
            r"[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}(?:\s+\d{4})?",
            # day month year format e.g. "10 Dec 2025 16:36:41"
            r"\d{1,2}\s+[A-Za-z]{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2}",
        ]
        for p in patterns:
            m = re.search(p, snippet)
            if m:
                candidate = m.group(0)
                dt = self._try_parse_datetime(candidate)
                if dt:
                    return dt
        # last-resort token scan
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
    # Selection helpers & explainers (logs_table is primary)
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
    # Time-range controls helpers
    # ---------------------------
    def _set_default_time_widgets(self):
        """Set start = now - 15 minutes, end = now"""
        now = datetime.now()
        start = now - timedelta(minutes=15)
        self._set_time_widgets(start, now)

    def _set_time_widgets(self, start_dt: datetime, end_dt: datetime):
        """Populate date/time widgets or fallback entries with given datetimes (24-hour)."""
        # Start
        try:
            date_str = start_dt.strftime("%Y-%m-%d")
            h = start_dt.strftime("%H")  # 00-23
            m = start_dt.strftime("%M")
            s = start_dt.strftime("%S")
            if DateEntry and hasattr(self, "start_date"):
                self.start_date.set_date(start_dt.date())
            elif hasattr(self, "start_date_text"):
                self.start_date_text.delete(0, tk.END)
                self.start_date_text.insert(0, date_str)
            self.start_hour.delete(0, tk.END)
            self.start_hour.insert(0, h)
            self.start_min.delete(0, tk.END)
            self.start_min.insert(0, m)
            self.start_sec.delete(0, tk.END)
            self.start_sec.insert(0, s)
        except Exception:
            logger.exception("Failed to set start time widgets")

        # End
        try:
            date_str = end_dt.strftime("%Y-%m-%d")
            h = end_dt.strftime("%H")
            m = end_dt.strftime("%M")
            s = end_dt.strftime("%S")
            if DateEntry and hasattr(self, "end_date"):
                self.end_date.set_date(end_dt.date())
            elif hasattr(self, "end_date_text"):
                self.end_date_text.delete(0, tk.END)
                self.end_date_text.insert(0, date_str)
            self.end_hour.delete(0, tk.END)
            self.end_hour.insert(0, h)
            self.end_min.delete(0, tk.END)
            self.end_min.insert(0, m)
            self.end_sec.delete(0, tk.END)
            self.end_sec.insert(0, s)
        except Exception:
            logger.exception("Failed to set end time widgets")

    def _read_time_widgets(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Read values from date + time widgets and return (start_dt, end_dt) or (None, None) on parse failure."""
        # Build start string (24-hour)
        try:
            if DateEntry and hasattr(self, "start_date"):
                date_val = self.start_date.get_date().strftime("%Y-%m-%d")
            elif hasattr(self, "start_date_text"):
                date_val = self.start_date_text.get().strip()
            else:
                date_val = ""
            h = self.start_hour.get().strip() or "00"
            mi = self.start_min.get().strip() or "00"
            s = self.start_sec.get().strip() or "00"
            start_str = f"{date_val} {h}:{mi}:{s}"
            start_dt = self._try_parse_datetime(start_str)
        except Exception:
            start_dt = None

        # Build end string (24-hour)
        try:
            if DateEntry and hasattr(self, "end_date"):
                date_val = self.end_date.get_date().strftime("%Y-%m-%d")
            elif hasattr(self, "end_date_text"):
                date_val = self.end_date_text.get().strip()
            else:
                date_val = ""
            h = self.end_hour.get().strip() or "23"
            mi = self.end_min.get().strip() or "59"
            s = self.end_sec.get().strip() or "59"
            end_str = f"{date_val} {h}:{mi}:{s}"
            end_dt = self._try_parse_datetime(end_str)
        except Exception:
            end_dt = None

        return start_dt, end_dt

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

        self._set_time_widgets(start, end)

    def explain_time_range(self):
        if not self.gemini:
            messagebox.showerror("Gemini Missing", "Gemini API client not initialized.")
            return

        start_dt, end_dt = self._read_time_widgets()

        if start_dt is None and (hasattr(self, "start_date_text") or DateEntry):
            messagebox.showerror("Invalid start time", "Could not parse the Start time. Use the date picker + time fields.")
            return
        if end_dt is None and (hasattr(self, "end_date_text") or DateEntry):
            messagebox.showerror("Invalid end time", "Could not parse the End time. Use the date picker + time fields.")
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
            # Limit to configured max (unless All)
            if self._max_events:
                events = events[: self._max_events]
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
    # New: handle changes to Load dropdown
    # ---------------------------
    def _on_max_events_changed(self):
        """Callback when user changes the 'Load' dropdown."""
        v = (self.load_count_var.get() or "").strip()
        if not v or v.lower() == "all":
            self._max_events = None
        else:
            try:
                self._max_events = int(v)
            except Exception:
                self._max_events = 100

        logger.info("Max events changed to: %s", self._max_events or "All")

        # If we loaded from a file previously, re-slice the in-memory events
        try:
            if self._loaded_from_file and self._loaded_events:
                if self._max_events:
                    self._loaded_events = self._loaded_events[: self._max_events]
            # For Windows logs, re-fetch happens inside _apply_log_type_filter
        except Exception:
            logger.exception("Error while applying new max events")

        # Re-apply filter so UI updates (and triggers re-fetch if needed)
        self._apply_log_type_filter()


# ---------------------------
# Public entry point
# ---------------------------
def start_ui(gemini_client: Optional[GeminiClient] = None):
    root = tk.Tk()
    app = MainWindow(root, gemini_client=gemini_client)
    root.mainloop()


if __name__ == "__main__":
    start_ui()
