import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import pyautogui
import keyboard
import os
import json
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
import base64
import subprocess
import math
import ctypes
from datetime import datetime, timedelta
from collections import deque
from PIL import Image, ImageTk, ImageGrab
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

matplotlib.use("TkAgg")

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

HOTKEY = "f7"

# Dark theme palette
BG = "#1e1f22"
SURFACE = "#2b2d31"
FG = "#e6e6e6"
MUTED = "#a0a0a0"
ACCENT = "#3b82f6"
ACCENT_ACTIVE = "#2f6fd0"
BORDER = "#3a3d41"

CLICKING_COLOR = "#3fb950"
STOPPED_COLOR = "#e3b341"

ACCEPT_BUTTON_IMAGE = "accept_all_button.png"
DATA_FILE = "vibecode_data.json"
MAX_DATA_AGE_WEEKS = 5
CONFIG_FILE = "vibecode_config.json"
LEADERBOARD_GITHUB_URL = "https://api.github.com/repos/kobel-studios/Kobel-vibecode-helper/contents/leaderboard_data.json"
GITHUB_ISSUES_URL = "https://github.com/kobel-studios/Kobel-vibecode-helper/issues/new"


def _get_non_primary_monitor():
    """Find a non-primary monitor on Windows. Returns (x, y, width, height) or None."""
    if not sys.platform.startswith("win"):
        return None
    try:
        user32 = ctypes.windll.user32
        # SM_XVIRTUALSCREEN=76, SM_YVIRTUALSCREEN=77, SM_CXVIRTUALSCREEN=78, SM_CYVIRTUALSCREEN=79
        vx = user32.GetSystemMetrics(76)
        vy = user32.GetSystemMetrics(77)
        vw = user32.GetSystemMetrics(78)
        vh = user32.GetSystemMetrics(79)
        # Primary monitor is at (0,0) with width=GetSystemMetrics(0), height=GetSystemMetrics(1)
        pw = user32.GetSystemMetrics(0)
        ph = user32.GetSystemMetrics(1)
        # If virtual screen is larger than primary, there are other monitors
        if vw <= pw and vh <= ph and vx == 0 and vy == 0:
            return None
        # Find a non-primary region: either left (vx < 0) or right (vx + vw > pw)
        if vx < 0:
            # There's a monitor to the left
            return (vx, 0, -vx, ph)
        elif vx + vw > pw:
            # There's a monitor to the right
            return (pw, 0, vx + vw - pw, ph)
        # Check above/below
        if vy < 0:
            return (0, vy, pw, -vy)
        elif vy + vh > ph:
            return (0, ph, pw, vy + vh - ph)
        return None
    except Exception:
        return None


class VibeCodeHelper:
    def __init__(self, root):
        self.root = root
        self.root.title("Vibe Code-Helper")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        # Set window icon
        self._set_window_icon()

        # Run intro sequence before building the main UI
        self.root.withdraw()
        self._run_intro_sequence()
        self.root.deiconify()
        
        # Position window on the right side of the main monitor
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        window_width = self.root.winfo_reqwidth()
        x_position = screen_width - window_width - 100
        y_position = 20
        self.root.geometry(f"+{x_position}+{y_position}")

        self.running = False
        self.stop_flag = threading.Event()
        self.worker = None
        self.accept_count = 0
        self.session_start_time = None
        self.total_clicks = 0
        
        # Graph data
        self.accept_rate_history = deque(maxlen=60)  # Store last 60 data points
        
        # Test mode flag
        self.test_mode = False
        
        # Leaderboard configuration
        self.username = None
        self.participate_leaderboard = False
        self.github_token = None
        
        # Load user configuration
        self._load_config()

        self._apply_dark_theme()
        self._build_ui()
        self._load_data()
        self._cleanup_old_data()
        self._check_for_leaderboard_updates()

        # Create desktop shortcut if it doesn't exist
        self._create_desktop_shortcut()

        # Position window on the right side of the screen
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        window_width = self.root.winfo_reqwidth()
        x_position = screen_width - window_width - 100
        y_position = 50
        self.root.geometry(f"{window_width}x{self.root.winfo_reqheight()}+{x_position}+{y_position}")


        keyboard.add_hotkey(HOTKEY, self._hotkey_pressed)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        # Bind click handler to entire window to remove focus from text boxes
        self.root.bind("<Button-1>", self._on_background_click)

    def _set_window_icon(self):
        """Set the window icon using a programmatically generated image."""
        try:
            from PIL import ImageDraw, ImageFilter

            icon_size = 256
            img = Image.new('RGBA', (icon_size, icon_size), (30, 31, 34, 255))
            draw = ImageDraw.Draw(img)

            cx, cy = 128, 120
            w = 70
            h = 120
            bar_w = 20

            top_left = (cx - w, cy - h // 2)
            top_right = (cx + w, cy - h // 2)
            bottom = (cx, cy + h // 2 + 10)

            inner_top_left = (cx - w + bar_w, cy - h // 2)
            inner_top_right = (cx + w - bar_w, cy - h // 2)
            inner_bottom_left = (cx - 2, cy + h // 2)
            inner_bottom_right = (cx + 2, cy + h // 2)

            color = (239, 68, 68, 255)

            draw.polygon([top_left, bottom, inner_bottom_right, inner_top_left], fill=color)
            draw.polygon([top_right, bottom, inner_bottom_left, inner_top_right], fill=color)

            glow = img.filter(ImageFilter.GaussianBlur(6))
            final = Image.new('RGBA', (icon_size, icon_size), (30, 31, 34, 255))
            final = Image.alpha_composite(final, glow)
            final = Image.alpha_composite(final, img)

            icon_path = "vch_icon_v7.ico"
            final.save(icon_path, format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

            self.root.iconbitmap(icon_path)
        except Exception as e:
            pass

    def _run_intro_sequence(self):
        """Kobel Studios logo with 20th Century Fox-style fanfare."""
        import pygame
        import numpy as np

        pygame.init()
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            pass

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        screen = pygame.display.set_mode((screen_width, screen_height), pygame.NOFRAME, display=0)
        pygame.display.set_caption("Kobel Studios")

        black = (0, 0, 0)
        white = (255, 255, 255)
        gold = (212, 175, 55)

        try:
            title_font = pygame.font.SysFont("georgia", 72, bold=True)
            sub_font = pygame.font.SysFont("georgia", 28, italic=True)
        except Exception:
            title_font = pygame.font.Font(None, 72)
            sub_font = pygame.font.Font(None, 28)

        # === Synthesize 20th Century Fox-style fanfare ===
        def make_tone(freq, duration, volume=0.3, harmonics=True):
            sample_rate = 44100
            n = int(sample_rate * duration)
            t = np.linspace(0, duration, n, endpoint=False)
            if harmonics:
                wave = (np.sin(2 * np.pi * freq * t) +
                        0.5 * np.sin(2 * np.pi * freq * 2 * t) +
                        0.3 * np.sin(2 * np.pi * freq * 3 * t) +
                        0.15 * np.sin(2 * np.pi * freq * 4 * t))
                wave /= 4.0
            else:
                wave = np.sin(2 * np.pi * freq * t)
            # Envelope: quick attack, sustain, quick release
            attack = int(0.02 * sample_rate)
            release = int(0.08 * sample_rate)
            env = np.ones(n)
            if attack > 0:
                env[:attack] = np.linspace(0, 1, attack)
            if release > 0 and release < n:
                env[-release:] = np.linspace(1, 0, release)
            wave = wave * env * volume
            stereo = np.column_stack([wave, wave])
            return (stereo * 32767).astype(np.int16)

        # Note frequencies
        notes = {
            'C4': 261.63, 'D4': 293.66, 'E4': 329.63, 'F4': 349.23,
            'G4': 392.00, 'A4': 440.00, 'B4': 493.88,
            'C5': 523.25, 'D5': 587.33, 'E5': 659.25, 'F5': 698.46,
            'G5': 783.99, 'A5': 880.00, 'B5': 987.77,
            'C6': 1046.50,
        }

        # Fanfare melody: (note, duration in seconds)
        fanfare = [
            ('G4', 0.3), ('C5', 0.15), ('C5', 0.15), ('C5', 0.15), ('C5', 0.15),
            ('G4', 0.2), ('A4', 0.15), ('B4', 0.15),
            ('C5', 0.15), ('D5', 0.15), ('E5', 0.15), ('F5', 0.15),
            ('G5', 0.3), ('G5', 0.15), ('G5', 0.15),
            ('C5', 0.2), ('E5', 0.15), ('G5', 0.15),
            ('C6', 0.6),
        ]

        # Build the full audio buffer
        all_samples = []
        for note_name, dur in fanfare:
            freq = notes.get(note_name, 440.0)
            tone = make_tone(freq, dur, volume=0.35)
            all_samples.append(tone)

        full_audio = np.concatenate(all_samples, axis=0)

        try:
            sound = pygame.sndarray.make_sound(full_audio)
            sound.play()
        except Exception:
            pass

        # === Animation ===
        clock = pygame.time.Clock()
        timer = 0
        total_duration = 360  # ~6 seconds at 60fps

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            clock.tick(60)
            timer += 1

            # Fade in: 0-30 frames, hold: 30-300, fade out: 300-360
            if timer < 30:
                alpha = int(255 * timer / 30)
            elif timer < 300:
                alpha = 255
            else:
                alpha = int(255 * (360 - timer) / 60)
                if alpha <= 0:
                    running = False

            screen.fill(black)

            # Spotlight glow effect
            glow_radius = 300 + int(50 * math.sin(timer * 0.05))
            for r in range(glow_radius, 0, -10):
                glow_alpha = int(40 * (1 - r / glow_radius))
                if glow_alpha > 0:
                    glow_surf = pygame.Surface((r * 2, r * 2))
                    pygame.draw.circle(glow_surf, (40, 40, 60), (r, r), r)
                    glow_surf.set_alpha(glow_alpha)
                    screen.blit(glow_surf, (screen_width // 2 - r, screen_height // 2 - r))

            # Kobel Studios text
            title_surf = title_font.render("Kobel Studios", True, gold)
            title_rect = title_surf.get_rect(center=(screen_width // 2, screen_height // 2 - 20))
            screen.blit(title_surf, title_rect)

            # Subtitle
            sub_surf = sub_font.render("Presents", True, white)
            sub_rect = sub_surf.get_rect(center=(screen_width // 2, screen_height // 2 + 50))
            screen.blit(sub_surf, sub_rect)

            # Apply fade
            if alpha < 255:
                fade_surf = pygame.Surface((screen_width, screen_height))
                fade_surf.fill(black)
                fade_surf.set_alpha(255 - alpha)
                screen.blit(fade_surf, (0, 0))

            pygame.display.flip()

        pygame.quit()

    def _check_accept_button_image(self):
        """Check if the accept button image exists; if not, prompt user to capture it."""
        if not os.path.exists(ACCEPT_BUTTON_IMAGE):
            response = messagebox.askyesno(
                "Setup Accept All Button",
                "No Accept All button image found.\n\n"
                "Would you like to capture one now?\n\n"
                "Instructions:\n"
                "1. Navigate to where the Accept All button appears\n"
                "2. Press F8 when your mouse is at the TOP-LEFT corner of the button\n"
                "3. Press F8 again when your mouse is at the BOTTOM-RIGHT corner of the button\n\n"
                "This only needs to be done once unless you update the app."
            )
            if response:
                self._capture_accept_button()
            else:
                messagebox.showwarning(
                    "Image Required",
                    f"The app needs {ACCEPT_BUTTON_IMAGE} to find the Accept All button.\n"
                    "You can capture it later by restarting the app."
                )

    def _capture_accept_button(self):
        """Capture a screenshot of the Accept All button from clipboard (Shift+Win+S)."""
        response = messagebox.askokcancel(
            "Capture Accept All Button",
            "Click OK to start capturing.\n\n"
            "The window will minimize and the snipping tool will open automatically.\n"
            "Select the Accept All button, then return here and click OK to save it."
        )
        if response:
            self.root.withdraw()
            # Give the window time to minimize, then open snipping tool
            self.root.after(500, self._open_snipping_tool)

    def _open_snipping_tool(self):
        """Automatically press Shift+Windows+S to open the snipping tool."""
        try:
            pyautogui.keyDown('shift')
            pyautogui.keyDown('win')
            pyautogui.keyDown('s')
            pyautogui.keyUp('s')
            pyautogui.keyUp('win')
            pyautogui.keyUp('shift')
        except Exception:
            pass
        # Wait for user to take screenshot, then show save dialog
        self.root.after(1000, self._show_save_dialog)

    def _show_save_dialog(self):
        """Show dialog asking user to confirm screenshot is ready."""
        self.root.deiconify()
        self.root.lift()
        response = messagebox.askokcancel(
            "Save Screenshot",
            "Have you selected the Accept All button with the snipping tool?\n\n"
            "Click OK to save it, or Cancel to try again."
        )
        if response:
            self._save_clipboard_screenshot()
        else:
            self.root.withdraw()
            self.root.after(500, self._open_snipping_tool)

    def _save_clipboard_screenshot(self):
        """Save the clipboard image as the Accept All button image."""
        try:
            screenshot = ImageGrab.grabclipboard()
            if screenshot is None:
                messagebox.showerror(
                    "No Screenshot Found",
                    "No image found in clipboard.\n"
                    "Please use Shift+Windows+S to capture the Accept All button first."
                )
                return

            if isinstance(screenshot, list):
                screenshot = screenshot[0]

            screenshot.save(ACCEPT_BUTTON_IMAGE)
            messagebox.showinfo("Success", f"Accept All button image saved as {ACCEPT_BUTTON_IMAGE}")

            # Hide the screenshot button after first capture
            if hasattr(self, 'screenshot_button'):
                self.screenshot_button.pack_forget()
                self.setup_text_var.set(
                    "• Accept All button image is set\n"
                    "• The script will auto-detect and use it\n"
                    "• Delete accept_all_button.png if you want to capture a new one"
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save screenshot: {e}")

    def _apply_dark_theme(self):
        self.root.configure(bg=BG)
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(".", background=BG, foreground=FG, fieldbackground=SURFACE)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("TLabelframe", background=BG, foreground=FG, bordercolor=BORDER)
        style.configure("TLabelframe.Label", background=BG, foreground=MUTED)
        style.configure(
            "TButton",
            background=ACCENT,
            foreground="#ffffff",
            borderwidth=0,
            focuscolor=ACCENT,
            padding=8,
        )
        style.map(
            "TButton",
            background=[("active", ACCENT_ACTIVE), ("pressed", ACCENT_ACTIVE)],
        )
        style.configure(
            "TEntry",
            fieldbackground=SURFACE,
            foreground=FG,
            insertcolor=FG,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
        )

    def _build_ui(self):
        pad = {"padx": 8, "pady": 6}
        container = ttk.Frame(self.root, padding=16)
        container.grid(row=0, column=0, sticky="nsew")

        title = ttk.Label(container, text="Kobel-vibecode-helper", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, columnspan=2, pady=(0, 12))

        # Check interval
        interval_frame = ttk.LabelFrame(container, text="Check interval (seconds)", padding=12)
        interval_frame.grid(row=1, column=0, columnspan=2, sticky="ew", **pad)

        self.interval_var = tk.StringVar(value="1")
        interval_entry = ttk.Entry(interval_frame, textvariable=self.interval_var, width=10, justify="center")
        interval_entry.pack()

        # Status
        self.status_var = tk.StringVar(value="Idle")
        self.status_label = ttk.Label(
            container, textvariable=self.status_var, font=("Segoe UI", 11, "bold"), foreground=MUTED
        )
        self.status_label.grid(row=2, column=0, columnspan=2, pady=(10, 2))

        # Settings buttons (above setup instructions)
        settings_frame = ttk.Frame(container)
        settings_frame.grid(row=3, column=0, columnspan=2, pady=(6, 0))
        
        ttk.Button(settings_frame, text="Save Settings", command=self._save_settings, width=12).pack(side="left", padx=2)
        ttk.Button(settings_frame, text="Load Settings", command=self._load_settings, width=12).pack(side="left", padx=2)

        # Settings instructions
        settings_info_frame = ttk.LabelFrame(container, text="Settings", padding=12)
        settings_info_frame.grid(row=4, column=0, columnspan=2, sticky="ew", **pad)

        settings_text = (
            "• Save Settings: Save your current interval to a file\n"
            "• Load Settings: Load a previously saved interval"
        )
        ttk.Label(settings_info_frame, text=settings_text, foreground=ACCENT, justify="left").pack()

        # Count
        self.count_var = tk.StringVar(value="Accepts performed: 0")
        ttk.Label(container, textvariable=self.count_var, foreground=MUTED).grid(row=5, column=0, columnspan=2, pady=(0, 4))
        
        # Statistics (only visible when running)
        self.stats_var = tk.StringVar(value="")
        self.stats_label = ttk.Label(container, textvariable=self.stats_var, foreground=MUTED, font=("Segoe UI", 9))
        self.stats_label.grid(row=6, column=0, columnspan=2, pady=(0, 8))
        self.stats_label.grid_remove()  # Hide initially

        # Setup instructions
        setup_frame = ttk.LabelFrame(container, text="Setup Instructions", padding=12)
        setup_frame.grid(row=7, column=0, columnspan=2, sticky="ew", **pad)

        self.setup_text_var = tk.StringVar(
            value=(
                "• Click the button below to capture the Accept All button\n"
                "• The snipping tool will open automatically — just select the button\n"
                "• Your screenshot is saved and ready to use\n"
                "• One capture lasts forever, unless you update the app from GitHub"
            )
        )
        ttk.Label(setup_frame, textvariable=self.setup_text_var, foreground=ACCENT, justify="left").pack()

        self.screenshot_button = ttk.Button(
            setup_frame,
            text="Take Screenshot",
            command=self._capture_accept_button,
            width=16
        )
        self.screenshot_button.pack(pady=(8, 0))

        # Hide button if screenshot already exists
        if os.path.exists(ACCEPT_BUTTON_IMAGE):
            self.screenshot_button.pack_forget()
            self.setup_text_var.set(
                "• Accept All button image is set\n"
                "• The script will auto-detect and use it\n"
                "• Delete accept_all_button.png to capture a new one"
            )

        # Controls
        self.toggle_button = ttk.Button(container, text="Start (F7)", command=self._toggle)
        self.toggle_button.grid(row=8, column=0, columnspan=2, sticky="ew", padx=6, pady=(6, 2))

        # Settings buttons
        settings_frame = ttk.Frame(container)
        settings_frame.grid(row=9, column=0, columnspan=2, pady=(6, 0))

        ttk.Button(settings_frame, text="Test Accept", command=self._test_accept, width=12).pack(side="left", padx=2)
        ttk.Button(settings_frame, text="View Graph", command=self._view_graph, width=12).pack(side="left", padx=2)
        ttk.Button(settings_frame, text="Leaderboard", command=self._view_leaderboard, width=12).pack(side="left", padx=2)

        hint = ttk.Label(
            container,
            text="Press F7 anywhere to start/stop. Press Esc to quit.\n"
                 "Fail-safe: slam mouse to a screen corner to abort.",
            foreground=MUTED,
            justify="center",
        )
        hint.grid(row=10, column=0, columnspan=2, pady=(8, 0))

    def _create_desktop_shortcut(self):
        """Create a desktop shortcut for Vibe Code Helper if it doesn't exist."""
        try:
            # Try multiple methods to get desktop path
            desktop_dir = None

            # Method 1: Windows API
            try:
                import ctypes
                from ctypes import wintypes
                CSIDL_DESKTOP = 0
                SHGFP_TYPE_CURRENT = 0
                buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
                ctypes.windll.shell32.SHGetFolderPathW(0, CSIDL_DESKTOP, 0, SHGFP_TYPE_CURRENT, buf)
                desktop_dir = buf.value
            except:
                pass

            # Method 2: Environment variable with OneDrive check
            if not desktop_dir or not os.path.exists(desktop_dir):
                one_drive_desktop = os.path.join(os.environ["USERPROFILE"], "OneDrive", "Desktop")
                if os.path.exists(one_drive_desktop):
                    desktop_dir = one_drive_desktop
                else:
                    desktop_dir = os.path.join(os.environ["USERPROFILE"], "Desktop")

            shortcut_path = os.path.join(desktop_dir, "Vibe Code Helper.lnk")
            script_path = os.path.abspath(__file__)
            python_path = self._get_pythonw_path()
            icon_path = os.path.join(os.path.dirname(script_path), "vibe_icon.ico")

            # Use the exact same format as Kobel Autoclicker
            ps_command = (
                f"$WshShell = New-Object -comObject WScript.Shell; "
                f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
                f"$Shortcut.TargetPath = '{python_path}'; "
                f"$Shortcut.Arguments = '\"{script_path}\"'; "
                f"$Shortcut.WorkingDirectory = '{os.path.dirname(script_path)}'; "
                f"$Shortcut.IconLocation = '{icon_path},0'; "
                f"$Shortcut.Description = 'Vibe Code Helper'; "
                f"$Shortcut.Save()"
            )

            subprocess.run(["powershell", "-Command", ps_command], check=False)
        except Exception as e:
            # Don't show error for shortcut creation - it's optional
            pass

    def _get_pythonw_path(self):
        """Get the path to pythonw.exe (for running without console window)."""
        python_dir = os.path.dirname(sys.executable)
        pythonw_path = os.path.join(python_dir, "pythonw.exe")
        return pythonw_path if os.path.exists(pythonw_path) else sys.executable

    def on_close(self):
        """Clean up on close."""
        self.stop_running()
        self.root.destroy()

    def _on_background_click(self, event):
        """Remove focus from text boxes when clicking on window background."""
        clicked_widget = event.widget
        
        if isinstance(clicked_widget, ttk.Entry):
            return
        
        current = clicked_widget
        while current:
            if isinstance(current, ttk.Entry):
                return
            if isinstance(current, (ttk.Button, ttk.Combobox, ttk.Checkbutton, ttk.Radiobutton)):
                return
            try:
                current = current.master
            except AttributeError:
                break
        
        self.root.focus_set()

    def _hotkey_pressed(self):
        self.root.after(0, self._toggle)

    def _toggle(self):
        if self.running:
            self.stop_running()
        else:
            self.start_running()

    def start_running(self):
        # Check if button image exists
        if not os.path.exists(ACCEPT_BUTTON_IMAGE):
            messagebox.showerror("Missing file", f"{ACCEPT_BUTTON_IMAGE} not found.\nPlease take a screenshot of the Accept All button and save it as {ACCEPT_BUTTON_IMAGE}")
            return

        try:
            interval = float(self.interval_var.get())
            if interval <= 0:
                raise ValueError("Interval must be greater than 0")
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc))
            return

        self.running = True
        self.stop_flag.clear()
        # Don't reset accept_count - let it persist across sessions
        self.session_start_time = time.time()
        self.accept_rate_history.clear()
        self.worker = threading.Thread(target=self._accept_loop, args=(interval,), daemon=True)
        self.worker.start()

        self.toggle_button.config(text="Stop (F7)")
        self._set_status("Running...", CLICKING_COLOR)
        self.stats_label.grid()  # Show stats when running

    def stop_running(self):
        self.stop_flag.set()
        self.running = False
        self.toggle_button.config(text="Start (F7)")
        self._set_status("Stopped", STOPPED_COLOR)
        self.stats_label.grid_remove()  # Hide stats when stopped
        # Ask if user wants to submit to leaderboard
        if self.participate_leaderboard and self.accept_count > 0:
            self._prompt_submit_leaderboard()

    def _accept_loop(self, interval):
        try:
            last_update = time.time()
            while not self.stop_flag.is_set():
                if self._click_accept_all():
                    # Only count if not in test mode
                    if not self.test_mode:
                        self.accept_count += 1
                        self.total_clicks += 1
                        self.root.after(0, self._update_count, self.accept_count)
                        self.root.after(0, self._update_stats)
                    
                    # Record for graph (only if not test mode)
                    current_time = time.time()
                    if self.session_start_time and not self.test_mode:
                        elapsed = current_time - self.session_start_time
                        accepts_per_min = (self.accept_count / elapsed) * 60 if elapsed > 0 else 0
                        self.accept_rate_history.append((elapsed, accepts_per_min))

                # Update graph every second (only if not test mode)
                current_time = time.time()
                if current_time - last_update >= 1.0 and self.session_start_time and not self.test_mode:
                    elapsed = current_time - self.session_start_time
                    accepts_per_min = (self.accept_count / elapsed) * 60 if elapsed > 0 else 0
                    self.accept_rate_history.append((elapsed, accepts_per_min))
                    last_update = current_time

                # Sleep for the interval (in seconds)
                time.sleep(interval)
        except Exception:
            pass
        finally:
            self.root.after(0, self._on_loop_done)

    def _click_accept_all(self, is_test=False):
        """Try to find and click the 'Accept All' button using image recognition."""

        try:
            button_location = pyautogui.locateOnScreen(ACCEPT_BUTTON_IMAGE, confidence=0.8)
            if button_location:
                button_center = pyautogui.center(button_location)

                # Save current mouse position
                original_pos = pyautogui.position()

                # Click the button
                pyautogui.click(button_center)

                # Restore mouse position without clicking
                pyautogui.move(original_pos[0] - button_center[0], original_pos[1] - button_center[1])

                return True
        except Exception as e:
            print(f"Error clicking Accept All: {e}")

        return False

    def _on_loop_done(self):
        self.running = False
        self.toggle_button.config(text="Start (F7)")
        self.count_var.set(f"Accepts performed: {self.accept_count}")
        self._set_status("Stopped", STOPPED_COLOR)
        # Ask if user wants to save to leaderboard before saving
        if self.participate_leaderboard and self.accept_count > 0:
            self._prompt_submit_leaderboard()

    def _set_status(self, text, color):
        self.status_var.set(text)
        self.status_label.config(foreground=color)

    def _update_count(self, count):
        self.count_var.set(f"Accepts performed: {count}")

    def _update_stats(self):
        """Update click statistics display."""
        if self.session_start_time and self.accept_count > 0:
            elapsed = time.time() - self.session_start_time
            if elapsed > 0:
                clicks_per_min = (self.accept_count / elapsed) * 60
                self.stats_var.set(f"Session: {self.accept_count} clicks | {clicks_per_min:.1f} clicks/min")
            else:
                self.stats_var.set(f"Session: {self.accept_count} clicks")
        elif self.accept_count > 0:
            self.stats_var.set(f"Session: {self.accept_count} clicks")
        else:
            self.stats_var.set("Session: 0 clicks")

    def _save_settings(self):
        """Save current settings to a JSON file with auto-generated name."""
        settings = {
            "interval": self.interval_var.get()
        }
        
        # Auto-generate filename with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = f"settings_{timestamp}.json"
        
        try:
            with open(file_path, "w") as f:
                json.dump(settings, f, indent=4)
            messagebox.showinfo("Success", f"Settings saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def _load_settings(self):
        """Load settings from a JSON file - show hub of all saved settings."""
        # Find all JSON files in current directory
        import glob
        json_files = glob.glob("*.json")
        
        # Filter out config files (vibecode_config.json, vibecode_data.json)
        settings_files = [f for f in json_files if not f.startswith("vibecode_")]
        
        if not settings_files:
            messagebox.showinfo("No Settings", "No saved settings files found.")
            return
        
        # Create settings hub window
        hub_window = tk.Toplevel(self.root)
        hub_window.title("Settings Hub")
        hub_window.geometry("400x500")
        hub_window.configure(bg=BG)
        hub_window.transient(self.root)
        
        # Title
        title = tk.Label(
            hub_window,
            text="Saved Settings",
            fg=FG,
            bg=BG,
            font=("Segoe UI", 14, "bold")
        )
        title.pack(pady=20)
        
        # Create scrollable frame for settings
        canvas = tk.Canvas(hub_window, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(hub_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=20, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        # Add each settings file as a button
        for file in settings_files:
            try:
                with open(file, "r") as f:
                    data = json.load(f)
                    interval = data.get("interval", "Unknown")
                    
                # Create button for this setting
                btn = tk.Button(
                    scrollable_frame,
                    text=f"{file}\nInterval: {interval}s",
                    bg=SURFACE,
                    fg=FG,
                    font=("Segoe UI", 10),
                    relief="flat",
                    padx=10,
                    pady=5,
                    cursor="hand2",
                    command=lambda f=file, i=interval: self._apply_settings(f, i, hub_window)
                )
                btn.pack(fill="x", pady=5, padx=10)
            except Exception:
                # Skip invalid files
                pass
        
        # Close button
        ttk.Button(hub_window, text="Close", command=hub_window.destroy).pack(pady=10)
        
        # Center window
        hub_window.update_idletasks()
        x = (hub_window.winfo_screenwidth() // 2) - (hub_window.winfo_width() // 2)
        y = (hub_window.winfo_screenheight() // 2) - (hub_window.winfo_height() // 2)
        hub_window.geometry(f"+{x}+{y}")

    def _apply_settings(self, file_path, interval, window):
        """Apply the selected settings and close the hub."""
        self.interval_var.set(str(interval))
        window.destroy()
        messagebox.showinfo("Success", f"Loaded settings from {file_path}")

    def on_close(self):
        self.stop_running()
        self.root.destroy()

    # ---------- Leaderboard System ----------
    def _load_config(self):
        """Load user configuration or prompt for username on first launch."""
        self.username = None
        self.participate_leaderboard = False
        self.github_token = None

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.username = config.get("username")
                    self.participate_leaderboard = config.get("participate_leaderboard", False)
                    self.github_token = config.get("github_token")
            except Exception:
                pass

        if not self.username or not self.participate_leaderboard:
            self._prompt_username()

    def _save_config(self):
        """Save user configuration to file."""
        config = {
            "username": self.username,
            "participate_leaderboard": self.participate_leaderboard,
            "github_token": self.github_token,
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def _ask_github_token(self):
        """Ask user for GitHub token with clickable link."""
        dialog = tk.Toplevel(self.root)
        dialog.title("GitHub Token")
        dialog.geometry("600x500")
        dialog.configure(bg=BG)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Instructions
        instructions = tk.Label(
            dialog,
            text="WHAT THIS DOES:\n"
                   "This lets the app add your score to the leaderboard automatically.\n"
                   "It does NOT give us access to your GitHub account or repos.\n"
                   "You create the token yourself, so you control it.\n\n"
                   "STEP 1: Click the link below\n"
                   "STEP 2: Click 'Generate new token (classic)'\n"
                   "STEP 3: Type a name (like 'vibecode')\n"
                   "STEP 4: Check the box that says 'repo'\n"
                   "STEP 5: Click the green button\n"
                   "STEP 6: Copy the code it shows you\n"
                   "STEP 7: Paste it in the box below",
            fg=FG,
            bg=BG,
            font=("Segoe UI", 10),
            justify="left"
        )
        instructions.pack(pady=20, padx=20)
        
        # Clickable link
        def open_link():
            webbrowser.open("https://github.com/settings/tokens/new?scopes=repo")
        
        link_label = tk.Label(
            dialog,
            text="https://github.com/settings/tokens/new?scopes=repo",
            fg=ACCENT,
            bg=BG,
            font=("Segoe UI", 10, "underline"),
            cursor="hand2"
        )
        link_label.pack(pady=5)
        link_label.bind("<Button-1>", lambda e: open_link())
        
        # Safety note
        safety_note = tk.Label(
            dialog,
            text="This is NOT your GitHub password. It's a special code you create.\n"
                   "You can delete it anytime from GitHub settings.\n\n"
                   "(Leave empty to use manual submission instead)",
            fg=MUTED,
            bg=BG,
            font=("Segoe UI", 9),
            justify="left"
        )
        safety_note.pack(pady=10, padx=20)
        
        # Token input
        token_var = tk.StringVar()
        token_entry = tk.Entry(
            dialog,
            textvariable=token_var,
            show="*",
            font=("Segoe UI", 10),
            bg=SURFACE,
            fg=FG,
            insertbackground=FG,
            width=40
        )
        token_entry.pack(pady=10, padx=20, fill="x")
        token_entry.focus()
        
        # Buttons
        button_frame = tk.Frame(dialog, bg=BG)
        button_frame.pack(pady=20)
        
        result = [None]
        
        def on_ok():
            result[0] = token_var.get()
            dialog.destroy()
        
        def on_cancel():
            result[0] = ""
            dialog.destroy()
        
        ok_button = tk.Button(
            button_frame,
            text="OK",
            command=on_ok,
            bg=ACCENT,
            fg="white",
            font=("Segoe UI", 10),
            relief="flat",
            padx=20
        )
        ok_button.pack(side="left", padx=5)
        
        cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            command=on_cancel,
            bg=SURFACE,
            fg=FG,
            font=("Segoe UI", 10),
            relief="flat",
            padx=20
        )
        cancel_button.pack(side="left", padx=5)
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Bind Enter key to OK
        dialog.bind("<Return>", lambda e: on_ok())
        
        # Wait for dialog to close
        self.root.wait_window(dialog)
        
        return result[0]

    def _prompt_username(self):
        """Prompt user for leaderboard participation and username."""
        result = messagebox.askyesno(
            "Leaderboard",
            "Do you want to participate in the global leaderboard?\n\n"
            "Your accepts will be tracked and compared with other users.\n\n"
            "(This will only be asked once)"
        )

        if result:
            # Ask for username (loop until unique or cancelled)
            while True:
                username = simpledialog.askstring(
                    "Username",
                    "Enter your username for the leaderboard:",
                    parent=self.root
                )
                
                if not username or not username.strip():
                    # User cancelled or entered empty username
                    self.participate_leaderboard = False
                    self._save_config()
                    return
                
                username = username.strip()
                
                # Check if username already exists in leaderboard
                if self._username_exists(username):
                    messagebox.showerror(
                        "Username Taken",
                        f"The username '{username}' is already taken. Please choose a different username."
                    )
                else:
                    self.username = username
                    self.participate_leaderboard = True
                    # Ask for GitHub token for automatic submission
                    token = self._ask_github_token()
                    self.github_token = token.strip() if token else None
                    self._save_config()
                    if self.github_token:
                        messagebox.showinfo("Welcome", f"Welcome, {self.username}! Your sessions will be automatically submitted to the leaderboard.")
                    else:
                        messagebox.showinfo("Welcome", f"Welcome, {self.username}! Your sessions will be saved to the leaderboard (manual submission via GitHub Issues).")
                    break
        else:
            # User declined - save this so we don't ask again
            self.participate_leaderboard = False
            self._save_config()

    def _username_exists(self, username):
        """Check if username already exists in the leaderboard."""
        try:
            # Fetch current data from GitHub API
            response = urllib.request.urlopen(LEADERBOARD_GITHUB_URL)
            file_data = json.loads(response.read().decode('utf-8'))
            
            # Decode base64 content
            import base64
            content = file_data.get("content", "")
            if content:
                decoded_content = base64.b64decode(content).decode('utf-8')
                data = json.loads(decoded_content)
            else:
                data = {"sessions": []}
            
            sessions = data.get("sessions", [])
            
            # Check if any session has this username
            for session in sessions:
                if session.get("username") == username:
                    return True
            
            return False
        except urllib.error.URLError:
            # Can't connect to GitHub - warn user but allow
            messagebox.showwarning(
                "Connection Error",
                "Cannot check if username is taken (no internet connection).\n"
                "You can continue, but your username might already be taken."
            )
            return False
        except Exception as e:
            # Other error - warn user but allow
            messagebox.showwarning(
                "Error",
                f"Cannot check if username is taken: {e}\n"
                "You can continue, but your username might already be taken."
            )
            return False

    def _save_session(self):
        """Save session data to local file."""
        if not self.session_start_time or self.accept_count == 0:
            return
        
        session_data = {
            "username": self.username,
            "timestamp": datetime.now().isoformat(),
            "accepts": self.accept_count,
            "duration_seconds": time.time() - self.session_start_time,
            "accepts_per_minute": (self.accept_count / (time.time() - self.session_start_time)) * 60 if self.session_start_time else 0
        }
        
        # Load existing data
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    sessions = data.get("sessions", [])
            except Exception:
                sessions = []
        else:
            sessions = []
        
        # Add new session
        sessions.append(session_data)
        
        # Save back
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"sessions": sessions}, f, indent=2)

    def _prompt_submit_leaderboard(self):
        """Prompt user to submit their session data to GitHub."""
        if self.github_token:
            # Automatic submission via GitHub API
            result = messagebox.askyesno(
                "Submit to Leaderboard",
                "Do you want to submit your session to the global leaderboard?\n\n"
                "This will automatically submit your data via GitHub API."
            )
            if result:
                # Save the session locally first
                self._save_session()
                # Then submit via GitHub API
                self._submit_to_github_api()
        else:
            # Manual submission via GitHub Issues
            result = messagebox.askyesno(
                "Submit to Leaderboard",
                "Do you want to submit your session to the global leaderboard?\n\n"
                "This will open a GitHub Issue where you can create your data."
            )
            if result:
                # Save the session locally first
                self._save_session()
                # Then open GitHub Issues
                self._submit_to_github()

    def _submit_to_github_api(self):
        """Submit session data to GitHub via API."""
        try:
            # Load the latest session data
            if not os.path.exists(DATA_FILE):
                messagebox.showerror("Error", "No session data found to submit.")
                return

            with open(DATA_FILE, "r", encoding="utf-8") as f:
                local_data = json.load(f)
            local_sessions = local_data.get("sessions", [])
            
            if not local_sessions:
                messagebox.showerror("Error", "No session data found to submit.")
                return

            # Get the most recent session
            latest_session = local_sessions[-1]

            # Fetch current data from GitHub API
            request = urllib.request.Request(
                LEADERBOARD_GITHUB_URL,
                headers={"Authorization": f"token {self.github_token}"}
            )
            response = urllib.request.urlopen(request)
            file_data = json.loads(response.read().decode('utf-8'))
            
            # Decode base64 content
            content = file_data.get("content", "")
            if content:
                decoded_content = base64.b64decode(content).decode('utf-8')
                remote_data = json.loads(decoded_content)
            else:
                remote_data = {"sessions": []}
            
            remote_sessions = remote_data.get("sessions", [])

            # Check if session already exists (by timestamp)
            if any(s.get("timestamp") == latest_session.get("timestamp") for s in remote_sessions):
                messagebox.showinfo("Info", "This session is already on the leaderboard.")
                return

            # Add new session
            remote_sessions.append(latest_session)
            remote_data["sessions"] = remote_sessions

            # Get the SHA of the current file (needed for updating)
            api_url = "https://api.github.com/repos/kobel-studios/Kobel-vibecode-helper/contents/leaderboard_data.json"
            request = urllib.request.Request(
                api_url,
                headers={"Authorization": f"token {self.github_token}"}
            )
            response = urllib.request.urlopen(request)
            file_info = json.loads(response.read().decode('utf-8'))
            sha = file_info.get("sha")

            # Update the file via GitHub API
            updated_content = json.dumps(remote_data, indent=2)
            encoded_content = base64.b64encode(updated_content.encode('utf-8')).decode('utf-8')

            put_data = {
                "message": f"Add session from {self.username}",
                "content": encoded_content,
                "sha": sha
            }

            request = urllib.request.Request(
                api_url,
                data=json.dumps(put_data).encode('utf-8'),
                headers={
                    "Authorization": f"token {self.github_token}",
                    "Content-Type": "application/json"
                },
                method="PUT"
            )
            response = urllib.request.urlopen(request)

            messagebox.showinfo("Success", "Your session has been successfully submitted to the leaderboard!")

        except urllib.error.HTTPError as e:
            error_msg = f"Failed to submit to GitHub (HTTP {e.code}).\n"
            if e.code == 401:
                error_msg += "Your GitHub token is invalid or expired.\nPlease generate a new token."
            elif e.code == 403:
                error_msg += "Your token doesn't have permission to write to this repository.\nMake sure the token has 'repo' scope."
            elif e.code == 409:
                error_msg += "There was a conflict. Someone else may have updated the leaderboard.\nPlease try again."
            else:
                error_msg += f"Error: {e.read().decode('utf-8')}"
            messagebox.showerror("Submission Failed", error_msg)
        except urllib.error.URLError as e:
            messagebox.showerror("Network Error", f"Failed to connect to GitHub: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to submit to leaderboard: {e}")

    def _submit_to_github(self):
        """Open GitHub Issues with pre-filled leaderboard data."""
        try:
            if not os.path.exists(DATA_FILE):
                messagebox.showerror("Error", "No session data found to submit.")
                return

            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                sessions = data.get("sessions", [])
            
            if not sessions:
                messagebox.showerror("Error", "No session data found to submit.")
                return

            latest_session = sessions[-1]
            
            # Format the data for GitHub Issues
            issue_title = f"Leaderboard Submission: {self.username}"
            issue_body = f"""Username: {self.username}
Timestamp: {latest_session.get('timestamp')}
Accepts: {latest_session.get('accepts')}
Duration: {latest_session.get('duration_seconds', 0):.2f} seconds
Accepts per minute: {latest_session.get('accepts_per_minute', 0):.2f}

Please add this session to the leaderboard_data.json file."""

            # URL encode the body
            encoded_body = urllib.parse.quote(issue_body)
            
            # Open GitHub Issues
            issue_url = f"https://github.com/kobel-studios/Kobel-vibecode-helper/issues/new?title={urllib.parse.quote(issue_title)}&body={encoded_body}"
            webbrowser.open(issue_url)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open GitHub Issues: {e}")

    def _view_leaderboard(self):
        """Display the leaderboard in a new window."""
        # Check for updates before showing leaderboard
        self._check_for_leaderboard_updates()

        if not os.path.exists(DATA_FILE):
            messagebox.showinfo("No data", "No saved sessions found.")
            return

        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions = data.get("sessions", [])

            if not sessions:
                messagebox.showinfo("No data", "No saved sessions found.")
                return

            # Sort by max accepts per minute (descending)
            sorted_sessions = sorted(
                sessions, key=lambda s: s.get("max_accepts_per_min", 0), reverse=True
            )
            
            # Create leaderboard window
            leaderboard_window = tk.Toplevel(self.root)
            leaderboard_window.title("Leaderboard")
            leaderboard_window.geometry("700x500")
            leaderboard_window.configure(bg=BG)
            leaderboard_window.transient(self.root)
            
            # Title
            title = tk.Label(
                leaderboard_window,
                text="Global Leaderboard - Accepts per Minute",
                fg=FG,
                bg=BG,
                font=("Segoe UI", 14, "bold")
            )
            title.pack(pady=20)
            
            # Configure Treeview style for dark theme
            style = ttk.Style()
            style.configure("Treeview",
                          background=BG,
                          foreground=FG,
                          fieldbackground=BG,
                          font=("Segoe UI", 10))
            style.configure("Treeview.Heading",
                          background=SURFACE,
                          foreground=FG,
                          font=("Segoe UI", 10, "bold"))
            style.map("Treeview",
                     background=[('selected', ACCENT)],
                     foreground=[('selected', 'white')])

            # Create treeview for leaderboard
            columns = ("rank", "username", "date", "max_rate", "avg_rate", "accepts")
            tree = ttk.Treeview(leaderboard_window, columns=columns, show="headings", style="Treeview")
            tree.heading("rank", text="#")
            tree.heading("username", text="Username")
            tree.heading("date", text="Date")
            tree.heading("max_rate", text="Max Rate")
            tree.heading("avg_rate", text="Avg Rate")
            tree.heading("accepts", text="Accepts")

            tree.column("rank", width=30, anchor="center")
            tree.column("username", width=80)
            tree.column("date", width=90)
            tree.column("max_rate", width=60, anchor="center")
            tree.column("avg_rate", width=60, anchor="center")
            tree.column("accepts", width=70, anchor="center")

            tree.pack(side="left", fill="both", expand=True, padx=10, pady=5)

            scrollbar = ttk.Scrollbar(leaderboard_window, orient="vertical", command=tree.yview)
            scrollbar.pack(side="right", fill="y")
            tree.configure(yscrollcommand=scrollbar.set)

            # Populate leaderboard
            for i, session in enumerate(sorted_sessions[:20], 1):  # Top 20
                date_str = datetime.fromisoformat(session["timestamp"]).strftime("%Y-%m-%d %H:%M")
                username = session.get("username", "Unknown")
                tree.insert(
                    "",
                    "end",
                    values=(
                        i,
                        username,
                        date_str,
                        f"{session['max_accepts_per_min']:.1f}",
                        f"{session['avg_accepts_per_min']:.1f}",
                        session["accepts"],
                    ),
                )
            
            # Button frame
            button_frame = ttk.Frame(leaderboard_window)
            button_frame.pack(pady=10)
            
            # Update button
            ttk.Button(button_frame, text="Update", command=self._update_leaderboard_from_github).pack(side="left", padx=5)
            # Close button
            ttk.Button(button_frame, text="Close", command=leaderboard_window.destroy).pack(side="left", padx=5)
            
            # Center window
            leaderboard_window.update_idletasks()
            x = (leaderboard_window.winfo_screenwidth() // 2) - (leaderboard_window.winfo_width() // 2)
            y = (leaderboard_window.winfo_screenheight() // 2) - (leaderboard_window.winfo_height() // 2)
            leaderboard_window.geometry(f"+{x}+{y}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load leaderboard: {e}")

    def _load_data(self):
        """Load saved session data from JSON file."""
        if not os.path.exists(DATA_FILE):
            return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.saved_sessions = data.get("sessions", [])
        except Exception:
            self.saved_sessions = []

    def _cleanup_old_data(self):
        """Remove sessions older than MAX_DATA_AGE_WEEKS."""
        if not os.path.exists(DATA_FILE):
            return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions = data.get("sessions", [])
            cutoff = datetime.now() - timedelta(weeks=MAX_DATA_AGE_WEEKS)
            filtered = [
                s for s in sessions
                if datetime.fromisoformat(s["timestamp"]) > cutoff
            ]
            if len(filtered) != len(sessions):
                data["sessions"] = filtered
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
        except Exception:
            pass

    def _save_session(self):
        """Save current session data to JSON file."""
        try:
            if not self.participate_leaderboard:
                return

            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"sessions": []}

            if not self.accept_rate_history:
                return
            times = [t for t, _ in self.accept_rate_history]
            rates = [r for _, r in self.accept_rate_history]
            avg_rate = sum(rates) / len(rates) if rates else 0
            max_rate = max(rates) if rates else 0
            total_accepts = self.accept_count
            duration = times[-1] - times[0] if times else 0

            session = {
                "timestamp": datetime.now().isoformat(),
                "username": self.username,
                "accepts": total_accepts,
                "duration_seconds": round(duration, 2),
                "avg_accepts_per_min": round(avg_rate * 60, 2),
                "max_accepts_per_min": round(max_rate * 60, 2),
                "rate_history": list(self.accept_rate_history),
            }

            data["sessions"].append(session)
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _check_for_leaderboard_updates(self):
        """Check for leaderboard updates and prompt user if available."""
        try:
            response = urllib.request.urlopen(LEADERBOARD_GITHUB_URL)
            api_response = json.loads(response.read().decode('utf-8'))

            if "content" in api_response:
                content = base64.b64decode(api_response["content"]).decode('utf-8')
                remote_data = json.loads(content)
            else:
                remote_data = {"sessions": []}

            remote_sessions = remote_data.get("sessions", [])

            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
            else:
                local_data = {"sessions": []}
            local_sessions = local_data.get("sessions", [])

            local_timestamps = {s["timestamp"] for s in local_sessions}
            new_sessions = [s for s in remote_sessions if s["timestamp"] not in local_timestamps]

            if new_sessions:
                if not local_sessions:
                    local_data["sessions"] = remote_sessions
                    with open(DATA_FILE, "w", encoding="utf-8") as f:
                        json.dump(local_data, f, indent=2)
                    self._load_data()
                else:
                    result = messagebox.askyesno(
                        "Leaderboard Update Available",
                        f"Found {len(new_sessions)} new session(s) on the global leaderboard.\n\n"
                        f"Do you want to download and merge them now?"
                    )
                    if result:
                        self._update_leaderboard_from_github()
        except urllib.error.URLError:
            pass
        except Exception:
            pass

    def _update_leaderboard_from_github(self):
        """Download and merge leaderboard data from GitHub."""
        try:
            response = urllib.request.urlopen(LEADERBOARD_GITHUB_URL)
            api_response = json.loads(response.read().decode('utf-8'))

            if "content" in api_response:
                content = base64.b64decode(api_response["content"]).decode('utf-8')
                remote_data = json.loads(content)
            else:
                remote_data = {"sessions": []}
            remote_sessions = remote_data.get("sessions", [])

            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    local_data = json.load(f)
            else:
                local_data = {"sessions": []}
            local_sessions = local_data.get("sessions", [])

            local_timestamps = {s["timestamp"] for s in local_sessions}
            new_sessions = [s for s in remote_sessions if s["timestamp"] not in local_timestamps]

            if not new_sessions:
                messagebox.showinfo("Up to date", "Your leaderboard is already up to date.")
                return

            result = messagebox.askyesno(
                "Update Leaderboard",
                f"Found {len(new_sessions)} new session(s) from GitHub.\n\n"
                f"Do you want to download and merge them with your local data?"
            )

            if result:
                merged_sessions = local_sessions + new_sessions
                merged_sessions.sort(key=lambda s: s["timestamp"], reverse=True)

                local_data["sessions"] = merged_sessions
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(local_data, f, indent=2)

                self._load_data()

                messagebox.showinfo("Success", f"Successfully merged {len(new_sessions)} new session(s).")

        except urllib.error.URLError as e:
            messagebox.showerror("Error", f"Failed to connect to GitHub: {e}\n\nCheck your internet connection and the GitHub URL.")
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Failed to parse data from GitHub. The file may be corrupted.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def _prompt_submit_leaderboard(self):
        """Prompt user to submit their session data to GitHub."""
        if self.github_token:
            result = messagebox.askyesno(
                "Submit to Leaderboard",
                "Do you want to submit your accept session to the global leaderboard?\n\n"
                "The leaderboard is updated monthly. Click 'Update' in the app to download the latest leaderboard data.\n\n"
                "This will automatically submit your data via GitHub API."
            )
            if result:
                self._save_session()
                self._submit_to_github_api()
        else:
            result = messagebox.askyesno(
                "Submit to Leaderboard",
                "Do you want to submit your accept session to the global leaderboard?\n\n"
                "The leaderboard is updated monthly. Click 'Update' in the app to download the latest leaderboard data.\n\n"
                "This will open a GitHub Issue where you can create your data."
            )
            if result:
                self._save_session()
                self._submit_to_github()

    def _submit_to_github_api(self):
        """Submit session data to GitHub via API."""
        try:
            if not os.path.exists(DATA_FILE):
                messagebox.showerror("Error", "No session data found to submit.")
                return

            with open(DATA_FILE, "r", encoding="utf-8") as f:
                local_data = json.load(f)
            local_sessions = local_data.get("sessions", [])

            if not local_sessions:
                messagebox.showerror("Error", "No session data found to submit.")
                return

            latest_session = local_sessions[-1]

            request = urllib.request.Request(
                LEADERBOARD_GITHUB_URL,
                headers={"Authorization": f"token {self.github_token}"}
            )
            response = urllib.request.urlopen(request)
            api_response = json.loads(response.read().decode('utf-8'))

            if "content" in api_response:
                content = base64.b64decode(api_response["content"]).decode('utf-8')
                remote_data = json.loads(content)
            else:
                remote_data = {"sessions": []}

            remote_sessions = remote_data.get("sessions", [])

            if any(s.get("timestamp") == latest_session.get("timestamp") for s in remote_sessions):
                messagebox.showinfo("Info", "This session is already on the leaderboard.")
                return

            remote_sessions.append(latest_session)
            remote_data["sessions"] = remote_sessions

            api_url = "https://api.github.com/repos/kobel-studios/Kobel-vibecode-helper/contents/leaderboard_data.json"
            request = urllib.request.Request(
                api_url,
                headers={"Authorization": f"token {self.github_token}"}
            )
            response = urllib.request.urlopen(request)
            file_info = json.loads(response.read().decode('utf-8'))
            sha = file_info.get("sha")

            updated_content = json.dumps(remote_data, indent=2)
            encoded_content = base64.b64encode(updated_content.encode('utf-8')).decode('utf-8')

            put_data = {
                "message": f"Add session from {self.username}",
                "content": encoded_content,
                "sha": sha
            }

            request = urllib.request.Request(
                api_url,
                data=json.dumps(put_data).encode('utf-8'),
                headers={
                    "Authorization": f"token {self.github_token}",
                    "Content-Type": "application/json"
                },
                method="PUT"
            )
            response = urllib.request.urlopen(request)

            messagebox.showinfo("Success", "Your session has been successfully submitted to the leaderboard!")

        except urllib.error.HTTPError as e:
            if e.code == 401:
                messagebox.showerror("Error", "Invalid GitHub token. Please check your token and try again.")
            elif e.code == 403:
                messagebox.showerror("Error", "GitHub token doesn't have permission to modify the repository. Please ensure your token has 'repo' scope.")
            elif e.code == 404:
                messagebox.showerror("Error", "Repository or file not found. Please check the GitHub URL.")
            else:
                messagebox.showerror("Error", f"GitHub API error: {e.code} - {e.reason}")
        except urllib.error.URLError as e:
            messagebox.showerror("Error", f"Failed to connect to GitHub: {e}\n\nCheck your internet connection.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def _submit_to_github(self):
        """Open GitHub Issues with pre-filled leaderboard data."""
        try:
            if not os.path.exists(DATA_FILE):
                messagebox.showerror("Error", "No session data found to submit.")
                return

            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            sessions = data.get("sessions", [])

            if not sessions:
                messagebox.showerror("Error", "No session data found to submit.")
                return

            latest_session = sessions[-1]

            issue_title = f"Leaderboard submission from {self.username or 'Anonymous'}"
            issue_body = f"""**Username:** {self.username or 'Anonymous'}

**Session Stats:**
- Total Accepts: {latest_session.get('accepts', 0)}
- Duration: {latest_session.get('duration_seconds', 0)} seconds
- Max Accepts/Min: {latest_session.get('max_accepts_per_min', 0)}
- Avg Accepts/Min: {latest_session.get('avg_accepts_per_min', 0)}

**Raw Data:**
```json
{json.dumps(latest_session, indent=2)}
```

Please merge this into the global leaderboard.
"""

            encoded_body = urllib.parse.quote(issue_body)
            encoded_title = urllib.parse.quote(issue_title)

            url = f"{GITHUB_ISSUES_URL}?title={encoded_title}&body={encoded_body}"

            webbrowser.open(url)

            messagebox.showinfo("Opening GitHub", "A browser window will open with your submission ready.\n\nClick 'Submit new issue' to complete the submission.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to prepare submission: {e}")

    def _view_graph(self):
        """Display the accepts per minute graph in a new window."""
        if not self.accept_rate_history:
            messagebox.showinfo("Graph", "No data available yet. Start a session to generate graph data.")
            return
        
        # Create graph window
        graph_window = tk.Toplevel(self.root)
        graph_window.title("Accepts Per Minute Graph")
        graph_window.geometry("800x600")
        graph_window.configure(bg=BG)
        graph_window.transient(self.root)
        
        # Create matplotlib figure with dark theme
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(8, 6), facecolor=BG)
        
        # Extract data
        times = [t[0] for t in self.accept_rate_history]
        rates = [t[1] for t in self.accept_rate_history]
        
        # Plot
        ax.plot(times, rates, color=ACCENT, linewidth=2)
        ax.set_xlabel('Time (seconds)', color=FG)
        ax.set_ylabel('Accepts per Minute', color=FG)
        ax.set_title('Accepts Per Minute Over Time', color=FG, fontsize=14, fontweight='bold')
        ax.tick_params(colors=FG)
        ax.grid(True, alpha=0.3)
        
        # Embed in tkinter
        canvas = FigureCanvasTkAgg(fig, master=graph_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=20)
        
        # Close button
        ttk.Button(graph_window, text="Close", command=graph_window.destroy).pack(pady=10)
        
        # Center window
        graph_window.update_idletasks()
        x = (graph_window.winfo_screenwidth() // 2) - (graph_window.winfo_width() // 2)
        y = (graph_window.winfo_screenheight() // 2) - (graph_window.winfo_height() // 2)
        graph_window.geometry(f"+{x}+{y}")

    def _test_accept(self):
        """Open a test window to test if the clicker can find the Accept All button."""
        test_window = tk.Toplevel(self.root)
        test_window.title("Accept Button Tester")
        test_window.geometry("500x400")
        test_window.configure(bg=BG)
        test_window.transient(self.root)
        
        # Enable test mode (clicks won't count)
        self.test_mode = True
        
        def on_close():
            self.test_mode = False
            test_window.destroy()
        
        test_window.protocol("WM_DELETE_WINDOW", on_close)
        
        # Title
        title = tk.Label(
            test_window,
            text="Accept Button Tester",
            fg=FG,
            bg=BG,
            font=("Segoe UI", 14, "bold")
        )
        title.pack(pady=20)
        
        # Instructions
        instructions = tk.Label(
            test_window,
            text="This will test if the clicker can find your Accept All button image.\n\n"
                   "Make sure your Accept All button is visible on screen,\n"
                   "then click 'Test Detection' below.",
            fg=MUTED,
            bg=BG,
            font=("Segoe UI", 10),
            justify="center"
        )
        instructions.pack(pady=10)
        
        # Show the reference image
        try:
            from PIL import Image, ImageTk, ImageGrab
            if os.path.exists(ACCEPT_BUTTON_IMAGE):
                pil_image = Image.open(ACCEPT_BUTTON_IMAGE)
                pil_image = pil_image.resize((200, 50), Image.Resampling.LANCZOS)
                tk_image = ImageTk.PhotoImage(pil_image)
                image_label = tk.Label(test_window, image=tk_image, bg=BG)
                image_label.image = tk_image  # Keep reference
                image_label.pack(pady=10)
                
                ref_label = tk.Label(test_window, text="Reference image:", fg=MUTED, bg=BG, font=("Segoe UI", 9))
                ref_label.pack()
            else:
                error_label = tk.Label(test_window, text=f"❌ {ACCEPT_BUTTON_IMAGE} not found!", fg="#e74c3c", bg=BG)
                error_label.pack(pady=10)
        except Exception as e:
            error_label = tk.Label(test_window, text=f"❌ Error loading image: {e}", fg="#e74c3c", bg=BG)
            error_label.pack(pady=10)
        
        # Test button
        test_button = tk.Button(
            test_window,
            text="Test Detection",
            bg=ACCENT,
            fg="white",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=30,
            pady=10,
            cursor="hand2",
            command=lambda: self._run_detection_test(test_window)
        )
        test_button.pack(pady=20)
        
        # Result label
        test_window.result_label = tk.Label(
            test_window,
            text="Click 'Test Detection' to begin",
            fg=MUTED,
            bg=BG,
            font=("Segoe UI", 10)
        )
        test_window.result_label.pack(pady=10)
        
        # Close button
        ttk.Button(test_window, text="Close", command=test_window.destroy).pack(pady=10)
        
        # Center window
        test_window.update_idletasks()
        x = (test_window.winfo_screenwidth() // 2) - (test_window.winfo_width() // 2)
        y = (test_window.winfo_screenheight() // 2) - (test_window.winfo_height() // 2)
        test_window.geometry(f"+{x}+{y}")

    def _run_detection_test(self, window):
        """Actually test if the Accept All button can be found on screen."""
        if not os.path.exists(ACCEPT_BUTTON_IMAGE):
            window.result_label.config(text="❌ Image file not found!", fg="#e74c3c")
            return
        
        try:
            # Try to locate the button on screen
            found = pyautogui.locateOnScreen(ACCEPT_BUTTON_IMAGE, confidence=0.8)
            
            if found:
                window.result_label.config(text="✓ Accept All button found on screen!", fg="#3fb950")
                # Optionally show coordinates
                left, top, width, height = found
                window.result_label.config(text=f"✓ Found at ({left}, {top}) size {width}x{height}", fg="#3fb950")
            else:
                window.result_label.config(text="✗ Accept All button not found on screen", fg="#e3b341")
                window.result_label.config(text="✗ Not found - make sure button is visible", fg="#e3b341")
                
        except Exception as e:
            window.result_label.config(text=f"❌ Error: {str(e)}", fg="#e74c3c")


def main():
    # Check if another instance is already running using a simple lock file approach
    lock_file = "vibecode_helper.lock"
    try:
        if os.path.exists(lock_file):
            # Check if the lock file is recent (within 10 seconds)
            lock_time = os.path.getmtime(lock_file)
            if time.time() - lock_time < 10:
                print("Vibe Code Helper is already running. Exiting.")
                return
            else:
                # Lock file is stale, remove it
                os.remove(lock_file)

        # Create lock file
        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))

        root = tk.Tk()
        app = VibeCodeHelper(root)
        root.mainloop()

    finally:
        # Clean up lock file
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except:
                pass


if __name__ == "__main__":
    main()
