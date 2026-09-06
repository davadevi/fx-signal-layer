#!/usr/bin/env python3
"""
FX Signal Layer — pitch deck, Alfa-Bank Hackathon, Сентябрь 2026.
4 слайда: Клиентский путь / Сигнал / Push-тексты / Кастомные доработки.
Сохраняет в submission/07_sept/01_presentation.pptx.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement

# ─── PALETTE ──────────────────────────────────────────────────────────────────
BG          = RGBColor(0xF9, 0xF9, 0xF6)
SURFACE     = RGBColor(0xFF, 0xFF, 0xFF)
SURFACE_ALT = RGBColor(0xF1, 0xF2, 0xEE)
INK         = RGBColor(0x12, 0x16, 0x1A)
INK2        = RGBColor(0x6D, 0x74, 0x7F)
INK3        = RGBColor(0xA6, 0xAC, 0xB3)
TEAL        = RGBColor(0x52, 0x8D, 0x8A)
TEAL_DEEP   = RGBColor(0x26, 0x67, 0x5F)
TEAL_PALE   = RGBColor(0xEB, 0xF2, 0xF0)
AMBER       = RGBColor(0xAD, 0x69, 0x2E)
AMBER_BG    = RGBColor(0xFC, 0xF4, 0xEA)
NEGATIVE    = RGBColor(0xAE, 0x46, 0x30)
DARK_TEAL   = RGBColor(0x3E, 0x68, 0x64)
BORDER      = RGBColor(0xE7, 0xE7, 0xE1)
WHITE       = RGBColor(0xFF, 0xFF, 0xFF)

FONT = "Calibri"
LEFT_ALIGN = PP_ALIGN.LEFT
CENTER     = PP_ALIGN.CENTER
RIGHT      = PP_ALIGN.RIGHT

prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def new_slide():
    return prs.slides.add_slide(BLANK)


def _no_line(shape):
    shape.line.fill.background()
    shape.shadow.inherit = False


def add_soft_shadow(shape, blur_pt=14, dist_pt=4, alpha_pct=16,
                    color="1A1A1A", direction=5400000):
    spPr = shape._element.spPr
    effectLst = OxmlElement("a:effectLst")
    outerShdw = OxmlElement("a:outerShdw")
    outerShdw.set("blurRad", str(int(Pt(blur_pt))))
    outerShdw.set("dist",    str(int(Pt(dist_pt))))
    outerShdw.set("dir",     str(direction))
    outerShdw.set("rotWithShape", "0")
    clr = OxmlElement("a:srgbClr")
    clr.set("val", color)
    alpha = OxmlElement("a:alpha")
    alpha.set("val", str(int(alpha_pct * 1000)))
    clr.append(alpha)
    outerShdw.append(clr)
    effectLst.append(outerShdw)
    spPr.append(effectLst)


def bg(slide, color=BG):
    sp = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
    )
    sp.fill.solid()
    sp.fill.fore_color.rgb = color
    _no_line(sp)
    spTree = slide.shapes._spTree
    spTree.remove(sp._element)
    spTree.insert(2, sp._element)
    return sp


def card(slide, x, y, w, h, fill=SURFACE, radius=0.045, shadow=True):
    sp = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    sp.adjustments[0] = radius
    sp.fill.solid()
    sp.fill.fore_color.rgb = fill
    _no_line(sp)
    if shadow:
        add_soft_shadow(sp)
    return sp


def pill(slide, x, y, w, h, fill=TEAL):
    sp = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    sp.adjustments[0] = 0.5
    sp.fill.solid()
    sp.fill.fore_color.rgb = fill
    _no_line(sp)
    return sp


def hline(slide, x, y, w, h=0.014, color=BORDER):
    sp = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    sp.fill.solid()
    sp.fill.fore_color.rgb = color
    _no_line(sp)
    return sp


def txt(slide, text, x, y, w, h, size=14, bold=False, italic=False,
        color=INK, align=LEFT_ALIGN, anchor=None):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    if anchor is not None:
        tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    f = run.font
    f.size   = Pt(size)
    f.bold   = bold
    f.italic = italic
    f.color.rgb = color
    f.name = FONT
    return box


def txt_para(slide, lines, x, y, w, h, size=14, bold=False, italic=False,
             color=INK, align=LEFT_ALIGN, space_after=2):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(space_after)
        run = p.add_run()
        run.text = line
        f = run.font
        f.size   = Pt(size)
        f.bold   = bold
        f.italic = italic
        f.color.rgb = color
        f.name = FONT
    return box


def two_run(slide, mark, mark_color, rest, rest_color, x, y, w, h,
            size=14, bold_mark=True):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = LEFT_ALIGN
    for text, color, bold in [(mark, mark_color, bold_mark), (rest, rest_color, False)]:
        r = p.add_run()
        r.text = text
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color
        r.font.name = FONT
    return box


def _clear_bullets(pPr):
    for tag in ("a:buClr","a:buSzPct","a:buSzPts","a:buFont",
                "a:buChar","a:buAutoNum","a:buNone"):
        el = pPr.find(qn(tag))
        if el is not None:
            pPr.remove(el)


def _bullet_char(pPr, char="•", color=None, size_pct=85):
    _clear_bullets(pPr)
    if color is not None:
        buClr = OxmlElement("a:buClr")
        srgb  = OxmlElement("a:srgbClr")
        srgb.set("val", str(color))
        buClr.append(srgb)
        pPr.append(buClr)
    sz = OxmlElement("a:buSzPct")
    sz.set("val", str(int(size_pct * 1000)))
    pPr.append(sz)
    bf = OxmlElement("a:buFont")
    bf.set("typeface", FONT)
    pPr.append(bf)
    bc = OxmlElement("a:buChar")
    bc.set("char", char)
    pPr.append(bc)


def _no_bullet(pPr):
    _clear_bullets(pPr)
    pPr.append(OxmlElement("a:buNone"))


def para_list(slide, x, y, w, h, items, default_size=14,
              default_color=INK, space_after=12):
    """items: list of dicts with keys: text, size, color, bold, italic,
    bullet ('char'|None), bullet_char, bullet_color, marL, indent, space_after."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, item in enumerate(items):
        p   = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment  = LEFT_ALIGN
        p.space_after = Pt(item.get("space_after", space_after))
        pPr  = p._p.get_or_add_pPr()
        bul  = item.get("bullet", "char")
        marL = item.get("marL", 0.22 if bul else 0.0)
        ind  = item.get("indent", -0.22 if bul else 0.0)
        pPr.set("marL",   str(int(Inches(marL))))
        pPr.set("indent", str(int(Inches(ind))))
        color  = item.get("color", default_color)
        bcolor = item.get("bullet_color", color)
        if bul == "char":
            _bullet_char(pPr, char=item.get("bullet_char","•"),
                         color=bcolor,
                         size_pct=item.get("bullet_size_pct", 85))
        else:
            _no_bullet(pPr)
        run = p.add_run()
        run.text = item["text"]
        f = run.font
        f.size   = Pt(item.get("size", default_size))
        f.bold   = item.get("bold", False)
        f.italic = item.get("italic", False)
        f.color.rgb = color
        f.name = FONT
    return box


def eyebrow(slide, text, x=0.55, y=0.30, color=TEAL_DEEP):
    hline(slide, x, y + 0.09, 0.22, 0.018, color)
    txt(slide, "  " + text.upper(), x + 0.28, y, 12.0, 0.28,
        size=10.5, bold=True, color=color)


def slide_num(slide, n, total=5):
    txt(slide, f"{n}/{total}", 12.15, 7.1, 0.65, 0.28,
        size=9, color=INK3, align=RIGHT)


def strip_table_style(table):
    tbl   = table._tbl
    tblPr = tbl.find(qn("a:tblPr"))
    if tblPr is None:
        return
    for child in list(tblPr):
        if child.tag == qn("a:tableStyleId"):
            tblPr.remove(child)
    sid = OxmlElement("a:tableStyleId")
    sid.text = "{5940675A-B579-460E-94D1-54222C63F5DA}"
    tblPr.append(sid)
    table.first_row    = False
    table.horz_banding = False


def _kill_borders(cell):
    tcPr = cell._tc.get_or_add_tcPr()
    for tag in ("a:lnL","a:lnR","a:lnT","a:lnB"):
        ln = OxmlElement(tag)
        ln.set("w","0")
        ln.append(OxmlElement("a:noFill"))
        tcPr.append(ln)


def style_cell(cell, text, size=13, bold=False, color=INK,
               fill=SURFACE, align=LEFT_ALIGN):
    _kill_borders(cell)
    cell.margin_left   = Inches(0.13)
    cell.margin_right  = Inches(0.13)
    cell.margin_top    = Inches(0.04)
    cell.margin_bottom = Inches(0.04)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    cell.fill.solid()
    cell.fill.fore_color.rgb = fill
    tf = cell.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    p.text = ""
    run = p.add_run()
    run.text = text
    run.font.size      = Pt(size)
    run.font.bold      = bold
    run.font.color.rgb = color
    run.font.name      = FONT




# =============================================================================
# СЛАЙД 1 — КЛИЕНТСКИЙ ПУТЬ
# =============================================================================
def slide_01():
    s = new_slide()
    bg(s)
    eyebrow(s, "Клиентский путь · FX Signal Layer · Alfa-Bank Hackathon 2026")
    txt(s, "От сигнала к переводу — пять шагов",
        0.55, 0.72, 12.2, 0.6, size=28, bold=True, color=INK)

    steps = [
        (True,  TEAL_DEEP, WHITE, "01", "Сигнал срабатывает",
         ["Рубль укрепляется", "быстрее обычного", "2 дня подряд"]),
        (False, TEAL,      WHITE, "02", "Push-уведомление",
         ["Факт о курсе", "Без прогнозов", "Не тревожим ночью"]),
        (False, TEAL,      WHITE, "03", "Экран курса",
         ["Сравнение с историей", "за 3 месяца", "Курс ЦБ сейчас"]),
        (False, TEAL_DEEP, WHITE, "04", "Форма перевода",
         ["Предзаполнена:", "сумма, получатель,", "направление"]),
        (False, SURFACE_ALT, INK, "05", "Клиент переводит",
         ["Осознанно,", "в хороший момент,", "не «когда вспомнил»"]),
    ]

    w = 2.6
    xs = [0.4, 2.75, 5.1, 7.45, 9.8]
    y0, hc = 1.62, 2.0

    for i, (is_first, fill, tc, step_num, title, desc) in enumerate(steps):
        x = xs[i]
        sp = s.shapes.add_shape(
            MSO_SHAPE.PENTAGON if is_first else MSO_SHAPE.CHEVRON,
            Inches(x), Inches(y0), Inches(w), Inches(hc)
        )
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
        _no_line(sp)

        pw, ph = 0.46, 0.30
        px = x + (w - pw) / 2
        pill_fill = WHITE if fill in (TEAL_DEEP, TEAL) else TEAL_PALE
        pill(s, px, y0 + 0.22, pw, ph, pill_fill)
        txt(s, step_num, px, y0 + 0.22, pw, ph, size=11, bold=True,
            color=TEAL_DEEP, align=CENTER, anchor=MSO_ANCHOR.MIDDLE)

        inner_x = x + (0.35 if i > 0 else 0.1)
        inner_w = w - (0.6  if i > 0 else 0.25)
        txt(s, title, inner_x, y0 + 0.74, inner_w, 0.5,
            size=13, bold=True, color=tc, align=CENTER)

        txt_para(s, desc, x + 0.15, y0 + hc + 0.18,
                 w - 0.3, 1.0, size=11, color=INK2, align=CENTER)

    # badge under step 4
    bx = xs[3] + (w - 2.3) / 2
    pill(s, bx, y0 + hc + 1.28, 2.3, 0.30, AMBER_BG)
    txt(s, "★  ОРИГИНАЛЬНАЯ ДОРАБОТКА", bx, y0 + hc + 1.28, 2.3, 0.30,
        size=8.5, bold=True, color=AMBER,
        align=CENTER, anchor=MSO_ANCHOR.MIDDLE)

    txt(s,
        "Предзаполненная форма передаёт сумму, получателя и направление "
        "из профиля клиента — реквизиты не нужно набирать заново.",
        0.4, 6.88, 12.5, 0.38, size=11, italic=True, color=INK2)

    slide_num(s, 1, total=4)
    return s


# =============================================================================
# СЛАЙД 2 — ВЫБОР СИГНАЛА И ФИЛЬТРЫ
# =============================================================================
def slide_02():
    s = new_slide()
    bg(s)
    eyebrow(s, "Выбор сигнала")
    txt(s, "Скорость изменения курса с подтверждением разворота",
        0.55, 0.72, 12.2, 0.6, size=28, bold=True, color=INK)

    # левая карточка — решения простыми словами
    card(s, 0.4, 1.62, 5.65, 5.25, SURFACE)
    txt(s, "ЧТО ВЫБРАЛИ И ПОЧЕМУ", 0.68, 1.87, 5.15, 0.28,
        size=10.5, bold=True, color=INK2)

    items = [
        # --- блок 1 ---
        {"text": "Смотрим на скорость, а не на уровень курса",
         "bold": True, "color": INK, "bullet": None, "marL": 0.0, "space_after": 5},
        {"text": "Сам курс медленно дрейфует — «1.43 сегодня» без истории ничего не значит",
         "color": NEGATIVE, "size": 12,
         "bullet": "char", "bullet_char": "→", "marL": 0.28, "indent": -0.28,
         "space_after": 3},
        {"text": "Скорость укрепления за 5 дней vs последние 60 дней — сравнение корректное",
         "color": TEAL_DEEP, "size": 12,
         "bullet": "char", "bullet_char": "→", "marL": 0.28, "indent": -0.28,
         "space_after": 20},
        # --- блок 2 ---
        {"text": "Подтверждение: два дня подряд, а не один",
         "bold": True, "color": INK, "bullet": None, "marL": 0.0, "space_after": 5},
        {"text": "Один день — может быть шумом: сигнал ложный в 60% случаев, курс не улучшается",
         "color": NEGATIVE, "size": 12,
         "bullet": "char", "bullet_char": "→", "marL": 0.28, "indent": -0.28,
         "space_after": 3},
        {"text": "Два дня подряд — признак продолжающегося движения, статистически значим",
         "color": TEAL_DEEP, "size": 12,
         "bullet": "char", "bullet_char": "→", "marL": 0.28, "indent": -0.28,
         "space_after": 20},
        # --- блок 3 ---
        {"text": "Фильтр турбулентного рынка",
         "bold": True, "color": INK, "bullet": None, "marL": 0.0, "space_after": 5},
        {"text": "Если рынок прыгает сильнее, чем в 85% периодов — сигнал не отправляем",
         "color": INK2, "size": 12,
         "bullet": "char", "bullet_char": "→", "marL": 0.28, "indent": -0.28,
         "space_after": 3},
        {"text": "В кризис паттерны разворота не работают — лучше промолчать",
         "color": INK3, "size": 12, "italic": True,
         "bullet": "char", "bullet_char": "→", "marL": 0.28, "indent": -0.28},
    ]
    para_list(s, 0.68, 2.28, 5.15, 4.4, items, default_size=13, space_after=12)

    # правая — таблица результатов
    txt(s, "РЕЗУЛЬТАТЫ ПРОВЕРКИ НА БУДУЩИХ ДАННЫХ (доверительный интервал 90%)",
        6.3, 1.62, 6.65, 0.28, size=10.5, bold=True, color=INK2)

    tdata = [
        ("RUB/KGS", "2.10", "1.84", "1.36 ✓", "+64 бп", True),
        ("RUB/TJS", "2.35", "1.76", "1.76 ✓", "+96 бп", True),
        ("RUB/AMD", "2.81", "2.16", "1.30 ⚠",  "+52 бп", False),
        ("RUB/UZS", "—",   "—",    "< 1.0 ✗",  "—",     False),
        ("RUB/KZT", "—",   "—",    "< 1.0 ✗",  "—",     False),
    ]

    tx, ty, tw, th = 6.3, 2.02, 6.65, 3.65
    gs = s.shapes.add_table(6, 5, Inches(tx), Inches(ty), Inches(tw), Inches(th))
    tbl = gs.table
    strip_table_style(tbl)
    for ci, cw in enumerate([1.5, 1.15, 1.35, 1.45, 1.2]):
        tbl.columns[ci].width = Inches(cw)
    tbl.rows[0].height = Inches(0.5)
    for r in range(1, 6):
        tbl.rows[r].height = Inches(0.62)

    for ci, h in enumerate(["КОРИДОР", "НА ИСТОРИИ", "НА НОВЫХ ДАННЫХ",
                             "НИЖНЯЯ ГРАНИЦА CI", "ВЫГОДА (10 ДНЕЙ)"]):
        style_cell(tbl.cell(0, ci), h, size=10.5, bold=True, color=INK2,
                   fill=SURFACE_ALT,
                   align=CENTER if ci > 0 else LEFT_ALIGN)

    for ri, (cor, isl, ootl, ci_v, bps, passing) in enumerate(tdata):
        rf = SURFACE if ri % 2 == 0 else BG
        ci_col = TEAL_DEEP if passing else (NEGATIVE if "✗" in ci_v else AMBER)
        style_cell(tbl.cell(ri+1, 0), cor,  size=13, bold=True, color=INK, fill=rf)
        style_cell(tbl.cell(ri+1, 1), isl,  size=13, color=INK, fill=rf, align=CENTER)
        style_cell(tbl.cell(ri+1, 2), ootl, size=13,
                   color=TEAL_DEEP if passing else INK3, fill=rf, align=CENTER)
        style_cell(tbl.cell(ri+1, 3), ci_v, size=13, bold=passing,
                   color=ci_col, fill=rf, align=CENTER)
        style_cell(tbl.cell(ri+1, 4), bps,  size=13,
                   color=TEAL_DEEP if bps.startswith("+") else INK3,
                   fill=rf, align=CENTER)

    card(s, 6.3, 5.83, 6.65, 0.88, SURFACE_ALT, radius=0.06, shadow=False)
    txt(s,
        "Простой базовый сигнал (по абсолютному уровню курса): результат 0.86–0.97 "
        "— хуже случайного выбора дня",
        6.5, 6.1, 6.25, 0.38, size=12, italic=True, color=INK2)

    slide_num(s, 2, total=4)
    return s


# =============================================================================
# СЛАЙД 3 — PUSH-ТЕКСТЫ · ЧАСОВЫЕ ПОЯСА · УСТАРЕВАНИЕ
# =============================================================================
def slide_03():
    s = new_slide()
    bg(s)
    eyebrow(s, "Push-тексты и производственные решения")
    txt(s, "Только факты. Правильное время. Без дублей.",
        0.55, 0.72, 12.2, 0.6, size=28, bold=True, color=INK)

    # левая карточка — push-тексты + compliance
    card(s, 0.4, 1.62, 6.05, 5.25, SURFACE)
    txt(s, "PUSH-ТЕКСТЫ (ПРОВЕРЕНО НА СООТВЕТСТВИЕ)", 0.68, 1.87, 5.6, 0.28,
        size=10.5, bold=True, color=INK2)

    # мокап уведомления #1
    card(s, 0.68, 2.27, 5.55, 1.02, TEAL_PALE, radius=0.06, shadow=False)
    txt(s, "Альфа-Банк", 0.95, 2.41, 4.8, 0.26,
        size=11, bold=True, color=TEAL_DEEP)
    txt(s,
        "Рубль укрепился к сомони за последние 5 дней\n"
        "сильнее, чем в 85% случаев за 3 месяца.\n"
        "Текущий курс: 6.3850 руб.",
        0.95, 2.65, 5.15, 0.57, size=11.5, color=INK)

    # мокап уведомления #2
    card(s, 0.68, 3.38, 5.55, 0.98, SURFACE_ALT, radius=0.06, shadow=False)
    txt(s, "Альфа-Банк", 0.95, 3.52, 4.8, 0.26,
        size=11, bold=True, color=TEAL_DEEP)
    txt(s,
        "Рубль укреплялся к сому несколько дней подряд —\n"
        "курс выгоднее, чем в 91% случаев за 3 месяца.\n"
        "Текущий курс: 1.4320 руб.",
        0.95, 3.76, 5.15, 0.52, size=11.5, color=INK)

    hline(s, 0.68, 4.48, 5.55, 0.012, BORDER)

    txt(s, "ПРАВИЛО COMPLIANCE", 0.68, 4.6, 5.5, 0.26, size=10.5, bold=True, color=INK2)
    para_list(s, 0.68, 4.9, 5.55, 1.7, [
        {"text": "Только факты прошлого/настоящего",
         "color": INK, "size": 12, "bullet_color": TEAL_DEEP},
        {"text": "Запрещено: «вырастет» / «успейте» / «гарантируем» / «заработайте»",
         "color": NEGATIVE, "size": 12, "bullet_color": NEGATIVE},
        {"text": "Автоматическая проверка каждого шаблона перед отправкой",
         "color": INK2, "size": 11},
    ], space_after=10)

    # правая верхняя — timezone
    card(s, 6.7, 1.62, 6.2, 2.42, SURFACE)
    txt(s, "ЧАСОВЫЕ ПОЯСА", 6.98, 1.87, 5.7, 0.28,
        size=10.5, bold=True, color=INK2)
    para_list(s, 6.98, 2.26, 5.7, 1.62, [
        {"text": "Получатель UTC+5 (UZS, KGS) — разница 2 ч от МСК",
         "color": INK, "size": 12, "bullet_color": INK2},
        {"text": "Тихое окно: 22:00–09:00 по времени получателя",
         "color": TEAL_DEEP, "bold": True, "size": 12, "bullet_color": TEAL_DEEP},
        {"text": "Сигнал не сгорает — ставится в очередь до открытия окна",
         "color": INK2, "size": 12, "bullet_color": INK2},
        {"text": "Математически верный сигнал в 01:00 — для продукта мусор",
         "color": INK3, "italic": True, "size": 11, "bullet_color": INK3},
    ], space_after=10)

    # правая нижняя — staleness
    card(s, 6.7, 4.2, 6.2, 2.42, SURFACE)
    txt(s, "УСТАРЕВАНИЕ И ДУБЛИ", 6.98, 4.45, 5.7, 0.28,
        size=10.5, bold=True, color=INK2)
    para_list(s, 6.98, 4.84, 5.7, 1.62, [
        {"text": "Пауза 3 дня между сигналами одного коридора — нет повторов",
         "color": INK, "size": 12, "bullet_color": INK2},
        {"text": "История сигналов хранится 30 дней — дубли исключены",
         "color": INK2, "size": 12, "bullet_color": INK2},
        {"text": "Сигнал на выходной → следующий торговый день",
         "color": INK2, "size": 12, "bullet_color": INK2},
        {"text": "TJS не блокирует KGS — cooldown независим по коридорам",
         "color": TEAL_DEEP, "bold": True, "size": 12, "bullet_color": TEAL_DEEP},
    ], space_after=10)

    slide_num(s, 3, total=4)
    return s


# =============================================================================
# СЛАЙД 4 — КАСТОМНЫЕ ДОРАБОТКИ
# =============================================================================
def slide_04():
    s = new_slide()
    bg(s)
    eyebrow(s, "Кастомные доработки")
    txt(s, "Двухуровневая система сигналов и проверка на будущих данных",
        0.55, 0.72, 12.2, 0.6, size=26, bold=True, color=INK)

    # левая карточка — двухуровневая система
    card(s, 0.4, 1.62, 5.9, 5.25, SURFACE)
    txt(s, "ДВУХУРОВНЕВАЯ СИСТЕМА", 0.68, 1.87, 5.4, 0.28,
        size=10.5, bold=True, color=INK2)

    pill(s, 0.68, 2.28, 2.0, 0.36, TEAL_DEEP)
    txt(s, "СИЛЬНЫЙ СИГНАЛ", 0.68, 2.28, 2.0, 0.36,
        size=10, bold=True, color=WHITE,
        align=CENTER, anchor=MSO_ANCHOR.MIDDLE)
    para_list(s, 0.68, 2.76, 5.4, 1.6, [
        {"text": "Статистически подтверждён (CI > 1.0 на KGS/TJS)",
         "color": INK, "size": 12, "bullet_color": TEAL_DEEP},
        {"text": "Редкий: ~0.057/нед — раз в 2–3 недели на коридор",
         "color": INK2, "size": 12},
        {"text": "Точность > частота: поток не разбавляем ради покрытия цели",
         "color": INK, "bold": True, "size": 12},
    ], space_after=12)

    hline(s, 0.68, 4.45, 5.4, 0.012, BORDER)

    pill(s, 0.68, 4.6, 2.55, 0.36, SURFACE_ALT)
    txt(s, "«НАБЛЮДЕНИЕ» НА ГЛАВНОМ ЭКРАНЕ", 0.68, 4.6, 2.55, 0.36,
        size=9.5, bold=True, color=INK2,
        align=CENTER, anchor=MSO_ANCHOR.MIDDLE)
    para_list(s, 0.68, 5.08, 5.4, 1.56, [
        {"text": "Мягкий сигнал в тихие недели — не push, не прерывает",
         "color": INK, "size": 12, "bullet_color": INK2},
        {"text": "Честно помечена как «наблюдение», не к действию",
         "color": INK2, "size": 12},
        {"text": "Цель 1–2 контакта/нед — без разбавления статистического edge",
         "color": TEAL_DEEP, "bold": True, "size": 12, "bullet_color": TEAL_DEEP},
    ], space_after=12)

    # правая карточка — no-lookahead + stack
    card(s, 6.55, 1.62, 6.38, 5.25, SURFACE)
    txt(s, "ПРОВЕРКА НА БУДУЩИХ ДАННЫХ", 6.83, 1.87, 5.9, 0.28,
        size=10.5, bold=True, color=INK2)

    rows = [
        ("Тест на будущих данных",        "обучение 2 года → тест 3 месяца → пауза 5 дней"),
        ("Отложенный тест",               "с 2025-07-01 — нетронутые данные"),
        ("Без заглядывания в будущее",    "сигнал видит только данные ≤ сегодня"),
        ("30 unit-тестов",                "включая проверку отсутствия lookahead"),
        ("Доверительный интервал",        "OOT мало → bootstrap на полной выборке"),
        ("Выгода в базисных пунктах",     "KGS +40–64 бп, TJS +69–96 бп на горизонте 5/10 дней"),
    ]
    y = 2.35
    for label, value in rows:
        card(s, 6.83, y, 5.85, 0.68, SURFACE_ALT, radius=0.04, shadow=False)
        txt(s, label, 7.03, y + 0.07, 2.2, 0.28,
            size=12, bold=True, color=INK)
        txt(s, value, 9.28, y + 0.07, 3.2, 0.52,
            size=11.5, color=INK2)
        y += 0.76

    slide_num(s, 4, total=4)
    return s


# =============================================================================
# СБОРКА
# =============================================================================
def main():
    slide_01()
    slide_02()
    slide_03()
    slide_04()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(os.path.dirname(script_dir), "01_presentation.pptx")
    prs.save(out_path)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
