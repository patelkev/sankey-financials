"""UI probes on a standalone chart: dark mode, phone width, keyboard, print, clipboard on file://."""
import asyncio, sys
from playwright.async_api import async_playwright
f, out = sys.argv[1], sys.argv[2]
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        # dark
        pg = await b.new_page(color_scheme='dark', viewport={'width': 900, 'height': 900})
        await pg.goto('file://' + f); await pg.screenshot(path=out + '_dark.png', full_page=True)
        # phone
        pg = await b.new_page(viewport={'width': 375, 'height': 800}, device_scale_factor=2, is_mobile=True, has_touch=True)
        await pg.goto('file://' + f); await pg.screenshot(path=out + '_phone.png', full_page=True)
        fs = await pg.evaluate("()=>{const t=document.querySelector('#sk text');const r=t.getBoundingClientRect();const sk=document.getElementById('sk').getBoundingClientRect();return {svgW:sk.width,scale:sk.width/760}}")
        print('phone svg', fs, 'effective 12px label ->', round(12 * fs['scale'], 1), 'px')
        # tap a node on phone: does a tooltip show?
        await pg.locator('rect.nd').first.tap(force=True)
        print('phone tap tooltip opacity', await pg.evaluate("getComputedStyle(document.getElementById('tip')).opacity"))
        # keyboard
        pg = await b.new_page(viewport={'width': 900, 'height': 900})
        await pg.goto('file://' + f)
        seen = []
        for i in range(12):
            await pg.keyboard.press('Tab')
            seen.append(await pg.evaluate("()=>{const e=document.activeElement;return e.tagName+(e.id?'#'+e.id:'')+(e.dataset&&e.dataset.n?'['+e.dataset.n+']':'')}"))
        print('tab order', seen)
        print('focusable nodes', await pg.evaluate("document.querySelectorAll('rect.nd[tabindex]').length"),
              'tabs role', await pg.evaluate("[...document.querySelectorAll('#views button')].map(b=>b.getAttribute('role')||'none')"),
              'svg aria', await pg.evaluate("document.getElementById('sk').getAttribute('aria-label')"))
        # clipboard on file:// (permission not granted)
        await pg.locator('rect.nd').first.click(force=True)
        await pg.wait_for_timeout(300)
        print('copied toast opacity after click', await pg.evaluate("getComputedStyle(document.getElementById('copied')).opacity"))
        clip = await pg.evaluate("navigator.clipboard.readText().then(t=>t,e=>'READ FAIL: '+e.message)")
        print('clipboard readback', clip[:80])
        # print
        await pg.emulate_media(media='print'); await pg.pdf(path=out + '_print.pdf') if False else None
        await pg.screenshot(path=out + '_print.png', full_page=True)
        await b.close()
asyncio.run(main())
