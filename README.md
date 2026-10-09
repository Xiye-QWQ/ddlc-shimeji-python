# DDLC Desktop Mascots

A Python/PySide6 desktop mascot engine featuring Monika, Yuri, Natsuki, and
Sayori. Run several independent mascots together, drag and throw them, and let
them animate and choose actions. This is a fresh implementation with no Java
or JAR dependency.

## Download and run on Windows

**[Download DDLCMascot.zip](https://github.com/flysandwichNOTFOUND/ddlc-shimeji-python/releases/latest/download/DDLCMascot.zip)**
or browse the [release notes](https://github.com/flysandwichNOTFOUND/ddlc-shimeji-python/releases).

1. Extract the ZIP to a writable location such as Documents.
2. Open the extracted `DDLCMascot` folder and run `DDLCMascot.exe`.
3. Choose a character and settings, then press **Start**.
4. Right-click a mascot and choose **Spawn another mascot**, or use the system
   tray's **Spawn mascot** menu to run additional characters at the same time.

Python and the original source files are not required for the Windows download.
Keep the executable and its `_internal` folder together:

```text
DDLCMascot/
├── DDLCMascot.exe
└── _internal/
    ├── characters/
    ├── config/settings.json
    └── supporting libraries...
```

Run the application after extracting it, rather than from inside the ZIP.
The portable build saves choices in `_internal/config/settings.json`; keep this
folder writable and back up that file before replacing the folder with an update.
Right-click **Quit** or press **Esc** while a mascot has focus to exit all mascots.

## Run from Python source

Requires Python 3.10 or newer. Run these commands from the repository folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

The compact startup menu selects a character and session options. Press Start
to launch or Quit to exit. Monika, Yuri, Natsuki, and Sayori share one engine;
each character's JSON maps the supplied artwork to animation states. Runtime
artwork lives in `characters/<name>/sprites`; the app does not need a `temp pics`
folder.

Use `main.py --character yuri` to preselect a character in the menu.
Launcher choices are saved to `config/settings.json` when Start is pressed and
reloaded next launch. The JSON is editable; character JSON files are unchanged.

Random action speed changes timed behavior durations, while animation speed
changes frame playback separately. Physics feel offers Light, Normal, and
Heavy; Normal retains the current weighted tuning. Disabling throwing preserves
dragging and gravity. Disabling autonomous behavior leaves the mascot idle
after landing and disables the starting-behavior selector. Airborne starts
fall before beginning the selected action.

Hold the left mouse button over the sprite and drag. Mascots use each monitor's
usable desktop area, excluding its taskbar. Click the mascot and
press Escape to quit, or right-click and choose Quit. With throwing enabled,
recent mouse motion transfers momentum on release, which settles under gravity
and friction. Frame dimensions set a stable transparent canvas for each character.

## Multiple mascots and tray controls

Right-click a mascot to change its character, force an action, toggle autonomous
behavior, spawn another instance, or remove only that mascot. Forced actions are
available on the floor and can run once even with autonomous behavior disabled.
Each instance owns its physics, playback, action timing, and cooldowns.

The Windows system tray offers Settings, Spawn mascot, Hide/Show mascots, and
Quit. Hidden mascots pause until shown again. Settings updates saved defaults
for new instances; existing mascots keep their options. A mascot's Spawn another
command copies its options and chooses a random initial position.

Removing the last mascot leaves the tray available for respawning. Quit or Esc
exits the entire application. If a system tray is unavailable, removing the last
mascot exits. Startup with Windows is not enabled.

## Build the Windows executable

After installing the source requirements, install PyInstaller and use the
included build specification on Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean DDLCMascot.spec
```

The result is `dist/DDLCMascot/DDLCMascot.exe`. The specification includes all
four characters, their configuration files, and the default settings. Zip the
complete output folder to share it:

```powershell
Compress-Archive -Path .\dist\DDLCMascot -DestinationPath .\dist\DDLCMascot.zip -Force
```

The distributed build uses PyInstaller 6.22.3 and Python 3.12. Build output and
ZIPs are excluded from Git; downloadable bundles are attached to GitHub Releases.
Rebuild after changing source files to include those changes in the executable.
Keep the one-folder build for now: the current settings location would be
temporary in a `--onefile` build.

## Structure

- `ui/launcher.py`: user-facing startup menu.
- `ui/context_menu.py`, `ui/tray.py`: instance and application controls.
- `config/settings.py`: session settings and mappings to engine values.
- `core/application.py`: mascot ownership, spawning/removal, and saved defaults.
- `core/mascot.py`: window, mouse input, and component coordination.
- `core/animation.py`: ordered PNG playback with elapsed time.
- `core/physics.py`: gravity, throws, drag/friction, and collision resolution.
- `core/screen.py`: usable desktop geometry and initial positions.
- `platforms/`: Windows window detection and experimental support surfaces.
- `DDLCMascot.spec`: reproducible PyInstaller entry point and asset mappings.
- `behaviors/`: shared idle, walk, sit, sleep, crawl, hop, look-around,
  drag, fall, and recovery transitions.
- `characters/`: per-character JSON and sprites.

`main.py` reloads settings, collects startup choices, starts the application
manager with the first mascot, and runs Qt.
Character `behaviors.choices` sets selection weights (`0` disables an action),
and `behaviors.cooldowns` sets seconds before completed or interrupted actions
can repeat. If all actions are cooling down, the mascot waits in idle.
Sleep and hop use the supplied artwork. Walk and slow crawl use only the two
standing-walk frames. Sideways physics motion also uses those frames; vertical
falling uses its fall pose, and manual dragging retains its drag pose.
Horizontal-capable clips are marked with `allow_horizontal` in character JSON, and
look-around reuses standing/blinking poses with direction changes because
dedicated sequences are not supplied.
Climbing remains a future milestone.

## Displays and experimental window tops

Drag between monitors or throw through an adjoining display edge. Each display
has its own resolution, scale, and usable floor. Windows physical monitor
coordinates bridge the gaps Qt can have between displays with different DPI.
Taskbars, gaps, and outer edges remain solid boundaries; only seams with enough
usable room for the sprite are open. Random starts can use any connected display.
Changing or disconnecting a display returns affected mascots to a usable area.

Enable **Window tops (experimental)** in the launcher or saved defaults to land
and walk on visible normal Windows application windows. It defaults to off and
is saved as `window_interaction` in settings JSON. Mascots pass upward through
these surfaces. Moving a supporting window carries the mascot between monitors,
including across different DPI scales. Resizing preserves the mascot's relative
horizontal position on the window, as long as there is room for the sprite.
Mascots can also walk across a window spanning an adjoining monitor seam.

Hiding, minimizing, closing, covering, or walking off a supporting window releases
the mascot to gravity. Both the supporting edge and the space occupied by the
mascot must be clear of windows in front. Tops too narrow for the sprite or too
close to the screen ceiling are ignored. Maximizing usually removes that
headroom, so the mascot falls from its last valid position instead of jumping
to the ceiling. Restoring a window makes it available for normal landings again.

`platforms/windows.py` performs read-only Win32 detection; shared
`platforms/window_surfaces.py` polls and resolves one-way surfaces independently
of `core/physics.py`. Detection runs at most twenty times per second, shared by
all mascots with window interaction enabled. This is
approximate rectangular window detection: rounded corners, transparent windows,
full-screen games, and rapidly moving windows may not behave precisely. A window
moved completely off usable desktop space releases its mascot at the last safe
position. On other platforms, window surfaces are unavailable.

Real Windows resize, overlap, maximize/restore, minimize, and close transitions
have been checked. Mixed-DPI monitor carries and walking across a spanning
window have been checked with simulated layouts for all four characters;
physical multi-monitor testing is still outstanding.
