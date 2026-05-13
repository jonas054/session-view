Copilot Context Menubar (macOS)

A minimal prototype that reads ~/.copilot/context_status.json (written by copilot_context_watcher.py) and displays Copilot context token usage in the macOS menu bar.

Build & run (macOS with Swift toolchain installed):

1. Build:
   swiftc -o copilot-context-menubar main.swift -framework AppKit

2. Run:
   ./copilot-context-menubar &

Notes:
- The watcher script copilot_context_watcher.py writes ~/.copilot/context_status.json. Run that in background for live updates.
- This is a lightweight prototype. For a proper app bundle, create an Xcode project / .app and include a proper Info.plist and signing.
- The app polls the JSON file every second; replace with DispatchSource file-watching for lower-latency.
