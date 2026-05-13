import Foundation
import AppKit

let STATUS_PATH = (NSHomeDirectory() as NSString).appendingPathComponent(".copilot/context_status.json")
let POLL_INTERVAL: TimeInterval = 1.0

class AppDelegate: NSObject, NSApplicationDelegate {
    var statusItem: NSStatusItem!
    var timer: Timer?
    var lastContents: String? = nil

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let button = statusItem.button {
            button.title = "Copilot: —"
        }

        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "Loading…", action: nil, keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        let quitItem = NSMenuItem(title: "Quit Copilot Context", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)
        statusItem.menu = menu

        // Polling timer. Also updates immediately.
        updateFromFile()
        timer = Timer.scheduledTimer(withTimeInterval: POLL_INTERVAL, repeats: true) { [weak self] _ in
            self?.updateFromFile()
        }
        RunLoop.current.add(timer!, forMode: .common)
    }

    @objc func quit() {
        NSApp.terminate(nil)
    }

    func updateFromFile() {
        let fm = FileManager.default
        var contents: String? = nil
        if fm.fileExists(atPath: STATUS_PATH) {
            contents = try? String(contentsOfFile: STATUS_PATH, encoding: .utf8)
        }

        // If file unchanged, skip
        if let c = contents, c == lastContents { return }
        lastContents = contents

        var menu = statusItem.menu!
        menu.removeAllItems()

        guard let c = contents, let data = c.data(using: .utf8) else {
            statusItem.button?.title = "Copilot: —"
            menu.addItem(NSMenuItem(title: "No active Copilot session", action: nil, keyEquivalent: ""))
            menu.addItem(NSMenuItem.separator())
            let quitItem = NSMenuItem(title: "Quit Copilot Context", action: #selector(quit), keyEquivalent: "q")
            quitItem.target = self
            menu.addItem(quitItem)
            return
        }

        do {
            if let json = try JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] {
                let model = json["model"] as? String ?? "unknown"
                let input = json["input_tokens"] as? Int
                let output = json["output_tokens"] as? Int
                let total = json["total_tokens"] as? Int
                let percent = json["percent_used"] as? Double
                let ts = json["timestamp"] as? String
                let updatedAt = json["updated_at"] as? Double

                var title = "Copilot"
                if let t = total {
                    let formatted: String
                    if t >= 1_000_000 {
                        formatted = String(format: "%.1fM", Double(t) / 1_000_000)
                    } else if t >= 1_000 {
                        formatted = String(format: "%.1fK", Double(t) / 1_000)
                    } else {
                        formatted = "\(t)"
                    }
                    title = "Copilot: \(formatted) tok"
                } else if let p = percent {
                    title = String(format: "Copilot: %.0f%%", p)
                }
                statusItem.button?.title = title

                menu.addItem(NSMenuItem(title: "Model: \(model)", action: nil, keyEquivalent: ""))
                if let i = input { menu.addItem(NSMenuItem(title: "Input: \(i)", action: nil, keyEquivalent: "")) }
                if let o = output { menu.addItem(NSMenuItem(title: "Output: \(o)", action: nil, keyEquivalent: "")) }
                if let tt = total { menu.addItem(NSMenuItem(title: "Total: \(tt)", action: nil, keyEquivalent: "")) }
                if let p = percent { menu.addItem(NSMenuItem(title: String(format: "%% Used: %.2f%%", p), action: nil, keyEquivalent: "")) }
                if let timestamp = ts { menu.addItem(NSMenuItem(title: "Last event: \(timestamp)", action: nil, keyEquivalent: "")) }
                if let u = updatedAt {
                    let date = Date(timeIntervalSince1970: u)
                    let fmt = DateFormatter()
                    fmt.dateStyle = .none
                    fmt.timeStyle = .medium
                    menu.addItem(NSMenuItem(title: "Updated: \(fmt.string(from: date))", action: nil, keyEquivalent: ""))
                }

                menu.addItem(NSMenuItem.separator())
                let openItem = NSMenuItem(title: "Open Copilot session folder…", action: #selector(openSessionFolder), keyEquivalent: "o")
                openItem.target = self
                menu.addItem(openItem)
                let runItem = NSMenuItem(title: "Run watcher (if missing)", action: #selector(runWatcher), keyEquivalent: "r")
                runItem.target = self
                menu.addItem(runItem)
                menu.addItem(NSMenuItem.separator())
                let quitItem = NSMenuItem(title: "Quit Copilot Context", action: #selector(quit), keyEquivalent: "q")
                quitItem.target = self
                menu.addItem(quitItem)

            } else {
                statusItem.button?.title = "Copilot: —"
                menu.addItem(NSMenuItem(title: "No readable JSON in \(STATUS_PATH)", action: nil, keyEquivalent: ""))
                menu.addItem(NSMenuItem.separator())
                let quitItem = NSMenuItem(title: "Quit Copilot Context", action: #selector(quit), keyEquivalent: "q")
                quitItem.target = self
                menu.addItem(quitItem)
            }
        } catch {
            statusItem.button?.title = "Copilot: —"
            menu.addItem(NSMenuItem(title: "Error reading status: \(error)", action: nil, keyEquivalent: ""))
            menu.addItem(NSMenuItem.separator())
            let quitItem = NSMenuItem(title: "Quit Copilot Context", action: #selector(quit), keyEquivalent: "q")
            quitItem.target = self
            menu.addItem(quitItem)
        }
    }

    @objc func openSessionFolder() {
        let path = (NSHomeDirectory() as NSString).appendingPathComponent(".copilot/session-state")
        NSWorkspace.shared.open(URL(fileURLWithPath: path))
    }

    @objc func runWatcher() {
        // Attempt to invoke bundled watcher script if present in current repo
        let repoWatcher = "\(FileManager.default.currentDirectoryPath)/copilot_context_watcher.py"
        _ = "/usr/bin/env python3"
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        task.arguments = ["python3", repoWatcher]
        do {
            try task.run()
        } catch {
            // ignore
        }
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
_ = NSApplicationMain(CommandLine.argc, CommandLine.unsafeArgv)
