"""Slayd matnini yaratish: Gemini AI (ixtiyoriy) yoki oflayn zaxira matn."""
import json
import logging
import os
import re

import requests

log = logging.getLogger(__name__)

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def ai_enabled():
    return bool(os.environ.get("GEMINI_API_KEY"))


# ----------------------------------------------------------------- AI qismi
PROMPT = """Sen o'zbek tilida talabalar uchun taqdimot matnini yozadigan yordamchisan.
Fan: {subject}
Mavzu: {topic}
Kerakli asosiy slaydlar soni: {n}

Faqat bitta JSON obyekt qaytar (izoh, markdown yoki ``` belgilarisiz). Tuzilishi:
{{
  "plan": ["reja bandi 1", "reja bandi 2", "reja bandi 3"],
  "slides": [
    {{
      "title": "qisqa sarlavha (6 so'zgacha)",
      "bullets": ["3-4 ta qisqa, aniq band (har biri 18 so'zgacha)"],
      "notes": "taqdimotchi uchun 2-3 gaplik izoh",
      "image_query": "Wikimedia Commons uchun 2-4 so'zli INGLIZCHA qidiruv so'rovi yoki bo'sh satr"
    }}
  ],
  "conclusion": ["2-3 ta xulosa bandi"]
}}

Qoidalar:
- "slides" ichida aynan {n} ta element bo'lsin; mantiqiy ketma-ketlikda (kirish -> asosiy qism -> amaliy misol -> xulosaga yaqin).
- Aniq raqam, sana, statistika yoki iqtibosni FAQAT ishonchli bo'lsa yoz; ishonching komil bo'lmasa umumiy ifoda ishlat. O'ylab topma.
- Rasm so'rovi faqat rasm mazmunga mos kelsa; aks holda "".
- Matn o'zbek tilida (lotin yozuvi), akademik, lekin sodda bo'lsin.
"""


def _clip(s, n):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _parse_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


def _ask_gemini(topic, subject, n):
    key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    r = requests.post(
        url,
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": PROMPT.format(topic=topic, subject=subject, n=n)}]}],
            "generationConfig": {"temperature": 0.6, "responseMimeType": "application/json"},
        },
        timeout=90,
    )
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return _parse_json("".join(p.get("text", "") for p in parts))


def _validate(raw, n):
    slides = []
    for s in raw.get("slides", []):
        if not isinstance(s, dict):
            continue
        title = _clip(s.get("title"), 70)
        bullets = [_clip(b, 170) for b in s.get("bullets", []) if str(b).strip()][:5]
        if not title or not bullets:
            continue
        slides.append({
            "title": title,
            "bullets": bullets,
            "notes": _clip(s.get("notes"), 600),
            "image_query": _clip(s.get("image_query"), 60),
        })
    if len(slides) < max(1, n // 2):
        raise ValueError("AI javobi yetarli slayd bermadi")
    plan = [_clip(p, 80) for p in raw.get("plan", []) if str(p).strip()][:5]
    concl = [_clip(c, 200) for c in raw.get("conclusion", []) if str(c).strip()][:4]
    return {"plan": plan, "slides": slides[:n], "conclusion": concl}


# ------------------------------------------------------------ Zaxira matn
def _fallback_slides(topic, subject):
    t, f = topic, subject
    return [
        ("Mavzuga kirish", [
            f"{t} — {f} fanining o'rganiladigan masalalaridan biri.",
            "Mavzuning dolzarbligi va amaliy ahamiyatini aniqlash kerak.",
            "Taqdimotda asosiy tushunchalar, omillar va xulosalar ketma-ket beriladi.",
        ]),
        ("Asosiy tushunchalar", [
            f"{t} bo'yicha asosiy atamalar aniq ta'riflanishi lozim.",
            "Har bir tushuncha qisqa izoh va misol bilan beriladi.",
            "Ta'riflar ishonchli darslik yoki ilmiy manbaga tayanishi kerak.",
        ]),
        ("Maqsad va vazifalar", [
            f"Maqsad: {t} bo'yicha bilimlarni tizimlashtirish.",
            "Vazifa: tushunchalarni izohlash va omillarni aniqlash.",
            "Vazifa: amaliy misol keltirib, natijalarni umumlashtirish.",
        ]),
        ("Muhim omillar", [
            f"{t} ga ta'sir qiluvchi ichki va tashqi omillarni ajratish.",
            "Omillarning o'zaro bog'liqligini hisobga olish kerak.",
            "Har bir omilning ta'siri dalil bilan asoslanadi.",
        ]),
        ("Amaliy misol", [
            f"{t} ni real vaziyatda ko'rib chiqish mavzuni yaxshi tushuntiradi.",
            "Boshlang'ich shartlar, jarayon va natijani solishtiring.",
            "Raqamlar ishlatilsa, ularning manbasi ko'rsatilishi shart.",
        ]),
        ("Tahlil usullari", [
            "Taqqoslash, tasniflash va kuzatish eng ko'p qo'llaniladi.",
            "Ma'lumotlarni jadval yoki diagrammada ifodalash foydali.",
            "Usul mavzu va mavjud ma'lumotga mos tanlanadi.",
        ]),
        ("Afzallik va cheklovlar", [
            "Ijobiy jihatlar bilan birga cheklovlarni ham baholash kerak.",
            "Xulosalar dalillarga asoslanishi lozim.",
            "Ortiqcha umumlashtirishdan saqlanish zarur.",
        ]),
        ("Muammolar va yechimlar", [
            f"{t} bilan bog'liq asosiy muammolarni aniqlash.",
            "Har bir muammo uchun mumkin bo'lgan yechimni taqqoslash.",
            "Yechimning afzallik va xavflarini baholash.",
        ]),
        ("Natijalar", [
            f"Ko'rib chiqilgan fikrlar {t} ni tizimli tahlil qilish muhimligini ko'rsatadi.",
            "Natijalarni baholashda ma'lumot sifati va kontekst e'tiborga olinadi.",
        ]),
        ("Rivojlanish istiqbollari", [
            f"{t} bo'yicha keyingi tadqiqot yo'nalishlarini belgilash.",
            "Yangi ma'lumot va texnologiyalardan foydalanish imkoniyatlari.",
        ]),
    ]


def fallback_content(topic, subject, n):
    base = _fallback_slides(topic, subject)
    slides = []
    for i in range(n):
        title, bullets = base[i % len(base)]
        if i >= len(base):
            title = f"{title} (davomi)"
        slides.append({"title": title, "bullets": bullets, "notes": "", "image_query": topic if i == 1 else ""})
    return {
        "plan": ["Kirish va asosiy tushunchalar", "Omillar va amaliy tahlil", "Natijalar va xulosa"],
        "slides": slides,
        "conclusion": [
            f"{topic} bo'yicha asosiy tushunchalarni aniqlash muhim.",
            "Tahlilda dalillar va ishonchli manbalarga tayaning.",
        ],
    }


def build_content(topic, subject, n):
    """(content, used_ai) qaytaradi. AI xato bersa, zaxira matnga o'tadi."""
    if ai_enabled():
        try:
            content = _validate(_ask_gemini(topic, subject, n), n)
            # AI kam slayd bergan bo'lsa, qolganini zaxira bilan to'ldiramiz
            if len(content["slides"]) < n:
                extra = fallback_content(topic, subject, n)["slides"]
                content["slides"] += extra[len(content["slides"]):n]
            fb = fallback_content(topic, subject, n)
            content["plan"] = content["plan"] or fb["plan"]
            content["conclusion"] = content["conclusion"] or fb["conclusion"]
            return content, True
        except Exception as e:  # tarmoq, kvota, noto'g'ri JSON va h.k.
            log.warning("AI matn yaratish muvaffaqiyatsiz, zaxira ishlatiladi: %s", e)
    return fallback_content(topic, subject, n), False
