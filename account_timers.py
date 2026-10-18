"""Account Timers - countdowns or daily clock-time reminders for your accounts, with a popup when time is up."""
import json
import os
import time
import uuid
import tkinter as tk
from datetime import datetime, timedelta
from tkinter import ttk, messagebox

APP_NAME = "Account Timers"
DATA_FILE = os.path.join(os.path.expanduser("~"), ".account_timers.json")

# ---- dark "editor" palette ----
BG, PANEL, FIELD, BTN = "#1e1e1e", "#252526", "#2d2d30", "#333337"
BORDER, FG, MUTED = "#3c3c3c", "#d4d4d4", "#858585"
ACCENT, ACCENT_BTN, SEL = "#569cd6", "#0e639c", "#094771"
GREEN, YELLOW, RED = "#4ec9b0", "#dcdcaa", "#f48771"
READY_BG = "#3b2020"
UI_FONT, MONO_FONT = ("Segoe UI", 10), ("Consolas", 10)
SOON = 10 * 60  # "Almost" when under 10 minutes are left


# ---------- time helpers ----------
def fmt(seconds):
    seconds = max(0, int(seconds))
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    return ("%dd " % d if d else "") + "%02d:%02d:%02d" % (h, m, s)


def fmt_length(seconds):
    d, rem = divmod(int(seconds), 86400)
    h, rem = divmod(rem, 3600)
    m, sec = divmod(rem, 60)
    parts = []
    if d:
        parts.append("%dd" % d)
    if h:
        parts.append("%dh" % h)
    if m:
        parts.append("%dm" % m)
    if sec or not parts:
        parts.append("%ds" % sec)
    return " ".join(parts)


def next_clock(clock, now=None):
    """Next time (epoch seconds) the computer's clock shows HH:MM:SS."""
    now = now or datetime.now()
    h, m, s = (int(x) for x in clock.split(":"))
    target = now.replace(hour=h, minute=m, second=s, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target.timestamp()


def schedule(a):
    """Work out when this account's timer ends, starting from now."""
    if a["mode"] == "clock":
        return next_clock(a["clock"])
    return time.time() + a["length"]


def describe(a):
    if a["mode"] == "countdown":
        return fmt_length(a["length"])
    c = a["clock"][:-3] if a["clock"].endswith(":00") else a["clock"]
    return ("Daily " if a["repeat"] else "At ") + c


def dark_titlebar(win):
    """Dark title bar on Windows 10/11 (silently skipped elsewhere)."""
    try:
        import ctypes
        win.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        val = ctypes.c_int(1)
        for attr in (20, 19):
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(val), 4) == 0:
                break
    except Exception:
        pass


def apply_theme(root):
    root.configure(bg=BG)
    st = ttk.Style(root)
    st.theme_use("clam")
    st.configure(".", background=BG, foreground=FG, fieldbackground=FIELD, bordercolor=BORDER,
                 lightcolor=BG, darkcolor=BG, troughcolor=PANEL, focuscolor=BG, font=UI_FONT)
    st.configure("TFrame", background=BG)
    st.configure("TLabel", background=BG, foreground=FG)
    st.configure("Muted.TLabel", foreground=MUTED)
    st.configure("Clock.TLabel", foreground=ACCENT, font=("Consolas", 12, "bold"))
    st.configure("Next.TLabel", foreground=GREEN, font=MONO_FONT)

    st.configure("TButton", background=BTN, foreground=FG, bordercolor=BORDER, padding=(12, 5), relief="flat")
    st.map("TButton", background=[("disabled", PANEL), ("pressed", SEL), ("active", "#3e3e42")],
           foreground=[("disabled", "#5a5a5a")])
    st.configure("Accent.TButton", background=ACCENT_BTN, foreground="#ffffff", bordercolor=ACCENT_BTN)
    st.map("Accent.TButton", background=[("pressed", SEL), ("active", "#1177bb")])

    for w in ("TEntry", "TCombobox", "TSpinbox"):
        st.configure(w, fieldbackground=FIELD, foreground=FG, insertcolor=FG, bordercolor=BORDER,
                     background=BTN, arrowcolor=FG, selectbackground=SEL, selectforeground="#ffffff", padding=4)
    st.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", FG)])
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", SEL)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")

    for w in ("TCheckbutton", "TRadiobutton"):
        st.configure(w, background=BG, foreground=FG, indicatorcolor=FIELD, indicatorbackground=FIELD,
                     indicatorforeground="#ffffff", upperbordercolor=BORDER, lowerbordercolor=BORDER)
        st.map(w, background=[("active", BG)], indicatorcolor=[("selected", ACCENT_BTN)],
               indicatorbackground=[("selected", ACCENT_BTN), ("active", "#3e3e42")])

    st.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG, bordercolor=BORDER,
                 rowheight=30, font=MONO_FONT, borderwidth=0)
    st.map("Treeview", background=[("selected", SEL)], foreground=[("selected", "#ffffff")])
    st.configure("Treeview.Heading", background=FIELD, foreground=MUTED, relief="flat",
                 font=("Segoe UI", 9, "bold"), padding=(6, 5))
    st.map("Treeview.Heading", background=[("active", "#37373d")])
    st.configure("Vertical.TScrollbar", background="#424242", troughcolor=PANEL, arrowcolor=FG,
                 bordercolor=PANEL)
    st.map("Vertical.TScrollbar", background=[("active", "#5a5a5a")])


class AccountDialog(tk.Toplevel):
    """Add or edit an account. self.result is set when the user presses Save."""

    def __init__(self, parent, names, account=None):
        super().__init__(parent)
        self.configure(bg=BG)
        self.result = None
        self._job = None
        self.editing = account is not None
        self.title("Edit account" if self.editing else "Add account")
        self.resizable(False, False)
        self.transient(parent)

        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Account name").grid(row=0, column=0, sticky="w")
        self.name = tk.StringVar(value=account["name"] if account else "")
        self.combo = ttk.Combobox(body, textvariable=self.name, values=sorted(names, key=str.lower), width=34)
        self.combo.grid(row=1, column=0, sticky="we", pady=(2, 12))

        ttk.Label(body, text="Timer type").grid(row=2, column=0, sticky="w")
        self.mode = tk.StringVar(value=account["mode"] if account else "countdown")
        modes = ttk.Frame(body)
        modes.grid(row=3, column=0, sticky="w", pady=(2, 10))
        ttk.Radiobutton(modes, text="Countdown (length)", value="countdown", variable=self.mode,
                        command=self.switch).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(modes, text="At a clock time", value="clock", variable=self.mode,
                        command=self.switch).pack(side="left")

        # --- countdown settings ---
        self.f_count = ttk.Frame(body)
        length = account["length"] if account and account["mode"] == "countdown" else 0
        d, rem = divmod(length, 86400)
        h, rem = divmod(rem, 3600)
        m, s = divmod(rem, 60)
        self.d, self.h, self.m, self.s = (tk.StringVar(value=str(v)) for v in (d, h, m, s))
        for var, lbl in ((self.d, "days"), (self.h, "hours"), (self.m, "min"), (self.s, "sec")):
            ttk.Spinbox(self.f_count, from_=0, to=999, width=4, textvariable=var).pack(side="left")
            ttk.Label(self.f_count, text=lbl, style="Muted.TLabel").pack(side="left", padx=(4, 12))

        # --- clock-time settings ---
        self.f_clock = ttk.Frame(body)
        if account and account["mode"] == "clock":
            hh, mm, ss = account["clock"].split(":")
        else:
            soon = datetime.now() + timedelta(minutes=1)
            hh, mm, ss = "%02d" % soon.hour, "%02d" % soon.minute, "00"
        self.ch, self.cm, self.cs = tk.StringVar(value=hh), tk.StringVar(value=mm), tk.StringVar(value=ss)
        row = ttk.Frame(self.f_clock)
        row.pack(anchor="w")
        for i, (var, top) in enumerate(((self.ch, 23), (self.cm, 59), (self.cs, 59))):
            if i:
                ttk.Label(row, text=":", font=("Consolas", 12, "bold")).pack(side="left", padx=3)
            ttk.Spinbox(row, from_=0, to=top, width=3, wrap=True, format="%02.0f",
                        textvariable=var).pack(side="left")
            var.trace_add("write", lambda *_a: self.update_preview())
        ttk.Label(row, text="  (24-hour, your computer's clock)", style="Muted.TLabel").pack(side="left")
        self.repeat = tk.BooleanVar(value=account["repeat"] if account else True)
        ttk.Checkbutton(self.f_clock, text="Repeat every day (re-arms itself automatically)",
                        variable=self.repeat).pack(anchor="w", pady=(10, 6))
        self.pc_label = ttk.Label(self.f_clock, style="Muted.TLabel")
        self.pc_label.pack(anchor="w")
        self.next_label = ttk.Label(self.f_clock, style="Next.TLabel")
        self.next_label.pack(anchor="w", pady=(2, 0))

        self.remember = tk.BooleanVar(value=True)
        ttk.Checkbutton(body, text="Remember this name for next time", variable=self.remember
                        ).grid(row=5, column=0, sticky="w", pady=(14, 0))
        self.restart = tk.BooleanVar(value=True)
        if self.editing:
            ttk.Checkbutton(body, text="Restart the timer now", variable=self.restart
                            ).grid(row=6, column=0, sticky="w", pady=(4, 0))

        btns = ttk.Frame(body)
        btns.grid(row=7, column=0, sticky="e", pady=(18, 0))
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(btns, text="Save", style="Accent.TButton", command=self.save).pack(side="right", padx=8)

        self.switch()
        self.bind("<Return>", lambda _e: self.save())
        self.bind("<Escape>", lambda _e: self.destroy())
        dark_titlebar(self)
        self.update_idletasks()
        self.geometry("+%d+%d" % (parent.winfo_rootx() + 60, parent.winfo_rooty() + 50))
        self.combo.focus_set()
        self.grab_set()
        self._tick()

    def switch(self):
        if self.mode.get() == "clock":
            self.f_count.grid_remove()
            self.f_clock.grid(row=4, column=0, sticky="w")
        else:
            self.f_clock.grid_remove()
            self.f_count.grid(row=4, column=0, sticky="w")

    def clock_text(self):
        return "%02d:%02d:%02d" % (int(self.ch.get()), int(self.cm.get()), int(self.cs.get()))

    def update_preview(self):
        self.pc_label.configure(text="Computer time now:  " + datetime.now().strftime("%H:%M:%S"))
        try:
            clock = self.clock_text()
            when = next_clock(clock)
            self.next_label.configure(text="Next reminder:  %s   (in %s)" % (
                datetime.fromtimestamp(when).strftime("%a %d %b, %H:%M:%S"), fmt(when - time.time())))
        except ValueError:
            self.next_label.configure(text="Next reminder:  -")

    def _tick(self):
        self.update_preview()
        self._job = self.after(1000, self._tick)

    def destroy(self):
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        super().destroy()

    def save(self):
        name = self.name.get().strip()
        if not name:
            messagebox.showwarning(APP_NAME, "Please enter an account name.", parent=self)
            return
        mode, length, clock = self.mode.get(), 86400, "00:00:00"
        try:
            if mode == "countdown":
                length = (int(self.d.get()) * 86400 + int(self.h.get()) * 3600
                          + int(self.m.get()) * 60 + int(self.s.get()))
                if length <= 0:
                    messagebox.showwarning(APP_NAME, "The timer must be longer than zero.", parent=self)
                    return
            else:
                if not (0 <= int(self.ch.get()) <= 23 and 0 <= int(self.cm.get()) <= 59
                        and 0 <= int(self.cs.get()) <= 59):
                    raise ValueError
                clock = self.clock_text()
        except ValueError:
            messagebox.showwarning(APP_NAME, "Please enter valid whole numbers for the time.", parent=self)
            return
        self.result = {"name": name, "mode": mode, "length": length, "clock": clock,
                       "repeat": self.repeat.get(), "remember": self.remember.get(),
                       "restart": self.restart.get()}
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("700x460")
        self.minsize(580, 340)
        apply_theme(self)
        dark_titlebar(self)
        self.accounts, self.names = self.load()

        # toolbar
        bar = ttk.Frame(self, padding=(12, 12, 12, 6))
        bar.pack(fill="x")
        ttk.Button(bar, text="+  Add account", style="Accent.TButton", command=self.add).pack(side="left")
        self.btn_edit = ttk.Button(bar, text="Edit", command=self.edit)
        self.btn_restart = ttk.Button(bar, text="Restart timer", command=self.restart_selected)
        self.btn_delete = ttk.Button(bar, text="Delete", command=self.delete)
        for b in (self.btn_edit, self.btn_restart, self.btn_delete):
            b.pack(side="left", padx=(6, 0))
        self.pc_clock = ttk.Label(bar, style="Clock.TLabel")
        self.pc_clock.pack(side="right")

        # table
        frame = ttk.Frame(self, padding=(12, 4))
        frame.pack(fill="both", expand=True)
        cols = ("name", "timer", "left", "status")
        self.tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        for c, t, w, stretch in (("name", "Account", 200, True), ("timer", "Timer", 130, False),
                                 ("left", "Time left", 130, False), ("status", "Status", 100, False)):
            self.tree.heading(c, text=t, anchor="w")
            self.tree.column(c, width=w, anchor="w", stretch=stretch)
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.tag_configure("running", foreground=GREEN)
        self.tree.tag_configure("soon", foreground=YELLOW)
        self.tree.tag_configure("ready", foreground=RED, background=READY_BG)

        self.hint = ttk.Label(self.tree, style="Muted.TLabel", justify="center", background=PANEL,
                              text="No accounts yet.\nClick  + Add account  to create your first timer.")
        self.status = ttk.Label(self, style="Muted.TLabel", padding=(14, 6))
        self.status.pack(fill="x")

        # context menu + shortcuts
        self.menu = tk.Menu(self, tearoff=0, bg=PANEL, fg=FG, activebackground=SEL,
                            activeforeground="#ffffff", bd=0, relief="flat")
        self.menu.add_command(label="Edit", command=self.edit)
        self.menu.add_command(label="Restart timer", command=self.restart_selected)
        self.menu.add_separator()
        self.menu.add_command(label="Delete", command=self.delete)
        self.tree.bind("<Button-3>", self.right_click)
        self.tree.bind("<Double-1>", lambda _e: self.edit())
        self.tree.bind("<Return>", lambda _e: self.edit())
        self.tree.bind("<Delete>", lambda _e: self.delete())
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.update_buttons())

        self.refresh()
        self.tick()

    # ---------- storage ----------
    def load(self):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return [], []
        if isinstance(data, list):  # oldest file format
            data = {"accounts": data, "names": []}
        accounts = []
        for a in data.get("accounts", []):
            try:
                mode = a.get("mode", "countdown")
                clock = a.get("clock", "00:00:00")
                if mode == "clock":
                    next_clock(clock)  # validates the format
                accounts.append({"id": a.get("id") or uuid.uuid4().hex, "name": str(a["name"]),
                                 "mode": "clock" if mode == "clock" else "countdown",
                                 "length": int(a["length"]), "clock": clock,
                                 "repeat": bool(a.get("repeat", False)),
                                 "ends_at": float(a["ends_at"]), "notified": bool(a.get("notified", False))})
            except (KeyError, TypeError, ValueError, AttributeError):
                continue
        return accounts, [str(n) for n in data.get("names", [])]

    def save(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump({"accounts": self.accounts, "names": self.names}, f, indent=2)
        except OSError:
            pass

    # ---------- helpers ----------
    def selected(self):
        sel = self.tree.selection()
        return next((a for a in self.accounts if a["id"] == sel[0]), None) if sel else None

    def remember(self, name):
        if name.lower() not in (n.lower() for n in self.names):
            self.names.append(name)

    def right_click(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.menu.tk_popup(event.x_root, event.y_root)

    def update_buttons(self):
        state = "normal" if self.selected() else "disabled"
        for b in (self.btn_edit, self.btn_restart, self.btn_delete):
            b.configure(state=state)

    # ---------- actions ----------
    def add(self):
        dlg = AccountDialog(self, self.names)
        self.wait_window(dlg)
        r = dlg.result
        if not r:
            return
        a = {"id": uuid.uuid4().hex, "name": r["name"], "mode": r["mode"], "length": r["length"],
             "clock": r["clock"], "repeat": r["repeat"], "notified": False}
        a["ends_at"] = schedule(a)
        self.accounts.append(a)
        if r["remember"]:
            self.remember(r["name"])
        self.save()
        self.refresh()

    def edit(self):
        a = self.selected()
        if not a:
            return
        dlg = AccountDialog(self, self.names, a)
        self.wait_window(dlg)
        r = dlg.result
        if not r:
            return
        changed = r["mode"] != a["mode"] or (r["mode"] == "clock" and r["clock"] != a["clock"])
        a.update(name=r["name"], mode=r["mode"], length=r["length"], clock=r["clock"], repeat=r["repeat"])
        if r["restart"] or changed:
            a["ends_at"], a["notified"] = schedule(a), False
        if r["remember"]:
            self.remember(r["name"])
        self.save()
        self.refresh()

    def restart_account(self, a):
        a["ends_at"], a["notified"] = schedule(a), False
        self.save()
        self.refresh()

    def restart_selected(self):
        a = self.selected()
        if a:
            self.restart_account(a)

    def delete(self):
        a = self.selected()
        if a and messagebox.askyesno(APP_NAME, "Delete '%s'?\n\nThe name stays in your remembered names." % a["name"]):
            self.accounts.remove(a)
            self.save()
            self.refresh()

    # ---------- display ----------
    def refresh(self):
        self.pc_clock.configure(text=datetime.now().strftime("%H:%M:%S"))
        sel = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        now = time.time()
        ready = 0
        for a in sorted(self.accounts, key=lambda x: x["ends_at"]):
            left = a["ends_at"] - now
            if left <= 0:
                ready += 1
                tag, status, shown = "ready", "Reset now", "00:00:00"
            elif left < SOON:
                tag, status, shown = "soon", "Almost", fmt(left)
            else:
                tag, status, shown = "running", "Running", fmt(left)
            self.tree.insert("", "end", iid=a["id"], tags=(tag,),
                             values=(a["name"], describe(a), shown, status))
        if sel and self.tree.exists(sel[0]):
            self.tree.selection_set(sel[0])
        if self.accounts:
            self.hint.place_forget()
        else:
            self.hint.place(relx=0.5, rely=0.45, anchor="center")
        n = len(self.accounts)
        self.status.configure(text="%d account%s   \u2022   %d ready to reset" % (n, "" if n == 1 else "s", ready)
                              if n else "Your timers are saved automatically.")
        self.update_buttons()

    def tick(self):
        now = time.time()
        for a in list(self.accounts):
            if a["ends_at"] <= now and not a["notified"]:
                auto = a["mode"] == "clock" and a["repeat"]
                if auto:  # re-arm for the next day by itself
                    a["ends_at"] = next_clock(a["clock"])
                else:
                    a["notified"] = True
                self.save()
                self.popup(a, auto)
        self.refresh()
        self.after(1000, self.tick)

    def popup(self, a, auto):
        win = tk.Toplevel(self)
        win.configure(bg=BG)
        win.title("Time's up")
        win.attributes("-topmost", True)
        win.resizable(False, False)
        body = ttk.Frame(win, padding=28)
        body.pack()
        ttk.Label(body, text=a["name"], font=("Segoe UI", 17, "bold"), foreground=RED).pack()
        ttk.Label(body, text="Time is up. Time to reset this account!").pack(pady=(6, 4))
        if auto:
            ttk.Label(body, text="Next reminder: " + datetime.fromtimestamp(a["ends_at"]).strftime("%a %d %b, %H:%M"),
                      style="Muted.TLabel").pack()
        row = ttk.Frame(body)
        row.pack(pady=(18, 0))
        if not auto:
            ttk.Button(row, text="Restart timer", style="Accent.TButton",
                       command=lambda: (self.restart_account(a), win.destroy())).pack(side="left", padx=4)
        ttk.Button(row, text="OK", command=win.destroy).pack(side="left", padx=4)
        dark_titlebar(win)
        win.update_idletasks()
        win.geometry("+%d+%d" % ((win.winfo_screenwidth() - win.winfo_width()) // 2,
                                 (win.winfo_screenheight() - win.winfo_height()) // 3))
        win.bell()
        win.lift()
        win.focus_force()


if __name__ == "__main__":
    App().mainloop()
