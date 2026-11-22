"""Click through the app in a headless browser and save screenshots.

Needs all three services running. Run:  python client/e2e_check.py [output folder]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "e2e_screens")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:5173"
ZAIN = [79, 78, 116, 161, 287, 291, 335, 372, 342, 271, 129, 87]   # Jan..Dec, from the real bill

errors = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

    page.goto(URL)
    page.wait_for_selector("text=Get my solar plan")
    page.wait_for_timeout(800)
    page.screenshot(path=OUT / "1_home.png", full_page=True)

    page.click("text=Get my solar plan")
    page.wait_for_selector("text=Your electricity bills")
    # Bills (12 month boxes) and home details are on the same page now
    inputs = page.locator("input[type=number]")
    for i, u in enumerate(ZAIN):
        inputs.nth(i).fill(str(u))
    page.wait_for_selector("text=About your home")
    page.wait_for_timeout(800)
    page.fill("#marla", "7")
    page.fill("#people", "4")
    page.fill("#load", "2")
    page.fill("textarea", "1 AC 1 ton non inverter, 5 pankhe, 1 fridge, 1 air cooler, 1 ups, 1 istri, 1 washing machine")
    page.wait_for_selector("text=5 × Ceiling fan")
    page.screenshot(path=OUT / "2_bills_home.png", full_page=True)
    page.click("button:has-text('Next')")

    page.wait_for_selector("text=Your roof")
    page.wait_for_timeout(2500)   # map tiles
    page.fill("#area", "900")
    page.screenshot(path=OUT / "4_roof.png", full_page=True)
    page.click("button:has-text('Show my solar plan')")

    page.wait_for_selector("text=Your solar plan", timeout=60000)
    page.wait_for_timeout(1500)
    page.screenshot(path=OUT / "5_result.png", full_page=True)

    page.goto(URL + "/model")
    page.wait_for_selector("text=How the model works")
    page.wait_for_timeout(800)
    page.screenshot(path=OUT / "6_model.png", full_page=True)

    page.goto(URL + "/prices")
    page.fill("input[type=password]", "change-me")
    page.click("button:has-text('Log in')")
    page.wait_for_selector("text=Equipment prices")
    page.wait_for_timeout(800)
    page.screenshot(path=OUT / "7_prices.png", full_page=True)

    # "Use my location" with a fake GPS position (Minar-e-Pakistan, a public landmark)
    geo = browser.new_context(viewport={"width": 1280, "height": 900}, permissions=["geolocation"],
                              geolocation={"latitude": 31.5925, "longitude": 74.3095, "accuracy": 20})
    gpage = geo.new_page()
    gpage.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    gpage.goto(URL + "/plan")
    gpage.click("button:has-text('3. Roof')")
    gpage.click("button:has-text('Use my location')")
    gpage.wait_for_selector("text=Your roof should be inside the orange circle", timeout=15000)
    gpage.wait_for_timeout(2500)
    gpage.screenshot(path=OUT / "4b_my_location.png")
    geo.close()

    # "Select my roof" on a phone: checks that a tap makes a selection (the narrow phone map may put open
    # ground under the tap rather than a roof; the test only checks the tap-to-select mechanism)
    tap = browser.new_context(viewport={"width": 390, "height": 1100}, is_mobile=True, has_touch=True,
                              permissions=["geolocation"],
                              geolocation={"latitude": 31.4697, "longitude": 74.2728, "accuracy": 10})
    tpage = tap.new_page()
    tpage.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    tpage.goto(URL + "/plan")
    tpage.tap("button:has-text('3. Roof')")
    tpage.tap("button:has-text('Use my location')")
    tpage.wait_for_function("() => { const t = [...document.querySelectorAll('.leaflet-tile')];"
                            " return t.length > 0 && t.every(i => i.complete && i.naturalWidth > 0) }", timeout=30000)
    tpage.tap("button:has-text('Select my roof')")
    tpage.evaluate("document.querySelector('.leaflet-container').scrollIntoView({block: 'center'})")
    tpage.wait_for_timeout(500)
    box = tpage.locator(".leaflet-container").bounding_box()
    tpage.touchscreen.tap(box["x"] + box["width"] / 2 - 60, box["y"] + box["height"] / 2 + 200)
    tpage.wait_for_selector("text=Selected roof", timeout=20000)
    tpage.screenshot(path=OUT / "4c_select_roof_phone.png", full_page=True)
    print("roof selected on phone:", tpage.locator("#area").input_value(), "sq ft")
    tap.close()

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(URL + "/plan")
    page.wait_for_timeout(800)
    page.screenshot(path=OUT / "8_mobile_plan.png", full_page=True)
    browser.close()

print("screens saved to", OUT)
print("ERRORS:" if errors else "no browser errors", *errors, sep="\n")
