# Changelog
Win Log Interpreter (Gemini-Only Edition)

All notable changes to this project will be documented in this file.

---

## [0.1.0] — Initial Release
**Date:** 2025-01-01  
**Status:** Development Build

### Added
- Complete project structure (modular, production-ready).
- Gemini-only API support via `GeminiClient`.
- Local event analyzer:
  - Severity detection
  - Pattern matching
  - Focus recommendations
- Log parser:
  - XML-like event extraction
  - Timestamp-based grouping
  - Blank-line grouping
  - Summarization utility
- Tkinter GUI:
  - Main window
  - Event viewer
  - Explanation panel
  - Timeline view
  - Logs table view
- Settings dialog for Gemini API key.
- Theme framework (light / dark).
- Utility modules:
  - validators
  - helpers
  - file loader
- Docs:
  - INSTALL
  - USAGE
  - API

### Changed
- Consolidated all AI usage to Gemini model only.
- Removed all references to OpenAI and other providers.

### Fixed
- Robust parser fallback for mixed-format logs.
- Improved JSON save/load reliability through atomic writes.

### Known Issues / TODO
- EVTX binary parsing is not yet supported (requires external library).
- Export functions for timeline/table not implemented.
- GUI does not yet display analyzer results in structured table format.

---

## [Unreleased]
### Planned Features
- Batch processing mode (explain all events).
- Export to PDF/HTML report.
- More advanced timestamp normalization.
- User-configurable analyzer rules.

---

