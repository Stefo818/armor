from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_context(viewport={"width": 1000, "height": 900}).new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:8765/index.html"); pg.wait_for_timeout(900)
    pg.evaluate("[...document.querySelectorAll('nav button, nav a, .tabs button, [data-tab]')].find(e=>/Grafici/.test(e.textContent)).click()"); pg.wait_for_timeout(1500)
    cv = pg.locator("#cfc").first
    cv.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
    b = cv.bounding_box()
    pg.mouse.move(b["x"] + b["width"] * 0.35, b["y"] + b["height"] * 0.5); pg.wait_for_timeout(300)
    pg.mouse.move(b["x"] + b["width"] * 0.36, b["y"] + b["height"] * 0.5); pg.wait_for_timeout(300)
    pg.screenshot(path="/tmp/tip.png", clip={"x": b["x"], "y": max(0, b["y"] - 10), "width": b["width"], "height": min(b["height"] + 20, 800)})
    print("semafori aperto:", pg.evaluate("!!document.querySelector('details.fold[open] .sgbox')"), "errori:", errs); br.close()
