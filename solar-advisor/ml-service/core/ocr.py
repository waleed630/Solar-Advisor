"""Read the 12-month "Bill history" table from a LESCO bill photo with Tesseract.

Steps: clean the image (OpenCV), run Tesseract a few ways, find every "MON YY ... units" pair,
and keep the reading that most variants agree on. The app always asks the user to check the numbers.
"""
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np
import pytesseract

WINDOWS_PATH = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# Letters Tesseract often gives instead of digits
DIGIT_FIX = str.maketrans({"O": "0", "o": "0", "D": "0", "Q": "0", "I": "1", "l": "1", "|": "1", "i": "1",
                           "Z": "2", "S": "5", "s": "5", "B": "8", "G": "6", "g": "9", "T": "7"})
MONTH_FIX = {"0CT": "OCT", "N0V": "NOV", "AUC": "AUG", "5EP": "SEP", "JUI": "JUL", "JU1": "JUL", "JUN": "JUN",
             "MAV": "MAY", "FE8": "FEB", "DEG": "DEC", "0EC": "DEC", "APH": "APR"}

ROW = re.compile(r"\b([A-Z0-9]{3})\s*[-'.]?\s*([0-9OoIlSZ]{2})\b")


def tesseract_cmd():
    if shutil.which("tesseract"):
        return "tesseract"
    if WINDOWS_PATH.exists():
        return str(WINDOWS_PATH)
    raise RuntimeError("Tesseract is not installed")


def variants(img):
    """A few cleaned versions of the photo; different photos work best with different cleaning."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    scale = 2200 / max(gray.shape)
    if scale > 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    yield cv2.GaussianBlur(gray, (3, 3), 0)
    yield cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    yield cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 41, 15)


MAX_UNITS = 20000  # more than this in one month is not a home's units (it is an ID, an amount or a barcode)


def parse(text):
    """Find 'MON YY <status> <units> <bill> <payment>' pairs; units = first number after the month.

    The first sensible reading of each month wins. The bill history table comes before the
    barcode line at the bottom ("OCT 26 - 10416794 - ... - 06 NOV 26 - 000007456"), which also
    has month names; those must not replace the table's numbers.
    """
    found = {}
    upper = text.upper()
    for match in ROW.finditer(upper):
        mon = MONTH_FIX.get(match.group(1), match.group(1))
        if mon not in MONTHS:
            continue
        year = match.group(2).translate(DIGIT_FIX)
        if not year.isdigit() or not 20 <= int(year) <= 40:
            continue
        rest = upper[match.end():match.end() + 40]
        nxt = ROW.search(rest)
        if nxt and MONTH_FIX.get(nxt.group(1), nxt.group(1)) in MONTHS:
            rest = rest[:nxt.start()]
        tokens = re.findall(r"-?[0-9OoIlSZ,]+", rest)
        month = MONTHS.index(mon) + 1
        if month in found:
            continue  # already read from the table above
        numbers = []
        for tok in tokens:
            t = tok.replace(",", "").translate(DIGIT_FIX)
            if t.lstrip("-").isdigit() and any(ch.isdigit() for ch in tok):
                numbers.append(int(t))
        units = plausible_units(numbers)
        if units is not None:
            found[month] = (units, 2000 + int(year))
    return found


def plausible_units(numbers):
    """A history row reads: units, bill (Rs), payment (Rs). Return the units, or None if they were not read.

    A month left empty is better than a wrong number: the user fills an empty box, but may not notice a wrong one.
    """
    if not numbers or not 0 <= numbers[0] <= MAX_UNITS:
        return None
    units = numbers[0]
    if len(numbers) >= 2 and units > 0:
        bill = numbers[1]
        if bill == units and units >= 500:
            return None  # "3018 3018": that is the bill and the payment; the units were not read
        if bill > 0 and bill / units < 3:
            return None  # cheaper than Rs 3 a unit: the "units" are really a rupee amount (e.g. bill, then a part payment)
        # Too small for its bill: a digit was lost ("96" read as "6"). Allow Rs 800 of fixed charges and taxes,
        # then no Pakistani tariff charges more than about Rs 100 a unit. Only for small numbers: a big bill
        # can also carry old unpaid amounts (arrears), which would make a real row look too expensive.
        if units < 50 and (bill - 800) / units > 100:
            return None
    return units


def history_crop(img):
    """Cut out the part of the bill below the 'BILL HISTORY' heading, if we can find it."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    data = pytesseract.image_to_data(gray, config="--psm 11", output_type=pytesseract.Output.DICT)
    for i, word in enumerate(data["text"]):
        if "HISTORY" in word.upper():
            top = max(0, data["top"][i] - 10)
            bottom = min(img.shape[0], top + int(img.shape[0] * 0.22))
            crop = img[top:bottom]
            return cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    return None


def read_bill(image_bytes):
    tesseract = tesseract_cmd()
    pytesseract.pytesseract.tesseract_cmd = tesseract
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError("Could not open the image")

    images = [img]
    crop = history_crop(img)
    if crop is not None:
        images.insert(0, crop)

    votes = defaultdict(Counter)
    for weight, im in zip((2, 1), images):          # the cropped table counts double
        for v in variants(im):
            for psm in (6, 4):
                text = pytesseract.image_to_string(v, config=f"--psm {psm}")
                for m, val in parse(text).items():
                    votes[m][val] += weight
        # All 12 months agreed on in the cropped table: no need to read the whole page as well
        if crop is not None and im is crop and sum(1 for c in votes.values() if c.most_common(1)[0][1] >= 4) == 12:
            break

    months, years, confidence = {}, {}, {}
    for m, counter in votes.items():
        (units, year), n = counter.most_common(1)[0]
        if 0 <= units <= MAX_UNITS:
            months[m] = units
            years[m] = year
            confidence[m] = round(min(1, n / 12), 2)   # how many readings agree
    return {"months": dict(sorted(months.items())), "years": years, "confidence": confidence,
            "note": "Read automatically. Always check every number against the bill."}
