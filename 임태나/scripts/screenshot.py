from playwright.sync_api import sync_playwright
import time, sys

def capture(output="current_screen.png", tab_index=0):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 400, "height": 900})
        page.goto("http://localhost:8501")
        time.sleep(5)

        # 탭 클릭 (0=진단, 1=상담, 2=약제, 3=이력)
        if tab_index > 0:
            tabs = page.query_selector_all('[data-baseweb="tab"]')
            if len(tabs) > tab_index:
                tabs[tab_index].click()
                time.sleep(2)

        page.screenshot(path=output, full_page=True)
        browser.close()
        print(f"[OK] saved: {output}")

if __name__ == "__main__":
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    out = sys.argv[2] if len(sys.argv) > 2 else "current_screen.png"
    capture(out, idx)
