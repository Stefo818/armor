from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = br.new_context(viewport={"width": 400, "height": 900}, device_scale_factor=2, has_touch=True, is_mobile=True)
    pg = ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("file:///home/claude/armor/site/index.html"); pg.wait_for_timeout(900)
    print("schede valutazioni:", pg.locator(".kc.vl").count())
    # apre la sezione «Paura, protezioni e prezzi» e fotografa le schede
    pg.evaluate("document.querySelector('.kc.vl').scrollIntoView({block:'center'})"); pg.wait_for_timeout(300)
    pg.screenshot(path="/tmp/v_cards.png")
    for k in ("cape", "buffett"):
        pg.evaluate(f"document.querySelector(\"[data-gi='{k}']\").click()"); pg.wait_for_timeout(800)
        print(k, pg.inner_text("#gi-nm").replace("\n", " "), "|", pg.inner_text("#gi-v"), "| chips:", pg.locator("#gi-rg button").all_inner_texts())
        pg.screenshot(path=f"/tmp/v_{k}.png")
        pg.evaluate("document.getElementById('gi-xb').click()"); pg.wait_for_timeout(400)
    print("errori:", errs); br.close()
