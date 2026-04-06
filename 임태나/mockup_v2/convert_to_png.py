"""mockup_v2 HTML → PNG 변환. 실행: python mockup_v2/convert_to_png.py"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import time

def convert_all():
    mockup_dir = Path(__file__).parent
    html_files = sorted(mockup_dir.glob("*.html"))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for f in html_files:
            page = browser.new_page(viewport={"width": 400, "height": 800})
            page.goto(f"file:///{f.resolve()}")
            time.sleep(1)
            phone = page.query_selector(".ph")
            if phone:
                phone.screenshot(path=str(f.with_suffix(".png")))
            else:
                page.screenshot(path=str(f.with_suffix(".png")))
            page.close()
            print(f"✅ {f.name} → {f.with_suffix('.png').name}")
        browser.close()
    print(f"\n완료: {len(html_files)}개 PNG 생성")

if __name__ == "__main__":
    convert_all()
