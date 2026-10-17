"""
AuraPDF - Aura AI Belge Asistani Diyalogu (Aura AI Document Assistant Dialog)
=============================================================================
PDF belgeleri üzerinde yönetici özeti, kritik risk/madde/tarih tespiti ve
etkilesimli soru-cevap yapabilen modern, çok sekmeli yapay zeka asistani.
"""

import os
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QScrollArea, QWidget, QFrame,
    QStackedWidget, QProgressBar, QFileDialog, QMessageBox,
    QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon, QClipboard

from src.core.i18n import LanguageManager
from src.core.ai_assistant import AuraAiWorker, GeminiApiClient
from src.ui.dialog_theme import apply_dialog_theme
from src.ui.icons import ModernIconFactory


class AuraAiAssistantDialog(QDialog):
    """
    Aura AI Belge Asistani Diyalog Penceresi.
    Tüm temalarla (8 tema) uyumlu, asenkron QThread mimarisiyle UI dondurmayan,
    yerel veya Gemini destekli akilli belge analiz merkezi.
    """

    def __init__(self, doc_path: str, initial_action: str = "summary", main_window=None, parent=None):
        super().__init__(parent or main_window)
        self.doc_path = doc_path
        self.initial_action = initial_action  # "summary" | "risks" | "qa"
        self.main_window = main_window

        self.worker: Optional[AuraAiWorker] = None
        self.doc_analysis: Optional[Dict[str, Any]] = None

        self.setWindowTitle(LanguageManager.tr("ai_dialog_title"))
        self.resize(860, 650)
        self.setMinimumSize(750, 520)

        self._init_ui()
        apply_dialog_theme(self, parent or main_window)

        # Ilk eyleme göre sekmeyi seç
        if self.initial_action == "risks":
            self._set_tab(1)
        elif self.initial_action in ("qa", "chat"):
            self._set_tab(2)
        else:
            self._set_tab(0)

        # Analizi arka planda baslat
        QTimer.singleShot(100, self._start_analysis)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 18)
        main_layout.setSpacing(14)

        # 1. ÜST BASLIK BARI
        header_bar = QHBoxLayout()
        header_bar.setSpacing(12)

        icon_badge = QLabel(self)
        icon_badge.setFixedSize(40, 40)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_badge.setObjectName("AiDialogIconBadge")
        icon_badge.setPixmap(ModernIconFactory.icon_sparkle("#a855f7").pixmap(24, 24))
        header_bar.addWidget(icon_badge)

        v_head = QVBoxLayout()
        v_head.setSpacing(2)

        h_title = QHBoxLayout()
        h_title.setSpacing(8)

        self.lbl_title = QLabel(LanguageManager.tr("ai_dialog_title"), self)
        f_title = QFont()
        f_title.setPointSize(13)
        f_title.setBold(True)
        self.lbl_title.setFont(f_title)
        h_title.addWidget(self.lbl_title)

        self.lbl_mode_badge = QLabel(self)
        self.lbl_mode_badge.setObjectName("AiModeBadge")
        h_title.addWidget(self.lbl_mode_badge)

        h_title.addStretch(1)
        v_head.addLayout(h_title)

        doc_name = os.path.basename(self.doc_path) if self.doc_path else ""
        self.lbl_doc_info = QLabel(doc_name, self)
        self.lbl_doc_info.setObjectName("AiDocInfoLabel")
        v_head.addWidget(self.lbl_doc_info)

        header_bar.addLayout(v_head, stretch=1)

        # API Ayarlari Butonu
        self.btn_api_settings = QPushButton(LanguageManager.tr("ai_btn_api_settings"), self)
        self.btn_api_settings.setIcon(ModernIconFactory.icon_settings())
        self.btn_api_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_api_settings.clicked.connect(self._open_api_settings)
        header_bar.addWidget(self.btn_api_settings)

        main_layout.addLayout(header_bar)

        # 2. SEKME SECICI (Segmented Switcher)
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(8)

        self.btn_tab_summary = QPushButton(LanguageManager.tr("ai_tab_summary"), self)
        self.btn_tab_summary.setObjectName("AiNavTab")
        self.btn_tab_summary.setCheckable(True)
        self.btn_tab_summary.setChecked(True)
        self.btn_tab_summary.setIcon(ModernIconFactory.icon_sparkle("#a855f7"))
        self.btn_tab_summary.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_summary.clicked.connect(lambda: self._set_tab(0))
        nav_layout.addWidget(self.btn_tab_summary)

        self.btn_tab_risks = QPushButton(LanguageManager.tr("ai_tab_risks").replace("&", "&&"), self)
        self.btn_tab_risks.setObjectName("AiNavTab")
        self.btn_tab_risks.setCheckable(True)
        self.btn_tab_risks.setIcon(ModernIconFactory.icon_search("#a855f7"))
        self.btn_tab_risks.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_risks.clicked.connect(lambda: self._set_tab(1))
        nav_layout.addWidget(self.btn_tab_risks)

        self.btn_tab_chat = QPushButton(LanguageManager.tr("ai_tab_chat").replace("&", "&&"), self)
        self.btn_tab_chat.setObjectName("AiNavTab")
        self.btn_tab_chat.setCheckable(True)
        self.btn_tab_chat.setIcon(ModernIconFactory.icon_comments("#a855f7"))
        self.btn_tab_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_chat.clicked.connect(lambda: self._set_tab(2))
        nav_layout.addWidget(self.btn_tab_chat)

        nav_layout.addStretch(1)
        main_layout.addLayout(nav_layout)

        self.setStyleSheet("""
            #AiDialogIconBadge {
                background-color: rgba(168, 85, 247, 0.15);
                border: 1px solid rgba(168, 85, 247, 0.3);
                border-radius: 20px;
            }
            #AiNavTab {
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            #AiNavTab:checked {
                background-color: rgba(168, 85, 247, 0.2);
                border-color: #a855f7;
                color: #ffffff;
            }
            #AiNavTab:hover:!checked {
                background-color: rgba(255, 255, 255, 0.05);
            }
            #AiContentCard {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 12px;
            }
            #AiCardHeader {
                font-size: 13px;
                font-weight: 700;
                color: #c084fc;
                margin-bottom: 6px;
            }
            #AiRiskPill {
                background-color: rgba(239, 68, 68, 0.18);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 6px;
                padding: 2px 7px;
                font-size: 10px;
                font-weight: 700;
            }
            #AiDatePill {
                background-color: rgba(59, 130, 246, 0.18);
                color: #60a5fa;
                border: 1px solid rgba(59, 130, 246, 0.35);
                border-radius: 6px;
                padding: 2px 7px;
                font-size: 10px;
                font-weight: 700;
            }
            #AiAmountPill {
                background-color: rgba(16, 185, 129, 0.18);
                color: #34d399;
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 6px;
                padding: 2px 7px;
                font-size: 10px;
                font-weight: 700;
            }
            #AiPagePill {
                background-color: rgba(255, 255, 255, 0.08);
                color: #94a3b8;
                border-radius: 5px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: 600;
            }
            #AiChatBubbleUser {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9333ea, stop:1 #6366f1);
                color: #ffffff;
                border-radius: 12px;
                max-width: 520px;
            }
            #AiChatBubbleBot {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                max-width: 580px;
            }
            #AiSuggestChip {
                background-color: rgba(168, 85, 247, 0.1);
                border: 1px solid rgba(168, 85, 247, 0.25);
                border-radius: 12px;
                color: #c084fc;
                font-size: 11px;
                padding: 3px 10px;
            }
            #AiSuggestChip:hover {
                background-color: rgba(168, 85, 247, 0.2);
                border-color: #a855f7;
            }
            #AiChatInput {
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
            }
            #AiSendBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9333ea, stop:1 #6366f1);
                border-radius: 8px;
                border: none;
            }
            #AiSendBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #a855f7, stop:1 #7275f3);
            }
            #AiStatsBanner {
                color: #94a3b8;
                font-size: 11px;
                font-weight: 500;
                padding-bottom: 4px;
            }
        """)

        # 3. YUKLEME & DURUM ÇUBUGU (Progress Bar)
        self.progress_container = QWidget(self)
        v_prog = QVBoxLayout(self.progress_container)
        v_prog.setContentsMargins(0, 0, 0, 0)
        v_prog.setSpacing(4)

        self.lbl_status = QLabel(LanguageManager.tr("ai_status_analyzing"), self)
        self.lbl_status.setObjectName("AiStatusLabel")
        v_prog.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        v_prog.addWidget(self.progress_bar)

        main_layout.addWidget(self.progress_container)

        # 4. YIGIN ALANI (Stacked Widget)
        self.stack = QStackedWidget(self)

        # --- SAYFA 0: YONETICI OZETI ---
        self.page_summary = self._create_summary_page()
        self.stack.addWidget(self.page_summary)

        # --- SAYFA 1: KRITIK MADDELER & RISKLER ---
        self.page_risks = self._create_risks_page()
        self.stack.addWidget(self.page_risks)

        # --- SAYFA 2: SORU-CEVAP & SOHBET ---
        self.page_chat = self._create_chat_page()
        self.stack.addWidget(self.page_chat)

        main_layout.addWidget(self.stack, stretch=1)

        self._update_mode_badge()

    # =========================================================================
    # SAYFA 0: YÖNETİCİ ÖZETİ
    # =========================================================================
    def _create_summary_page(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 4, 0, 0)
        vbox.setSpacing(10)

        # Istatistik Bandi
        self.lbl_stats = QLabel(self)
        self.lbl_stats.setObjectName("AiStatsBanner")
        vbox.addWidget(self.lbl_stats)

        # Kaydirilabilir Içerik
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self.v_summary_content = QVBoxLayout(content)
        self.v_summary_content.setContentsMargins(0, 0, 8, 0)
        self.v_summary_content.setSpacing(14)

        # Genel Bakis Karti
        self.card_overview = QFrame()
        self.card_overview.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.card_overview.setObjectName("AiContentCard")
        v_ov = QVBoxLayout(self.card_overview)
        lbl_ov_title = QLabel(LanguageManager.tr("ai_card_overview"))
        lbl_ov_title.setObjectName("AiCardHeader")
        v_ov.addWidget(lbl_ov_title)
        self.txt_overview = QLabel()
        self.txt_overview.setWordWrap(True)
        self.txt_overview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        v_ov.addWidget(self.txt_overview)
        self.v_summary_content.addWidget(self.card_overview)

        # Önemli Bulgular Karti
        self.card_takeaways = QFrame()
        self.card_takeaways.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.card_takeaways.setObjectName("AiContentCard")
        self.v_takeaways = QVBoxLayout(self.card_takeaways)
        lbl_tk_title = QLabel(LanguageManager.tr("ai_card_takeaways"))
        lbl_tk_title.setObjectName("AiCardHeader")
        self.v_takeaways.addWidget(lbl_tk_title)
        self.v_summary_content.addWidget(self.card_takeaways)

        # Bölüm Dagilimi Karti
        self.card_sections = QFrame()
        self.card_sections.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.card_sections.setObjectName("AiContentCard")
        self.v_sections = QVBoxLayout(self.card_sections)
        lbl_sec_title = QLabel(LanguageManager.tr("ai_card_sections"))
        lbl_sec_title.setObjectName("AiCardHeader")
        self.v_sections.addWidget(lbl_sec_title)
        self.v_summary_content.addWidget(self.card_sections)

        self.v_summary_content.addStretch(1)
        scroll.setWidget(content)
        vbox.addWidget(scroll, stretch=1)

        # Alt Eylem Butonlari
        h_bottom = QHBoxLayout()
        h_bottom.setSpacing(10)

        self.btn_copy_summary = QPushButton(LanguageManager.tr("ai_btn_copy_summary"))
        self.btn_copy_summary.setIcon(ModernIconFactory.icon_copy())
        self.btn_copy_summary.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_summary.clicked.connect(self._copy_summary)
        h_bottom.addWidget(self.btn_copy_summary)

        self.btn_export_summary = QPushButton(LanguageManager.tr("ai_btn_export_summary"))
        self.btn_export_summary.setIcon(ModernIconFactory.icon_save())
        self.btn_export_summary.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_export_summary.clicked.connect(self._export_summary)
        h_bottom.addWidget(self.btn_export_summary)

        self.lbl_copied_toast = QLabel("")
        self.lbl_copied_toast.setStyleSheet("color: #10b981; font-weight: 600; font-size: 11px;")
        h_bottom.addWidget(self.lbl_copied_toast)

        h_bottom.addStretch(1)
        vbox.addLayout(h_bottom)

        return container

    # =========================================================================
    # SAYFA 1: KRİTİK MADDELER & RİSKLER
    # =========================================================================
    def _create_risks_page(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 4, 0, 0)
        vbox.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self.v_risks_content = QVBoxLayout(content)
        self.v_risks_content.setContentsMargins(0, 0, 8, 0)
        self.v_risks_content.setSpacing(14)

        # 1. Hukuki Koşullar & Riskler Karti
        self.card_risks_grp = QFrame()
        self.card_risks_grp.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.card_risks_grp.setObjectName("AiContentCard")
        self.v_risks_list = QVBoxLayout(self.card_risks_grp)
        lbl_r_title = QLabel(LanguageManager.tr("ai_grp_risks"))
        lbl_r_title.setObjectName("AiCardHeader")
        self.v_risks_list.addWidget(lbl_r_title)
        self.v_risks_content.addWidget(self.card_risks_grp)

        # 2. Tarihler & Süreler Karti
        self.card_dates_grp = QFrame()
        self.card_dates_grp.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.card_dates_grp.setObjectName("AiContentCard")
        self.v_dates_list = QVBoxLayout(self.card_dates_grp)
        lbl_d_title = QLabel(LanguageManager.tr("ai_grp_dates"))
        lbl_d_title.setObjectName("AiCardHeader")
        self.v_dates_list.addWidget(lbl_d_title)
        self.v_risks_content.addWidget(self.card_dates_grp)

        # 3. Parasal Tutarlar Karti
        self.card_amounts_grp = QFrame()
        self.card_amounts_grp.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.card_amounts_grp.setObjectName("AiContentCard")
        self.v_amounts_list = QVBoxLayout(self.card_amounts_grp)
        lbl_a_title = QLabel(LanguageManager.tr("ai_grp_amounts"))
        lbl_a_title.setObjectName("AiCardHeader")
        self.v_amounts_list.addWidget(lbl_a_title)
        self.v_risks_content.addWidget(self.card_amounts_grp)

        self.v_risks_content.addStretch(1)
        scroll.setWidget(content)
        vbox.addWidget(scroll, stretch=1)

        return container

    # =========================================================================
    # SAYFA 2: SORU-CEVAP & SOHBET
    # =========================================================================
    def _create_chat_page(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 4, 0, 0)
        vbox.setSpacing(10)

        # Hizli Soru Önerileri Çipleri
        h_sugg = QHBoxLayout()
        h_sugg.setSpacing(8)

        suggestions = [
            LanguageManager.tr("ai_chat_suggest_topic"),
            LanguageManager.tr("ai_chat_suggest_dates"),
            LanguageManager.tr("ai_chat_suggest_parties"),
        ]
        for s in suggestions:
            btn_s = QPushButton(s)
            btn_s.setObjectName("AiSuggestChip")
            btn_s.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_s.clicked.connect(lambda _, q=s: self._send_preset_query(q))
            h_sugg.addWidget(btn_s)

        h_sugg.addStretch(1)
        vbox.addLayout(h_sugg)

        # Mesaj Geçmisi Alani
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.chat_content = QWidget()
        self.v_chat_messages = QVBoxLayout(self.chat_content)
        self.v_chat_messages.setContentsMargins(0, 0, 8, 0)
        self.v_chat_messages.setSpacing(12)

        # Karsilama Baloncugu
        self._add_chat_bubble(LanguageManager.tr("ai_chat_welcome"), is_user=False)

        self.v_chat_messages.addStretch(1)
        self.chat_scroll.setWidget(self.chat_content)
        vbox.addWidget(self.chat_scroll, stretch=1)

        # Alt Girdi Alani
        h_input = QHBoxLayout()
        h_input.setSpacing(8)

        self.txt_query = QLineEdit()
        self.txt_query.setObjectName("AiChatInput")
        self.txt_query.setPlaceholderText(LanguageManager.tr("ai_chat_placeholder"))
        self.txt_query.returnPressed.connect(self._send_query)
        h_input.addWidget(self.txt_query, stretch=1)

        self.btn_send = QPushButton()
        self.btn_send.setObjectName("AiSendBtn")
        self.btn_send.setIcon(ModernIconFactory.icon_send("#ffffff"))
        self.btn_send.setIconSize(QSize(16, 16))
        self.btn_send.setFixedSize(38, 36)
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self._send_query)
        h_input.addWidget(self.btn_send)

        vbox.addLayout(h_input)

        return container

    # =========================================================================
    # ANALİZ VE ÇALIŞMA MANTIĞI
    # =========================================================================
    def _start_analysis(self):
        """Belge analiz iş parçacığını başlatır."""
        self.progress_container.show()
        self.progress_bar.setValue(5)
        self.lbl_status.setText(LanguageManager.tr("ai_status_analyzing"))

        lang = "tr"
        if hasattr(LanguageManager, "get_language"):
            lang = LanguageManager.get_language()

        self.worker = AuraAiWorker(
            task_type="analyze",
            doc_path=self.doc_path,
            lang=lang,
            parent=self
        )
        self.worker.progressChanged.connect(self._on_worker_progress)
        self.worker.analysisFinished.connect(self._on_analysis_finished)
        self.worker.errorOccurred.connect(self._on_worker_error)
        self.worker.start()

    def _on_worker_progress(self, percent: int, msg: str):
        self.progress_bar.setValue(percent)
        self.lbl_status.setText(msg)

    def _on_analysis_finished(self, result: Dict[str, Any]):
        self.doc_analysis = result
        self.progress_container.hide()
        self._update_mode_badge()

        doc_info = result.get("doc_info", {})
        summary = result.get("summary", {})
        risks_data = result.get("risks_data", {})
        gemini_summary = result.get("gemini_summary")

        # 1. İstatistikler
        p_count = doc_info.get("total_pages", 0)
        w_count = doc_info.get("word_count", 0)
        t_min = doc_info.get("reading_time_min", 1)
        self.lbl_stats.setText(LanguageManager.tr("ai_stats_label").format(
            pages=p_count,
            words=w_count,
            time=t_min
        ))

        # 2. Genel Bakış
        if gemini_summary:
            self.txt_overview.setText(gemini_summary)
        else:
            self.txt_overview.setText(summary.get("overview", ""))

        # 3. Önemli Bulgular
        takeaways = summary.get("key_takeaways", [])
        for t in takeaways:
            lbl = QLabel(f"• {t}")
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.v_takeaways.addWidget(lbl)

        # 4. Bölümler
        sections = summary.get("sections", [])
        for sec in sections:
            row_w = QWidget()
            h_sec = QHBoxLayout(row_w)
            h_sec.setContentsMargins(0, 2, 0, 2)
            lbl_badge = QLabel(LanguageManager.tr("ai_page_badge").format(page=sec['page']))
            lbl_badge.setObjectName("AiPagePill")
            lbl_sec = QLabel(f"<b>{sec['heading']}</b> — {sec['preview']}")
            lbl_sec.setWordWrap(True)
            h_sec.addWidget(lbl_badge)
            h_sec.addWidget(lbl_sec, stretch=1)
            self.v_sections.addWidget(row_w)

        # 5. Riskler ve Maddeler
        risks = risks_data.get("risks", [])
        if risks:
            for r in risks:
                row_w = QWidget()
                h_r = QHBoxLayout(row_w)
                h_r.setContentsMargins(0, 3, 0, 3)
                pill_cat = QLabel(r['category'])
                pill_cat.setObjectName("AiRiskPill")
                pill_page = QLabel(LanguageManager.tr("ai_page_badge").format(page=r['page']))
                pill_page.setObjectName("AiPagePill")
                lbl_clause = QLabel(r['clause'])
                lbl_clause.setWordWrap(True)
                lbl_clause.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                h_r.addWidget(pill_cat)
                h_r.addWidget(pill_page)
                h_r.addWidget(lbl_clause, stretch=1)
                self.v_risks_list.addWidget(row_w)
        else:
            lbl_none = QLabel(LanguageManager.tr("ai_no_risks"))
            lbl_none.setStyleSheet("color: #64748b; font-style: italic;")
            self.v_risks_list.addWidget(lbl_none)

        # 6. Tarihler
        dates = risks_data.get("dates", [])
        if dates:
            for d in dates:
                row_w = QWidget()
                h_d = QHBoxLayout(row_w)
                h_d.setContentsMargins(0, 2, 0, 2)
                pill_val = QLabel(d['value'])
                pill_val.setObjectName("AiDatePill")
                pill_page = QLabel(LanguageManager.tr("ai_page_badge").format(page=d['page']))
                pill_page.setObjectName("AiPagePill")
                lbl_ctx = QLabel(d['context'])
                lbl_ctx.setWordWrap(True)
                h_d.addWidget(pill_val)
                h_d.addWidget(pill_page)
                h_d.addWidget(lbl_ctx, stretch=1)
                self.v_dates_list.addWidget(row_w)
        else:
            lbl_none = QLabel(LanguageManager.tr("ai_no_dates"))
            lbl_none.setStyleSheet("color: #64748b; font-style: italic;")
            self.v_dates_list.addWidget(lbl_none)

        # 7. Tutarlar
        amounts = risks_data.get("amounts", [])
        if amounts:
            for a in amounts:
                row_w = QWidget()
                h_a = QHBoxLayout(row_w)
                h_a.setContentsMargins(0, 2, 0, 2)
                pill_val = QLabel(a['value'])
                pill_val.setObjectName("AiAmountPill")
                pill_page = QLabel(LanguageManager.tr("ai_page_badge").format(page=a['page']))
                pill_page.setObjectName("AiPagePill")
                lbl_ctx = QLabel(a['context'])
                lbl_ctx.setWordWrap(True)
                h_a.addWidget(pill_val)
                h_a.addWidget(pill_page)
                h_a.addWidget(lbl_ctx, stretch=1)
                self.v_amounts_list.addWidget(row_w)
        else:
            lbl_none = QLabel(LanguageManager.tr("ai_no_amounts"))
            lbl_none.setStyleSheet("color: #64748b; font-style: italic;")
            self.v_amounts_list.addWidget(lbl_none)

    def _on_worker_error(self, err_msg: str):
        self.progress_container.hide()
        self.lbl_status.setText(err_msg)

    # =========================================================================
    # SOHBET / SORU-CEVAP MANTIĞI
    # =========================================================================
    def _send_preset_query(self, query: str):
        self.txt_query.setText(query)
        self._send_query()

    def _send_query(self):
        query = self.txt_query.text().strip()
        if not query:
            return

        self.txt_query.clear()
        self._add_chat_bubble(query, is_user=True)

        lang = "tr"
        if hasattr(LanguageManager, "get_language"):
            lang = LanguageManager.get_language()

        doc_info = self.doc_analysis.get("doc_info") if self.doc_analysis else None

        self.chat_worker = AuraAiWorker(
            task_type="chat",
            doc_path=self.doc_path,
            query=query,
            doc_info=doc_info,
            lang=lang,
            parent=self
        )
        self.chat_worker.chatFinished.connect(lambda ans: self._add_chat_bubble(ans, is_user=False))
        self.chat_worker.errorOccurred.connect(lambda err: self._add_chat_bubble(f"Hata: {err}", is_user=False))
        self.chat_worker.start()

    def _add_chat_bubble(self, text: str, is_user: bool = False):
        bubble = QFrame()
        bubble.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        bubble.setObjectName("AiChatBubbleUser" if is_user else "AiChatBubbleBot")
        v = QVBoxLayout(bubble)
        v.setContentsMargins(14, 10, 14, 10)

        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if is_user:
            lbl.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: 500;")
            bubble.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9333ea, stop:1 #6366f1); border-radius: 12px; max-width: 520px;")
        else:
            lbl.setStyleSheet("color: #f1f5f9; font-size: 12px; font-weight: 400;")
            bubble.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.14); border-radius: 12px; max-width: 580px;")
        v.addWidget(lbl)

        row = QHBoxLayout()
        if is_user:
            row.addStretch(1)
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch(1)

        # En alta yerlestir
        insert_idx = max(0, self.v_chat_messages.count() - 1)
        self.v_chat_messages.insertLayout(insert_idx, row)

        # Otomatik en alta kaydir
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))

    # =========================================================================
    # EYLEMLER & YARDIMCI METOTLAR
    # =========================================================================
    def _set_tab(self, index: int):
        self.stack.setCurrentIndex(index)
        self.btn_tab_summary.setChecked(index == 0)
        self.btn_tab_risks.setChecked(index == 1)
        self.btn_tab_chat.setChecked(index == 2)

    def _update_mode_badge(self):
        has_gemini = bool(GeminiApiClient.get_api_key())
        if has_gemini:
            self.lbl_mode_badge.setText(LanguageManager.tr("ai_badge_gemini"))
            self.lbl_mode_badge.setStyleSheet(
                "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6);"
                "color: #ffffff; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 8px;"
            )
        else:
            self.lbl_mode_badge.setText(LanguageManager.tr("ai_badge_local"))
            self.lbl_mode_badge.setStyleSheet(
                "background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3);"
                "font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 8px;"
            )

    def _copy_summary(self):
        summary_text = self.txt_overview.text()
        takeaways = []
        for i in range(1, self.v_takeaways.count()):
            w = self.v_takeaways.itemAt(i).widget()
            if isinstance(w, QLabel):
                takeaways.append(w.text())

        full_copy = f"# {LanguageManager.tr('ai_card_overview')}\n{summary_text}\n\n# {LanguageManager.tr('ai_card_takeaways')}\n" + "\n".join(takeaways)

        clipboard = QApplication.clipboard()
        clipboard.setText(full_copy)

        self.lbl_copied_toast.setText(LanguageManager.tr("ai_copied_toast"))
        QTimer.singleShot(2500, lambda: self.lbl_copied_toast.setText(""))

    def _export_summary(self):
        base_name = os.path.splitext(os.path.basename(self.doc_path))[0]
        suggested = f"{base_name}_AuraAI_Ozet.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            LanguageManager.tr("ai_btn_export_summary"),
            suggested,
            "Text Files (*.txt);;Markdown Files (*.md)"
        )
        if file_path:
            try:
                summary_text = self.txt_overview.text()
                takeaways = []
                for i in range(1, self.v_takeaways.count()):
                    w = self.v_takeaways.itemAt(i).widget()
                    if isinstance(w, QLabel):
                        takeaways.append(w.text())

                content = (
                    f"AuraPDF AI Belge Analiz Raporu\n"
                    f"Belge: {os.path.basename(self.doc_path)}\n"
                    f"{'=' * 50}\n\n"
                    f"GENEL BAKIŞ:\n{summary_text}\n\n"
                    f"ÖNEMLİ BULGULAR:\n" + "\n".join(takeaways)
                )
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.lbl_copied_toast.setText(LanguageManager.tr("save_success"))
                QTimer.singleShot(2500, lambda: self.lbl_copied_toast.setText(""))
            except Exception as e:
                QMessageBox.warning(self, LanguageManager.tr("error"), str(e))

    def _open_api_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(LanguageManager.tr("ai_settings_title"))
        dlg.resize(460, 210)
        apply_dialog_theme(dlg, self)

        v = QVBoxLayout(dlg)
        v.setContentsMargins(18, 18, 18, 18)
        v.setSpacing(10)

        lbl_desc = QLabel(LanguageManager.tr("ai_settings_desc"), dlg)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        v.addWidget(lbl_desc)

        lbl_k = QLabel(LanguageManager.tr("ai_settings_key_label"), dlg)
        v.addWidget(lbl_k)

        txt_k = QLineEdit(dlg)
        txt_k.setEchoMode(QLineEdit.EchoMode.Password)
        txt_k.setText(GeminiApiClient.get_api_key())
        v.addWidget(txt_k)

        h_btn = QHBoxLayout()
        h_btn.addStretch(1)

        btn_save = QPushButton(LanguageManager.tr("ai_settings_save"), dlg)
        btn_save.setIcon(ModernIconFactory.icon_save())
        btn_save.clicked.connect(lambda: (
            GeminiApiClient.set_api_key(txt_k.text()),
            self._update_mode_badge(),
            dlg.accept()
        ))
        h_btn.addWidget(btn_save)
        v.addLayout(h_btn)

        dlg.exec()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.abort()
            self.worker.wait(400)
        super().closeEvent(event)
