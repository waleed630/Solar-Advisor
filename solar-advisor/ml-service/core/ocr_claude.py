"""Optional: read the bill history table with Claude vision (much better than Tesseract on phone photos).

Used only when ANTHROPIC_API_KEY is set. Each bill costs a small API fee.
"""
import base64
import json
import os

import anthropic
import cv2
import numpy as np

MODEL = "claude-opus-5-5"
MAX_IMAGE_BYTES = 4_500_000

PROMPT = """This is a photo of a Pakistani electricity bill (LESCO or another DISCO).
Find the "BILL HISTORY" table. For every row, give the month (1-12), the 4-digit year and the UNITS
(not the bill amount in rupees, not the payment). Units can be 0 or negative on net-metering bills.
Also give the current bill month, year and its units from the meter info section.
If a number is unreadable, leave that row out instead of guessing."""

SCHEMA = {
    "type": "object",
    "properties": {
        "history": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"month": {"type": "integer"}, "year": {"type": "integer"}, "units": {"type": "integer"}},
                "required": ["month", "year", "units"],
                "additionalProperties": False,
            },
        },
        "current": {
            "type": "object",
            "properties": {"month": {"type": "integer"}, "year": {"type": "integer"}, "units": {"type": "integer"}},
            "required": ["month", "year", "units"],
            "additionalProperties": False,
        },
        "net_metering": {"type": "boolean"},
    },
    "required": ["history", "current", "net_metering"],
    "additionalProperties": False,
}


def enabled():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _as_jpeg(image_bytes):
    """Re-encode as JPEG and shrink if needed, so the upload stays under the image size limit."""
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError("Could not open the image")
    scale = min(1.0, 2400 / max(img.shape[:2]))
    if scale < 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    for quality in (90, 80, 70):
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if ok and len(buf) <= MAX_IMAGE_BYTES:
            return buf.tobytes()
    return buf.tobytes()


def read_bill_claude(image_bytes):
    client = anthropic.Anthropic()
    data = base64.standard_b64encode(_as_jpeg(image_bytes)).decode("utf-8")
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": data}},
                {"type": "text", "text": PROMPT},
            ]}],
        )
    except anthropic.AuthenticationError:
        raise RuntimeError("Claude API key is not valid")
    except anthropic.RateLimitError:
        raise RuntimeError("Claude API is busy, try again in a minute")
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"Claude API error {e.status_code}")
    except anthropic.APIConnectionError:
        raise RuntimeError("Could not reach the Claude API")

    if response.stop_reason == "refusal":
        raise RuntimeError("The photo could not be read")
    text = next(b.text for b in response.content if b.type == "text")
    out = json.loads(text)

    # Keep the newest reading of each month (history + current bill)
    rows = out["history"] + [out["current"]]
    months, years = {}, {}
    for r in sorted(rows, key=lambda r: (r["year"], r["month"])):
        if 1 <= r["month"] <= 12:
            months[r["month"]], years[r["month"]] = r["units"], r["year"]
    return {"months": dict(sorted(months.items())), "years": years, "net_metering": out["net_metering"],
            "engine": "claude", "note": "Read automatically. Always check every number against the bill."}
