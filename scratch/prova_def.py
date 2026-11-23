from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    pg = br.new_context(viewport={"width": 400, "height": 860}, has_touch=True, is_mobile=True).new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:8765/index.html"); pg.wait_for_timeout(900)
    pg.evaluate("[...document.querySelectorAll('nav button, nav a, .tabs button, [data-tab]')].find(e=>/Grafici/.test(e.textContent)).click()"); pg.wait_for_timeout(1500)
    print(pg.evaluate("[...document.querySelectorAll('label[data-k]')].filter(l=>l.querySelector('input')?l.querySelector('input').checked:l.classList.contains('on')).map(l=>l.dataset.k)"))
    print(pg.evaluate("[...document.querySelectorAll('label[data-k]')].slice(0,40).map(l=>l.dataset.k+':'+l.className)").__str__()[:600])
    print("errori", errs); br.close()
