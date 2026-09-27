"""
MuJoCo demo for the ESP32 WiFi car.

Hold an arrow (or the on-screen pad) to drive. Release and the motors stop.
Left / right: both sides still roll forward, inside pair slower than outside pair.
The body stays upright and collides with the track walls.

Run:
  venv\\Scripts\\python sim\\drive.py
"""

from __future__ import annotations

import ctypes
import math
import sys
import threading
import tkinter as tk
from pathlib import Path

import mujoco
import mujoco.viewer

CRUISE_OMEGA = 4.5
TURN_INNER_OMEGA = 1.6
TURN_OUTER_OMEGA = 4.5

MOTOR_ACCEL = 50.0
MOTOR_BRAKE = 80.0

SCENE = Path(__file__).resolve().parent / "assets" / "race_track.xml"

# Win32 virtual-key codes. Polled every frame so a tap does not stick.
_VK_LEFT = 0x25
_VK_UP = 0x26
_VK_RIGHT = 0x27
_VK_DOWN = 0x28
_VK_A = 0x41
_VK_D = 0x44
_VK_S = 0x53
_VK_W = 0x57
_user32 = ctypes.windll.user32


def _held(vk: int) -> bool:
    return bool(_user32.GetAsyncKeyState(vk) & 0x8000)


def poll_keyboard() -> str:
    """Command is active only while the key is physically held."""
    up = _held(_VK_UP) or _held(_VK_W)
    down = _held(_VK_DOWN) or _held(_VK_S)
    left = _held(_VK_LEFT) or _held(_VK_A)
    right = _held(_VK_RIGHT) or _held(_VK_D)
    if up and not down:
        return "F"
    if down and not up:
        return "B"
    if left and not right:
        return "L"
    if right and not left:
        return "R"
    return "S"


class CarController:
    """Hold-to-drive skid steer with a short motor ramp."""

    def __init__(self) -> None:
        self._mouse_cmd = "S"
        self._lock = threading.Lock()
        self._omega_left = 0.0
        self._omega_right = 0.0

    def set_mouse_cmd(self, cmd: str) -> None:
        with self._lock:
            self._mouse_cmd = cmd

    def command(self) -> str:
        key_cmd = poll_keyboard()
        if key_cmd != "S":
            return key_cmd
        with self._lock:
            return self._mouse_cmd

    def _targets(self) -> tuple[float, float]:
        cmd = self.command()
        if cmd == "F":
            return CRUISE_OMEGA, CRUISE_OMEGA
        if cmd == "B":
            return -CRUISE_OMEGA, -CRUISE_OMEGA
        # Both sides forward; inside wheels slower so the car arcs.
        if cmd == "L":
            return TURN_INNER_OMEGA, TURN_OUTER_OMEGA
        if cmd == "R":
            return TURN_OUTER_OMEGA, TURN_INNER_OMEGA
        return 0.0, 0.0

    @staticmethod
    def _ramp(current: float, target: float, dt: float) -> float:
        rate = MOTOR_BRAKE if abs(target) < abs(current) else MOTOR_ACCEL
        step = rate * dt
        if abs(target - current) <= step:
            return target
        return current + math.copysign(step, target - current)

    def apply(self, data: mujoco.MjData, dt: float) -> None:
        target_left, target_right = self._targets()
        self._omega_left = self._ramp(self._omega_left, target_left, dt)
        self._omega_right = self._ramp(self._omega_right, target_right, dt)

        # Wheel motors only. Ground friction pushes the chassis toward the red nose.
        data.ctrl[0] = self._omega_left
        data.ctrl[1] = self._omega_right
        data.ctrl[2] = self._omega_left
        data.ctrl[3] = self._omega_right


def launch_mobile_ui(controller: CarController) -> None:
    root = tk.Tk()
    root.title("ESP32 CAR")
    root.configure(bg="#111111")
    root.resizable(False, False)

    tk.Label(
        root,
        text="ESP32 CAR (sim)",
        fg="white",
        bg="#111111",
        font=("Arial", 16, "bold"),
    ).pack(pady=(16, 8))
    tk.Label(
        root,
        text="Hold a button or arrow key.\nRelease = motors off.",
        fg="#aaaaaa",
        bg="#111111",
        font=("Arial", 9),
    ).pack(pady=(0, 10))

    frame = tk.Frame(root, bg="#111111")
    frame.pack(padx=16, pady=8)

    def press(cmd: str) -> None:
        controller.set_mouse_cmd(cmd)

    def release() -> None:
        controller.set_mouse_cmd("S")

    def mk_btn(text: str, cmd: str, *, stop: bool = False) -> tk.Button:
        btn = tk.Button(
            frame,
            text=text,
            width=4,
            height=2,
            font=("Arial", 18),
            bg="#d22222" if stop else "#333333",
            fg="white",
            activebackground="#008cff",
            activeforeground="white",
            relief=tk.FLAT,
            bd=0,
        )
        if stop:
            btn.configure(command=lambda: press("S"))
        else:
            btn.bind("<ButtonPress-1>", lambda _e: press(cmd))
            btn.bind("<ButtonRelease-1>", lambda _e: release())
            btn.bind("<Leave>", lambda _e: release())
        return btn

    mk_btn("^", "F").grid(row=0, column=1, pady=4)
    mk_btn("<", "L").grid(row=1, column=0, padx=6, pady=4)
    mk_btn("STOP", "S", stop=True).grid(row=1, column=1, padx=6, pady=4)
    mk_btn(">", "R").grid(row=1, column=2, padx=6, pady=4)
    mk_btn("v", "B").grid(row=2, column=1, pady=4)
    root.mainloop()


def main() -> int:
    # Call before any window opens, or Windows leaves black bars beside the 3D view.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()

    if not SCENE.is_file():
        print(f"Missing scene: {SCENE}", file=sys.stderr)
        return 1

    model = mujoco.MjModel.from_xml_path(str(SCENE))
    data = mujoco.MjData(model)
    controller = CarController()

    # East straight. qpos: x, y, z, yaw. Red block is the front (+X).
    data.qpos[0] = 2.6
    data.qpos[1] = -0.4
    data.qpos[2] = 0.002
    data.qpos[3] = math.pi / 2
    mujoco.mj_forward(model, data)

    threading.Thread(target=launch_mobile_ui, args=(controller,), daemon=True).start()
    dt = model.opt.timestep

    print("Hold arrow keys or the pad buttons. Release to stop.")
    print("Red block on the car is the front.")

    with mujoco.viewer.launch_passive(
        model, data, show_left_ui=False, show_right_ui=False
    ) as viewer:
        viewer.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
        viewer.cam.trackbodyid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "car")
        viewer.cam.distance = 1.8
        viewer.cam.elevation = -32
        viewer.cam.azimuth = 140

        hwnd = _user32.FindWindowW(None, "MuJoCo : esp32_race_track")
        if hwnd:
            _user32.ShowWindow(hwnd, 3)  # maximize

        while viewer.is_running():
            controller.apply(data, dt)
            mujoco.mj_step(model, data)
            viewer.sync()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
