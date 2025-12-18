# Win Log Interpreter — Installation Guide
(Gemini-Only Edition)

This guide explains how to install and run the Win Log Interpreter from source.

---

## 1. Requirements

**Operating System**
- Windows 10/11 (recommended)
- macOS or Linux also supported

**Software**
- Python **3.10 or newer**
- pip (Python package installer)
- Internet connection (for Gemini API requests)

---

## 2. Clone or Download the Project

```bash
git clone https://github.com/your-repo/win-log-interpreter.git
cd win-log-interpreter
If you downloaded a ZIP, extract it and open a terminal inside the folder.

3. Create a Virtual Environment (Recommended)
bash
Copy code
python -m venv venv
Activate it:

Windows

bash
Copy code
venv\Scripts\activate
macOS/Linux

bash
Copy code
source venv/bin/activate
4. Install Dependencies
bash
Copy code
pip install -r requirements.txt
This installs:

Tkinter UI dependencies

Requests for HTTP calls

Utility libraries

5. Configure Your Gemini API Key
Your API key can be set in one of two ways:

Option A — Environment Variable
arduino
Copy code
set GEMINI_API_KEY=YOUR_KEY_HERE    (Windows)
export GEMINI_API_KEY=YOUR_KEY_HERE (Mac/Linux)
Option B — app_settings.json
Edit:

arduino
Copy code
config/app_settings.json
Example:

json
Copy code
{
    "GEMINI_API_KEY": "YOUR_KEY_HERE",
    "theme": "light"
}
6. Run the Application
bash
Copy code
python src/main/app.py
GUI will launch automatically.

To run without GUI:

bash
Copy code
python src/main/app.py --headless
7. Optional Arguments
Option	Description
--headless	Run without UI (CLI mode)
--input path	Path to event log file
--debug	Enable verbose logging

8. Common Issues
❗ Missing GEMINI_API_KEY
Set the key in environment or config/app_settings.json.

❗ SSL / Connection Errors
Ensure your system date/time is correct and internet connection is stable.

❗ Tkinter Missing
On Linux, install:

bash
Copy code
sudo apt install python3-tk
9. Uninstallation
Just delete the folder and (optionally) your virtual environment.

10. Need Help?
Contact support or open an issue in your repository.

You’re now ready to analyze Windows event logs using Gemini AI!