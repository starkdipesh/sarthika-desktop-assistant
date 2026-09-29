# Sarthika Code — Privacy Policy & Guarantee

Sarthika Code is built on an uncompromising **local-first, zero-telemetry architecture**. Your source code, conversations, model configurations, and developer metadata never leave your computer.

---

## 1. Core Privacy Commitments

1. **No Cloud Inference**: All AI token generation is performed entirely by a local executable (`llama-server`) running on your local machine (`127.0.0.1`).
2. **Zero Telemetry or Analytics**: The application contains no tracking libraries, no usage beacons, no user identifiers, no Google Analytics, no PostHog, and no telemetry pings.
3. **No User Accounts**: There are no logins, passwords, cloud profiles, subscriptions, or credit card requirements.
4. **No External Network Calls**: Sarthika Code makes zero outbound requests to the internet. Network I/O is strictly restricted to local loopback communication (`http://127.0.0.1:<port>`) with the user's local inference engine.
5. **No Hidden Advertising**: Sarthika Code will never display third-party advertisements or sponsored recommendations.

---

## 2. Source Code & Context Protection

* **Explicit File Selection Only**: Sarthika Code will never silently scan, index, or parse your filesystem or repositories. Files are only loaded into memory when you explicitly select them via the file selection dialog.
* **Sensitive File Denylist**: The system automatically screens selected files and blocks sensitive assets (such as `.env`, cryptographic keys, `id_rsa`, `node_modules`, and binary databases) from being read into prompts.
* **No File Write Operations**: Sarthika Code never modifies or writes files back to your local filesystem. Generated code remains in the chat window until you choose to copy and paste it into your editor.

---

## 3. Data Storage & Local Retention

* **Database Storage**: All conversations, settings, and message histories are persisted locally in an unencrypted SQLite database located in your standard operating system application data directory:
  * **Windows**: `%LOCALAPPDATA%\sarthika_code\data\sarthika.db`
  * **Linux**: `~/.local/share/sarthika_code/data/sarthika.db`
* **Local Logging**: Diagnostic logs are written to the local log directory:
  * **Windows**: `%LOCALAPPDATA%\sarthika_code\logs\sarthika.log`
  * **Linux**: `~/.local/state/sarthika_code/logs/sarthika.log`
  * Log files redact user home directory paths and will never record prompt code contents or sensitive tokens.
* **Complete User Control**: You can delete individual chats, clear your entire conversation history, or remove all application data at any time directly through the application settings or by deleting the local database file.

---

## 4. Chat Export Privacy

When exporting conversations to Markdown or JSON:
* The application provides an option to strip or sanitize absolute filesystem paths.
* Exports are saved exclusively to the local directory chosen by the user in the system file dialog.
