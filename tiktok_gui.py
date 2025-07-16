import threading, time, random, pandas as pd, os
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

WAIT_RANGE = (3, 6)
LOG_FILE = "bot.log"

def wait_random():
    time.sleep(random.uniform(*WAIT_RANGE))

class TikTokBot(threading.Thread):
    def __init__(self, accounts, targets, logger, controls):
        super().__init__()
        self.accounts = accounts
        self.targets = targets
        self.logger = logger
        self.controls = controls
        self.pause_flag = threading.Event()
        self.stop_flag = threading.Event()
        self.total = len(accounts)

    def log(self, msg):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.logger(f"[{timestamp}] {msg}")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {msg}\n")

    def run(self):
        for idx, (i, acc) in enumerate(self.accounts, start=1):
            if self.stop_flag.is_set(): break
            self.log(f"🔐 Account {idx}/{self.total} – Logging in: {acc['username']}")
            driver = uc.Chrome(options=uc.ChromeOptions().add_argument("--disable-notifications"))
            try:
                if self.login(driver, acc['username'], acc['password']):
                    for target in self.targets:
                        self._check_pause()
                        self.follow_and_like(driver, target)
                        self._check_pause()
                else:
                    self.log(f"❗ Login failed: {acc['username']}")
            finally:
                driver.quit()
            wait_random()
        self.log("✅ Bot run complete.")
        self.controls['on_done']()

    def login(self, driver, username, password):
        driver.get("https://www.tiktok.com/login/phone-or-email/email")
        wait_random()
        try:
            driver.find_element(By.NAME, "username").send_keys(username); wait_random()
            driver.find_element(By.NAME, "password").send_keys(password); wait_random()
            driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
            wait_random(5, 8)
            return True
        except Exception as e:
            self.log(f"❌ Login error for {username}: {e}")
            return False

    def follow_and_like(self, driver, target):
        self.log(f"➡️ Visiting @{target}")
        driver.get(f"https://www.tiktok.com/@{target}")
        wait_random(4, 7)
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Follow')]")
            if btn.text.strip().lower() == "follow":
                btn.click()
                self.log(f"👍 Followed @{target}")
            else:
                self.log(f"✅ Already following @{target}")
            wait_random()
            videos = driver.find_elements(By.XPATH, '//div[@data-e2e="user-post-item"]//a')
            self.log(f"📹 {len(videos)} videos found")
            for v in videos:
                self._check_pause()
                url = v.get_attribute("href")
                driver.get(url); wait_random(3, 5)
                try:
                    like_btn = driver.find_element(By.XPATH, '//span[contains(@class,"like-icon") and not(contains(@class,"liked"))]')
                    like_btn.click()
                    self.log(f"❤️ Liked {url}")
                except Exception:
                    self.log(f"✅ Already liked or unavailable on {url}")
                wait_random()
        except Exception as e:
            self.log(f"⚠️ Error on @{target}: {e}")

    def _check_pause(self):
        while self.pause_flag.is_set():
            if self.stop_flag.is_set(): raise Exception("Stopped")
            time.sleep(0.5)
        if self.stop_flag.is_set(): raise Exception("Stopped")

    def stop(self): self.stop_flag.set()
    def pause(self): self.pause_flag.set()
    def resume(self): self.pause_flag.clear()

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TikTok GUI Bot")
        self.geometry("650x550")
        self.accounts = []
        self.targets = []
        self.bot = None
        self.build()
        if os.path.exists(LOG_FILE): open(LOG_FILE,'a').close()

    def build(self):
        frm = ttk.Frame(self); frm.pack(padx=10, pady=10, fill='x')
        ttk.Button(frm, text="Load Accounts", command=self.load_accounts).pack(side='left', padx=5)
        ttk.Button(frm, text="Load Targets", command=self.load_targets).pack(side='left', padx=5)
        self.acc_var = tk.BooleanVar()
        ttk.Checkbutton(frm, text="Select All Accounts", variable=self.acc_var, command=self.toggle_all).pack(side='left')
        self.listbox = tk.Listbox(self, selectmode=tk.MULTIPLE, height=6); self.listbox.pack(fill='x', padx=10, pady=5)
        btns = ttk.Frame(self); btns.pack(padx=10, pady=5)
        self.start_btn = ttk.Button(btns, text="▶️ Start", command=self.start)
        self.pause_btn = ttk.Button(btns, text="⏸️ Pause", command=self.pause, state='disabled')
        self.stop_btn = ttk.Button(btns, text="⛔ Stop", command=self.stop, state='disabled')
        self.start_btn.pack(side='left', padx=5); self.pause_btn.pack(side='left', padx=5); self.stop_btn.pack(side='left', padx=5)
        self.log = scrolledtext.ScrolledText(self, height=25); self.log.pack(fill='both', padx=10, pady=5)

    def load_accounts(self):
        df = pd.read_csv("accounts.csv")
        self.accounts = list(df.to_dict("records"))
        self.listbox.delete(0,'end')
        for acc in self.accounts: self.listbox.insert('end', acc['username'])
        self.log_msg(f"✅ Loaded {len(self.accounts)} accounts")

    def load_targets(self):
        with open("targets.txt") as f: self.targets = [l.strip() for l in f if l.strip()]
        self.log_msg(f"✅ Loaded {len(self.targets)} targets")

    def toggle_all(self):
        sel = self.acc_var.get()
        if sel: self.listbox.select_set(0,'end')
        else: self.listbox.select_clear(0,'end')

    def start(self):
        sel = self.listbox.curselection()
        if not sel: messagebox.showwarning("Warning","Select at least one account"); return
        accounts = [(i,self.accounts[i]) for i in sel]
        self.bot = TikTokBot(accounts, self.targets, self.log_msg, {'on_done':self.on_done})
        self.bot.start()
        self.start_btn.config(state='disabled')
        self.pause_btn.config(state='normal')
        self.stop_btn.config(state='normal')
        self.log_msg("🚀 Bot started")

    def pause(self):
        self.bot.pause(); self.start_btn.config(state='normal')
        self.pause_btn.config(state='disabled'); self.log_msg("⏸️ Bot paused")

    def stop(self):
        self.bot.stop(); self.log_msg("🛑 Stopping bot...")

    def on_done(self):
        self.start_btn.config(state='normal'); self.pause_btn.config(state='disabled'); self.stop_btn.config(state='disabled')
        self.log_msg("✅ Bot finished")

    def log_msg(self, msg):
        self.log.insert('end', msg+"\n"); self.log.see('end')

if __name__ == "__main__":
    Application().mainloop()
