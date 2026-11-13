"""
AuraPDF - Sürükle-Bırak Tekerleği Özelleştirme Penceresi
========================================================
Tekerlekte görünecek eylemleri (3 ile 8 arası) ve sırasını, tetikleyici tuşu ve
tekerlek boyutunu ayarlar. Değişiklikler sistem tepsisi yardımcısına birkaç saniye
içinde otomatik yansır.
"""

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QLabel,
                             QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout)

from src.core import drag_wheel_config as cfg
from src.core.i18n import LanguageManager
from src.ui.dialog_theme import apply_dialog_theme
from src.ui.icons import AuraIconFactory


class AuraDragWheelSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(LanguageManager.tr("wheel_cfg_title"))
        self.setMinimumSize(460, 520)
        self.resize(500, 580)
        self.setSizeGripEnabled(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        # Tetikleyici
        root.addWidget(QLabel(LanguageManager.tr("wheel_cfg_trigger_lbl")))
        self.cmb_trigger = QComboBox()
        for code in cfg.TRIGGERS:
            self.cmb_trigger.addItem(LanguageManager.tr(f"wheel_cfg_trigger_{code}"), code)
        root.addWidget(self.cmb_trigger)
        self.lbl_trigger_hint = QLabel(LanguageManager.tr("wheel_cfg_trigger_hint"))
        self.lbl_trigger_hint.setWordWrap(True)
        self.lbl_trigger_hint.setStyleSheet("font-size: 12px; color: #94a3b8;")
        root.addWidget(self.lbl_trigger_hint)

        # Boyut
        root.addWidget(QLabel(LanguageManager.tr("wheel_cfg_size_lbl")))
        self.cmb_size = QComboBox()
        for code in cfg.SIZES:
            self.cmb_size.addItem(LanguageManager.tr(f"wheel_cfg_size_{code}"), code)
        root.addWidget(self.cmb_size)

        # Eylemler
        root.addWidget(QLabel(LanguageManager.tr("wheel_cfg_actions_lbl", min=cfg.MIN_ACTIONS, max=cfg.MAX_ACTIONS)))
        row = QHBoxLayout()
        self.list_actions = QListWidget()
        self.list_actions.setIconSize(QSize(22, 22))
        self.list_actions.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_actions.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list_actions.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        row.addWidget(self.list_actions, 1)

        col = QVBoxLayout()
        self.btn_up = QPushButton(LanguageManager.tr("wheel_cfg_move_up"))
        self.btn_down = QPushButton(LanguageManager.tr("wheel_cfg_move_down"))
        self.btn_up.clicked.connect(lambda: self._move(-1))
        self.btn_down.clicked.connect(lambda: self._move(1))
        col.addWidget(self.btn_up)
        col.addWidget(self.btn_down)
        col.addStretch()
        row.addLayout(col)
        root.addLayout(row, 1)

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("font-size: 12px; color: #94a3b8;")
        root.addWidget(self.lbl_count)
        self.list_actions.itemChanged.connect(lambda _i: self._update_count())

        # Düğmeler
        btns = QHBoxLayout()
        self.btn_reset = QPushButton(LanguageManager.tr("wheel_cfg_reset"))
        self.btn_reset.clicked.connect(self._reset_defaults)
        btns.addWidget(self.btn_reset)
        btns.addStretch()
        btn_cancel = QPushButton(LanguageManager.tr("print_btn_cancel"))
        btn_cancel.setObjectName("CancelBtn")
        btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton(LanguageManager.tr("wheel_cfg_save"))
        self.btn_save.setObjectName("PrimaryBtn")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._save)
        btns.addWidget(btn_cancel)
        btns.addWidget(self.btn_save)
        root.addLayout(btns)

        apply_dialog_theme(self, parent)
        self._load(cfg.load_config())

    # ------------------------------------------------------------------ veri
    def _load(self, conf: dict):
        self._set_combo(self.cmb_trigger, conf["trigger"])
        self._set_combo(self.cmb_size, conf["size"])
        self.list_actions.clear()
        chosen = list(conf["actions"])
        # Seçili olanlar kayıtlı sırayla üstte, kalanlar katalog sırasıyla altta
        for code in chosen + [c for c in cfg.CATALOG if c not in chosen]:
            self._add_item(code, code in chosen)
        self._update_count()

    def _add_item(self, code: str, checked: bool):
        key, icon_name = cfg.CATALOG[code]
        item = QListWidgetItem(LanguageManager.tr(key))
        item.setData(Qt.ItemDataRole.UserRole, code)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        try:
            item.setIcon(getattr(AuraIconFactory, icon_name)())
        except Exception:
            pass
        self.list_actions.addItem(item)

    @staticmethod
    def _set_combo(combo: QComboBox, data):
        idx = combo.findData(data)
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    def checked_actions(self):
        out = []
        for i in range(self.list_actions.count()):
            it = self.list_actions.item(i)
            if it.checkState() == Qt.CheckState.Checked:
                out.append(it.data(Qt.ItemDataRole.UserRole))
        return out

    def _update_count(self):
        n = len(self.checked_actions())
        self.lbl_count.setText(LanguageManager.tr("wheel_cfg_count", count=n, min=cfg.MIN_ACTIONS, max=cfg.MAX_ACTIONS))

    def _move(self, delta: int):
        row = self.list_actions.currentRow()
        new = row + delta
        if row < 0 or not (0 <= new < self.list_actions.count()):
            return
        item = self.list_actions.takeItem(row)
        self.list_actions.insertItem(new, item)
        self.list_actions.setCurrentRow(new)

    def _reset_defaults(self):
        self._load({"trigger": cfg.DEFAULT_TRIGGER, "size": cfg.DEFAULT_SIZE,
                    "actions": list(cfg.DEFAULT_ACTIONS), "enabled": True})

    def _save(self):
        actions = self.checked_actions()
        if not (cfg.MIN_ACTIONS <= len(actions) <= cfg.MAX_ACTIONS):
            QMessageBox.warning(self, LanguageManager.tr("warning"),
                                LanguageManager.tr("wheel_cfg_count_error", min=cfg.MIN_ACTIONS, max=cfg.MAX_ACTIONS))
            return
        cfg.save_config(actions, self.cmb_trigger.currentData(), self.cmb_size.currentData())
        self.accept()
