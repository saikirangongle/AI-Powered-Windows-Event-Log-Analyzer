# Win Log Interpreter — Usage Guide
(Gemini-Only Edition)

This document explains how to use the Win Log Interpreter after installation.

---

## Start the App

**GUI mode (default)**

```bash
python src/main/app.py
The Tkinter GUI will open. Use the File → Open Log File menu to load a log, or paste events into the left panel.

Headless / CLI mode

bash
Copy code
python src/main/app.py --headless --input path/to/logfile.log
Add --debug to enable verbose logging.

Basic Workflow
Configure Gemini API

Either set the GEMINI_API_KEY environment variable or open Settings in the app and paste the key.

The app will use this key to call the Gemini API for explanations.

Open / Load Logs

File → Open Log File, or paste raw log text into the left pane.

Supported input types: .evtx exports (XML), .log, .txt. The parser will attempt a best-effort parse.

Local Analysis

Click Analyze to run local heuristics:

Severity counts

Pattern detection (auth, network, service, filesystem, kernel, security)

Summary appears in the right-side panel.

Request AI Explanation

Select a single event in the event list (highlight it).

Click Explain Selected to send a prompt to Gemini.

The AI explanation will appear in the explanation panel.

Use Copy / Save buttons to export the explanation.

Timeline & Table Views

(If enabled) Use the timeline component to visualize events chronologically.

Use the logs table for a structured view and double-click to inspect the raw event.

UI Controls
File → Open Log File — open a file and populate the event list.

Analyze — run offline analysis on events currently loaded.

Explain Selected — request Gemini explanation for the highlighted event.

Settings → Gemini API Info — view the masked API key and open settings dialog.

Theme (if enabled) — toggle light/dark theme (persisted in app settings).

Command-Line Options
css
Copy code
--headless        Run without GUI (CLI workflow)
--input <path>    Path to an event log to analyze (headless)
--debug           Enable debug-level logging
Output & Saving
Explanations can be saved from the explanation panel (Save button).

Use the Save... button to export explanation text as .txt.

Logs table and timeline are UI-only; export via copy/paste or by saving explanations.

Troubleshooting
No GEMINI_API_KEY error — Set the environment variable or open Settings and add it to config/app_settings.json.

Gemini network errors / timeouts — Check connectivity, API key validity, and configured base URL in src/api/api_client_gemini.py.

Parser didn’t split events — If your log is binary EVTX, export it to XML (e.g., wevtutil) or use a dedicated EVTX parser before using this tool.

Tips
For noisy logs, analyze a smaller timeframe or filter events before sending to Gemini to save quota and get focused explanations.

Use local analysis first to triage high-severity events, then ask Gemini for explanations on the top candidates.

Keep the API key private — do not commit it to git.