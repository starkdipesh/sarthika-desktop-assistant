For One-Click Launching Right Now (From Source)

Three one-click launchers are now available in your project root:

On Linux (Ubuntu / GNOME / KDE):

Desktop App Icon (sarthika-code.desktop): To make Sarthika Code appear in your system application menu (Ubuntu Dash/Dock) with its official icon, run this one-time command:
bash
```
cp sarthika-code.desktop ~/.local/share/applications/
```
You can now search for "Sarthika Code" in your applications menu and launch or pin it to your dock with one click!
Double-Clickable Script (run.sh): A double-clickable bash script run.sh automatically finds the virtual environment and starts the GUI.

On Windows:

Double-Clickable Launcher (run.bat): Double-clicking run.bat in Windows File Explorer automatically launches the application using pythonw.exe without even showing a black command-prompt window.