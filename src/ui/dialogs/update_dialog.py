"""
AuraPDF - Güncelleme Bilgilendirme ve İndirme Penceresi
=====================================================
Kullanıcıya mevcut ve en son sürümü gösteren, sürüm notlarını
listeyen ve kurulum dosyasını doğrudan indirip kurabilen modern diyalog.
"""

import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextBrowser, QProgressBar, QFrame,
                             QMessageBox, QApplication, QWidget)
from PyQt6.QtCore import Qt, QUrl, QSettings
from PyQt6.QtGui import QDesktopServices, QFont

from src.core.i18n import LanguageManager
from src.core.updater import UpdateInfo, UpdateDownloader, launch_installer
from src.ui.icons import ModernIconFactory
from src.ui.dialog_theme import apply_dialog_theme


class UpdateDialog(QDialog):
    def __init__(self, update_info=None, parent=None):
        if isinstance(update_info, QWidget) and parent is None:
            parent = update_info
            update_info = None
        super().__init__(parent)
        self.parent_widget = parent
        self.update_info = update_info if isinstance(update_info, UpdateInfo) else UpdateInfo()
        self.downloader = None
        self.downloaded_path = None

        self.setWindowTitle(LanguageManager.tr("updates_section_title"))
        self.setWindowIcon(ModernIconFactory.icon_update())
        self.resize(560, 480)
        self.setMinimumSize(480, 400)

        self._init_ui()
        self._apply_dialog_style()

    def _apply_dialog_style(self):
        apply_dialog_theme(self, self.parent_widget, extra_css="""
            QFrame.card {
                border-radius: 8px;
                padding: 12px;
            }
            QTextBrowser {
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QProgressBar {
                border-radius: 6px;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
                height: 22px;
            }
            QProgressBar::chunk {
                border-radius: 5px;
            }
            QPushButton#PrimaryBtn {
                font-weight: bold;
            }
        """)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # 1. Başlık Kartı
        header_card = QFrame()
        header_card.setProperty("class", "card")
        h_layout = QHBoxLayout(header_card)
        h_layout.setContentsMargins(12, 10, 12, 10)
        h_layout.setSpacing(14)

        lbl_icon = QLabel()
        lbl_icon.setPixmap(ModernIconFactory.icon_update().pixmap(36, 36))
        h_layout.addWidget(lbl_icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        if self.update_info.has_update:
            lbl_title = QLabel(LanguageManager.tr("updates_available_title"))
            lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
            cur_v = str(self.update_info.current_version or "")
            if not cur_v.lower().startswith(('v', 'pro', 'basic')):
                cur_v = f"v{cur_v}"
            lat_v = str(self.update_info.latest_version or "")
            if not lat_v.lower().startswith(('v', 'pro', 'basic')):
                lat_v = f"v{lat_v}"
            lbl_sub = QLabel(LanguageManager.tr("updates_available_desc",
                                                version=lat_v,
                                                current_version=cur_v))
            lbl_sub.setWordWrap(True)
            lbl_sub.setStyleSheet("font-size: 12px;")
        elif self.update_info.error_message:
            lbl_title = QLabel(LanguageManager.tr("updates_error_title"))
            lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f87171;")
            lbl_sub = QLabel(self.update_info.error_message)
            lbl_sub.setWordWrap(True)
            lbl_sub.setStyleSheet("font-size: 12px; color: #cbd5e1;")
        else:
            lbl_title = QLabel(LanguageManager.tr("updates_uptodate_title"))
            lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4ade80;")
            cur_v = str(self.update_info.current_version or "")
            if not cur_v.lower().startswith(('v', 'pro', 'basic')):
                cur_v = f"v{cur_v}"
            lbl_sub = QLabel(LanguageManager.tr("updates_uptodate_desc", version=cur_v))
            lbl_sub.setWordWrap(True)
            lbl_sub.setStyleSheet("font-size: 12px;")

        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        h_layout.addLayout(title_box, 1)
        layout.addWidget(header_card)

        # 2. Sürüm Notları (Changelog) Alanı
        if self.update_info.has_update and self.update_info.release_notes:
            lbl_notes_title = QLabel(LanguageManager.tr("updates_release_notes_label", default="Sürüm Notları ve Yenilikler:"))
            lbl_notes_title.setStyleSheet("font-weight: bold; font-size: 13px;")
            layout.addWidget(lbl_notes_title)

            self.txt_notes = QTextBrowser()
            self.txt_notes.setOpenExternalLinks(True)
            self.txt_notes.setMarkdown(self.update_info.release_notes)
            layout.addWidget(self.txt_notes, 1)

        # 3. İlerleme Çubuğu ve İndirme Durumu
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 12px; color: #38bdf8;")
        self.lbl_status.hide()
        layout.addWidget(self.lbl_status)

        layout.addStretch() if not (self.update_info.has_update and self.update_info.release_notes) else None

        # 4. Alt İşlem Butonları
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        if self.update_info.html_url:
            btn_github = QPushButton(LanguageManager.tr("updates_btn_open_github"))
            btn_github.clicked.connect(self._open_github)
            btn_layout.addWidget(btn_github)

        btn_layout.addStretch()

        self.btn_close = QPushButton(LanguageManager.tr("updates_btn_later") if self.update_info.has_update else LanguageManager.tr("close"))
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)

        if self.update_info.has_update and self.update_info.download_url:
            self.btn_download = QPushButton(LanguageManager.tr("updates_btn_download"))
            self.btn_download.setObjectName("PrimaryBtn")
            self.btn_download.clicked.connect(self._start_download)
            btn_layout.addWidget(self.btn_download)

        layout.addLayout(btn_layout)

    def _open_github(self):
        if self.update_info.html_url:
            QDesktopServices.openUrl(QUrl(self.update_info.html_url))

    def _start_download(self):
        if not self.update_info.download_url:
            self._open_github()
            return

        self.btn_download.setEnabled(False)
        self.progress_bar.show()
        self.lbl_status.show()
        self.lbl_status.setText(LanguageManager.tr("updates_downloading", progress=0, mb="0.0"))

        filename = self.update_info.asset_name or f"AuraPDF_{self.update_info.latest_version}_Setup.exe"
        self.downloader = UpdateDownloader(self.update_info.download_url, filename=filename, parent=self)
        self.downloader.progress.connect(self._on_download_progress)
        self.downloader.download_finished.connect(self._on_download_finished)
        self.downloader.download_failed.connect(self._on_download_failed)
        self.downloader.start()

    def _on_download_progress(self, downloaded: int, total: int):
        if total > 0:
            pct = int((downloaded / total) * 100)
            self.progress_bar.setValue(pct)
            mb = downloaded / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            self.lbl_status.setText(f"{pct}% ({mb:.1f} MB / {tot_mb:.1f} MB)")
        else:
            mb = downloaded / (1024 * 1024)
            self.lbl_status.setText(f"{mb:.1f} MB indirildi...")

    def _on_download_finished(self, local_path: str):
        self.downloaded_path = local_path
        self.lbl_status.setText("İndirme tamamlandı!")
        self.progress_bar.setValue(100)

        ret = QMessageBox.question(
            self,
            LanguageManager.tr("updates_section_title"),
            LanguageManager.tr("updates_download_success"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if ret == QMessageBox.StandardButton.Yes:
            launch_installer(local_path)
            self.accept()
        else:
            self.btn_download.setText("Kurulumu Başlat")
            self.btn_download.setEnabled(True)
            self.btn_download.clicked.disconnect()
            self.btn_download.clicked.connect(lambda: launch_installer(local_path))

    def _on_download_failed(self, error_msg: str):
        self.lbl_status.setText(f"Hata: {error_msg}")
        self.lbl_status.setStyleSheet("color: #f87171;")
        self.btn_download.setEnabled(True)
        QMessageBox.warning(self, LanguageManager.tr("updates_error_title"), error_msg)

    def closeEvent(self, event):
        if self.downloader and self.downloader.isRunning():
            self.downloader.cancel()
            self.downloader.wait(1000)
        super().closeEvent(event)
