from playwright.sync_api import sync_playwright
import time
import os
import sqlite3
import sys

BASE = "http://127.0.0.1:8501"
TEST_USER = "e2e_user"
TEST_PASS = "e2e_pass_123"
DB_PATH = '/workspaces/CoCock_app/receipts.db'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(20000)
    try:
        page.goto(BASE)
        page.wait_for_load_state("domcontentloaded")
        time.sleep(1)
        # Open account expander in sidebar and perform a UI login using seeded test user
        try:
            page.locator("text=アカウント（登録 / ログイン）").first.click()
        except Exception:
            pass
        time.sleep(0.5)
        # Fill login fields using label-based selectors if available
        try:
            page.get_by_label("ユーザー名").fill(TEST_USER)
        except Exception:
            try:
                page.locator("input[placeholder='ユーザー名']").fill(TEST_USER)
            except Exception:
                # fallback: try the first text input in sidebar
                try:
                    page.locator("aside input[type='text']").first.fill(TEST_USER)
                except Exception:
                    pass
        try:
            page.get_by_label("パスワード").fill(TEST_PASS)
        except Exception:
            try:
                page.locator("input[type='password']").first.fill(TEST_PASS)
            except Exception:
                pass
        time.sleep(0.2)
        try:
            page.locator("button:has-text(\"ログイン\")").first.click()
        except Exception as e:
            print('login click failed', e)
        time.sleep(1)
        page.screenshot(path="/workspaces/CoCock_app/e2e_after_login2.png")
        # Switch to 登録フォーム tab
        try:
            page.locator("text=登録フォーム").first.click()
        except Exception:
            pass
        time.sleep(0.5)
        # Fill minimal dish data
        try:
            page.locator("input[placeholder='鶏むね肉の照り焼き']").fill("E2E Dish")
        except Exception:
            try:
                page.locator("main input[type='text']").nth(0).fill("E2E Dish")
            except Exception as e:
                print('fill name failed', e)
        try:
            page.locator("textarea").first.fill("E2E memo")
        except Exception as e:
            print('fill memo failed', e)
        time.sleep(0.5)
        # Submit the form: click last 登録する button and use max-id detection to find newly inserted rows
        try:
            buttons = page.locator("button:has-text(\"登録する\")")
            count = buttons.count()
            if count > 0:
                buttons.nth(count-1).click()
            else:
                print('no submit button')
        except Exception as e:
            print('submit click failed', e)
        time.sleep(2)
        page.screenshot(path="/workspaces/CoCock_app/e2e_after_submit2.png")
        content = page.content()
        with open('/workspaces/CoCock_app/e2e_page_content2.html','w',encoding='utf-8') as f:
            f.write(content)

        # New robust detection: capture prev max id before submit and poll for id > prev_max
        candidates = ["E2E Dish", "E2E Test Dish", "E2E"]

        def get_user_id(dbfile: str, username: str):
            try:
                conn = sqlite3.connect(dbfile)
                cur = conn.cursor()
                cur.execute("SELECT id FROM users WHERE username = ? LIMIT 1", (username,))
                r = cur.fetchone()
                conn.close()
                return r[0] if r else None
            except Exception as e:
                print('get_user_id error', e)
                return None

        def get_rows_after(dbfile: str, min_id: int):
            try:
                conn = sqlite3.connect(dbfile)
                cur = conn.cursor()
                cur.execute("SELECT id, name, owner_id, created_at FROM dishes WHERE id > ? AND datetime(created_at) >= datetime('now', '-5 minutes') ORDER BY id ASC", (min_id,))
                rows = cur.fetchall()
                conn.close()
                return rows
            except Exception as e:
                print(f"E2E: get_rows_after error: {e}")
                return []

        # capture prev_max (best-effort if we didn't capture before clicking)
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT MAX(id) FROM dishes")
            r = cur.fetchone()
            conn.close()
            prev_max = r[0] or 0
        except Exception:
            prev_max = 0

        # poll for new rows with id > prev_max
        timeout = 15
        deadline = time.time() + timeout
        found = None
        while time.time() < deadline and found is None:
            if os.path.exists(DB_PATH):
                user_id = get_user_id(DB_PATH, TEST_USER)
                rows = get_rows_after(DB_PATH, prev_max)
                if rows:
                    for rid, rname, row_owner, created_at in rows:
                        if user_id is not None and row_owner == user_id:
                            found = rname
                            break
                        for cand in candidates:
                            if cand in (rname or ""):
                                found = rname
                                break
                        if found:
                            break
            else:
                print(f"DB not found at {DB_PATH}, waiting...")
            if found:
                break
            time.sleep(1)

        if found:
            print(f"Submission confirmed in DB (found '{found}')")
            sys.exit(0)

        # fallback: check saved HTML
        if any(c in content for c in candidates):
            print('Submission appears in saved HTML fallback')
            sys.exit(1)

        print('Submission not confirmed; check artifacts')
        sys.exit(2)
        # click submit and use max-id detection to find newly inserted rows
        try:
            submit = page.locator("button:has-text(\"保存する\")")
            # capture current max id before clicking
            def get_max_dish_id(dbfile: str) -> int:
                try:
                    conn = sqlite3.connect(dbfile)
                    cur = conn.cursor()
                    cur.execute("SELECT MAX(id) FROM dishes")
                    r = cur.fetchone()
                    conn.close()
                    return r[0] or 0
                except Exception:
                    return 0

            prev_max_id = get_max_dish_id(DB_PATH)
            submit.first.click()
        except Exception as e:
            print("Failed to click save button:", e)

        # wait for DB confirmation using id > prev_max_id and created_at window
        found = False
        deadline = time.time() + timeout
        def get_rows_after(dbfile: str, min_id: int):
            try:
                conn = sqlite3.connect(dbfile)
                cur = conn.cursor()
                cur.execute("SELECT id, name, owner_id, created_at FROM dishes WHERE id > ? AND datetime(created_at) >= datetime('now', '-5 minutes') ORDER BY id ASC", (min_id,))
                rows = cur.fetchall()
                conn.close()
                return rows
            except Exception as e:
                print(f"E2E: get_rows_after error: {e}")
                return []

        while time.time() < deadline and not found:
            if os.path.exists(DB_PATH):
                user_id = get_user_id(DB_PATH, TEST_USER)
                rows = get_rows_after(DB_PATH, prev_max_id)
                if rows:
                    for rid, rname, row_owner, created_at in rows:
                        if user_id is not None and row_owner == user_id:
                            found = True
                            break
                        if dish_name in (rname or ""):
                            found = True
                            break
                    if found:
                        break
            time.sleep(1)
    finally:
        browser.close()
    print('done')
