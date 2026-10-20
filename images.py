"""Wikimedia Commons'dan rasm topish (muallif va litsenziya bilan)."""
import html
import logging
import re
from io import BytesIO

import requests
from PIL import Image

log = logging.getLogger(__name__)

UA = {"User-Agent": "FreeStudentSlidesBot/2.0 (educational project)"}
ALLOWED = ("cc by", "cc0", "public domain", "pd", "cc-by")


def _strip(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()


def search_image(query):
    """(url, credit_text) yoki None."""
    if not query:
        return None
    try:
        r = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query", "format": "json", "generator": "search",
                "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": 6,
                "gsrlimit": 10, "prop": "imageinfo",
                "iiprop": "url|extmetadata|size", "iiurlwidth": 1280,
            },
            headers=UA, timeout=15,
        )
        r.raise_for_status()
        pages = sorted(r.json().get("query", {}).get("pages", {}).values(),
                       key=lambda p: p.get("index", 0))
        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            url = info.get("thumburl") or info.get("url")
            if not url or not url.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png")):
                continue
            if info.get("width", 0) < 600:
                continue
            meta = info.get("extmetadata", {})
            lic = _strip(meta.get("LicenseShortName", {}).get("value"))
            if not lic or not any(a in lic.lower() for a in ALLOWED):
                continue
            artist = _strip(meta.get("Artist", {}).get("value")) or "noma'lum muallif"
            credit = f"Rasm: {artist[:40]}, {lic[:25]}, Wikimedia Commons"
            return url, credit
    except Exception as e:
        log.warning("Wikimedia qidiruvi xato: %s", e)
    return None


def fetch_image(query, box_ratio):
    """Rasmni yuklab, kerakli nisbatga (kenglik/balandlik) kesadi. (BytesIO, credit) yoki None."""
    found = search_image(query)
    if not found:
        return None
    url, credit = found
    try:
        r = requests.get(url, headers=UA, timeout=20)
        r.raise_for_status()
        if len(r.content) > 8 * 1024 * 1024:
            return None
        img = Image.open(BytesIO(r.content)).convert("RGB")
        w, h = img.size
        ratio = w / h
        if ratio > box_ratio:                      # juda keng -> yonlarini kesamiz
            nw = int(h * box_ratio)
            img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
        else:                                      # juda baland -> tepa/pastini kesamiz
            nh = int(w / box_ratio)
            img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
        img.thumbnail((1280, 1280))
        out = BytesIO()
        img.save(out, "JPEG", quality=85)
        out.seek(0)
        return out, credit
    except Exception as e:
        log.warning("Rasm yuklash xato: %s", e)
        return None
