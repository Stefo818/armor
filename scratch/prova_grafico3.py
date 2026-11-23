import re, html
from playwright.sync_api import sync_playwright
s = open('/home/claude/armor/site/index.html', encoding='utf-8').read()
t = re.sub(r"<style.*?</style>|<script.*?</script>", "", s, flags=re.S)
t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))
a, b, c = (t.find(x) for x in ("Paura, protezioni e prezzi", "La bussola di oggi", "Indice Armor e Super Armor"))
print("ordine (Indice Armor < Paura < Bussola):", c < a < b, c, a, b)
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = br.new_context(viewport={"width": 400, "height": 900}, device_scale_factor=2, has_touch=True, is_mobile=True)
    pg = ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("file:///home/claude/armor/site/index.html"); pg.wait_for_timeout(800)
    for k in ("armor", "super"):
        el = pg.locator(f"[data-gi='{k}']").first
        el.evaluate("e=>e.click()"); pg.wait_for_timeout(700)
        print(k, "tessere:", pg.locator(".gi-k").count(), pg.locator(".gi-k").all_inner_texts())
        pg.screenshot(path=f"/tmp/k_{k}.png")
        if k == "armor":
            pg.locator(".gi-k").nth(3).click(); pg.wait_for_timeout(600)
            print(" figlio:", pg.inner_text("#gi-nm").replace("\n", " "), "| indietro:", pg.inner_text("#gi-bk"))
            pg.click("#gi-bk"); pg.wait_for_timeout(500)
            print(" tornato a:", pg.inner_text("#gi-nm").replace("\n", " "))
        print("errori finora:", errs); pg.evaluate("document.getElementById('gi-xb').click()"); pg.wait_for_timeout(400)
    print("errori:", errs); br.close()
