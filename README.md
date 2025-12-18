# AI-Powered-Windows-Event-Log-Analyzer

Win Log Interpreter is an **AI-powered Windows Event Log analysis tool** designed for **SOC Analysts, VAPT professionals, and cybersecurity learners**.  
It combines **local forensic analysis** with **Google Gemini–based AI explanations** to help users understand security events, anomalies, and attack patterns efficiently.

This project focuses on **Windows System, Application, and Security logs** with a clean, interactive GUI built using Python and Tkinter.

---

## 🚀 Key Features

- 📂 Load Windows event logs (`.log`, `.txt`, `.xml` – EVTX exports)
- 🔍 View and filter logs by type:
  - **System**
  - **Application**
  - **Security**
- 🧠 AI-powered explanations using **Google Gemini**
- 🧩 Three-panel GUI layout:
  - Logs Viewer
  - Single Event AI Explainer
  - Time-Range AI Explainer
- ⏱️ Explain a specific event or a selected range of events
- 📊 Local (non-AI) analysis:
  - Severity estimation
  - Pattern detection
- 🔐 Secure API key entry via GUI (no hardcoded keys)
- ♻️ Auto-load last opened log after API key is saved

---

## 🎯 Target Audience

- SOC Analysts  
- Incident Responders  
- VAPT / Red Team / Blue Team Professionals  
- Cybersecurity Students & Researchers  

---

## 🗂️ Project Structure

```

win-log-interpreter/
│
├── assets/
│   ├── icons/                  # App icons (if any)
│   ├── images/                 # Screenshots / UI images
│   └── README.md               # Asset usage notes (optional)
│
├── config/
│   ├── default_settings.json   # Default config (no secrets)
│   └── app_settings.json       # User config (API key, last opened log)
│
├── docs/
│   ├── architecture.md         # Application architecture overview
│   ├── usage.md                # Detailed usage guide
│   └── screenshots.md          # UI screenshots documentation
│
├── src/
│   ├── main/
│   │   ├── config.py            # Load/save configuration
│   │   └── logger.py            # Logging setup
│   │
│   ├── api/
│   │   ├── api_client_gemini.py # Gemini API client
│   │   ├── ai_explainer.py      # AI explanation logic
│   │   └── event_analyzer.py    # Local (non-AI) log analysis
│   │
│   ├── ui/
│   │   ├── main_window.py       # Main 3-panel GUI
│   │   ├── settings_dialog.py   # API key & settings UI
│   │   └── components/
│   │       ├── event_viewer.py      # Logs viewer component
│   │       ├── explanation_panel.py # AI output panel
│   │       ├── logs_table.py         # Structured log table
│   │       └── timeline_panel.py     # Timeline visualization
│   │
│   ├── utils/
│   │   ├── parser.py            # Log parsing logic
│   │   ├── file_loader.py       # File loading helpers
│   │   ├── validators.py        # API key & input validation
│   │   └── helpers.py           # Shared utility functions
│   │
│   └── data/
│       └── schemas/             # Optional JSON schemas
│
├── tests/
│   ├── test_api_client.py       # Gemini API tests
│   ├── test_analyzer.py         # Local analyzer tests
│   └── test_parser.py           # Log parser tests
│
├── .env.example                 # Example environment variables
├── app.py                       # Application entry point
├── LICENSE                      # MIT License
├── README.md                    # Main project documentation
├── requirements.txt             # Dependencies
└── setup.py                     # Packaging & installation


````

---

## ⚙️ Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/saikirangongle/AI-Powered-Windows-Event-Log-Analyzer.git
cd AI-Powered-Windows-Event-Log-Analyzer
````

### 2️⃣ Create a Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Application

From the project root:

```bash
python app.py
```

### What happens on first run?

* The GUI starts **without requiring an API key**
* Logs are **not visible**
* AI explanation features are **disabled**

---

## 🔑 Setting Up the Gemini API Key

1. Launch the application:

   ```bash
   python app.py
   ```
2. In the GUI, go to:

   ```
   Settings → Settings
   ```
3. Paste your **Google Gemini API key**
4. Click **Save**

### After saving the API key:

* Gemini client initializes dynamically
* Logs become visible
* AI explanation features are enabled
* Last opened log file is auto-loaded (if available)

> 🔐 API keys are stored **locally only** and are never hardcoded.

---

## 📄 Loading and Analyzing Logs

### 📂 Load a Log File

```
File → Open Log File
```

Supported formats:

* `.log`
* `.txt`
* `.xml` (Windows EVTX export)

---

### 🔍 Log Type Selection

Use the dropdown to switch between:

* **System logs**
* **Application logs**
* **Security logs**

The logs viewer updates automatically based on selection.

---

## 🧠 AI-Based Log Analysis

### 🔹 Single Log Explanation

1. Select a log entry from the Logs Viewer
2. Click:

   ```
   Explain Selected
   ```
3. Gemini provides:

   * Event explanation
   * Possible cause
   * Security relevance
   * Recommended actions

---

### 🔹 Time-Range Log Explanation

1. Enter a start and end index (or range)
2. Click:

   ```
   Explain Range
   ```
3. Gemini analyzes correlated events and provides:

   * Timeline-based insights
   * Attack or anomaly patterns
   * Summary of system behavior

---

## 📊 Local Analysis (Without AI)

Local analysis runs without Gemini and includes:

* Event count
* Severity grouping
* Pattern detection (authentication, service failures, system errors)

This is useful when API access is unavailable.

---

## 🔐 Important Note About **Security Logs**

⚠️ **Windows Security Logs require Administrator privileges**

To load **Security logs** successfully:

### ✅ You MUST run the application as Administrator

1. Open **Command Prompt / PowerShell as Administrator**
2. Activate your virtual environment
3. Run:

   ```bash
   python app.py
   ```

Without admin privileges:

* Security logs may not load
* Access may be denied by Windows

This is a **Windows OS restriction**, not an application issue.

---

## 🔒 Security & Privacy

* API keys are stored locally in configuration files
* No logs are sent to Gemini unless the user explicitly requests AI explanation
* Designed for **offline analysis with optional AI enrichment**

---

## 📌 Use Cases

* SOC alert investigation
* Incident response & root cause analysis
* VAPT log review and attack simulation validation
* Learning Windows event log internals
* Cybersecurity portfolio demonstration

---

<!-- ## 🔮 Future Enhancements (Roadmap)

> **Recommended placement:**
> Keep Future Updates **near the end of README** (as done here).
> Recruiters like to see vision *after* understanding current capabilities.
-->
Planned improvements:

* ⏱️ Timestamp-based time range selection (date & time picker)
* 🔍 Advanced log search and keyword filtering
* 📈 Event correlation and attack chain visualization
* 📤 Export reports (PDF / HTML)
* 🧠 Improved AI prompt engineering for threat intelligence
* 🖥️ Windows executable build (EXE)
* 🛡️ MITRE ATT&CK mapping for security events

---

## 📜 License

This project is licensed under the **MIT License**.

---

## ⚠️ Disclaimer

This tool is intended for **educational, research, and defensive security purposes only**.
Do not use it for unauthorized monitoring or malicious activities.

---

## 👤 Author

Developed by **Saikiran G**
GitHub: (https://github.com/saikirangongle)
<!--
```

---

## ✅ Where to mention **Future Updates** (Best Practice)

✔ **Best location:** Near the **end of README**  
✔ Why:
- Recruiters first see what you’ve built
- Then they see your **vision and roadmap**
- Shows long-term thinking and ownership

You did this **correctly** by asking 👍

---

## 🔥 If you want next
I can:
- Optimize README for **ATS & recruiters**
- Add **badges** (Python, License, Status)
- Write a **SECURITY.md**
- Create a **professional GitHub release**
- Review your actual uploaded repo for improvements

Just tell me what’s next 🚀
```
-->
