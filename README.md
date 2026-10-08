# Python desktop mascots

This directory is the `ddlc_shimeji` project root. A fresh Python/PySide6
implementation, with no Java or JAR dependency. Requires Python 3.10 or newer.

## Run on Windows

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

The compact startup menu selects a character and session options. Press Start
to launch or Quit to exit. Monika, Yuri, Natsuki, and Sayori share one engine;
each character's JSON maps the supplied artwork to animation states. Original
source artwork remains in `temp pics`.

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

## Structure

- `ui/launcher.py`: user-facing startup menu.
- `ui/context_menu.py`, `ui/tray.py`: instance and application controls.
- `config/settings.py`: session settings and mappings to engine values.
- `core/application.py`: mascot ownership, spawning/removal, and saved defaults.
- `core/mascot.py`: window, mouse input, and component coordination.
- `core/animation.py`: ordered PNG playback with elapsed time.
- `core/physics.py`: gravity, throws, drag/friction, and collision resolution.
- `core/screen.py`: usable desktop geometry and initial positions.
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
these surfaces. Moving a supporting window carries the mascot; hiding, minimizing,
closing, covering, or walking off it releases the mascot to gravity. Window tops
too narrow for the sprite or too close to the screen ceiling are ignored.

`platforms/windows.py` performs read-only Win32 detection; shared
`platforms/window_surfaces.py` polls and resolves one-way surfaces independently
of `core/physics.py`. Detection runs at most five times per second. This is
approximate rectangular window detection: rounded corners, transparent windows,
full-screen games, and rapidly moving windows may not behave precisely. Moving a
supporting window to another monitor releases the mascot rather than carrying
it across the display seam. On other platforms, window surfaces are unavailable.
