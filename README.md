# ✨ Customize Mouse (`CustomizMousee`)

An interactive, multi-monitor Windows mouse customization utility built with Python, PyQt5, and Win32 APIs. Create beautiful neon-glow mouse trails, halos, click animations (ripples and particles), and customize them to fit your aesthetic!

---

## 🌟 Key Features

*   **🖥️ Multi-Monitor Canvas**: Seamlessly spans all active displays to draw trails without bounds.
*   **💫 Neon Glow Trails**: Fluid cursor-following trails featuring dynamic tapering, wave effects, and customizable widths.
*   **⭕ Cursor Halo**: A glowing target ring around your mouse pointer for high visibility.
*   **⚡ Click Ripples & Particles**: Visual feedback on left/right-clicks with customized colors, expanding rings, and decaying particle sparks.
*   **🖼️ Custom Textures**: Upload custom image files (PNG, JPG, BMP, etc.) to replace standard trails.
*   **🎨 Premium Control Hub**: Customize theme (Dark/Light mode), opacity, trail length, trail width, halo radius, and colors.
*   **📥 System Tray Integration**: Minimizes seamlessly to the Windows system tray (`Run in Background`). Control the overlay or restore the UI directly from the context menu.
*   **💾 Config Persistence**: Automatically saves and loads your setup to/from `%APPDATA%\CustomizeMousee\settings.json`.

---

## 🛠️ Requirements & Installation

This application is designed specifically for Windows systems due to the Win32 API extensions used for transparent window properties and cursor tracking.

### Prerequisites

*   **Python 3.8+** (Ensure it is added to your environment `PATH`)
*   **Active Internet Connection** (Only required on first run to automatically fetch Font Awesome icons)

### Setup Instructions

1.  **Clone or Download the Repository:**
    ```bash
    git clone https://github.com/lonowin/CustomizMousee.git
    cd CustomizMousee
    ```

2.  **Install the Dependencies:**
    You can install the required packages using `pip`:
    ```bash
    pip install PyQt5 pyautogui pywin32
    ```

3.  **Run the Application:**
    Start the customizer via python:
    ```bash
    python app.py
    ```

> [!NOTE]
> On the very first launch, the application will download `fa-solid-900.ttf` directly from the Font Awesome repository to the configuration folder to render icons correctly.

---

## ⚙️ Usage Guide

### Settings Panel (`CustomizerHubUI`)
- **Trail Tab**: Toggle cursor trails, choose the cursor style, pick colors, adjust opacity, trail length, width, and upload custom textures.
- **Halo Tab**: Toggle the cursor halo, choose the halo color, and adjust the radius slider.
- **General Tab**: Switch between **Dark** and **Light** themes, and toggle the `Run in Background` setting.
- **Maintenance Tab**: Manually save/load JSON configurations, or restore the default system settings.

### System Tray Behavior
When `Run in Background` is enabled, closing the settings window will not exit the app; it will remain active in the taskbar notification tray.
*   **Double-Click** the tray icon to restore the Settings Panel.
*   **Right-Click** the tray icon to:
    *   Show or Hide the UI.
    *   Quick-toggle overlay rendering.
    *   Exit the application entirely.

---

## 🏗️ Building the Executable

You can compile the Python scripts into a standalone Windows executable (`.exe`) that runs without requiring a Python installation.

### Method 1: Using `build_exe.bat`
This script upgrades `pip` and `pyinstaller` before bundling the application as a single windowed/noconsole executable:
```bash
# Double-click build_exe.bat or run:
./build_exe.bat
```

### Method 2: Using `build_executable.bat`
A quick script to build the executable directly via `pyinstaller`:
```bash
# Double-click build_executable.bat or run:
./build_executable.bat
```

Once built, you will find the standalone executable in the newly created `dist/` directory.

---

## 📂 Project Structure

```
CustomizMousee/
│
├── app.py                # Main PyQt5 application, overlays, and system tray logic
├── config.py             # Configuration loader, saver, and helper routines
├── build_exe.bat         # Automated build script (pip upgrade + pyinstaller setup)
├── build_executable.bat  # Quick build script using PyInstaller
├── README.md             # Project documentation (this file)
└── [dist/ / build/]      # Formed during PyInstaller compilations
```

---

## 🔒 Configuration File Path

User configurations are persisted as JSON files located under:
```
%APPDATA%\CustomizeMousee\settings.json
```
If you encounter configuration issues, you can delete this file to force the application to recreate it with system defaults.
