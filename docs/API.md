# Win Log Interpreter — Internal API Documentation
(Gemini-Only Edition)

This document describes the internal Python APIs used within the Win Log Interpreter application.

It does **not** describe the Gemini external API — only how our app interacts with it.

---

# 1. Module: `src/api/api_client_gemini.py`

## Class: `GeminiClient`

### **Constructor**
```python
GeminiClient(api_key: str = None, base_url: str = None, timeout: int = 25)
Parameters
Parameter	Type	Description
api_key	str	Gemini API key (required)
base_url	str	Base API URL (default from constants)
timeout	int	Request timeout in seconds

Methods
chat(prompt: str) -> dict
Sends a text prompt to Gemini and returns the raw JSON response.

Input:

python
Copy code
response = client.chat("Explain this event...")
Raises:

GeminiAPIError

ValueError

requests exceptions

2. Module: src/api/event_analyzer.py
Provides local analysis before sending data to Gemini.

Function: analyze(events: list[str]) -> dict
Analyzes a list of events.

Returns structure:

python
Copy code
{
  "total_events": int,
  "severities": {"info": 0, "warning": 0, "error": 0, "critical": 0},
  "pattern_counts": {...},
  "events": [ ... detailed analysis ... ]
}
Function: analyze_single(event: str) -> dict
Returns:

severity

detected patterns

recommended focus areas

3. Module: src/api/ai_explainer.py
Used to interact with Gemini for explanations.

Function: build_explain_prompt(event, context=None)
Constructs a detailed structured prompt for Gemini.

Function: parse_gemini_response(resp)
Extracts plain text from different possible response formats.

Function: get_explanation(gemini_client, event, context=None, retries=1)
High-level helper that:

Builds a prompt

Calls Gemini

Parses and cleans the output

Returns:

python
Copy code
"Final explanation text..."
4. Module: src/utils/parser.py
Handles log parsing.

Function: parse_log(raw)
Returns list of event strings.

Handles:

XML-like exports

Timestamp grouping

Multiline blocks

Blank-line separation

Function: summarize_event(event_text, max_len=200)
Short one-line preview used for UI table summaries.

5. Module: src/utils/validators.py
Validation helpers.

Functions
python
Copy code
is_valid_api_key(key)
is_valid_event(event)
is_valid_event_list(events)
is_valid_path(path)
non_empty_string(value)
6. Module: src/utils/helpers.py
General-purpose helpers.

Highlights
python
Copy code
ensure_dir(path)
now_iso()
safe_write_json(path, obj)
chunk_text(text, size)
truncate(text, max_len)
ensure_list(obj)
7. UI API (Tkinter Components)
Component: MainWindow
Located in: src/ui/main_window.py

Methods:
open_file()

analyze_events()

explain_selected_event()

_get_events_from_ui()

show_api_info()

8. Component: EventViewer
File: src/ui/components/event_viewer.py

Methods:

python
Copy code
load_events(events)
get_selected_event()
clear()
9. Component: ExplanationPanel
File: src/ui/components/explanation_panel.py

Methods:

set_text(text)

append_text(text)

clear()

get_text()

copy_to_clipboard()

save_to_file()

find_next()

10. Component: TimelinePanel
File: src/ui/components/timeline_panel.py

Methods:

load_events(events)

set_on_select(callback)

clear()

11. Component: LogsTable
File: src/ui/components/logs_table.py

Methods:

add_row(timestamp, severity, summary, raw_event)

load_rows(rows)

get_selected()

on_double_click(callback)

_sort_by(column)

12. Settings API
File: src/ui/settings_dialog.py

Methods:

save_key()

_mask_key()

open_settings()

13. Configuration API
File: src/main/config.py

Functions:
python
Copy code
load_config() -> dict
save_app_settings(settings) -> bool
Reads:

default_settings.json

app_settings.json

environment variables

14. Application Entry
File: src/main/app.py

Core Flow:
Load config

Setup logging

Initialize Gemini client

Start GUI or headless mode

CLI Arguments:

css
Copy code
--headless
--input <path>
--debug
15. Logger API
File: src/main/logger.py

Functions:

setup_logging(debug=False)

Logger instance: logger