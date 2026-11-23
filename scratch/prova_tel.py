from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_context(viewport={"width": 400, "height": 860}, device_scale_factor=2, has_touch=True, is_mobile=True).new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:8765/index.html"); pg.wait_for_timeout(900)
    pg.evaluate("[...document.querySelectorAll('nav button, nav a, .tabs button, [data-tab]')].find(e=>/Grafici/.test(e.textContent)).click()"); pg.wait_for_timeout(1500)
    pg.evaluate("document.querySelector('.cfstrip').scrollIntoView({block:'start'})"); pg.wait_for_timeout(300)
    b = pg.locator("#cfc").first.bounding_box()
    pg.touchscreen.tap(b["x"] + b["width"] * 0.5, b["y"] + b["height"] * 0.5); pg.wait_for_timeout(400)
    pg.screenshot(path="/tmp/tel.png"); print("errori:", errs); br.close()
