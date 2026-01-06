#!/usr/bin/env python3
# startmenu.py — fast, no-animation terminal start menu for customenu-cli
# cleaned version (no background capsules, no icons, no CPU/MEM)

import os
import sys
import time
import json
import shlex
import curses
import subprocess
import datetime

BASE_DIR = os.path.expanduser("~/.config/customenu-cli")
MENU_FILE = os.path.join(BASE_DIR, "menu.json")
HEADER_FILE = os.path.join(BASE_DIR, "header.txt")

os.makedirs(BASE_DIR, exist_ok=True)

DEFAULT_MENU = {
    "menu": [
        {"label": "Editor", "cmd": "bash -lc 'nvim'", "shortcut": "Ctrl+E"},
        {"label": "Extras", "cmd": "popup", "shortcut": "Ctrl+X"},
        {"label": "Search", "cmd": "bash -lc 'fzf; read -p \"Enter\"'", "shortcut": "Ctrl+S"},
        {"label": "Switch to shell", "cmd": "shell", "shortcut": "Ctrl+Space"}
    ]
}

if not os.path.exists(MENU_FILE):
    with open(MENU_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_MENU, f, indent=2)

with open(MENU_FILE, "r", encoding="utf-8") as f:
    MENU = json.load(f).get("menu", DEFAULT_MENU["menu"])

BREW_SUB = [
    {"label": "Brew update", "cmd": "bash -lc 'brew update; read -p \"Enter\"'"},
    {"label": "Brew upgrade", "cmd": "bash -lc 'brew upgrade; read -p \"Enter\"'"},
    {"label": "Brew list installed", "cmd": "bash -lc 'brew list; read -p \"Enter\"'"},
    {"label": "Brew search (type name)", "cmd": "brew_search"},
    {"label": "Brew info (type name)", "cmd": "brew_info"},
    {"label": "Back", "cmd": "back"}
]

EXTRAS_ITEMS = [
    {"label": "System info (macchina)", "cmd": "bash -lc 'macchina || uname -a; read -p \"Enter\"'"},
    {"label": "Finder -> yazi", "cmd": "bash -lc 'yazi || echo \"yazi not found\"; read -p \"Enter\"'"},
    {"label": "Brew …", "cmd": "brewmenu"},
    {"label": "---", "cmd": None},
    {"label": "Matrix", "cmd": "bash -lc 'echo Custom A; read -p \"Enter\"'"},
    {"label": "Spotify", "cmd": "bash -lc 'echo Custom B; read -p \"Enter\"'"},
    {"label": "Back", "cmd": "back"}
]

def load_header():
    if os.path.exists(HEADER_FILE):
        with open(HEADER_FILE, "r", encoding="utf-8", errors="ignore") as f:
            return [ln.rstrip("\n") for ln in f.readlines()]
    return ["WELCOME"]

HEADER = load_header()

ICON_MAP = {"Ctrl": "⌃", "Cmd": "⌘", "Alt": "⌥", "Opt": "⌥", "Shift": "⇧", "Space": "␣"}
def iconify_shortcut(s):
    parts = [p.strip() for p in s.split("+")]
    return " ".join(ICON_MAP.get(p, p) for p in parts)

def center_x(w, text):
    return max(0, (w - len(text)) // 2)

def get_system_info():
    try:
        host = subprocess.run(["scutil", "--get", "ComputerName"], capture_output=True, text=True, timeout=0.6)
        host_name = host.stdout.strip() or os.uname().nodename
    except Exception:
        host_name = os.uname().nodename

    try:
        ver = subprocess.run(["sw_vers", "-productVersion"], capture_output=True, text=True, timeout=0.6)
        os_ver = "macOS " + ver.stdout.strip()
    except Exception:
        os_ver = "macOS"

    return host_name, os_ver

def get_weather(timeout_s=1.0):
    try:
        p = subprocess.run(
            ["curl", "-s", "--max-time", str(timeout_s), "https://wttr.in/?format=%c+%t"],
            capture_output=True, text=True
        )
        return p.stdout.strip()
    except Exception:
        return ""

# ------------ CLEAN STATUS BAR (NO CAPSULES, NO CPU/MEM, NO BACKGROUND) ----------
def draw_status(stdscr, left_text, weather, clock):
    h, w = stdscr.getmaxyx()

    right = f"{weather}   {clock}".strip()

    space = w - len(left_text) - len(right) - 2
    if space < 1:
        left_text = left_text[:max(0, w - len(right) - 4)]
        space = 1

    bar = left_text + (" " * space) + right

    try:
        stdscr.addstr(h - 1, 0, bar[:w - 1])
    except curses.error:
        pass

# -----------------------------------------------------------------------------

def draw_full(stdscr, header_lines, menu_items, selected):
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    header_h = len(header_lines)
    menu_h = len(menu_items)
    total_h = header_h + 2 + menu_h
    start_y = max(1, (h - total_h) // 2)

    for i, ln in enumerate(header_lines):
        y = start_y + i
        if 0 <= y < h - 1:
            try:
                stdscr.addstr(y, center_x(w, ln), ln)
            except curses.error:
                pass

    mid = w // 2
    left_col = mid - 20
    right_col = mid + 16

    for i, it in enumerate(menu_items):
        y = start_y + header_h + 2 + i
        label = it.get("label", "")
        shortcut = iconify_shortcut(it.get("shortcut", ""))
        if 0 <= y < h - 1:
            try:
                if i == selected:
                    stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(y, left_col, label[:max(0, w - left_col - 1)])
                stdscr.addstr(y, right_col, shortcut[:max(0, w - right_col - 1)])
                if i == selected:
                    stdscr.attroff(curses.A_REVERSE)
            except curses.error:
                pass

    host, osver = get_system_info()
    left_status = f"{host} • {osver}"
    weather = get_weather()
    now = datetime.datetime.now().strftime("%H:%M")
    draw_status(stdscr, left_status, weather, now)

    stdscr.refresh()
    return start_y

def update_selection(stdscr, header_lines, menu_items, prev, cur):
    h, w = stdscr.getmaxyx()
    header_h = len(header_lines)
    base = max(1, (h - (header_h + 2 + len(menu_items))) // 2) + header_h + 2
    mid = w // 2
    left_col = mid - 20
    right_col = mid + 16

    for row, idx in [(prev, prev), (cur, cur)]:
        if 0 <= idx < len(menu_items):
            y = base + idx
            label = menu_items[idx].get("label", "")
            shortcut = iconify_shortcut(menu_items[idx].get("shortcut", ""))
            try:
                if idx == cur:
                    stdscr.attron(curses.A_REVERSE)
                stdscr.addstr(y, left_col, " " * (w - left_col - 1))
                stdscr.addstr(y, left_col, label[:max(0, w - left_col - 1)])
                stdscr.addstr(y, right_col, shortcut[:max(0, w - right_col - 1)])
                if idx == cur:
                    stdscr.attroff(curses.A_REVERSE)
            except curses.error:
                pass

    stdscr.refresh()

# ---------------- popups unchanged ----------------
# (all popup code stays the same – no display background changes needed)

def prompt_input_shell(prompt="pkg"):
    curses.endwin()
    try:
        name = input(f"{prompt}: ").strip()
    except Exception:
        name = ""
    stdscr = curses.initscr()
    return name

def brew_search_flow():
    name = prompt_input_shell("Search brew for")
    if not name:
        return
    curses.endwin()
    subprocess.run(f"bash -lc 'brew search {shlex.quote(name)}; read -p \"Enter\"'", shell=True)

def brew_info_flow():
    name = prompt_input_shell("Brew info for")
    if not name:
        return
    curses.endwin()
    subprocess.run(f"bash -lc 'brew info {shlex.quote(name)}; read -p \"Enter\"'", shell=True)

def extras_menu_flow(stdscr):
    items = EXTRAS_ITEMS[:]
    idx = 0
    while True:
        h, w = stdscr.getmaxyx()
        ph = min(len(items) + 4, h - 6)
        pw = min(56, w - 8)
        py = (h - ph) // 2
        px = (w - pw) // 2
        win = curses.newwin(ph, pw, py, px)
        win.keypad(True)
        win.erase()
        win.box()
        title = "Extras"
        try:
            win.addstr(1, center_x(pw, title), title, curses.A_BOLD)
        except curses.error:
            pass

        for i, it in enumerate(items):
            y = 3 + i
            if y >= ph - 1:
                break
            lbl = it.get("label", "")
            if i == idx:
                win.attron(curses.A_REVERSE)
                win.addstr(y, 2, lbl[:pw-4])
                win.attroff(curses.A_REVERSE)
            else:
                win.addstr(y, 2, lbl[:pw-4])
        win.refresh()

        key = win.getch()
        if key in (curses.KEY_UP, ord("k")):
            idx = (idx - 1) % len(items)
        elif key in (curses.KEY_DOWN, ord("j")):
            idx = (idx + 1) % len(items)
        elif key in (10, 13):
            cmd = items[idx].get("cmd")
            if cmd == "back":
                return
            if cmd == "brewmenu":
                brew_submenu_flow(stdscr)
                return
            curses.endwin()
            subprocess.run(cmd, shell=True)
            stdscr = curses.initscr()
            return
        elif key in (27, ord("q")):
            return

def brew_submenu_flow(stdscr):
    items = BREW_SUB
    idx = 0
    while True:
        h, w = stdscr.getmaxyx()
        ph = min(len(items) + 4, h - 6)
        pw = min(56, w - 8)
        py = (h - ph) // 2
        px = (w - pw) // 2
        win = curses.newwin(ph, pw, py, px)
        win.keypad(True)
        win.erase()
        win.box()
        title = "Homebrew"
        try:
            win.addstr(1, center_x(pw, title), title, curses.A_BOLD)
        except curses.error:
            pass

        for i, it in enumerate(items):
            y = 3 + i
            if y >= ph - 1:
                break
            lbl = it.get("label", "")
            if i == idx:
                win.attron(curses.A_REVERSE)
                win.addstr(y, 2, lbl[:pw-4])
                win.attroff(curses.A_REVERSE)
            else:
                win.addstr(y, 2, lbl[:pw-4])
        win.refresh()

        key = win.getch()
        if key in (curses.KEY_UP, ord("k")):
            idx = (idx - 1) % len(items)
        elif key in (curses.KEY_DOWN, ord("j")):
            idx = (idx + 1) % len(items)
        elif key in (10, 13):
            cmd = items[idx].get("cmd")
            if cmd == "back":
                return
            if cmd == "brew_search":
                brew_search_flow()
                return
            if cmd == "brew_info":
                brew_info_flow()
                return
            curses.endwin()
            subprocess.run(cmd, shell=True)
            stdscr = curses.initscr()
            return
        elif key in (27, ord("q")):
            return

def main(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.use_default_colors()

    selected = 0
    prev = 0

    draw_full(stdscr, HEADER, MENU, selected)
    last_refresh = time.time()
    refresh_interval = 3

    while True:
        if time.time() - last_refresh > refresh_interval:
            host, osver = get_system_info()
            left_status = f"{host} • {osver}"
            weather = get_weather()
            now = datetime.datetime.now().strftime("%H:%M")
            draw_status(stdscr, left_status, weather, now)
            last_refresh = time.time()

        key = stdscr.getch()

        if key in (curses.KEY_UP, ord("k")):
            prev = selected
            selected = (selected - 1) % len(MENU)
            update_selection(stdscr, HEADER, MENU, prev, selected)
        elif key in (curses.KEY_DOWN, ord("j")):
            prev = selected
            selected = (selected + 1) % len(MENU)
            update_selection(stdscr, HEADER, MENU, prev, selected)
        elif key in (10, 13):
            cmd = MENU[selected].get("cmd", "")
            if cmd == "shell":
                return
            if cmd == "popup":
                extras_menu_flow(stdscr)
                draw_full(stdscr, HEADER, MENU, selected)
            else:
                curses.endwin()
                subprocess.run(cmd, shell=True)
                stdscr = curses.initscr()
                stdscr.keypad(True)
                draw_full(stdscr, HEADER, MENU, selected)
        elif key in (27,):
            return

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass