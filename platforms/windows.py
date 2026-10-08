"""Small read-only Win32 adapter. Coordinates returned here are physical pixels."""

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os
import sys


@dataclass(frozen=True)
class NativeMonitor:
    name: str
    rect: tuple[int, int, int, int]


@dataclass(frozen=True)
class NativeWindow:
    handle: int
    rect: tuple[int, int, int, int]
    eligible: bool


def _rect(rect):
    return rect.left, rect.top, rect.right, rect.bottom


if sys.platform == "win32":
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    dwm = ctypes.WinDLL("dwmapi")
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    monitor_callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE,
                                         wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

    class MonitorInfo(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                    ("work", wintypes.RECT), ("flags", wintypes.DWORD),
                    ("device", wintypes.WCHAR * 32)]

    user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.c_void_p, monitor_callback, wintypes.LPARAM]
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    for name in ("IsWindowVisible", "IsIconic"):
        getattr(user32, name).argtypes = [wintypes.HWND]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    get_style = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    get_style.argtypes = [wintypes.HWND, ctypes.c_int]
    get_style.restype = ctypes.c_ssize_t
    dwm.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
    dwm.DwmGetWindowAttribute.restype = ctypes.c_long


def monitors() -> list[NativeMonitor]:
    if sys.platform != "win32":
        return []
    result = []

    @monitor_callback
    def visit(handle, dc, rect, data):
        info = MonitorInfo()
        info.size = ctypes.sizeof(info)
        if user32.GetMonitorInfoW(handle, ctypes.byref(info)):
            result.append(NativeMonitor(info.device, _rect(info.monitor)))
        return True

    user32.EnumDisplayMonitors(None, None, visit, 0)
    return result


def windows() -> list[NativeWindow]:
    """Visible windows in front-to-back order; own-process windows are excluded."""
    if sys.platform != "win32":
        return []
    result = []

    @callback_type
    def visit(handle, data):
        if not user32.IsWindowVisible(handle) or user32.IsIconic(handle):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        if pid.value == os.getpid():
            return True
        cloaked = wintypes.DWORD()
        if dwm.DwmGetWindowAttribute(handle, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked)) == 0 and cloaked.value:
            return True
        name = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(handle, name, len(name))
        if name.value in {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}:
            return True
        rect = wintypes.RECT()
        if dwm.DwmGetWindowAttribute(handle, 9, ctypes.byref(rect), ctypes.sizeof(rect)) != 0:
            if not user32.GetWindowRect(handle, ctypes.byref(rect)):
                return True
        if rect.right <= rect.left or rect.bottom <= rect.top:
            return True
        style, extended = get_style(handle, -16), get_style(handle, -20)
        eligible = bool(style & (0x00C00000 | 0x00040000)) and not bool(extended & 0x80)
        result.append(NativeWindow(int(handle), _rect(rect), eligible))
        return True

    user32.EnumWindows(visit, 0)
    return result
