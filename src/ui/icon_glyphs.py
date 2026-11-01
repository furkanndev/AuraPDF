"""
AuraPDF - Vektörel İkon Motoru (Glyph Engine)
=============================================
Arayüzün tüm genel ikonları 24x24 ızgarada, 1.75 kalınlığında tek çizgi diliyle
AuraPDF'e özgü olarak çizilmiştir. Her ikon istenen boyut ve DPI'da yeniden boyanır;
renk verilmezse aktif temanın metin rengini canlı olarak kullanır.

Glyph söz dizimi (her öğe bir çizim):
  "M x y L x y H x V y Q cx cy x y C c1x c1y c2x c2y x y Z"  çizgi yolu
  "c cx cy r"                                               daire
  "r x y w h radius"                                        yuvarlak dikdörtgen
Başına "f " eklenen öğe çizilmek yerine doldurulur.
"""

import re
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QPointF, QRect, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QIconEngine, QPainter, QPainterPath, QPen, QPixmap

STROKE_WIDTH = 1.75
GRID_SIZE = 24.0
DISABLED_OPACITY = 0.38
SATURATED_ABOVE = 0.35

_DOC = "M7 3H14L19 8V19Q19 21 17 21H7Q5 21 5 19V5Q5 3 7 3Z"
_FOLD = "M14 3V8H19"
_DOC_OPEN = "M11 21H7Q5 21 5 19V5Q5 3 7 3H14L19 8V11"
_PAGE = "r 6 3 12 18 2"
_BOOK = "M12 6.5Q9 4.5 3.5 5V18.5Q9 18 12 20Q15 18 20.5 18.5V5Q15 4.5 12 6.5Z"
_BUBBLE = "M5 4.5H19Q21 4.5 21 6.5V14.5Q21 16.5 19 16.5H11L6.5 20V16.5H5Q3 16.5 3 14.5V6.5Q3 4.5 5 4.5Z"
_PENCIL = "M4 20L5 15.5L15.5 5Q17 3.5 18.5 5L19 5.5Q20.5 7 19 8.5L8.5 19Z"
_FOLDER = "M3.5 7Q3.5 5 5.5 5H9.5L11.5 7.5H18.5Q20.5 7.5 20.5 9.5V17Q20.5 19 18.5 19H5.5Q3.5 19 3.5 17Z"
_STAR = "M12 3.5L14.6 9L20.5 9.8L16.2 13.9L17.3 19.9L12 17L6.7 19.9L7.8 13.9L3.5 9.8L9.4 9Z"
_SPARK = "M11 4L12.8 9.2L18 11L12.8 12.8L11 18L9.2 12.8L4 11L9.2 9.2Z"
_LOCK = ("r 5 10.5 14 10 2.5", "M8 10.5V7.5Q8 3.5 12 3.5Q16 3.5 16 7.5V10.5")

GLYPHS: Dict[str, Tuple[str, ...]] = {
    # Temel
    "menu_hamburger": ("M4 6.5H20", "M4 12H20", "M4 17.5H20"),
    "close": ("M6 6L18 18", "M18 6L6 18"),
    "cross": ("M6 6L18 18", "M18 6L6 18"),
    "plus": ("M12 5V19", "M5 12H19"),
    "minus": ("M5 12H19",),
    "check": ("M5 12.5L10 17.5L19.5 7",),
    "dot": ("f c 12 12 3.5",),
    "chevron_left": ("M15 5.5L8.5 12L15 18.5",),
    "chevron_right": ("M9 5.5L15.5 12L9 18.5",),
    "chevron_up": ("M5.5 15L12 8.5L18.5 15",),
    "chevron_down": ("M5.5 9L12 15.5L18.5 9",),
    "first_page": ("M5.5 5V19", "M18 5.5L11.5 12L18 18.5"),
    "last_page": ("M18.5 5V19", "M6 5.5L12.5 12L6 18.5"),
    "nav_back": ("M19.5 12H5", "M11 6L5 12L11 18"),
    "nav_forward": ("M4.5 12H19", "M13 6L19 12L13 18"),
    "move_left": ("M19.5 12H5", "M11 6L5 12L11 18"),
    "move_right": ("M4.5 12H19", "M13 6L19 12L13 18"),
    "search": ("c 11 11 6.75", "M16 16L20.5 20.5"),
    "zoom_in": ("c 11 11 6.75", "M16 16L20.5 20.5", "M11 8V14", "M8 11H14"),
    "zoom_out": ("c 11 11 6.75", "M16 16L20.5 20.5", "M8 11H14"),
    "settings": ("M4 7.5H11", "M15.5 7.5H20", "c 13.25 7.5 2.25", "M4 16.5H6.5", "M11 16.5H20", "c 8.75 16.5 2.25"),
    "info": ("c 12 12 8.5", "M12 11V16.5", "f c 12 7.75 1.1"),
    "warning": ("M12 4L21 19.5H3Z", "M12 10V14.5", "f c 12 17 1"),
    "home": ("M4 11L12 4L20 11", "M6.5 9.5V18.5Q6.5 20 8 20H16Q17.5 20 17.5 18.5V9.5", "M10 20V14H14V20"),
    "refresh": ("M20 8Q17.5 4 12.5 4Q5 4 4 11", "M20 3.5V8H15.5", "M4 16Q6.5 20 11.5 20Q19 20 20 13", "M4 20.5V16H8.5"),
    "update": ("M20 8Q17.5 4 12.5 4Q5 4 4 11", "M20 3.5V8H15.5", "M4 16Q6.5 20 11.5 20Q19 20 20 13", "M4 20.5V16H8.5"),
    "undo": ("M4 9H14Q20 9 20 14.5Q20 20 14 20H9", "M8.5 4.5L4 9L8.5 13.5"),
    "redo": ("M20 9H10Q4 9 4 14.5Q4 20 10 20H15", "M15.5 4.5L20 9L15.5 13.5"),
    "rotate": ("M19.5 12Q19.5 5 12 4.5Q4.5 5 4.5 12Q4.5 19.5 12 19.5", "M16 8.5H20V4.5"),
    "rotate_ccw": ("M4.5 12Q4.5 5 12 4.5Q19.5 5 19.5 12Q19.5 19.5 12 19.5", "M8 8.5H4V4.5"),
    "swap": ("M4 8H19", "M15 4L19 8L15 12", "M20 16H5", "M9 12L5 16L9 20"),
    "share": ("c 6.5 12 2.75", "c 17.5 6 2.75", "c 17.5 18 2.75", "M9 10.5L15 7.5", "M9 13.5L15 16.5"),
    "send": ("M4 4.5L21 12L4 19.5L6.5 12Z", "M6.5 12H13"),
    "link": ("M10 14Q12.5 16.5 15 14L19 10Q21 7 18.5 5Q16 3 13.5 5.5L12.5 6.5", "M14 10Q11.5 7.5 9 10L5 14Q3 17 5.5 19Q8 21 10.5 18.5L11.5 17.5"),
    "attachment": ("M19.5 11.5L12 19Q8.5 22 5.5 19Q2.5 16 5.5 12.5L13 5Q15.5 3 17.5 5Q19.5 7 17.5 9.5L10.5 16.5Q9 17.5 8 16.5Q7 15.5 8 14L14.5 7.5",),
    "copy": ("r 8.5 8.5 12 12 2", "M15.5 8.5V5.5Q15.5 3.5 13.5 3.5H5.5Q3.5 3.5 3.5 5.5V13.5Q3.5 15.5 5.5 15.5H8.5"),
    "duplicate": ("r 8.5 8.5 12 12 2", "M15.5 8.5V5.5Q15.5 3.5 13.5 3.5H5.5Q3.5 3.5 3.5 5.5V13.5Q3.5 15.5 5.5 15.5H8.5", "M14.5 11.5V17.5", "M11.5 14.5H17.5"),
    "paste": ("r 5 5 14 16 2", "r 9 3 6 4 1.25", "M9 12H15", "M9 16H13"),
    "pin": ("M9 3.5H15", "M10 3.5V10L7 14H17L14 10V3.5", "M12 14V20.5"),
    "unpin": ("M9 3.5H15", "M10 3.5V10L7 14H17L14 10V3.5", "M12 14V20.5", "M3.5 3.5L20.5 20.5"),
    "star": (_STAR,),
    "keyboard_shortcuts": ("r 3 6 18 12 2.5", "M7 10H7.1", "M11 10H11.1", "M15 10H15.1", "M8 14.5H16"),
    "accessibility": ("c 12 12 9", "f c 12 7.5 1.25", "M7.5 10.5L12 11.5L16.5 10.5", "M12 11.5V14.5L9.5 18", "M12 14.5L14.5 18"),
    "toolbox": ("r 3.5 8 17 12 2.5", "M8.5 8V6Q8.5 4 10.5 4H13.5Q15.5 4 15.5 6V8", "M3.5 13.5H20.5", "M12 12.25V14.75"),
    "sparkle": (_SPARK, "M18.5 3.5V7", "M16.75 5.25H20.25"),
    "emoji": ("c 12 12 8.5", "M8.5 14Q12 18 15.5 14", "f c 9 10 1.1", "f c 15 10 1.1"),
    "gif": ("r 3.5 5.5 17 13 2.5", "M10.5 10H8.5Q7 10 7 12Q7 14 8.5 14H10.5V12H9", "M13 10V14", "M15.5 14V10H18", "M15.5 12H17.5"),
    "date": ("r 4 5.5 16 15 2.5", "M4 10.5H20", "M8.5 3.5V7", "M15.5 3.5V7"),
    "palette_grid": ("r 4 4 7 7 2", "r 13 4 7 7 2", "r 4 13 7 7 2", "c 16.5 16.5 3.5"),
    "eyedropper": ("M14 6L18 10", "M12.5 7.5L16.5 11.5L8 20H4V16Z", "M15 5Q17 3 19 5Q21 7 19 9L17.5 10.5L13.5 6.5Z"),
    "brush": ("M20 4Q13 8 10 12.5L12 14.5Q16.5 11.5 20 4Z", "M10 13Q6.5 13 6 16.5Q5.5 19 3.5 19.5Q8 21.5 11 19Q12.5 17 12 15"),
    # Dosya ve belge
    "folder": (_FOLDER,),
    "folder_open": ("M3.5 17V7Q3.5 5 5.5 5H9.5L11.5 7.5H17.5Q19.5 7.5 19.5 9.5V10.5", "M3.5 19L6 11.5Q6.5 10.5 7.5 10.5H20.5Q22 10.5 21.5 12L19.5 17.5Q19 19 17.5 19Z"),
    "open_file": ("M3.5 17V7Q3.5 5 5.5 5H9.5L11.5 7.5H17.5Q19.5 7.5 19.5 9.5V10.5", "M3.5 19L6 11.5Q6.5 10.5 7.5 10.5H20.5Q22 10.5 21.5 12L19.5 17.5Q19 19 17.5 19Z"),
    "save": ("M6 3.5H16L20.5 8V18.5Q20.5 20.5 18.5 20.5H5.5Q3.5 20.5 3.5 18.5V6Q3.5 3.5 6 3.5Z", "M7.5 3.5V8.5H14.5V3.5", "M7.5 20.5V14H16.5V20.5"),
    "print": ("M7 8V3.5H17V8", "r 3.5 8 17 9 2.5", "r 7 14 10 6.5 1", "M16.5 11H16.6"),
    "upload": ("M12 15.5V4.5", "M7.5 9L12 4.5L16.5 9", "M4.5 15V18Q4.5 20 6.5 20H17.5Q19.5 20 19.5 18V15"),
    "export_pdf": ("M11 21H7Q5 21 5 19V5Q5 3 7 3H14L19 8V12", _FOLD, "M13.5 17H21", "M18 14L21 17L18 20"),
    "extract": ("M11 21H7Q5 21 5 19V5Q5 3 7 3H14L19 8V12", _FOLD, "M21 17H13.5", "M16.5 14L13.5 17L16.5 20"),
    "new_document": (_DOC, _FOLD, "M12 12V18", "M9 15H15"),
    "add_page": (_DOC, _FOLD, "M12 12V18", "M9 15H15"),
    "insert_pdf": (_DOC, _FOLD, "M8.5 14.5H15.5", "M12.5 11.5L15.5 14.5L12.5 17.5"),
    "replace_page": ("r 3.5 3.5 10 13 1.75", "r 10.5 7.5 10 13 1.75"),
    "doc_properties": (_DOC, _FOLD, "M12 13V17.5", "f c 12 10.5 1"),
    "page_label": ("M4 5.5H12.5L20 13L13.5 19.5L4 11Z", "f c 8 9 1.1"),
    "page_number": (_DOC, _FOLD, "M11 12.5L12.5 11.5V17.5"),
    "bates": (_DOC, _FOLD, "M9 13H15", "M9 17H15"),
    "header_footer": (_PAGE, "M6 8H18", "M6 16H18"),
    "watermark": ("M12 3.5Q18.5 10 18.5 14.5Q18.5 20.5 12 20.5Q5.5 20.5 5.5 14.5Q5.5 10 12 3.5Z", "M8.5 14.5Q9 17.5 12 17.5"),
    "background": (_PAGE, "M6 14L10 10L18 18"),
    "compress": ("M9 3.5V9H3.5", "M15 3.5V9H20.5", "M9 20.5V15H3.5", "M15 20.5V15H20.5"),
    "combine_files": ("r 3.5 3.5 7 9 1.5", "r 13.5 3.5 7 9 1.5", "M7 12.5V15Q7 17 9 17H15Q17 17 17 15V12.5", "M12 17V21"),
    "merge": ("M6 3.5V8Q6 12 12 12Q18 12 18 8V3.5", "M12 12V20.5", "M8.5 17L12 20.5L15.5 17"),
    "split": ("M12 3.5V12", "M12 12Q6 12 6 16V20.5", "M12 12Q18 12 18 16V20.5", "M3 17.5L6 20.5L9 17.5", "M15 17.5L18 20.5L21 17.5"),
    "compare": ("r 3.5 4.5 7.5 15 1.75", "r 13 4.5 7.5 15 1.75", "M12 2.5V21.5"),
    "ocr": ("M4 8.5V6Q4 4 6 4H8.5", "M15.5 4H18Q20 4 20 6V8.5", "M20 15.5V18Q20 20 18 20H15.5", "M8.5 20H6Q4 20 4 18V15.5", "M8 9H16", "M12 9V16"),
    "redact": ("r 3.5 5.5 17 13 2.5", "f r 6.5 10 11 4 1"),
    "lock": _LOCK,
    "recovery": ("c 8 15.5 4.5", "M11.5 12L20 3.5", "M16 7.5L19 10.5", "M19 4.5L21 6.5"),
    "stamp": ("M9.5 11.5Q10 9.5 9 7.5Q8 4 12 3.5Q16 4 15 7.5Q14 9.5 14.5 11.5", "r 4.5 11.5 15 5 1.5", "M5.5 20.5H18.5"),
    "signature": ("M3 17.5Q5.5 7 8 7Q10 7.5 8 13Q6.5 18 9 16.5Q11 15 12.5 13Q13 15.5 15 14Q16 13.5 17 14.5H21", "M3 20.5H21"),
    "sign": ("M3 17.5Q5.5 7 8 7Q10 7.5 8 13Q6.5 18 9 16.5Q11 15 12.5 13Q13 15.5 15 14Q16 13.5 17 14.5H21", "M3 20.5H21"),
    "fill_sign": ("M13 21H7Q5 21 5 19V5Q5 3 7 3H14L19 8V10", _FOLD, "M14 20.5L14.5 17.5L20 12L22 14L16.5 19.5Z"),
    "prepare_form": ("r 4 4 16 16 2.5", "M8 9H16", "r 8 13 8 3 1"),
    "initials": ("M4 18L8.5 6L13 18", "M5.75 14H11.25", "M15 17.5Q17 18.5 18.5 17Q20 15 18 14Q16 13 17.5 11Q19 9.5 20.5 10.5"),
    # Görünüm
    "thumbnails": ("r 4 4 7 7 2", "r 13 4 7 7 2", "r 4 13 7 7 2", "r 13 13 7 7 2"),
    "all_grid": ("r 4 4 7 7 2", "r 13 4 7 7 2", "r 4 13 7 7 2", "r 13 13 7 7 2"),
    "organize": ("r 4 4 7 7 2", "r 13 4 7 7 2", "r 4 13 7 7 2", "M16.5 13V20", "M13 16.5H20"),
    "bookmark": ("M7 3.5H17Q18.5 3.5 18.5 5V20.5L12 16.5L5.5 20.5V5Q5.5 3.5 7 3.5Z",),
    "comments": (_BUBBLE, "M8 9H16", "M8 12.5H13"),
    "contents": ("f c 5 6.5 1.1", "f c 5 12 1.1", "f c 5 17.5 1.1", "M9 6.5H20", "M9 12H20", "M9 17.5H20"),
    "view_single": (_PAGE, "M9.5 8.5H14.5", "M9.5 12H14.5", "M9.5 15.5H14.5"),
    "view_double": ("r 3 4 8 16 1.75", "r 13 4 8 16 1.75"),
    "multiview": ("r 3.5 4.5 17 15 2.5", "M12 4.5V19.5"),
    "fit_page": ("r 6 3.5 12 17 2", "M9.5 9.5L12 7L14.5 9.5", "M9.5 14.5L12 17L14.5 14.5"),
    "fit_width": ("r 3.5 6 17 12 2", "M9.5 9.5L7 12L9.5 14.5", "M14.5 9.5L17 12L14.5 14.5"),
    "fullscreen": ("M4 9V6Q4 4 6 4H9", "M15 4H18Q20 4 20 6V9", "M20 15V18Q20 20 18 20H15", "M9 20H6Q4 20 4 18V15"),
    "reading_mode": (_BOOK, "M12 6.5V20"),
    "reading_dark": ("M20 14.5Q18 15.5 15.5 15.5Q8.5 15 8.5 8Q8.5 5.5 9.5 3.5Q3.5 6 3.5 12.5Q4 20.5 12 20.5Q18 20 20 14.5Z",),
    "reading_sepia": (_BOOK, "M12 6.5V20", "M6.5 9.5H9", "M15 9.5H17.5"),
    "speech": ("M4 9.5V14.5H8L13 18.5V5.5L8 9.5Z", "M16.5 9Q18.5 12 16.5 15", "M19 6.5Q22.5 12 19 17.5"),
    "headphones": ("M4 15V12.5Q4 4 12 4Q20 4 20 12.5V15", "r 3.5 14 4 6.5 1.5", "r 16.5 14 4 6.5 1.5"),
    "speed": ("M4.5 17.5Q2.5 9 9 5.5Q16 2.5 20 9Q21.5 13.5 19.5 17.5", "M12 14L16.5 9", "c 12 14 1.5"),
    # Çizim araçları
    "cursor": ("M6 3.5L19 11.5L12.75 13.25L9.75 19.5Z",),
    "select_rect": ("M4 8V6Q4 4 6 4H8", "M16 4H18Q20 4 20 6V8", "M20 16V18Q20 20 18 20H16", "M8 20H6Q4 20 4 18V16", "M11 4H13", "M20 11V13", "M11 20H13", "M4 11V13"),
    "select_lasso": ("M7.5 17.5Q3.5 15.5 3.5 11.5Q4 5 12 4.5Q20.5 5 20.5 11Q20 17 12 17.5Q9.5 17.5 7.5 17.5Z", "M7.5 17.5Q7 20.5 9.5 21"),
    "select_move": ("M12 3.5V20.5", "M3.5 12H20.5", "M9.5 6L12 3.5L14.5 6", "M9.5 18L12 20.5L14.5 18", "M6 9.5L3.5 12L6 14.5", "M18 9.5L20.5 12L18 14.5"),
    "select_pan": ("M8 11.5V6Q8 4.75 9.25 4.75Q10.5 4.75 10.5 6V11", "M10.5 10.5V4.5Q10.5 3.25 11.75 3.25Q13 3.25 13 4.5V10.5", "M13 10.5V5.5Q13 4.25 14.25 4.25Q15.5 4.25 15.5 5.5V11", "M15.5 11V7.5Q15.5 6.25 16.75 6.25Q18 6.25 18 7.5V14.5Q18 20.5 12.5 20.5Q9 20.5 7 17.5L4.5 13.5Q4 12.25 5.25 11.75Q6.25 11.5 7 12.5L8 14V11.5"),
    "ruler": ("M3.5 15.5L15.5 3.5L20.5 8.5L8.5 20.5Z", "M7.5 11.5L9.5 13.5", "M10.5 8.5L12.5 10.5", "M13.5 5.5L15.5 7.5"),
    "pen": (_PENCIL, "M14 6.5L17.5 10"),
    "pen_pencil": ("M4 20L5 15.5L15.5 5Q17 3.5 18.5 5L19 5.5Q20.5 7 19 8.5L8.5 19Z", "M5 15.5L8.5 19", "M13.5 7L17 10.5"),
    "pen_fountain": ("M12 21L6 12L9 4H15L18 12Z", "M12 21V14", "c 12 12.5 1.5"),
    "pen_brush": ("M20.5 3.5L12 12", "M12 12Q8 11 7 14Q6.5 17 3.5 18Q9 21.5 12 18.5Q14.5 16 13 13Z"),
    "marker": ("M6.5 14.5L15 6L18 9L9.5 17.5Z", "M6.5 14.5L4 20L9.5 17.5", "M15 6L17 4L20 7L18 9"),
    "highlighter": ("M9 15L5 19H10L13 16", "M9 15L16.5 5Q18 3.5 19.5 5Q21 6.5 19.5 8L13 16Z", "M4 21H20"),
    "eraser": ("M8.5 20L4 15.5Q3 14.5 4 13.5L13 4.5Q14 3.5 15 4.5L20 9.5Q21 10.5 20 11.5L11.5 20Z", "M8.5 9L15.5 16", "M8.5 20H20"),
    "pointer": ("c 12 12 3", "M12 3.5V6", "M12 18V20.5", "M3.5 12H6", "M18 12H20.5", "M6 6L7.75 7.75", "M16.25 16.25L18 18", "M18 6L16.25 7.75", "M7.75 16.25L6 18"),
    "text_tool": ("M5 7V5H19V7", "M12 5V19", "M9.5 19H14.5"),
    "text_box": ("r 3.5 4.5 17 15 2.5", "M8 9V8H16V9", "M12 8V16", "M10.5 16H13.5"),
    "insert": ("c 12 12 8.5", "M12 8V16", "M8 12H16"),
    "line": ("M5 19L19 5",),
    "edit": (_PENCIL, "M14 6.5L17.5 10"),
    "edit_content": ("M12.5 21H7Q5 21 5 19V5Q5 3 7 3H14L19 8V10", _FOLD, "M14 20.5L14.5 17.5L20 12L22 14L16.5 19.5Z"),
    "crop": ("M7 3V15Q7 17 9 17H21", "M3 7H15Q17 7 17 9V21"),
    "auto_crop": ("M7 3V15Q7 17 9 17H14", "M3 7H15Q17 7 17 9V12", "M19.5 15V21", "M16.5 18H22.5"),
    "underline": ("M7 4.5V11Q7 16 12 16Q17 16 17 11V4.5", "M5 20H19"),
    "strikethrough": ("M4 12H20", "M16.5 7.5Q15.5 4.5 12 4.5Q7.5 4.5 7.5 8Q7.5 10 10 11", "M8 16.5Q9 19.5 12.5 19.5Q17 19.5 17 16Q17 14.5 16 13.5"),
    "align_left": ("M4 6H20", "M4 10.5H14", "M4 15H20", "M4 19.5H14"),
    "align_center": ("M4 6H20", "M7 10.5H17", "M4 15H20", "M7 19.5H17"),
    "align_right": ("M4 6H20", "M10 10.5H20", "M4 15H20", "M10 19.5H20"),
    "align_justify": ("M4 6H20", "M4 10.5H20", "M4 15H20", "M4 19.5H20"),
    "translate": ("M4 6.5H13", "M8.5 4.5V6.5", "M11 6.5Q9.5 12 4.5 14.5", "M6 9.5Q8 13 11.5 14.5", "M12.5 20L16.5 10.5L20.5 20", "M14 17H19"),
    # Medya
    "play": ("M7.5 5L18.5 12L7.5 19Z",),
    "pause": ("r 7 5 3.25 14 1", "r 13.75 5 3.25 14 1"),
    "stop": ("r 6 6 12 12 2",),
    "skip_forward": ("M5 5.5L15.5 12L5 18.5Z", "M18.5 5.5V18.5"),
    "skip_back": ("M19 5.5L8.5 12L19 18.5Z", "M5.5 5.5V18.5"),
    "media_next": ("M5 5.5L15.5 12L5 18.5Z", "M18.5 5.5V18.5"),
    "media_prev": ("M19 5.5L8.5 12L19 18.5Z", "M5.5 5.5V18.5"),
    "image": ("r 3.5 4.5 17 15 2.5", "c 8.5 9.5 1.5", "M3.5 16.5L8.5 12.5L12 15.5L15.5 12L20.5 16.5"),
    "image_gallery": ("r 6.5 7.5 14.5 12 2", "c 11 11.5 1.25", "M6.5 16.5L10.5 13.5L13.5 16L16.5 13.5L21 17", "M3 15.5V7Q3 4.5 5.5 4.5H16"),
    "menu_image": ("r 3.5 4.5 17 15 2.5", "c 8.5 9.5 1.5", "M3.5 16.5L8.5 12.5L12 15.5L15.5 12L20.5 16.5"),
    "menu_camera": ("r 3 6.5 12.5 11 2.5", "M15.5 10.5L21 7.5V16.5L15.5 13.5"),
    "menu_audio": ("M9 18V6L19.5 4V16", "c 6.5 18 2.5", "c 17 16 2.5"),
    "menu_table": ("r 3.5 4.5 17 15 2.5", "M3.5 9.5H20.5", "M3.5 14.5H20.5", "M9.5 9.5V19.5", "M15 9.5V19.5"),
    "menu_drawing": (_PENCIL, "M14 6.5L17.5 10"),
    "menu_voice_recording": ("r 9 3.5 6 11 3", "M5.5 11.5Q5.5 18 12 18Q18.5 18 18.5 11.5", "M12 18V21"),
    "export_audio": ("M9 18V6L19.5 4V11", "c 6.5 18 2.5", "M14 17.5H21", "M18 14.5L21 17.5L18 20.5"),
    "cloud_share": ("M7 18.5Q3 18 3 14Q3 10.5 6.5 10Q7.5 5.5 12 5.5Q16.5 5.5 17.5 10Q21 10.5 21 14Q21 18 17 18.5", "M12 20.5V12.5", "M9 15.5L12 12.5L15 15.5"),
}

# Anlamı rengiyle taşıyan ikonlar: Onay, iptal ve uyarı renkleri korunur.
SEMANTIC_GLYPHS = {"check", "cross", "warning"}

# Araç ve özellik ikonları, çağıran yerin verdiği kendi rengini korur.
COLORFUL_GLYPHS = {
    "pen", "pen_pencil", "pen_fountain", "pen_brush", "marker", "highlighter", "eraser", "text_tool", "comments", "pointer", "insert", "select_rect",
    "stamp", "signature", "fill_sign", "compress", "ocr", "combine_files", "export_pdf",
    "edit_content", "organize", "lock", "redact", "compare", "prepare_form", "sparkle",
    "trash", "star", "image", "link", "watermark", "new_document", "add_page",
}

_TOKEN = re.compile(r"[MLHVQCZ]|-?\d*\.?\d+")


def _parse_path(spec: str) -> QPainterPath:
    tokens = _TOKEN.findall(spec)
    path = QPainterPath()
    x = y = 0.0
    i = 0

    def take(count: int) -> List[float]:
        nonlocal i
        values = [float(v) for v in tokens[i:i + count]]
        i += count
        return values

    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd == "M":
            x, y = take(2)
            path.moveTo(x, y)
        elif cmd == "L":
            x, y = take(2)
            path.lineTo(x, y)
        elif cmd == "H":
            x = take(1)[0]
            path.lineTo(x, y)
        elif cmd == "V":
            y = take(1)[0]
            path.lineTo(x, y)
        elif cmd == "Q":
            cx, cy, x, y = take(4)
            path.quadTo(cx, cy, x, y)
        elif cmd == "C":
            c1x, c1y, c2x, c2y, x, y = take(6)
            path.cubicTo(c1x, c1y, c2x, c2y, x, y)
        elif cmd == "Z":
            path.closeSubpath()
    return path


def _build_element(spec: str) -> Tuple[QPainterPath, bool]:
    filled = spec.startswith("f ")
    if filled:
        spec = spec[2:]
    path = QPainterPath()
    if spec.startswith("c "):
        cx, cy, r = (float(v) for v in spec[2:].split())
        path.addEllipse(QPointF(cx, cy), r, r)
    elif spec.startswith("r "):
        x, y, w, h, radius = (float(v) for v in spec[2:].split())
        path.addRoundedRect(QRectF(x, y, w, h), radius, radius)
    else:
        path = _parse_path(spec)
    return path, filled


class AuraGlyphEngine(QIconEngine):
    """Glyph'i istenen boyutta yeniden çizer; ölçekli ekranlarda pikselleşmez."""

    theme_text = "#f1f5f9"

    def __init__(self, name: str, elements: List[Tuple[QPainterPath, bool]], color: Optional[str], filled: bool = False):
        super().__init__()
        self.name = name
        self.elements = elements
        self.color = color
        self.filled = filled

    def clone(self):
        return AuraGlyphEngine(self.name, self.elements, self.color, self.filled)

    def key(self):
        return "AuraGlyphEngine"

    def paint(self, painter: QPainter, rect: QRect, mode, state):
        color = QColor(self.color or AuraGlyphEngine.theme_text)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if mode == QIcon.Mode.Disabled:
            painter.setOpacity(painter.opacity() * DISABLED_OPACITY)
        side = min(rect.width(), rect.height())
        painter.translate(rect.x() + (rect.width() - side) / 2.0, rect.y() + (rect.height() - side) / 2.0)
        painter.scale(side / GRID_SIZE, side / GRID_SIZE)
        pen = QPen(color, STROKE_WIDTH, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        for path, filled in self.elements:
            if filled or self.filled:
                painter.fillPath(path, color)
            if not filled:
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPath(path)
        painter.restore()

    def pixmap(self, size: QSize, mode, state):
        pix = QPixmap(size)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        self.paint(painter, QRect(0, 0, size.width(), size.height()), mode, state)
        painter.end()
        return pix


_PARSED: Dict[str, List[Tuple[QPainterPath, bool]]] = {}
_theme_keep: set = set()


def set_glyph_theme(text: str, accent: str, accent_hover: str, danger: str):
    """Renk verilmeyen ikonların izleyeceği metin rengini ve korunacak tema renklerini günceller."""
    AuraGlyphEngine.theme_text = text
    _theme_keep.clear()
    _theme_keep.update(c.lower() for c in (accent, accent_hover, danger))


def _visible_color(name: str, color: Optional[str]) -> Optional[str]:
    """Dekoratif doygun renkleri eler; ikon rengi tema vurgusu ve anlam renkleriyle sınırlı kalır."""
    if not color or name in SEMANTIC_GLYPHS or name in COLORFUL_GLYPHS or color.lower() in _theme_keep:
        return color
    parsed = QColor(color)
    if parsed.isValid() and parsed.hslSaturationF() > SATURATED_ABOVE:
        return None
    return color


def glyph_icon(name: str, color: Optional[str] = None, filled: bool = False) -> QIcon:
    if name not in _PARSED:
        _PARSED[name] = [_build_element(spec) for spec in GLYPHS[name]]
    return QIcon(AuraGlyphEngine(name, _PARSED[name], _visible_color(name, color), filled))


def install_glyph_icons(factory):
    """Fabrikanın glyph karşılığı olan ikon metotlarını yeni çizim diliyle değiştirir."""

    def make(name):
        def icon_method(*args, **kwargs):
            filled = bool(kwargs.pop("filled", False))
            color = kwargs.pop("color", None)
            if name == "star" and args:
                filled = bool(args[0])
                args = args[1:]
            if args and (args[0] is None or isinstance(args[0], str)):
                color = args[0]
            return glyph_icon(name, color, filled)
        return staticmethod(icon_method)

    for glyph_name in GLYPHS:
        setattr(factory, f"icon_{glyph_name}", make(glyph_name))
