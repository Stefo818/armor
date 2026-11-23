from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 400, "height": 820}, device_scale_factor=2, has_touch=True, is_mobile=True)
    pg = ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("file:///home/claude/armor/site/index.html"); pg.wait_for_timeout(800)
    n = pg.locator("[data-gi]").count(); print("elementi toccabili:", n)
    ids = pg.evaluate("[...document.querySelectorAll('[data-gi]')].map(e=>e.dataset.gi)"); print(ids)
    for k in ("p3", "armor"):
        el = pg.locator(f"[data-gi='{k}']").first
        el.evaluate("e=>e.scrollIntoView()"); el.click(force=True); pg.wait_for_timeout(700)
        print(k, pg.inner_text("#gi-nm"), "|", pg.inner_text("#gi-v"), "|", pg.inner_text("#gi-zn"))
        pg.screenshot(path=f"/tmp/h_{k}.png"); pg.click("#gi-xb"); pg.wait_for_timeout(400)
    print("errori:", errs); b.close()
