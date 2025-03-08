# Yasumi

> **⚠️ WARNING:** macOS support is **untested**! Use at your own risk 🚫  
> *(macOS users, please note that while basic functionality may work, full testing has only been performed on Windows.)*

**Yasumi** is a cross-platform automation tool designed for AFK (Away From Keyboard) tasks. It leverages image/template matching techniques along with macro recording and playback functionalities. The tool is modularly organized and currently supports the Windows environment.

## Features

- **🖼️ Image Matching:**  
  Uses several methods (e.g., PyAutoGUI, grayscale template matching, and ORB/SIFT/AKAZE algorithms) to locate images on-screen and simulate clicks.

- **🎬 Macro Recording & Playback:**  
  Record keyboard and mouse inputs and replay them automatically. Macro playback is implemented using **pydirectinput** on Windows and **pyautogui** on macOS.

- **⚙️ Configurable Settings:**  
  Easily adjust matching thresholds, scanning intervals, and stop keys via a configuration file (`.config`).

- **👤 Profile Management:**  
  Create, import, and manage multiple profiles. Each profile can have its own set of images to detect as well as dedicated macro recordings.

- **💻 Curses-based Menu:**  
  A text-based interface allows you to select matching algorithms and configure settings.

## Folder Structure

The project is organized under the **src** folder as follows:

```
Yasumi/
├── README.md
├── requirements.txt
└── src/
    ├── __init__.py            # Package initialization.
    ├── config.py              # Configuration management functions.
    ├── state.py               # Global state variables.
    ├── platform_utils.py      # Utility functions (platform-specific left click, SendInput, etc.)
    ├── matchers.py            # Image matching functions and classes.
    ├── macros.py              # Macro recording, playback, and profile management.
    ├── modes.py               # Functions for continuous and debug matching modes.
    ├── ui/
    │   ├── __init__.py
    │   └── menus.py           # Curses-based menus.
    └── yasumi.py              # Main entry point.
```

## Installation

1. **Clone the Repository** 📥

   ```bash
   git clone https://github.com/yourusername/yasumi.git
   cd yasumi
   ```

2. **Install Dependencies**

   Make sure you have Python 3 installed. Then install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

   _Note:_  
   - On Windows, you may need to install `windows-curses` for the curses module.  
   - On macOS, ensure your terminal (or packaged app) has Accessibility permissions for automation.

## Usage

1. **Run the Tool** 🚀

   From the project root, run:

   ```bash
   python -m src/yasumi.py
   ```

2. **Main Menu Options**

   - **Start with default profile:**  
     Starts the automation/matching mode using the default profile. Macro playback runs in the background if a macro is recorded.
   
   - **Edit Profile:**  
     Create new profiles, import existing profiles, or modify key macros (record, select, and clear macros).
   
   - **Settings:**  
     Adjust stop keys, matching thresholds, scanning duration, and more.
   
   - **Debug:**  
     Run the tool in debug mode for live troubleshooting.
   
   - **Exit:**  
     Quit the tool.

## Macro Recording & Playback

- **Recording:**  
  In the Edit Profile menu under “Modify Key Macro”, you can start/stop macro recording using F8 (to toggle recording on/off).

- **Playback:**  
  Macro playback runs continuously in the background when starting with the default profile.  
  On Windows, **pydirectinput** is used for playback; on macOS, **pyautogui** and a Quartz-based `left_click` helper are used.

- **Profile Selection:**  
  You can choose a specific profile to save your macro under and also clear the macro for a selected profile.

- **Stopping Macro Playback:**  
  The playback loop monitors a global flag so you can implement a stop function (for example, via additional menu options or hotkeys).

## Building an Executable

To create a standalone executable, you can use PyInstaller. For example, create a `.spec` file that includes your **src** folder and run:

```bash
pyinstaller --onefile --paths src src/yasumi.py
```

This will produce an executable in the **dist** folder.

## Contributing

Contributions and feedback are welcome! Feel free to open issues or submit pull requests to help improve the project. 💡

## License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.
