#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор отчета по учебному проекту «Национальная игра Алтай Шатра».

Собирает документ Отчет.docx на основе:
  - неизменного титульного листа из Отчет.docx.bak (первые 25 абзацев);
  - реальных фактов, извлечённых из кода проекта (backend/, game_engine/,
    crates/shatra-engine/, services/shatra-ai/, frontend/, docs/, alembic/);
  - реальных скриншотов и схем из report_assets/img/ (см. screenshots.spec.js
    и generate_diagrams.py);
  - реальных результатов прогонов тестов (см. README раздела 4.2 ниже).

Оформление — по ГОСТ 7.32-2017 (см. .cursor/rules/gost-report-editor.md):
  Times New Roman 14pt, интервал 1.5, абзацный отступ 1.25 см, выравнивание
  по ширине, поля 30/10/20/20 мм, заголовки разделов заглавными по центру.

СОДЕРЖАНИЕ собирается как статический список с точными номерами страниц
(двухпроходная сборка: черновой рендер в PDF -> определение страниц по
заголовкам -> финальная сборка с подставленными номерами). Титульный лист
(секция 1 документа) не редактируется вообще — новый контент добавляется
в отдельной секции 2 с разрывом страницы и собственными полями/колонтитулом.

Запуск:
    source report_assets/.venv/bin/activate
    python3 report_assets/build_report.py
"""
import copy
import os
import subprocess
import sys

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.styles.style import StyleFactory

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG = os.path.join(HERE, "img")
SOURCE_DOCX = os.path.join(ROOT, "Отчет.docx.bak")
OUTPUT_DOCX = os.path.join(ROOT, "Отчет.docx")
DRAFT_PDF = os.path.join(HERE, "_draft.pdf")
FINAL_PDF = os.path.join(HERE, "_final_check.pdf")

FONT = "Times New Roman"
SZ = Pt(14)

# ---------------------------------------------------------------------------
# Счётчики рисунков/таблиц (сквозная нумерация по всему документу)
# ---------------------------------------------------------------------------
FIG_COUNTER = [0]
TAB_COUNTER = [0]
doc_global = None
HEADING_STYLES = {}  # заполняется в setup_styles(): {1: Style, 2: Style}


def get_style_by_exact_name(doc, name):
    """Обходит несовпадение UI/internal имён встроенных стилей Word в этом
    конкретном файле (см. BabelFish.ui2internal) — ищет стиль по точному
    значению w:name напрямую в XML, а не через doc.styles[name]."""
    style_elm = doc.styles.element.get_by_name(name)
    if style_elm is None:
        raise KeyError(f"style '{name}' not found in document")
    return StyleFactory(style_elm)


def next_fig():
    FIG_COUNTER[0] += 1
    return FIG_COUNTER[0]


def next_tab():
    TAB_COUNTER[0] += 1
    return TAB_COUNTER[0]


# ---------------------------------------------------------------------------
# Низкоуровневые помощники OOXML
# ---------------------------------------------------------------------------
def _set_run_font(run, size=SZ, bold=False, italic=False):
    run.font.name = FONT
    run.font.size = size
    run.font.bold = bold
    run.font.italic = italic
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), FONT)


def set_outline_level(paragraph, level):
    pPr = paragraph._p.get_or_add_pPr()
    el = pPr.find(qn("w:outlineLvl"))
    if el is None:
        el = OxmlElement("w:outlineLvl")
        pPr.append(el)
    el.set(qn("w:val"), str(level))


def add_page_number_field(paragraph):
    run = paragraph.add_run()
    _set_run_font(run)
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE \\* MERGEFORMAT "
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    fld_txt = OxmlElement("w:t")
    fld_txt.text = "2"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    r = run._r
    r.append(fld_begin)
    r.append(instr)
    r2 = copy.deepcopy(r)
    for c in list(r2):
        r2.remove(c)
    r2.append(fld_sep)
    r2.append(fld_txt)
    paragraph._p.append(r2)
    r3 = copy.deepcopy(r2)
    for c in list(r3):
        r3.remove(c)
    r3.append(fld_end)
    paragraph._p.append(r3)


# ---------------------------------------------------------------------------
# Стили документа (безопасно: титульный лист использует прямое форматирование
# и НЕ ссылается на изменяемые ниже стили — проверено инспекцией Отчет.docx)
# ---------------------------------------------------------------------------
def setup_styles(doc):
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = SZ
    rpr = normal.element.get_or_add_rPr()
    rFonts = rpr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rpr.append(rFonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), FONT)
    pf = normal.paragraph_format
    pf.first_line_indent = Cm(1.25)
    pf.line_spacing = 1.5
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for lvl, size, in ((1, SZ), (2, SZ)):
        st = get_style_by_exact_name(doc, f"Heading {lvl}")
        HEADING_STYLES[lvl] = st
        st.font.name = FONT
        st.font.size = size
        st.font.bold = True
        st.font.color.rgb = RGBColor(0, 0, 0)
        st.paragraph_format.space_before = Pt(0)
        st.paragraph_format.space_after = Pt(0)
        st.paragraph_format.line_spacing = 1.5
        st.paragraph_format.keep_with_next = True


def new_gost_section(doc):
    """Новая секция с полями по ГОСТ (30/10/20/20 мм) и разрывом страницы."""
    section = doc.add_section(WD_SECTION.NEW_PAGE)
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(1.0)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.header_distance = Cm(1.25)
    section.footer_distance = Cm(1.25)
    section.footer.is_linked_to_previous = False
    section.header.is_linked_to_previous = False
    for p in list(section.footer.paragraphs):
        p.text = ""
    fp = section.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fp.paragraph_format.line_spacing = 1.0
    fp.paragraph_format.first_line_indent = Cm(0)
    add_page_number_field(fp)
    return section


# ---------------------------------------------------------------------------
# Помощники для контента
# ---------------------------------------------------------------------------
def add_heading1(doc, text, page_break_before=True):
    p = doc.add_paragraph(style=HEADING_STYLES[1])
    if page_break_before:
        p.paragraph_format.page_break_before = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    set_outline_level(p, 0)
    run = p.add_run(text.upper())
    _set_run_font(run, bold=True)
    return p


def add_heading2(doc, text):
    p = doc.add_paragraph(style=HEADING_STYLES[2])
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent = Cm(1.25)
    p.paragraph_format.space_before = Pt(6)
    set_outline_level(p, 1)
    run = p.add_run(text)
    _set_run_font(run, bold=True)
    return p


def add_body(doc, text, indent=True, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=0):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(1.25) if indent else Cm(0)
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(space_after)
    p.alignment = align
    run = p.add_run(text)
    _set_run_font(run)
    return p


def add_bullet(doc, text, num=None):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.left_indent = Cm(1.25)
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(0)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    prefix = f"{num}) " if num else "– "
    run = p.add_run(prefix + text)
    _set_run_font(run)
    return p


def add_figure(doc, filename, caption, width_cm=14, num=None):
    path = os.path.join(IMG, filename)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run()
    run.add_picture(path, width=Cm(width_cm))
    n = num if num is not None else next_fig()
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.first_line_indent = Cm(0)
    cap.paragraph_format.space_after = Pt(12)
    cap.paragraph_format.line_spacing = 1.0
    run2 = cap.add_run(f"Рисунок {n} — {caption}")
    _set_run_font(run2)
    return n


def add_table_caption(doc, title, num=None):
    n = num if num is not None else next_tab()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(f"Таблица {n} — {title}")
    _set_run_font(run)
    return n


def style_table_gost(table, header_bold=True):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = doc_global.styles["Table Grid"]
    for ri, row in enumerate(table.rows):
        for cell in row.cells:
            cell.vertical_alignment = 1
            for p in cell.paragraphs:
                p.paragraph_format.first_line_indent = Cm(0)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.0
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in p.runs:
                    _set_run_font(run, size=Pt(12), bold=(header_bold and ri == 0))


def add_table(doc, headers, rows, widths_cm=None):
    table = doc.add_table(rows=1, cols=len(headers))
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
    for r in rows:
        cells = table.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = str(v)
    style_table_gost(table)
    if widths_cm:
        for i, w in enumerate(widths_cm):
            for row in table.rows:
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_appendix_heading(doc, letter, title):
    p = doc.add_paragraph(style=HEADING_STYLES[1])
    p.paragraph_format.page_break_before = True
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    set_outline_level(p, 0)
    run = p.add_run(f"ПРИЛОЖЕНИЕ {letter}")
    _set_run_font(run, bold=True)
    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.paragraph_format.first_line_indent = Cm(0)
    p2.paragraph_format.space_after = Pt(12)
    run2 = p2.add_run(title)
    _set_run_font(run2, italic=True)
    return p


def add_code_listing(doc, code, source_note):
    p_note = doc.add_paragraph()
    p_note.paragraph_format.first_line_indent = Cm(1.25)
    p_note.paragraph_format.line_spacing = 1.5
    run = p_note.add_run(source_note)
    _set_run_font(run, italic=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(0)
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), "F2F2F2")
    pPr.append(shd)
    lines = code.strip("\n").split("\n")
    for i, line in enumerate(lines):
        run = p.add_run((line if line else " ") + ("\n" if i < len(lines) - 1 else ""))
        run.font.name = "Liberation Mono"
        run.font.size = Pt(10)
        rPr = run._element.get_or_add_rPr()
        rFonts = OxmlElement("w:rFonts")
        for attr in ("w:ascii", "w:hAnsi", "w:cs"):
            rFonts.set(qn(attr), "Liberation Mono")
        rPr.append(rFonts)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


# ---------------------------------------------------------------------------
# СОДЕРЖАНИЕ (статический список с точными номерами страниц)
# ---------------------------------------------------------------------------
TOC_ENTRIES = [
    (0, "ВВЕДЕНИЕ"),
    (0, "1 АНАЛИЗ ПРЕДМЕТНОЙ ОБЛАСТИ"),
    (1, "1.1 Правила игры «Шатра»"),
    (1, "1.2 Обзор аналогов онлайн-платформ настольных игр"),
    (1, "1.3 Обоснование выбора технологий"),
    (0, "2 ПРОЕКТИРОВАНИЕ СИСТЕМЫ"),
    (1, "2.1 Требования к системе"),
    (1, "2.2 Архитектура системы"),
    (1, "2.3 Схема базы данных"),
    (1, "2.4 Протокол взаимодействия клиент-сервер"),
    (1, "2.5 UX-решения и локализация интерфейса"),
    (0, "3 РЕАЛИЗАЦИЯ СИСТЕМЫ"),
    (1, "3.1 Backend: FastAPI и WebSocket-протокол"),
    (1, "3.2 Игровой движок: правила игры"),
    (1, "3.3 AI-сервис: вычисление ходов"),
    (1, "3.4 Frontend: React-приложение"),
    (1, "3.5 Инфраструктура и контейнеризация"),
    (1, "3.6 Локализация интерфейса"),
    (1, "3.7 Звуковая подсистема"),
    (1, "3.8 Рейтинговая система Elo"),
    (0, "4 ТЕСТИРОВАНИЕ И РЕЗУЛЬТАТЫ"),
    (1, "4.1 Виды и покрытие тестов"),
    (1, "4.2 Результаты прогонов тестов"),
    (1, "4.3 Развертывание и мониторинг"),
    (0, "ЗАКЛЮЧЕНИЕ"),
    (0, "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ"),
    (0, "ПРИЛОЖЕНИЕ А"),
    (0, "ПРИЛОЖЕНИЕ Б"),
    (0, "ПРИЛОЖЕНИЕ В"),
]


def build_toc(doc, page_map):
    add_heading1(doc, "СОДЕРЖАНИЕ")
    for level, text in TOC_ENTRIES:
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(0)
        p.paragraph_format.left_indent = Cm(1.25) if level == 1 else Cm(0)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.15
        tab_stops = p.paragraph_format.tab_stops
        right_pos = Cm(17.0) - (Cm(1.25) if level == 1 else Cm(0))
        tab_stops.add_tab_stop(right_pos, WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        page = page_map.get(text, "…")
        run = p.add_run(f"{text}\t{page}")
        _set_run_font(run, bold=(level == 0))
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


# ---------------------------------------------------------------------------
# ВВЕДЕНИЕ
# ---------------------------------------------------------------------------
def build_intro(doc):
    add_heading1(doc, "ВВЕДЕНИЕ")
    add_body(
        doc,
        "Алтайская национальная игра «Шатра» относится к традиционным настольным "
        "играм тюркских народов Южной Сибири и представляет собой разновидность "
        "игры на захват фигур соперника на доске нестандартной формы. В отличие "
        "от шахмат, шашек и других массовых настольных игр, «Шатра» не имеет "
        "широкого распространения в цифровой среде: на момент выполнения работы "
        "специализированные онлайн-платформы для игры в «Шатра» в открытом "
        "доступе не обнаружены, тогда как правила игры зафиксированы главным "
        "образом в неформализованном виде (устная традиция, разрозненные "
        "текстовые описания в сообществах, посвящённых алтайской культуре [3]). "
        "Актуальность работы обусловлена необходимостью сохранения национальной "
        "игры в цифровом виде: перевод правил в программно проверяемую форму, "
        "снятие географических ограничений для игроков и создание условий для "
        "популяризации игры среди широкой аудитории, включая возможность "
        "тренировки против компьютерного соперника.",
    )
    add_body(
        doc,
        "Целью работы является разработка и реализация онлайн-платформы для "
        "игры в «Шатра», обеспечивающей партии между двумя пользователями "
        "в реальном времени, партии пользователя с компьютерным соперником, "
        "учёт результатов партий и рейтинга участников.",
    )
    add_body(doc, "Для достижения поставленной цели решались следующие задачи:")
    add_bullet(doc, "изучить и формализовать правила игры «Шатра» в виде программно проверяемой модели (доска, фигуры, допустимые ходы, обязательные взятия, условия окончания партии);", 1)
    add_bullet(doc, "спроектировать архитектуру системы: взаимодействие клиента и сервера, протокол обмена сообщениями, схему хранения данных;", 2)
    add_bullet(doc, "реализовать серверную часть (backend), игровой движок, сервис компьютерного соперника, клиентское веб-приложение и инфраструктуру развёртывания;", 3)
    add_bullet(doc, "обеспечить тестовое покрытие реализованных компонентов и проверить работоспособность системы в развёрнутом виде.", 4)
    add_body(
        doc,
        "Методы решения задач включают анализ предметной области и существующих "
        "аналогов, проектирование клиент-серверной архитектуры с протоколом "
        "WebSocket для обмена состоянием партии в реальном времени, разработку "
        "программного обеспечения на языках Python, TypeScript/JavaScript и "
        "Rust, а также модульное, контрактное и интеграционное тестирование "
        "средствами pytest, vitest, Playwright и cargo test.",
    )
    add_body(
        doc,
        "Объектом исследования выступает процесс цифровизации традиционной "
        "настольной игры, предметом — архитектура и программная реализация "
        "многопользовательской веб-платформы для игры в «Шатра» с поддержкой "
        "компьютерного соперника.",
    )


# ---------------------------------------------------------------------------
# РАЗДЕЛ 1. АНАЛИЗ ПРЕДМЕТНОЙ ОБЛАСТИ
# ---------------------------------------------------------------------------
def build_section1(doc):
    add_heading1(doc, "1 Анализ предметной области")

    add_heading2(doc, "1.1 Правила игры «Шатра»")
    add_body(
        doc,
        "Игра ведётся на доске из 62 пронумерованных клеток. Клетки 1–9 "
        "образуют крепость чёрных, клетка 10 — ворота крепости чёрных; "
        "клетки 54–62 образуют крепость белых, клетка 53 — ворота крепости "
        "белых. Клетки 11–52 составляют большое поле. В программной модели "
        "доска представлена словарём, в котором ключом служит номер клетки, "
        "а значением — фигура, находящаяся на клетке (или отсутствие фигуры). "
        "В игре участвуют фигуры трёх типов: шатра, бий и батыр. В начальной "
        "позиции шатры и бий каждой стороны расставлены в собственной "
        "крепости и в большом поле (чёрные шатры — на клетках 11–24, белые "
        "шатры — на клетках 39–52), бии стоят в воротах своих крепостей "
        "(чёрный бий — на клетке 10, белый — на клетке 53); батыры в "
        "начальной расстановке отсутствуют.",
    )
    add_body(
        doc,
        "Каждый тип фигуры обладает собственным набором допустимых ходов и "
        "взятий, зафиксированным в справочных словарях (game_engine/"
        "dictionaries.py): ходы шатры и бия задаются как отображение "
        "«исходная клетка → список доступных клеток», взятия шатрой и бием "
        "— как отображение «исходная клетка → {клетка приземления: клетка "
        "взятой фигуры}». Батыр, в отличие от шатры и бия, перемещается по "
        "трём фиксированным направлениям и может как совершать ход на "
        "ближнюю свободную клетку направления, так и перепрыгивать через "
        "клетку с не более чем одной фигурой соперника, взятием снимая её с "
        "доски. Батыр появляется на доске не с начала партии: белая шатра, "
        "достигшая клетки 1, 2 или 3, либо чёрная шатра, достигшая клетки "
        "60, 61 или 62, превращается в батыра. Ввод шатры и бия из "
        "собственной крепости в большое поле подчиняется строгому порядку "
        "очерёдности клеток: для чёрных — от клетки 9 к клетке 1, для белых "
        "— от клетки 54 к клетке 62; кроме того, фигуре запрещено "
        "занимать собственные ворота или крепость ходом либо взятием, если "
        "там уже находится собственная шатра.",
    )
    add_body(
        doc,
        "Взятие фигуры соперника обязательно для шатры и батыра при "
        "наличии такой возможности; бий обязан сделать ход, но не обязан "
        "совершать взятие, если оно доступно. При одновременной "
        "возможности взятия несколькими типами фигур обычный (не берущий) "
        "ход бием запрещён — обязательно выполняется взятие одной из "
        "фигур. Если после взятия шатрой или батыром эта же фигура может "
        "продолжить серию взятий, продолжение обязательно; для бия "
        "продолжение серии взятий не обязательно, и ход может быть "
        "передан после одного взятия. В пределах одной серии множественных "
        "взятий батыру запрещено перепрыгивать через уже взятые в этой "
        "серии фигуры соперника. Партия завершается победой стороны, "
        "снявшей с доски бия соперника, либо ничьей — по соглашению "
        "игроков, при троекратном повторении позиции, либо если после "
        "того, как на доске остались только два бия, было сделано три "
        "хода без изменения этого соотношения.",
    )
    add_body(
        doc,
        "Изложенные правила формализованы в модуле game_engine (пакет "
        "правил на языке Python) и продублированы независимой реализацией "
        "на TypeScript (packages/shatra-rules) для мгновенной проверки "
        "ходов на клиенте, а также реализацией на Rust (crates/"
        "shatra-engine) для сервиса компьютерного соперника. Совпадение "
        "поведения всех трёх реализаций подтверждается контрактными "
        "тестами (раздел 4.1).",
    )

    add_heading2(doc, "1.2 Обзор аналогов онлайн-платформ настольных игр")
    add_body(
        doc,
        "Специализированных цифровых версий игры «Шатра» с многопользовательским "
        "режимом в открытом доступе на момент выполнения работы не выявлено: "
        "правила игры зафиксированы преимущественно в неформализованном виде — "
        "текстовое описание в сообществах, посвящённых алтайской культуре, "
        "было использовано как источник для формализации правил [3]. При этом "
        "для распространённых настольных игр (шахматы, шашки, го, реверси) "
        "существует развитая экосистема онлайн-платформ, архитектурные решения "
        "которых применимы к рассматриваемой задаче. Платформа lichess.org "
        "— открытый (исходный код опубликован под лицензией AGPL-3.0) сервис "
        "для игры в шахматы в реальном времени — реализует клиент-серверную "
        "архитектуру с WebSocket-протоколом, разделением серверного "
        "(валидация ходов) и клиентского (мгновенная подсветка ходов без "
        "ожидания ответа сервера) движков правил, что рассматривалось как "
        "образец при проектировании WebSocket-протокола и клиентского "
        "движка правил настоящей системы (см. docs/architecture/"
        "TARGET_ARCHITECTURE_V2.md). Платформы chess.com и Board Game Arena "
        "также построены на клиент-серверной модели, однако являются "
        "закрытыми коммерческими продуктами и не публикуют детали "
        "внутренней архитектуры.",
    )
    add_body(
        doc,
        "Сопоставление изученных аналогов позволяет выделить общий для "
        "предметной области набор архитектурных решений: канал реального "
        "времени (WebSocket) для передачи ходов, разделение ответственности "
        "между сервером (источник истины) и клиентом (немедленная "
        "визуальная реакция), учёт партий и рейтинга участников, поддержка "
        "игры с компьютерным соперником. Эти решения приняты за основу при "
        "проектировании системы (раздел 2) с учётом специфики доски "
        "«Шатра» нестандартной формы (62 клетки, крепости, обязательные "
        "серии взятий), не имеющей прямых аналогов в перечисленных играх.",
    )

    add_heading2(doc, "1.3 Обоснование выбора технологий")
    add_body(
        doc,
        "Для серверной части выбран язык Python и асинхронный "
        "веб-фреймворк FastAPI, обеспечивающий типизацию входных данных "
        "через Pydantic, встроенную поддержку WebSocket-соединений и "
        "асинхронного взаимодействия с базой данных, а также широкую "
        "экосистему сопутствующих библиотек (SQLAlchemy, Alembic, pytest). "
        "Клиентское приложение реализовано на React с использованием "
        "сборщика Vite, что обеспечивает компонентную модель интерфейса, "
        "быстрый цикл разработки (Hot Module Replacement) и зрелую "
        "экосистему тестирования (vitest для модульных тестов, Playwright "
        "для сквозных сценариев). Для сервиса компьютерного соперника "
        "выбран язык Rust: минимаксный поиск с альфа-бета-отсечением "
        "требователен к производительности вычислений, а гарантии "
        "безопасности памяти и статическая типизация Rust снижают риск "
        "ошибок в вычислительном ядре; взаимодействие сервиса с backend "
        "организовано через gRPC (библиотека tonic), обеспечивающий "
        "компактный бинарный протокол и строгий контракт (protobuf).",
    )
    add_body(
        doc,
        "В качестве основного хранилища данных выбран PostgreSQL — "
        "реляционная СУБД, обеспечивающая целостность связей между "
        "пользователями, рейтингом и архивом завершённых партий, а миграции "
        "схемы выполняются через Alembic. Для хранения состояния активных "
        "партий и присутствия пользователей выбран Redis — хранилище "
        "«ключ-значение» с поддержкой TTL, соответствующее временной "
        "природе игровой сессии (партия завершается или удаляется по "
        "истечении времени ожидания). Развёртывание многокомпонентной "
        "системы (backend, AI-сервис, база данных, кэш, средства "
        "мониторинга) выполняется через Docker Compose, что обеспечивает "
        "воспроизводимость окружения разработки и продуктивного контура "
        "одним набором конфигурационных файлов.",
    )


# ---------------------------------------------------------------------------
# РАЗДЕЛ 2. ПРОЕКТИРОВАНИЕ СИСТЕМЫ
# ---------------------------------------------------------------------------
def build_section2(doc):
    add_heading1(doc, "2 Проектирование системы")

    add_heading2(doc, "2.1 Требования к системе")
    add_body(doc, "К системе предъявлены следующие функциональные требования:")
    for i, t in enumerate([
        "регистрация пользователя и вход по логину/паролю, а также анонимная "
        "игра без регистрации;",
        "создание игровой комнаты с выбором цвета фигур, контроля времени и "
        "рейтинговости партии, поиск и присоединение к открытым комнатам;",
        "проведение партии в реальном времени с подсветкой доступных ходов, "
        "обязательных взятий и серий взятий;",
        "партия против компьютерного соперника с выбором сложности;",
        "текстовый чат между участниками партии;",
        "контроль времени партии (таймер с добавкой секунд за ход);",
        "сохранение результатов завершённых партий и рейтинга Elo участников;",
        "переключение языка интерфейса;",
        "административная панель для просмотра статистики и обращений "
        "пользователей;",
        "корректная работа интерфейса на мобильных устройствах.",
    ], start=1):
        add_bullet(doc, t, i)
    add_body(doc, "Нефункциональные требования включают:")
    for i, t in enumerate([
        "развёртывание системы одной командой средствами Docker Compose;",
        "устойчивость к временному разрыву соединения — переподключение "
        "клиента с восстановлением состояния партии в течение окна ожидания;",
        "наблюдаемость: структурированные логи, метрики Prometheus, сбор "
        "ошибок клиента и сервера (Sentry);",
        "базовую защиту: аутентификация по JWT, ограничение доступа к "
        "служебным эндпоинтам, ограничение частоты запросов.",
    ], start=1):
        add_bullet(doc, t, i)

    add_heading2(doc, "2.2 Архитектура системы")
    n1 = next_fig()
    add_body(
        doc,
        "Система построена по клиент-серверной архитектуре с выделением "
        "вычислительно сложной логики компьютерного соперника в отдельный "
        "сервис. Общая схема взаимодействия компонентов представлена на "
        f"рисунке {n1}.",
    )
    add_figure(doc, "architecture.png", "Архитектура системы «Шатра»", width_cm=15, num=n1)
    add_body(
        doc,
        "Клиентское React-приложение обменивается с сервером данными по "
        "двум каналам: REST API (аутентификация, создание и поиск комнат, "
        "административные операции) и WebSocket-соединение (/ws/v2/{room_id}/) "
        "для обмена состоянием партии в реальном времени. Сервер на FastAPI "
        "хранит состояние активных партий и присутствия пользователей в "
        "Redis, персистентные данные (учётные записи, архив завершённых "
        "партий, рейтинг) — в PostgreSQL. Ходы, требующие поиска "
        "(партии с компьютерным соперником), передаются по gRPC в сервис "
        "shatra-ai, реализованный на Rust; при недоступности gRPC-сервиса "
        "предусмотрен резервный расчёт хода средствами Python-реализации "
        "движка непосредственно в backend. Подсистема наблюдаемости "
        "(Prometheus, Grafana, Loki, Promtail) собирает метрики и логи "
        "всех контейнеров.",
    )

    add_heading2(doc, "2.3 Схема базы данных")
    n2 = next_fig()
    add_body(
        doc,
        "Персистентные данные системы хранятся в пяти таблицах PostgreSQL, "
        "описанных SQLAlchemy-моделями (backend/db/models.py) и созданных "
        "14 миграциями Alembic (alembic/versions/001…014). ER-диаграмма "
        f"базы данных представлена на рисунке {n2}.",
    )
    add_figure(doc, "er_diagram.png", "ER-диаграмма базы данных PostgreSQL", width_cm=10.5, num=n2)
    tn1 = add_table_caption(doc, "Назначение таблиц базы данных")
    add_table(
        doc,
        ["Таблица", "Назначение"],
        [
            ["users", "учётные записи, рейтинг Elo, счётчик рейтинговых партий, признак администратора"],
            ["refresh_tokens", "долгоживущие токены обновления сессии (хэш токена, срок действия, отзыв)"],
            ["finished_games", "архив завершённых партий: состав участников, победитель, причина завершения, история ходов, изменение рейтинга"],
            ["presence_sessions", "сессии присутствия пользователей (в том числе анонимных) для учёта онлайн-активности"],
            ["bug_reports", "обращения пользователей об ошибках со скриншотом и контекстом страницы"],
        ],
        widths_cm=[4, 13],
    )
    add_body(
        doc,
        "Таблица finished_games связана внешними ключами с users по "
        "полям white_user_id и black_user_id (ON DELETE SET NULL — удаление "
        "учётной записи не приводит к потере архива партий); таблицы "
        "refresh_tokens, presence_sessions и bug_reports также ссылаются на "
        "users по внешнему ключу с приведением к NULL или каскадным "
        "удалением. Поля white_rating_delta и black_rating_delta таблицы "
        "finished_games фиксируют изменение рейтинга по итогам партии "
        "(миграции 011–013, раздел 3.8).",
    )

    add_heading2(doc, "2.4 Протокол взаимодействия клиент-сервер")
    add_body(
        doc,
        "REST API отвечает за операции, не требующие поддержания "
        "постоянного соединения: POST /rooms — создание комнаты, GET "
        "/rooms — список открытых комнат, POST /rooms/{room_id}/join — "
        "присоединение, GET /rooms/{room_id}/status — статус комнаты, "
        "а также маршруты аутентификации (/api/auth), администрирования "
        "(/api/admin) и обращений об ошибках (/api/bug-reports). "
        "Состояние партии передаётся по протоколу второй версии через "
        "единственный WebSocket-эндпоинт /ws/v2/{room_id}/. Сообщения "
        "сервера типизированы полем t: snapshot (полное состояние партии "
        "при подключении/переподключении), move (инкрементальное "
        "изменение доски по итогам хода — «дельта», а не полная доска), "
        "waiting (ожидание второго игрока), clock (обновление игровых "
        "таймеров), gameOver (результат партии), reject и error "
        "(отклонение недопустимого действия). Такой дельта-обмен снижает "
        "объём передаваемых данных по сравнению с пересылкой всей доски "
        "на каждый ход.",
    )
    n3 = next_fig()
    add_body(
        doc,
        "Диаграмма последовательности типового хода игрока представлена на "
        f"рисунке {n3}.",
    )
    add_figure(doc, "sequence_move.png", "Диаграмма последовательности хода игрока", width_cm=15, num=n3)
    add_body(
        doc,
        "Клиент выполняет предварительную (optimistic) проверку "
        "допустимости хода собственным TS-движком правил (packages/"
        "shatra-rules) и немедленно отражает результат на доске, не "
        "дожидаясь ответа сервера; итоговым источником истины остаётся "
        "серверная проверка. При рассинхронизации версии партии (счётчик "
        "ply) клиент запрашивает полный snapshot вместо частичной дельты. "
        "Диаграмма состояний игровой сессии на сервере представлена на "
        "рисунке {n4}.".format(n4=(n4 := next_fig())),
    )
    add_figure(doc, "state_diagram.png", "Диаграмма состояний игровой сессии", width_cm=17, num=n4)

    add_heading2(doc, "2.5 UX-решения и локализация интерфейса")
    n5 = next_fig()
    add_body(
        doc,
        "Главная страница приложения (лобби) предоставляет переход к "
        "созданию новой партии, просмотру списка открытых комнат и "
        "обучающему разделу с правилами игры; общий вид главной страницы "
        f"показан на рисунке {n5}.",
    )
    add_figure(doc, "01-lobby.png", "Главная страница приложения (лобби)", num=n5)
    n6 = next_fig()
    n7 = next_fig()
    add_body(
        doc,
        "При создании партии пользователь выбирает цвет фигур, контроль "
        "времени из набора предустановленных таймеров и признак "
        f"рейтинговости партии (рисунок {n6}); список открытых "
        f"комнат, ожидающих второго игрока, показан на рисунке {n7}.",
    )
    add_figure(doc, "02-create-room.png", "Настройка параметров новой партии", num=n6)
    add_figure(doc, "03-rooms-list.png", "Список открытых комнат в зале ожидания", num=n7)
    add_body(
        doc,
        "Интерфейс поддерживает переключение языка (раздел 3.6) и "
        "адаптивную раскладку для мобильных устройств с уменьшенным "
        "«облегчённым» режимом отображения доски (раздел 3.4), что "
        "отвечает требованиям кроссплатформенной доступности приложения.",
    )


# ---------------------------------------------------------------------------
# РАЗДЕЛ 3. РЕАЛИЗАЦИЯ СИСТЕМЫ
# ---------------------------------------------------------------------------
def build_section3(doc):
    add_heading1(doc, "3 Реализация системы")

    add_heading2(doc, "3.1 Backend: FastAPI и WebSocket-протокол")
    add_body(
        doc,
        "Серверная часть реализована на Python с использованием FastAPI "
        "(main.py — точка входа приложения). Жизненный цикл приложения "
        "(инициализация подключений к PostgreSQL/Redis, применение "
        "миграций, остановка фоновых задач) управляется через lifespan-"
        "контекст. Код backend разделён по пакетам, отражающим отдельные "
        "предметные области: auth (регистрация, вход, JWT- и "
        "refresh-токены), admin (административная панель и статистика), "
        "rating (рейтинг Elo и анти-фрод), bug_reports (обращения "
        "пользователей), session (обработка событий партии и подпакет v2 "
        "— WebSocket-протокол второй версии), observability (логирование, "
        "метрики Prometheus, интеграция с Sentry), db (модели SQLAlchemy и "
        "сессии). Взаимодействие с клиентом организовано через REST "
        "маршруты (создание и поиск комнат, аутентификация, "
        "администрирование) и единственный WebSocket-эндпоинт /ws/v2/"
        "{room_id}/, обслуживающий обмен состоянием партии, чат и "
        "управляющие сообщения (сдача, предложение ничьей, реванш). "
        "Middleware наблюдаемости (backend/observability/middleware.py) "
        "измеряет длительность каждого HTTP-запроса и публикует метрики в "
        "формате Prometheus по эндпоинту /metrics, доступ к которому "
        "ограничен служебным токеном; отдельный модуль rate_limit.py "
        "ограничивает частоту запросов к чувствительным маршрутам.",
    )

    add_heading2(doc, "3.2 Игровой движок: правила игры")
    add_body(
        doc,
        "Игровой движок реализован как модуль без внутреннего состояния "
        "(game_engine), принимающий на вход текущую доску и событие "
        "(намерение хода) и возвращающий результат применения правил. "
        "Модуль разделён на board.py (представление доски и клеток "
        "крепостей), domain.py (типизированные Color и PieceType), "
        "dictionaries.py (статические справочники ходов и взятий для "
        "каждой фигуры, о которых сказано в разделе 1.1), validation.py "
        "(проверка допустимости хода), hints.py (вычисление подсказок "
        "доступных ходов для подсветки на клиенте), moves.py "
        "(применение хода к доске), endgame.py (проверка условий победы, "
        "ничьей и повторения позиции) и message_codes.py (коды исходов "
        "хода, используемые для локализованных сообщений клиенту); "
        "фасадная функция handle_event связывает перечисленные модули в "
        "единый конвейер обработки хода.",
    )
    n8 = next_fig()
    add_body(
        doc,
        f"Начальная позиция партии показана на рисунке {n8}.",
    )
    add_figure(doc, "04-board-initial.png", "Игровая доска в начальной позиции", num=n8)
    n9 = next_fig()
    add_body(
        doc,
        "При выборе фигуры клиент подсвечивает доступные клетки для хода "
        f"или обязательного взятия (рисунок {n9}); правило обязательности "
        "взятия и продолжения серии взятий шатрой и батыром иллюстрируется "
        f"рисунками {n9 + 1} и {n9 + 2}, полученными на реальной "
        "легальной последовательности ходов, воспроизведённой из "
        "тестового сценария tests/test_ai.py.",
    )
    add_figure(doc, "05-move-hints.png", "Подсветка доступных ходов фигуры", num=n9)
    n10 = next_fig()
    add_figure(doc, "06-capture-chain.png", "Обязательное продолжение серии взятий", num=n10)
    n11 = next_fig()
    add_figure(doc, "07-capture-result.png", "Доска после завершения серии взятий", num=n11)
    add_body(
        doc,
        "Идентичное поведение правил на сервере (Python), клиенте "
        "(TypeScript, packages/shatra-rules) и в сервисе компьютерного "
        "соперника (Rust, crates/shatra-engine/src/rules) обеспечивается "
        "общим набором контрактных тестовых сценариев, экспортируемых "
        "из Python-эталона скриптом scripts/export_rules_contract.py в "
        "JSON-фикстуры и воспроизводимых во всех трёх реализациях "
        "(раздел 4.1).",
    )

    add_heading2(doc, "3.3 AI-сервис: вычисление ходов")
    n12 = next_fig()
    add_body(
        doc,
        "Ход компьютерного соперника вычисляется одним из двух взаимно "
        "заменяемых движков, переключаемых переменной окружения "
        "AI_ENGINE. При значении python расчёт выполняется "
        "непосредственно в backend (backend/ai.py — минимаксный поиск с "
        "альфа-бета-отсечением, backend/ai_weights.py — весовые "
        "коэффициенты оценочной функции, backend/ai_trained.py — обученные "
        "параметры). При значении grpc (используется по умолчанию в "
        "docker-compose.yml) запрос передаётся по gRPC в отдельный сервис "
        "shatra-ai, реализованный на Rust: crates/shatra-engine содержит "
        "как реализацию правил (подпакет rules), так и поисковое ядро "
        "(подпакет search — минимакс, оценочная функция, геометрия доски "
        "для эвристик), а services/shatra-ai (main.rs, grpc_impl.rs, "
        f"worker.rs, health.rs, рисунок {n12}) оформляет это ядро в виде "
        "gRPC-сервиса на базе tonic с пулом вычислительных потоков, "
        "размер которого задаётся переменной SHATRA_AI_WORKERS, и "
        "отдельным HTTP health-check эндпоинтом на axum. Контракт вызова "
        "описан в proto/shatra/ai/v1/ai.proto и генерируется в Python- и "
        "Rust-код. При ошибке или недоступности gRPC-сервиса backend "
        "автоматически переключается на резервный Python-расчёт "
        "(backend/ai_client.py); переменная AI_SHADOW_VERIFY позволяет "
        "в тестовом контуре параллельно сверять результат обоих движков "
        "без влияния на ответ пользователю.",
    )
    add_figure(doc, "08-ai-game.png", "Партия против компьютерного соперника", num=n12)

    add_heading2(doc, "3.4 Frontend: React-приложение")
    add_body(
        doc,
        "Клиентское приложение реализовано на React 19 со сборщиком Vite "
        "8, маршрутизацией react-router-dom, интернационализацией через "
        "i18next/react-i18next и сбором ошибок через Sentry. Структура "
        "src/ разделена на board/ (геометрия и отрисовка доски, включая "
        "canvas-реализацию для облегчённого режима и DOM-реализацию для "
        "полнофункционального режима), components/ (переиспользуемые "
        "элементы интерфейса), game/ (редьюсер состояния партии, "
        "обработка серверных сообщений, синхронизация), ws/v2/ "
        "(адаптер WebSocket-протокола второй версии) и engine/ "
        "(интеграция с локальным движком правил). Локальный движок "
        "правил packages/shatra-rules зеркалирует серверную "
        "Python-реализацию на TypeScript и покрыт собственным контрактным "
        "тестом (contract.test.js), что позволяет клиенту мгновенно "
        "подсвечивать доступные ходы без обращения к серверу (раздел 2.4). "
        "Доска поддерживает перетаскивание фигур (drag-and-drop) как в "
        "canvas-, так и в DOM-варианте отображения.",
    )
    n14 = next_fig()
    add_body(doc, f"Индикация игровых таймеров показана на рисунке {n14}.")
    add_figure(doc, "09-timers.png", "Индикация игровых таймеров партии", num=n14)
    n17 = next_fig()
    add_body(
        doc,
        "Раскладка интерфейса адаптируется под мобильные устройства: при "
        "уменьшении области просмотра доска и панели управления "
        f"перестраиваются в компактную вертикальную раскладку (рисунок {n17}), "
        "проверенную для типового мобильного разрешения 390×844 "
        "точек (e2e-сценарии frontend/e2e/mobile-*.spec.js, frontend/e2e/"
        "board-layout.spec.js).",
    )
    add_figure(doc, "13-mobile.png", "Мобильная версия интерфейса (390×844)", width_cm=6.5, num=n17)

    add_heading2(doc, "3.5 Инфраструктура и контейнеризация")
    add_body(
        doc,
        "Развёртывание системы описано в docker-compose.yml (окружение "
        "разработки) и docker-compose.prod.yml (продуктивный контур) и "
        "включает восемь сервисов: postgres (СУБД), redis (кэш и "
        "состояние партий), shatra-ai (Rust gRPC-сервис компьютерного "
        "соперника), app (backend FastAPI, отдающий также собранный "
        "фронтенд как статические файлы), prometheus (сбор метрик), loki "
        "и promtail (агрегация логов контейнеров) и grafana "
        "(визуализация дашбордов). Образ сервиса app собирается "
        "многоступенчатым Dockerfile: на первом этапе выполняется сборка "
        "клиентского приложения (npm run build), на втором — "
        "формируется образ с Python-зависимостями и собранными "
        "статическими файлами. Конфигурация передаётся переменными "
        "окружения (.env, включая обязательный JWT_SECRET); при старте "
        "контейнера app применяются миграции Alembic (alembic upgrade "
        "head). Продуктивный контур дополнительно включает nginx с "
        "TLS-сертификатами Let's Encrypt (certbot) и процедуру "
        "автоматического развёртывания при обновлении основной ветки "
        "репозитория (docs/DEPLOY.md).",
    )

    add_heading2(doc, "3.6 Локализация интерфейса")
    n16 = next_fig()
    add_body(
        doc,
        "Локализация реализована средствами i18next: тексты интерфейса "
        "хранятся в frontend/src/locales в виде JSON-словарей для трёх "
        "локалей — ru (русский), en (английский) и alt (алтайский язык). "
        "Модуль frontend/src/i18n/index.js определяет полный список "
        "подготовленных локалей (ALL_LOCALES) и список локалей, "
        "предлагаемых пользователю в переключателе интерфейса "
        "(SELECTABLE_LOCALES); на момент выполнения работы в "
        "переключателе доступны русская и английская локали, тогда как "
        "алтайская локаль подготовлена на уровне словаря переводов "
        "(файл alt.json содержит переводы, сопоставимые по объёму с "
        "русской локалью), но не активирована в пользовательском "
        f"переключателе до завершения вычитки переводов. Переключение "
        f"между доступными языками показано на рисунке {n16}.",
    )
    add_figure(doc, "11-locale-ru-en.png", "Переключение языка интерфейса (русский/английский)", width_cm=16, num=n16)

    add_heading2(doc, "3.7 Звуковая подсистема")
    add_body(
        doc,
        "Звуковое сопровождение партии (ход, взятие, уведомления, "
        "завершение партии) использует набор звуков piano из открытого "
        "проекта lichess-org/lila (frontend/public/sounds/piano/*.ogg, "
        "автор — Enigmahack, лицензия AGPL-3.0-or-later). Файлы "
        "загружаются скриптом scripts/copy-lichess-sounds.sh, "
        "воспроизведение и выбор звука по типу события реализованы в "
        "frontend/src/audio/playGameSound.js. Использование звуков, "
        "распространяемых на условиях AGPL-3.0-or-later, определяет "
        "выбор лицензии всего проекта — GNU AGPL v3 (файл LICENSE в "
        "корне репозитория, см. docs/SOUNDS.md).",
    )

    add_heading2(doc, "3.8 Рейтинговая система Elo")
    add_body(
        doc,
        "Рейтинг участников рассчитывается по классической формуле Elo "
        "со шкалой 400 и индивидуальным для каждого игрока динамическим "
        "K-фактором (backend/rating/elo.py). Ожидаемый результат партии "
        "для игрока A против игрока B вычисляется как "
        "E_A = 1 / (1 + 10^((R_B − R_A) / 400)); изменение рейтинга по "
        "итогам партии — ΔR = round(K·(S − E)), где S — фактический "
        "результат (1 — победа, 0.5 — ничья, 0 — поражение). Значение "
        "K-фактора определяется числом сыгранных рейтинговых партий и "
        "текущим рейтингом игрока (таблица 2).",
    )
    add_table_caption(doc, "Правила выбора K-фактора рейтинга Elo")
    add_table(
        doc,
        ["Условие", "K"],
        [
            ["менее 10 рейтинговых партий", "40"],
            ["от 10 до 19 рейтинговых партий", "30"],
            ["20 и более партий, рейтинг ≥ 2000", "10"],
            ["20 и более партий, рейтинг < 2000", "20"],
        ],
        widths_cm=[12, 5],
    )
    add_body(
        doc,
        "Новый пользователь начинает со стартовым рейтингом 1200 "
        "(DEFAULT_RATING, миграция 012_rating_default_1200, приводящая "
        "ранее заведённых пользователей со стартовым значением 1500 к "
        "новому стандарту). Партия считается рейтинговой (функция "
        "is_rated_match), если оба участника — зарегистрированные "
        "пользователи и партия проходит в публичной комнате либо в "
        "приватной комнате с явно установленным признаком rated; партии "
        "с ботом, партии с участием анонимных игроков и партии зрителей "
        "рейтинг не изменяют. Для защиты от искусственного накручивания "
        "рейтинга реализованы две анти-фрод меры (backend/rating/"
        "antifraud.py): ограничение количества засчитываемых побед над "
        "одним и тем же соперником — не более трёх приростов рейтинга за "
        "победу над одним соперником в течение скользящих 24 часов, и "
        "блокировка прироста рейтинга при подозрении на накручивание "
        "через новые учётные записи — после трёх быстрых (не более 10 "
        "ходов) побед над игроками с малым числом рейтинговых партий за "
        "24 часа последующий прирост рейтинга блокируется на "
        "аналогичный срок (поле users.rating_gain_blocked_until). "
        "Изменение рейтинга сохраняется в полях white_rating_delta и "
        "black_rating_delta таблицы finished_games в той же транзакции, "
        "что и архивирование партии.",
    )


# ---------------------------------------------------------------------------
# РАЗДЕЛ 4. ТЕСТИРОВАНИЕ И РЕЗУЛЬТАТЫ
# ---------------------------------------------------------------------------
def build_section4(doc, results):
    add_heading1(doc, "4 Тестирование и результаты")

    add_heading2(doc, "4.1 Виды и покрытие тестов")
    add_body(
        doc,
        "Проверка работоспособности системы выполняется на четырёх "
        "уровнях, соответствующих технологическому разделению компонентов. "
        "Серверная часть на Python покрыта тестами pytest (каталог "
        "tests/), сгруппированными по предметным областям: правила "
        "игрового движка (test_shatra, test_biy, test_capture_chains, "
        "test_mandatory_captures, test_batyr и другие), рейтинг Elo и "
        "анти-фрод (tests/rating/), аутентификация, административная "
        "панель, обращения об ошибках, наблюдаемость, работа с БД, "
        "серверные регрессионные сценарии (tests/server/) и интеграционные "
        "WebSocket-сценарии (tests/integration/). Клиентское React-"
        "приложение покрыто модульными тестами vitest (компоненты, "
        "редьюсер состояния партии, i18n, работа с API, хуки) и "
        "контрактным тестом локального движка правил (packages/"
        "shatra-rules/contract.test.js), сверяющим TS-реализацию правил с "
        "Python-эталоном. Сквозные пользовательские сценарии проверяются "
        "тестами Playwright (frontend/e2e/): полный цикл «лобби → партия "
        "→ ход», ходы в PvP и против бота, drag-and-drop фигур, "
        "переподключение и реванш, обработка отключения соперника, "
        "мобильные раскладки, чат в комнате. Игровой движок на Rust "
        "(crates/shatra-engine) покрыт контрактным тестом "
        "rules_contract_matches_engine (tests/contract.rs), воспроизводящим "
        "тот же набор сценариев, что и Python- и TS-реализации, на "
        "JSON-фикстурах, экспортированных из Python-эталона.",
    )

    add_heading2(doc, "4.2 Результаты прогонов тестов")
    add_body(
        doc,
        "В ходе выполнения работы были выполнены прогоны всех "
        "перечисленных наборов тестов в развёрнутом окружении разработки "
        "(docker compose up --build -d, PostgreSQL и Redis в контейнерах). "
        f"Итоговые результаты приведены в таблице 3.",
    )
    add_table_caption(doc, "Результаты прогонов тестов")
    total_t = sum(r[2] for r in results)
    total_p = sum(r[3] for r in results)
    total_f = sum(r[4] for r in results)
    rows = [[r[0], r[1], r[2], r[3], r[4]] for r in results]
    rows.append(["Итого", "—", total_t, total_p, total_f])
    add_table(
        doc,
        ["Набор тестов", "Технологии", "Всего", "Пройдено", "Не пройдено"],
        rows,
        widths_cm=[5, 5.5, 2.5, 2.5, 2.5],
    )
    add_body(
        doc,
        "Из 1158 тестов backend не пройдены два теста в модуле "
        "tests/integration/test_ws_identity_e2e.py "
        "(TestReconnectIdentity::test_reconnect_without_token_preserves_"
        "user_id и TestReconnectIdentity::test_reconnect_with_token_late_"
        "login); при повторном изолированном запуске этого модуля "
        "результат воспроизводится стабильно (concurrent.futures."
        "CancelledError при отмене асинхронной задачи тестового HTTP-"
        "клиента httpx в сценарии повторного WebSocket-подключения). "
        "Ошибка локализована в тестовой инфраструктуре сценария "
        "реконнекта (взаимодействие тестового ASGI-транспорта с "
        "долгоживущим WebSocket-соединением) и не связана с корректностью "
        "правил игры, протокола или бизнес-логики: все тесты игрового "
        "движка, рейтинга, аутентификации и административной части, а "
        "также независимые Rust- и клиентские контрактные тесты правил, "
        "пройдены полностью. Проверка сквозных пользовательских сценариев "
        "Playwright и модульных тестов клиента vitest пройдена без "
        "замечаний в полном объёме.",
    )
    n15 = next_fig()
    add_body(
        doc,
        f"Экран завершения партии, использованный при проверке отработки "
        f"условий окончания игры, показан на рисунке {n15}.",
    )
    add_figure(doc, "10-game-over.png", "Экран завершения партии", num=n15)

    add_heading2(doc, "4.3 Развертывание и мониторинг")
    add_body(
        doc,
        "Развёртывание для проверки выполнялось стандартной командой "
        "docker compose up --build -d; готовность приложения проверяется "
        "эндпоинтом /health, а собранное клиентское приложение отдаётся "
        "сервером FastAPI как статические файлы по корневому маршруту. "
        "Для наблюдения за системой в развёрнутом контуре предусмотрены: "
        "эндпоинт /metrics в формате Prometheus (частота и длительность "
        "HTTP-запросов, метрики WebSocket-соединений), дашборды Grafana, "
        "агрегация логов контейнеров через Loki и Promtail и отправка "
        "необработанных исключений клиента и сервера в Sentry. "
        "Продуктивное развёртывание (docs/DEPLOY.md) дополнительно "
        "использует nginx в роли обратного проксирующего сервера с "
        "TLS-сертификатами Let's Encrypt и выполняет резервное "
        "копирование базы данных PostgreSQL средствами pg_dump.",
    )


# ---------------------------------------------------------------------------
# ЗАКЛЮЧЕНИЕ
# ---------------------------------------------------------------------------
def build_conclusion(doc):
    add_heading1(doc, "ЗАКЛЮЧЕНИЕ")
    add_body(
        doc,
        "В ходе выполнения учебного проекта разработана и реализована "
        "онлайн-платформа для алтайской национальной игры «Шатра», "
        "решающая поставленные во введении задачи.",
    )
    add_body(
        doc,
        "Правила игры «Шатра» изучены и формализованы в виде программно "
        "проверяемой модели: доска из 62 клеток с крепостями и большим "
        "полем, три типа фигур с собственными наборами ходов и взятий, "
        "правила обязательного взятия и продолжения серии взятий, "
        "порядок ввода фигур из крепости и условия появления батыра "
        "реализованы в модуле game_engine и независимо воспроизведены "
        "в клиентском (packages/shatra-rules) и Rust-движках (crates/"
        "shatra-engine); совпадение поведения трёх реализаций "
        "подтверждено контрактными тестами. Первая задача решена в "
        "полном объёме.",
    )
    add_body(
        doc,
        "Архитектура системы спроектирована и документирована: "
        "клиент-серверное взаимодействие через REST и WebSocket-протокол "
        "второй версии с дельта-синхронизацией состояния партии, схема "
        "базы данных из пяти таблиц PostgreSQL с 14 миграциями Alembic, "
        "диаграммы последовательности хода и состояний игровой сессии. "
        "Вторая задача решена в полном объёме.",
    )
    add_body(
        doc,
        "Реализованы все заявленные компоненты системы: серверная часть "
        "на FastAPI, игровой движок правил, сервис компьютерного "
        "соперника с двумя взаимозаменяемыми реализациями (Python и Rust "
        "через gRPC), клиентское React-приложение с локальным движком "
        "правил и адаптивной раскладкой для мобильных устройств, "
        "инфраструктура контейнеризации для контуров разработки и "
        "продуктивной эксплуатации, звуковая подсистема и рейтинговая "
        "система Elo с анти-фрод защитой. Локализация интерфейса "
        "выполнена для русского и английского языков в полном объёме; "
        "перевод для алтайского языка подготовлен на уровне словаря "
        "ресурсов приложения, но не включён в пользовательский "
        "переключатель языка до завершения вычитки — эта часть третьей "
        "задачи требует дополнительного лингвистического этапа, "
        "выходящего за рамки программной реализации.",
    )
    add_body(
        doc,
        "Тестовое покрытие обеспечено на всех уровнях системы: 1158 "
        "тестов backend (pytest), 767 тестов клиентского приложения "
        "(vitest) в 62 файлах, 44 сквозных пользовательских сценария "
        "(Playwright) и контрактный тест Rust-движка правил, всего 1970 "
        "тестов, из которых пройдено 1968. Работоспособность системы "
        "проверена в реальном развёрнутом окружении Docker Compose. "
        "Четвёртая задача решена; выявленные два непройденных теста "
        "локализованы в тестовой инфраструктуре сценария "
        "WebSocket-реконнекта и не затрагивают корректность игровой "
        "логики, протокола или иных компонентов системы.",
    )
    add_body(
        doc,
        "Таким образом, цель работы — разработка и реализация "
        "онлайн-платформы для игры в «Шатра» с поддержкой партий между "
        "пользователями и партий с компьютерным соперником — достигнута. "
        "Направления дальнейшего развития системы включают: завершение "
        "и активацию алтайской локализации интерфейса; расширение "
        "функциональности предварительных ходов (premove) и турнирного "
        "режима; горизонтальное масштабирование обработки WebSocket-"
        "соединений при росте числа одновременных партий (этап 9 "
        "целевой архитектуры, docs/architecture/TARGET_ARCHITECTURE_"
        "V2.md); возможный перенос клиентского движка правил на единое "
        "ядро Rust/WebAssembly для устранения дублирования логики между "
        "TypeScript- и Rust-реализациями; дальнейшее расширение "
        "эвристик анти-фрод защиты рейтинговой системы; устранение "
        "причины двух непройденных интеграционных тестов реконнекта.",
    )


# ---------------------------------------------------------------------------
# СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ
# ---------------------------------------------------------------------------
REFERENCES = [
    "ГОСТ 7.32-2017. Отчет о научно-исследовательской работе. Структура и "
    "правила оформления. — М. : Стандартинформ, 2017. — 27 с.",
    "ГОСТ Р 7.0.100-2018. Библиографическая запись. Библиографическое "
    "описание. Общие требования и правила составления. — М. : "
    "Стандартинформ, 2018. — 124 с.",
    "Правила национальной алтайской игры «Шатра» [Электронный ресурс] // "
    "ВКонтакте : социальная сеть. — URL: "
    "https://vk.com/topic-78545460_30578723 (дата обращения: 05.09.2026). "
    "— Текст : электронный.",
    "Lichess — Free Online Chess [Электронный ресурс] : открытая "
    "шахматная платформа. — URL: https://lichess.org (дата обращения: "
    "05.09.2026). — Текст : электронный.",
    "lichess-org/lila [Электронный ресурс] : исходный код платформы "
    "Lichess // GitHub. — URL: https://github.com/lichess-org/lila (дата "
    "обращения: 05.09.2026). — Текст : электронный.",
    "Elo, A. E. The Rating of Chessplayers, Past and Present / A. E. Elo. "
    "— New York : Arco Publishing, 1978. — 224 p.",
    "FastAPI documentation [Электронный ресурс]. — URL: "
    "https://fastapi.tiangolo.com/ (дата обращения: 05.09.2026). — Текст "
    ": электронный.",
    "SQLAlchemy 2.0 Documentation [Электронный ресурс]. — URL: "
    "https://docs.sqlalchemy.org/en/20/ (дата обращения: 05.09.2026). — "
    "Текст : электронный.",
    "Alembic Documentation [Электронный ресурс]. — URL: "
    "https://alembic.sqlalchemy.org/ (дата обращения: 05.09.2026). — "
    "Текст : электронный.",
    "The Rust Programming Language [Электронный ресурс] / S. Klabnik, C. "
    "Nichols. — URL: https://doc.rust-lang.org/book/ (дата обращения: "
    "05.09.2026). — Текст : электронный.",
    "Tokio — asynchronous runtime for Rust [Электронный ресурс]. — URL: "
    "https://tokio.rs/ (дата обращения: 05.09.2026). — Текст : "
    "электронный.",
    "gRPC Documentation [Электронный ресурс]. — URL: https://grpc.io/docs/ "
    "(дата обращения: 05.09.2026). — Текст : электронный.",
    "React documentation [Электронный ресурс]. — URL: https://react.dev/ "
    "(дата обращения: 05.09.2026). — Текст : электронный.",
    "Vite documentation [Электронный ресурс]. — URL: https://vitejs.dev/ "
    "(дата обращения: 05.09.2026). — Текст : электронный.",
    "PostgreSQL 16 Documentation [Электронный ресурс]. — URL: "
    "https://www.postgresql.org/docs/16/ (дата обращения: 05.09.2026). — "
    "Текст : электронный.",
    "Redis documentation [Электронный ресурс]. — URL: https://redis.io/"
    "docs/ (дата обращения: 05.09.2026). — Текст : электронный.",
    "Playwright documentation [Электронный ресурс]. — URL: "
    "https://playwright.dev/ (дата обращения: 05.09.2026). — Текст : "
    "электронный.",
]


def build_references(doc):
    add_heading1(doc, "СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ")
    for i, ref in enumerate(REFERENCES, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Cm(-1.25)
        p.paragraph_format.left_indent = Cm(1.25)
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(4)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = p.add_run(f"{i}. {ref}")
        _set_run_font(run)


# ---------------------------------------------------------------------------
# ПРИЛОЖЕНИЯ
# ---------------------------------------------------------------------------
DOMAIN_PY_SNIPPET = '''class Color(str, Enum):
    WHITE = "белый"
    BLACK = "черный"

    @classmethod
    def from_str(cls, value: str) -> Color:
        if value == cls.WHITE.value:
            return cls.WHITE
        if value == cls.BLACK.value:
            return cls.BLACK
        raise ValueError(f"Неизвестный цвет: {value!r}")

    def opposite(self) -> Color:
        return Color.BLACK if self is Color.WHITE else Color.WHITE


class PieceType(str, Enum):
    BIY = "бий"
    SHATRA = "шатра"
    BATYR = "батыр"'''

TYPES_RS_SNIPPET = '''#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TurnInput {
    pub board: HashMap<i32, String>,
    pub mover_color: String,
    pub depth: i32,
    pub time_ms: i32,
    pub pending_batyr_captures: Vec<i32>,
    pub pending_mandatory_position: Option<i32>,
    pub position_history: HashMap<String, i32>,
    pub moves_with_two_biys: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MoveResult {
    pub message_code: String,
    pub movers_color: Option<String>,
    pub game_over: bool,
    pub winner_color: Option<String>,
    pub draw_reason: Option<String>,
    pub updated_positions: HashMap<i32, String>,
    pub captured_positions: Vec<i32>,
    pub captured_pieces: Vec<i32>,
    ...
}'''

PROTOCOL_PY_SNIPPET = '''PROTO_VERSION = 2

def is_v2_message(data: dict) -> bool:
    return isinstance(data, dict) and data.get("v") == PROTO_VERSION \\
        and isinstance(data.get("t"), str)

def build_move_event_from_game(game: dict, from_cell: int, to_cell: int) -> GameEvent:
    pending = game.get("pending_mandatory_position")
    return GameEvent(
        positions=_norm_board_keys(game.get("board", {})),
        mover_color=game["mover"],
        from_pos=from_cell,
        to_pos=to_cell,
        position_for_mandatory_capture=pending,
    )

def build_snapshot(game, room_data, my_color, *, players_info=None) -> dict:
    ...  # t = "snapshot": полное состояние партии при (пере)подключении

def build_move_delta(...) -> dict:
    ...  # t = "move": инкрементальная дельта хода (ply, updated_positions)'''


def build_appendices(doc, tree_fig_num):
    add_appendix_heading(doc, "А", "Структура каталогов проекта")
    add_body(
        doc,
        "На рисунке ниже приведена структура основных каталогов "
        "репозитория проекта, полученная построением дерева файлов "
        "(за исключением служебных каталогов сборки, зависимостей и "
        "кэшей).",
        indent=False,
    )
    add_figure(doc, "project_tree.png", "Структура каталогов проекта", width_cm=15, num=tree_fig_num)

    add_appendix_heading(doc, "Б", "Листинг: доменные типы игрового движка")
    add_body(
        doc,
        "Ниже приведены фрагменты определения базовых доменных типов "
        "игрового движка в двух независимых реализациях правил — "
        "Python (серверный эталон) и Rust (сервис компьютерного "
        "соперника), — иллюстрирующие соответствие структур данных "
        "между реализациями.",
        indent=False,
    )
    add_code_listing(doc, DOMAIN_PY_SNIPPET, "Фрагмент game_engine/domain.py (Python):")
    add_code_listing(doc, TYPES_RS_SNIPPET, "Фрагмент crates/shatra-engine/src/types.rs (Rust):")

    add_appendix_heading(doc, "В", "Листинг: протокол WebSocket v2")
    add_body(
        doc,
        "Ниже приведён фрагмент модуля построения сообщений протокола "
        "WebSocket второй версии, определяющего типы сообщений сервера "
        "(snapshot, move, waiting, clock, gameOver, reject, error) и "
        "формат передачи хода в виде дельты состояния (раздел 2.4).",
        indent=False,
    )
    add_code_listing(doc, PROTOCOL_PY_SNIPPET, "Фрагмент backend/session/v2/protocol.py (Python):")


# ---------------------------------------------------------------------------
# Реальные результаты тестовых прогонов (зафиксированы в ходе выполнения
# работы, см. вывод pytest / vitest / cargo test / playwright test)
# ---------------------------------------------------------------------------
TEST_RESULTS = [
    ("pytest (backend)", "Python / pytest", 1158, 1156, 2),
    ("vitest (frontend, 62 файла)", "JavaScript / Vitest", 767, 767, 0),
    ("cargo test -p shatra-engine", "Rust / cargo test", 1, 1, 0),
    ("Playwright e2e (13 спецификаций)", "JavaScript / Playwright", 44, 44, 0),
]


# ---------------------------------------------------------------------------
# Сборка полного документа
# ---------------------------------------------------------------------------
def build_document(page_map):
    global doc_global
    FIG_COUNTER[0] = 0
    TAB_COUNTER[0] = 0
    doc = Document(SOURCE_DOCX)
    doc_global = doc
    new_gost_section(doc)
    setup_styles(doc)
    build_toc(doc, page_map)
    build_intro(doc)
    build_section1(doc)
    build_section2(doc)
    build_section3(doc)
    build_section4(doc, TEST_RESULTS)
    build_conclusion(doc)
    build_references(doc)
    build_appendices(doc, tree_fig_num=next_fig())
    return doc


def render_pdf(docx_path, pdf_path):
    outdir = os.path.dirname(pdf_path)
    base = os.path.splitext(os.path.basename(docx_path))[0]
    subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", outdir, docx_path],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180,
    )
    generated = os.path.join(outdir, base + ".pdf")
    if generated != pdf_path:
        os.replace(generated, pdf_path)


def extract_heading_pages(pdf_path):
    """Возвращает {заголовок: номер_страницы_pdf} для точных совпадений строк."""
    out = subprocess.run(["pdftotext", "-layout", pdf_path, "-"], capture_output=True, check=True)
    text = out.stdout.decode("utf-8", errors="replace")
    pages = text.split("\x0c")
    wanted = {t for _, t in TOC_ENTRIES}
    found = {}
    for page_idx, page_text in enumerate(pages, start=1):
        for line in page_text.split("\n"):
            stripped = line.strip()
            if stripped in wanted and stripped not in found:
                found[stripped] = page_idx
    return found


def main():
    if not os.path.exists(SOURCE_DOCX):
        print(f"ОШИБКА: не найден backup титульного листа {SOURCE_DOCX}", file=sys.stderr)
        sys.exit(1)

    print("== Проход 1: черновая сборка (для определения номеров страниц) ==")
    draft = build_document(page_map={})
    draft_path = os.path.join(HERE, "_draft.docx")
    draft.save(draft_path)
    render_pdf(draft_path, DRAFT_PDF)
    page_map = extract_heading_pages(DRAFT_PDF)
    missing = [t for _, t in TOC_ENTRIES if t not in page_map]
    if missing:
        print("ВНИМАНИЕ: не найдены страницы для заголовков:", missing)

    print("== Проход 2: финальная сборка с точными номерами страниц ==")
    final = build_document(page_map=page_map)
    final.save(OUTPUT_DOCX)
    render_pdf(OUTPUT_DOCX, FINAL_PDF)
    verify_map = extract_heading_pages(FINAL_PDF)

    mismatches = {
        t: (page_map.get(t), verify_map.get(t))
        for _, t in TOC_ENTRIES
        if page_map.get(t) != verify_map.get(t)
    }
    if mismatches:
        print("ВНИМАНИЕ: страницы сместились после вставки реального СОДЕРЖАНИЯ:")
        for t, (old, new) in mismatches.items():
            print(f"  {t}: было {old}, стало {new}")
    else:
        print("Номера страниц в СОДЕРЖАНИИ подтверждены финальным рендером PDF.")

    n_pages = subprocess.run(["pdfinfo", FINAL_PDF], capture_output=True, check=True).stdout.decode()
    for line in n_pages.split("\n"):
        if line.startswith("Pages:"):
            print(line)
    print(f"Готово: {OUTPUT_DOCX}")
    print(f"Рисунков: {FIG_COUNTER[0]}, таблиц: {TAB_COUNTER[0]}")


if __name__ == "__main__":
    main()
