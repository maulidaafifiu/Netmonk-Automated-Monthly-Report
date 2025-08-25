from playwright.sync_api import sync_playwright
import os
from datetime import datetime

def screenshot_specific_element_playwright(
    url, selector, output_file=None, folder_name='screenshots',
    wait_time=15, tab=None, wait_for=None
):
    if output_file is None:
        os.makedirs(folder_name, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m% d_%H%M%S")
        output_file = os.path.join(folder_name, f"dashboard_{timestamp}.png")
    else:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        page.goto(url)
        # apply_date_filter_last_month(page)
        
        page.wait_for_timeout(wait_time * 1000)

        # Klik tab jika diminta
        if tab:
            try:
                print(f"👉 Klik tab: {tab}")
                page.click(tab, timeout=10000)
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"⚠️ Tidak bisa klik tab {tab}: {e}")

        # Tunggu elemen tertentu jika diminta
        if wait_for:
            try:
                print(f"⏳ Menunggu munculnya: {wait_for}")
                page.wait_for_selector(wait_for, timeout=10000)
            except Exception as e:
                print(f"⚠️ Teks '{wait_for}' tidak muncul: {e}")

        # Screenshot elemen utama
        try:
            element = page.locator(selector)
            element.wait_for(state="visible", timeout=10000)

            # Pastikan tidak blur
            page.wait_for_function(
                """(selector) => {
                    const el = document.querySelector(selector);
                    if (!el) return false;
                    const style = window.getComputedStyle(el);
                    return style.opacity === '1' && style.filter === 'none';
                }""",
                arg=selector,
                timeout=10000
            )

            page.wait_for_timeout(2000)
            element.screenshot(path=output_file)
            print(f"✅ Screenshot elemen berhasil disimpan: {output_file}")

        except Exception as e:
            print(f"❌ Gagal screenshot elemen: {e}")
        finally:
            browser.close()

