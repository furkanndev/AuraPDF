"""
AuraPDF - PDF Sıkıştırma ve Dosya Boyutu Küçültme Diyaloğu
=========================================================
Kullanıcının PDF belgelerinin dosya boyutunu kalite kaybını minimize ederek
optimize etmesini sağlayan modern, arka planda çalışan arayüz bileşeni.
"""

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QFileDialog, QMessageBox, QGroupBox, QRadioButton,
    QButtonGroup, QProgressBar, QCheckBox, QSlider, QFrame, QLineEdit,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from src.core.i18n import LanguageManager
from src.core.pdf_compressor import PDFCompressor
from src.ui.dialog_theme import apply_dialog_theme
from src.ui.icons import ModernIconFactory


class CompressThread(QThread):
    """Sıkıştırma işlemini arka planda yürüten iş parçacığı."""
    progressChanged = pyqtSignal(int, int, str)
    finishedSuccess = pyqtSignal(dict)
    finishedError = pyqtSignal(str)

    def __init__(self, input_path: str, output_path: str, preset: str, quality: Optional[int], max_dpi: Optional[int]):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.preset = preset
        self.quality = quality
        self.max_dpi = max_dpi

    def run(self):
        try:
            def cb(curr, total, msg):
                self.progressChanged.emit(curr, total, msg)

            res = PDFCompressor.compress_pdf(
                input_path=self.input_path,
                output_path=self.output_path,
                preset=self.preset,
                image_quality=self.quality,
                max_dpi=self.max_dpi,
                progress_callback=cb
            )
            self.finishedSuccess.emit(res)
        except Exception as e:
            self.finishedError.emit(str(e))


class PDFCompressDialog(QDialog):
    """PDF Dosya Boyutu Küçültme Penceresi."""

    def __init__(self, parent=None, default_input_path: str = ""):
        super().__init__(parent)
        self.setWindowTitle(LanguageManager.tr("compress_dialog_title"))
        self.resize(560, 580)
        self.setModal(True)

        self.input_path = default_input_path
        self.compressed_pdf_path: Optional[str] = None
        self.open_after_compress = True
        self.worker_thread: Optional[CompressThread] = None

        self._init_ui()
        apply_dialog_theme(self, parent)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Başlık
        header_layout = QHBoxLayout()
        icon_lbl = QLabel(self)
        icon_lbl.setPixmap(ModernIconFactory.icon_compress().pixmap(32, 32))
        header_layout.addWidget(icon_lbl)

        title_vbox = QVBoxLayout()
        lbl_title = QLabel(LanguageManager.tr("compress_dialog_title"), self)
        f_title = QFont()
        f_title.setPointSize(12)
        f_title.setBold(True)
        lbl_title.setFont(f_title)
        lbl_desc = QLabel(LanguageManager.tr("compress_dialog_desc"), self)
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_desc)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # 1. Dosya Seçimi Grubu
        grp_file = QGroupBox(LanguageManager.tr("compress_grp_file"), self)
        grid_file = QGridLayout(grp_file)
        grid_file.setContentsMargins(12, 16, 12, 12)
        grid_file.setSpacing(8)

        lbl_in = QLabel(LanguageManager.tr("compress_lbl_input"), self)
        self.txt_input = QLineEdit(self)
        self.txt_input.setPlaceholderText(LanguageManager.tr("compress_ph_input"))
        if self.input_path:
            self.txt_input.setText(self.input_path)

        btn_browse_in = QPushButton(LanguageManager.tr("browse"), self)
        btn_browse_in.setIcon(ModernIconFactory.icon_folder())
        btn_browse_in.clicked.connect(self._browse_input)

        grid_file.addWidget(lbl_in, 0, 0, 1, 2)
        grid_file.addWidget(self.txt_input, 1, 0)
        grid_file.addWidget(btn_browse_in, 1, 1)

        self.lbl_orig_size = QLabel(self._format_orig_size(), self)
        self.lbl_orig_size.setStyleSheet("color: #38bdf8; font-size: 11px; font-weight: 500;")
        grid_file.addWidget(self.lbl_orig_size, 2, 0, 1, 2)

        main_layout.addWidget(grp_file)

        # 2. Sıkıştırma Seviyesi
        grp_level = QGroupBox(LanguageManager.tr("compress_grp_level"), self)
        v_level = QVBoxLayout(grp_level)
        v_level.setContentsMargins(12, 16, 12, 12)
        v_level.setSpacing(8)

        self.rad_medium = QRadioButton(LanguageManager.tr("compress_level_medium"), self)
        self.rad_low = QRadioButton(LanguageManager.tr("compress_level_low"), self)
        self.rad_high = QRadioButton(LanguageManager.tr("compress_level_high"), self)
        self.rad_custom = QRadioButton(LanguageManager.tr("compress_level_custom"), self)

        self.rad_medium.setChecked(True)
        self.btn_group = QButtonGroup(self)
        self.btn_group.addButton(self.rad_medium)
        self.btn_group.addButton(self.rad_low)
        self.btn_group.addButton(self.rad_high)
        self.btn_group.addButton(self.rad_custom)

        v_level.addWidget(self.rad_medium)
        v_level.addWidget(self.rad_low)
        v_level.addWidget(self.rad_high)
        v_level.addWidget(self.rad_custom)

        # Özel ayar paneli
        self.frame_custom = QFrame(grp_level)
        grid_cust = QGridLayout(self.frame_custom)
        grid_cust.setContentsMargins(18, 4, 4, 4)
        grid_cust.setSpacing(6)

        lbl_q = QLabel("JPEG Kalitesi (%):", self.frame_custom)
        self.slider_quality = QSlider(Qt.Orientation.Horizontal, self.frame_custom)
        self.slider_quality.setRange(20, 95)
        self.slider_quality.setValue(70)
        self.lbl_q_val = QLabel("70%", self.frame_custom)
        self.slider_quality.valueChanged.connect(lambda v: self.lbl_q_val.setText(f"{v}%"))

        grid_cust.addWidget(lbl_q, 0, 0)
        grid_cust.addWidget(self.slider_quality, 0, 1)
        grid_cust.addWidget(self.lbl_q_val, 0, 2)

        self.frame_custom.setEnabled(False)
        self.rad_custom.toggled.connect(self.frame_custom.setEnabled)
        v_level.addWidget(self.frame_custom)

        main_layout.addWidget(grp_level)

        # 3. Hedef Kayıt Yolu
        grp_out = QGroupBox(LanguageManager.tr("compress_grp_output"), self)
        h_out = QHBoxLayout(grp_out)
        h_out.setContentsMargins(12, 16, 12, 12)
        h_out.setSpacing(8)

        self.txt_output = QLineEdit(self)
        self.txt_output.setText(self._generate_default_output())
        btn_browse_out = QPushButton(LanguageManager.tr("browse"), self)
        btn_browse_out.setIcon(ModernIconFactory.icon_folder())
        btn_browse_out.clicked.connect(self._browse_output)

        h_out.addWidget(self.txt_output)
        h_out.addWidget(btn_browse_out)
        main_layout.addWidget(grp_out)

        # İlerleme Çubuğu ve Durum
        self.prog_bar = QProgressBar(self)
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setVisible(False)
        main_layout.addWidget(self.prog_bar)

        self.lbl_status = QLabel("", self)
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 11px;")
        self.lbl_status.setVisible(False)
        main_layout.addWidget(self.lbl_status)

        # Sonuç Kartı
        self.card_result = QFrame(self)
        self.card_result.setStyleSheet("background-color: rgba(56, 189, 248, 0.12); border: 1px solid #38bdf8; border-radius: 6px; padding: 10px;")
        self.card_result.setVisible(False)
        v_res = QVBoxLayout(self.card_result)
        v_res.setContentsMargins(8, 8, 8, 8)
        self.lbl_result_text = QLabel(self.card_result)
        self.lbl_result_text.setStyleSheet("font-weight: 600; color: #f0fdf4;")
        v_res.addWidget(self.lbl_result_text)
        main_layout.addWidget(self.card_result)

        self.chk_open_after = QCheckBox(LanguageManager.tr("compress_chk_open"), self)
        self.chk_open_after.setChecked(True)
        main_layout.addWidget(self.chk_open_after)

        # Alt Butonlar
        main_layout.addStretch()
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton(LanguageManager.tr("cancel"), self)
        self.btn_cancel.setObjectName("CancelBtn")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_compress = QPushButton(LanguageManager.tr("compress_btn_start"), self)
        self.btn_compress.setObjectName("PrimaryBtn")
        self.btn_compress.setIcon(ModernIconFactory.icon_compress())
        self.btn_compress.clicked.connect(self._start_compression)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_compress)
        main_layout.addLayout(btn_layout)

    def _format_orig_size(self) -> str:
        if self.input_path and os.path.isfile(self.input_path):
            sz = os.path.getsize(self.input_path)
            return f"Orijinal Dosya Boyutu: {self._format_bytes(sz)}"
        return ""

    @staticmethod
    def _format_bytes(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"

    def _generate_default_output(self) -> str:
        if not self.input_path:
            return os.path.expanduser("~/Documents/Belge_Sikistirilmis.pdf")
        base, ext = os.path.splitext(self.input_path)
        return f"{base}_kucultulmus{ext}"

    def _browse_input(self):
        curr = self.txt_input.text().strip() or os.path.expanduser("~/Documents")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Sıkıştırılacak PDF Dosyasını Seç",
            curr,
            "PDF Belgeleri (*.pdf)"
        )
        if path:
            self.input_path = path
            self.txt_input.setText(path)
            self.txt_output.setText(self._generate_default_output())
            self.lbl_orig_size.setText(self._format_orig_size())

    def _browse_output(self):
        curr = self.txt_output.text().strip() or self._generate_default_output()
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Sıkıştırılmış PDF Belgesini Kaydet",
            curr,
            "PDF Belgeleri (*.pdf)"
        )
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            self.txt_output.setText(path)

    def _start_compression(self):
        inp = self.txt_input.text().strip()
        if not inp or not os.path.isfile(inp):
            QMessageBox.warning(self, LanguageManager.tr("warning"), "Lütfen geçerli bir PDF dosyası seçin.")
            return

        outp = self.txt_output.text().strip()
        if not outp:
            QMessageBox.warning(self, LanguageManager.tr("warning"), "Lütfen hedef kayıt yolunu belirleyin.")
            return

        if os.path.abspath(inp) == os.path.abspath(outp):
            QMessageBox.warning(
                self,
                LanguageManager.tr("warning"),
                "Orijinal belgenin üzerine yazamazsınız. Lütfen farklı bir dosya adı belirleyin."
            )
            return

        # Sıkıştırma parametreleri
        preset = "medium"
        quality = None
        max_dpi = None

        if self.rad_low.isChecked():
            preset = "low"
        elif self.rad_high.isChecked():
            preset = "high"
        elif self.rad_custom.isChecked():
            preset = "medium"
            quality = self.slider_quality.value()
            max_dpi = 120

        self.btn_compress.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.prog_bar.setVisible(True)
        self.prog_bar.setValue(0)
        self.lbl_status.setVisible(True)
        self.lbl_status.setText("Sıkıştırma başlatılıyor...")
        self.card_result.setVisible(False)

        self.worker_thread = CompressThread(inp, outp, preset, quality, max_dpi)
        self.worker_thread.progressChanged.connect(self._on_progress)
        self.worker_thread.finishedSuccess.connect(self._on_success)
        self.worker_thread.finishedError.connect(self._on_error)
        self.worker_thread.start()

    def _on_progress(self, curr: int, total: int, msg: str):
        pct = int(curr / max(1, total) * 100)
        self.prog_bar.setValue(pct)
        self.lbl_status.setText(msg)

    def _on_success(self, res: dict):
        self.prog_bar.setValue(100)
        self.lbl_status.setText("Sıkıştırma tamamlandı.")
        self.btn_compress.setEnabled(True)
        self.btn_cancel.setEnabled(True)

        orig_str = self._format_bytes(res["original_size"])
        comp_str = self._format_bytes(res["compressed_size"])
        pct = res["savings_percent"]

        self.compressed_pdf_path = self.txt_output.text().strip()
        self.open_after_compress = self.chk_open_after.isChecked()

        msg = (
            f"Başarıyla Sıkıştırıldı:\n"
            f"Orijinal Boyut: {orig_str} -> Yeni Boyut: {comp_str}\n"
            f"Tasarruf: %{pct} ({self._format_bytes(res['saved_bytes'])} küçültüldü)"
        )
        self.lbl_result_text.setText(msg)
        self.card_result.setVisible(True)

        QMessageBox.information(self, LanguageManager.tr("success"), msg)
        self.accept()

    def _on_error(self, err_msg: str):
        self.btn_compress.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.prog_bar.setVisible(False)
        self.lbl_status.setVisible(False)
        QMessageBox.critical(self, LanguageManager.tr("error"), f"Sıkıştırma sırasında hata oluştu:\n{err_msg}")
