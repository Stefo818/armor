from playwright.sync_api import sync_playwright
import sys
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 400, "height": 820}, device_scale_factor=2, has_touch=True, is_mobile=True)
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto("file:///home/claude/armor/site/index.html"); pg.wait_for_timeout(800)
    pg.locator("[data-gi='crollo']").first.scroll_into_view_if_needed()
    pg.locator("[data-gi='crollo']").first.click(position={"x": 30, "y": 20}); pg.wait_for_timeout(700)
    pg.screenshot(path="/tmp/g1.png")
    for i, name in ((7, "max"), (4, "1a")):
        pg.locator(".gi-rg button").nth(i).click(); pg.wait_for_timeout(900); pg.screenshot(path=f"/tmp/g_{name}.png")
    # pan con un dito e pinch via CDP
    cv = pg.locator("#gi-cv"); bb = cv.bounding_box(); cy = bb["y"] + bb["height"] / 2; cx = bb["x"] + bb["width"] / 2
    cdp = ctx.new_cdp_session(pg)
    def touch(t, pts): cdp.send("Input.dispatchTouchEvent", {"type": t, "touchPoints": [{"x": x, "y": y, "id": i} for i, (x, y) in enumerate(pts)]})
    pg.locator(".gi-rg button").nth(4).click(); pg.wait_for_timeout(600)
    touch("touchStart", [(cx - 20, cy), (cx + 20, cy)])
    for k in range(1, 11): touch("touchMove", [(cx - 20 - k * 8, cy), (cx + 20 + k * 8, cy)])
    touch("touchEnd", []); pg.wait_for_timeout(300); pg.screenshot(path="/tmp/g_pinch.png")
    touch("touchStart", [(cx - 80, cy)])
    for k in range(1, 8): touch("touchMove", [(cx - 80 + k * 20, cy)])
    touch("touchEnd", []); pg.wait_for_timeout(300); pg.screenshot(path="/tmp/g_pan.png")
    touch("touchStart", [(cx + 40, cy)]); touch("touchEnd", []); pg.wait_for_timeout(400); pg.screenshot(path="/tmp/g_tap.png")
    pg.click("#gi-xb"); pg.wait_for_timeout(500)
    print("aperto dopo X:", pg.evaluate("document.getElementById('gi-ov').classList.contains('on')"))
    pg.locator("[data-gi='armor']").first.scroll_into_view_if_needed(); pg.locator("[data-gi='armor']").first.click(position={"x": 20, "y": 20}); pg.wait_for_timeout(700); pg.screenshot(path="/tmp/g_armor.png")
    print("errori:", errs); b.close()
