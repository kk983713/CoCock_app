from playwright.sync_api import sync_playwright
import time
import os
import sqlite3
import sys

# Path to the SQLite DB used by the app. Adjust if your DB is placed elsewhere.
# Use the workspace receipts.db (adjust if your DB is elsewhere).
db_path = '/workspaces/CoCock_app/receipts.db'
BASE = "http://127.0.0.1:8501"
TEST_USER = "e2e_user"
TEST_PASS = "e2e_pass_123"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(20000)
    try:
        page.goto(BASE)
        page.wait_for_load_state("domcontentloaded")

        # Open the sidebar by ensuring it's rendered; Streamlit renders sidebar by default
        # Expand the "アカウント（登録 / ログイン）" expander by clicking its header text
        try:
            # locate expander by text and click
            page.locator("text=アカウント（登録 / ログイン）").first.click()
        except Exception:
            pass

        time.sleep(1)

        # Fill registration fields
        # Try label-based selectors then fallback to placeholder / nth input
        def safe_fill(label_text, value):
            try:
                page.get_by_label(label_text).fill(value)
                return True
            except Exception:
                try:
                    # fallback: try input[placeholder]
                    page.locator(f"input[placeholder=\"{label_text}\"]").fill(value)
                    return True
                except Exception:
                    return False

        ok = safe_fill("新規ユーザー名", TEST_USER)
        ok2 = safe_fill("新規パスワード", TEST_PASS)
        time.sleep(0.5)
        # Click the registration button near the registration area
        # There may be multiple buttons with the same text; pick the first '登録する' button
        try:
            page.locator("button:has-text(\"登録する\")").first.click()
        except Exception as e:
            print("Failed to click register button:", e)

        time.sleep(1)
        page.screenshot(path="/workspaces/CoCock_app/e2e_after_register.png")

        # Now login: fill login_user and login_pass
        ok3 = safe_fill("ユーザー名", TEST_USER)
        ok4 = safe_fill("パスワード", TEST_PASS)
        time.sleep(0.5)
        # Click login button with text 'ログイン'
        try:
            page.locator("button:has-text(\"ログイン\")").first.click()
        except Exception as e:
            print("Failed to click login button:", e)

        time.sleep(1)
        page.screenshot(path="/workspaces/CoCock_app/e2e_after_login.png")

        # Switch to 登録フォーム tab by clicking its tab text
        try:
            page.locator("text=登録フォーム").first.click()
        except Exception:
            pass
        time.sleep(0.5)

        # Fill the dish form: name, memo, tags
        try:
            # find inputs by placeholder or label
            try:
                page.get_by_placeholder("鶏むね肉の照り焼き").fill("E2E Test Dish")
            except Exception:
                # fallback: fill first text input in main area
                page.locator("main input[type='text']").nth(0).fill("E2E Test Dish")
            # memo: textarea
            try:
                page.get_by_placeholder("作った理由や工夫などを書いておけます。").fill("これは E2E テストの投稿です。")
            except Exception:
                page.locator("textarea").first.fill("これは E2E テストの投稿です。")
        except Exception as e:
            print("Failed to fill dish form:", e)

        time.sleep(0.5)
        # Submit the form (button text '登録する' — pick the form submit; use the last matching button)
        try:
            # use nth to pick the last '登録する' (form submit) button
            buttons = page.locator("button:has-text(\"登録する\")")
            count = buttons.count()
            # record max id before submit to later detect newly inserted rows
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
            if count > 0:
                prev_max_id = get_max_dish_id(db_path)
                buttons.nth(count-1).click()
            else:
                print("No register button found for form")
        except Exception as e:
            print("Failed to click form submit:", e)

        time.sleep(2)
        page.screenshot(path="/workspaces/CoCock_app/e2e_after_submit.png")

        # After submit, switch to the listing tab and look for the created entry.
        try:
            page.locator("text=一覧 / 検索").first.click()
        except Exception:
            pass

        # Save final page HTML for debugging regardless
        content = page.content()
        with open('/workspaces/CoCock_app/e2e_page_content.html', 'w', encoding='utf-8') as f:
            f.write(content)

        # DB-based verification (stronger): confirm the created dish both by name
        # and by owner_id (the test user). We'll poll until timeout.
        created_candidates = [
            "E2E Test Dish",
            "E2E Dish",
            "E2E",
        ]

        # Allow more time for DB visibility in CI/slow environments
        timeout = 30
        interval = 1
        # short wait before starting DB polling to reduce race with commit visibility
        time.sleep(2)
        deadline = time.time() + timeout

        def get_user_id(dbfile: str, username: str):
            try:
                conn = sqlite3.connect(dbfile)
                cur = conn.cursor()
                cur.execute("SELECT id FROM users WHERE username = ? LIMIT 1", (username,))
                r = cur.fetchone()
                conn.close()
                return r[0] if r else None
            except Exception as e:
                print(f"E2E: get_user_id error: {e}")
                return None

        def check_db_for_dish(dbfile: str, name: str, owner_id=None) -> bool:
            """Return True if a dish with matching name (and optional owner) was created within the last 5 minutes."""
            try:
                conn = sqlite3.connect(dbfile)
                cur = conn.cursor()
                time_window = "datetime('now', '-5 minutes')"
                if owner_id is not None:
                    cur.execute(
                        "SELECT id FROM dishes WHERE name = ? AND owner_id = ? AND datetime(created_at) >= " + time_window + " ORDER BY id DESC LIMIT 1",
                        (name, owner_id),
                    )
                else:
                    cur.execute(
                        "SELECT id FROM dishes WHERE name = ? AND datetime(created_at) >= " + time_window + " ORDER BY id DESC LIMIT 1",
                        (name,),
                    )
                row = cur.fetchone()
                conn.close()
                return row is not None
            except Exception as e:
                print(f"E2E: DB check error: {e}")
                return False

        # New robust detection: prefer rows with id > prev_max_id (inserted after submit)
        found_name = None
        def get_rows_after(dbfile: str, min_id: int):
            try:
                conn = sqlite3.connect(dbfile)
                cur = conn.cursor()
                # include created_at window as well
                cur.execute("SELECT id, name, owner_id, created_at FROM dishes WHERE id > ? AND datetime(created_at) >= datetime('now', '-5 minutes') ORDER BY id ASC", (min_id,))
                rows = cur.fetchall()
                conn.close()
                return rows
            except Exception as e:
                print(f"E2E: get_rows_after error: {e}")
                return []

        while time.time() < deadline and found_name is None:
            if os.path.exists(db_path):
                user_id = get_user_id(db_path, TEST_USER)
                rows = get_rows_after(db_path, prev_max_id)
                if rows:
                    # inspect new rows and try to match by owner or name
                    for rid, rname, row_owner, created_at in rows:
                        if user_id is not None and row_owner == user_id:
                            found_name = rname
                            break
                        for cand in created_candidates:
                            if cand in (rname or ""):
                                found_name = rname
                                break
                        if found_name:
                            break
            else:
                print(f"E2E: DB file not found at {db_path}, waiting...")
            if found_name:
                break
            time.sleep(interval)

        if found_name:
            print(f"E2E: Submission confirmed in DB (found '{found_name}' in {db_path})")
            sys.exit(0)

        # As a fallback, check the saved HTML once more for debugging
        page_content_path = os.path.join(os.getcwd(), 'e2e_page_content.html')
        if os.path.exists(page_content_path):
            with open(page_content_path, 'r', encoding='utf-8') as f:
                html = f.read()
                for cand in created_candidates:
                    if cand in html:
                        print(f"E2E: Submission appears in saved HTML fallback (found '{cand}') - but DB check failed")
                        sys.exit(1)

        print("E2E: Could not confirm submission (DB check timed out); check screenshots and saved HTML")
        sys.exit(2)

    finally:
        browser.close()

    print("E2E script finished")
