import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 400, "height": 900})
    page.goto("http://localhost:8501")
    time.sleep(5)
    tabs = page.query_selector_all('[data-baseweb="tab"]')
    if len(tabs) > 1:
        tabs[1].click()
        time.sleep(2)

    result = page.evaluate("""() => {
        const btn = document.querySelector('button[data-testid="stBaseButton-segmented_controlActive"]');
        if (!btn) return "btn not found";
        let el = btn;
        let chain = [];
        for (let i = 0; i < 6; i++) {
            el = el.parentElement;
            if (!el) break;
            const tid = el.getAttribute('data-testid') || '';
            const cls = el.className.substring(0, 60);
            chain.push(`${el.tagName} testid=${tid} class=${cls}`);
        }
        return chain.join('\\n');
    }""")
    print(result)
    browser.close()
