# src/api/event_analyzer.py
"""
Local event analysis engine for Win Log Interpreter (Gemini-only).

This module performs *non-AI* analysis of Windows event logs to:
- normalize event text
- detect severity levels
- identify suspicious patterns
- produce structured summaries
- prepare context for AI explanation

Public functions:
- analyze(events: list[str]) -> dict
- analyze_single(event: str) -> dict
- detect_patterns(event: str) -> dict
"""

import re
from typing import List, Dict, Any
from src.main.logger import logger


# -----------------------------------------
# Utility: classify severity based on text
# -----------------------------------------
def classify_severity(event: str) -> str:
    text = event.lower()

    if any(w in text for w in ("critical", "fatal", "panic", "crash", "bsod")):
        return "critical"

    if any(w in text for w in ("error", "failed", "failure", "denied", "timeout")):
        return "error"

    if any(w in text for w in ("warning", "slow", "degraded", "retrying")):
        return "warning"

    return "info"


# -----------------------------------------
# Utility: detect patterns or keywords
# -----------------------------------------
def detect_patterns(event: str) -> Dict[str, Any]:
    """
    Pattern detection based on keywords or regex.
    Expand this dictionary as you want to cover more event types.
    """

    patterns = {
        "authentication_issue": bool(re.search(r"(login|logon|credential|password|auth)", event, re.I)),
        "network_issue": bool(re.search(r"(timeout|connection|network|dns|tcp|port)", event, re.I)),
        "service_issue": bool(re.search(r"(service|daemon|stopped|restart|crashed)", event, re.I)),
        "filesystem_issue": bool(re.search(r"(disk|io|file|path|read|write|permission)", event, re.I)),
        "security_flag": bool(re.search(r"(virus|malware|ransom|attack|threat)", event, re.I)),
        "kernel_issue": bool(re.search(r"(kernel|driver|ntoskrnl|memory|bsod)", event, re.I)),
    }

    # Count matches
    match_count = sum(1 for v in patterns.values() if v)

    return {
        "matches": patterns,
        "match_count": match_count,
    }


# -----------------------------------------
# Analyze a single event
# -----------------------------------------
def analyze_single(event: str) -> dict:
    """
    Analyze one event text and produce a dictionary with:
    - raw text
    - severity classification
    - detected patterns
    - recommended focus areas
    """

    if not isinstance(event, str):
        event = str(event)

    severity = classify_severity(event)
    patterns = detect_patterns(event)

    # Recommended focus areas based on patterns matched
    recommended_focus = []
    if patterns["matches"]["authentication_issue"]:
        recommended_focus.append("authentication")
    if patterns["matches"]["network_issue"]:
        recommended_focus.append("network")
    if patterns["matches"]["service_issue"]:
        recommended_focus.append("services")
    if patterns["matches"]["filesystem_issue"]:
        recommended_focus.append("filesystem")
    if patterns["matches"]["security_flag"]:
        recommended_focus.append("security")
    if patterns["matches"]["kernel_issue"]:
        recommended_focus.append("kernel/drivers")

    return {
        "event": event,
        "severity": severity,
        "patterns": patterns,
        "recommended_focus": recommended_focus,
    }


# -----------------------------------------
# Analyze a list of events
# -----------------------------------------
def analyze(events: List[str]) -> dict:
    """
    High-level batch analysis.

    Returns:
        {
            "total_events": int,
            "severities": {info/error/warning/critical: count},
            "pattern_counts": {...},
            "events": [... analyzed event dicts ...]
        }
    """

    logger.info("Analyzing %d events (local analysis)", len(events))

    results = []
    severities = {"info": 0, "warning": 0, "error": 0, "critical": 0}
    pattern_counts = {
        "authentication_issue": 0,
        "network_issue": 0,
        "service_issue": 0,
        "filesystem_issue": 0,
        "security_flag": 0,
        "kernel_issue": 0,
    }

    for ev in events:
        analysis = analyze_single(ev)
        results.append(analysis)

        # Count severity
        severities[analysis["severity"]] += 1

        # Count patterns
        for pname, matched in analysis["patterns"]["matches"].items():
            if matched:
                pattern_counts[pname] += 1

    return {
        "total_events": len(events),
        "severities": severities,
        "pattern_counts": pattern_counts,
        "events": results,
    }


# -----------------------------------------
# Self-test
# -----------------------------------------
if __name__ == "__main__":
    demo_events = [
        "Service failed to start due to timeout",
        "User login failed for admin",
        "Network connection timeout on port 445",
        "System reboot completed successfully",
    ]

    summary = analyze(demo_events)
    print(summary)
