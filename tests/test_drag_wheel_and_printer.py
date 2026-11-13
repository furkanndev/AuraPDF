import os
import sys
import unittest
from unittest import mock

from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class DragWheelHitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def _overlay(self):
        from PyQt6.QtWidgets import QWidget
        from src.ui.drag_wheel import AuraDragWheelOverlay
        host = QWidget()
        host.resize(900, 700)
        ov = AuraDragWheelOverlay(host)
        ov._center = QPointF(450, 350)
        return host, ov

    def test_center_and_sectors(self):
        host, ov = self._overlay()
        self.assertEqual(ov._hit_test(QPointF(450, 350)), "open")
        # Tepe: ilk dilim (merge); saat yönünde sırayla split, word, pptx, excel
        self.assertEqual(ov._hit_test(QPointF(450, 350 - 110)), "merge")
        self.assertEqual(ov._hit_test(QPointF(450 + 105, 350 - 35)), "split")
        self.assertEqual(ov._hit_test(QPointF(450 + 65, 350 + 90)), "word")
        self.assertEqual(ov._hit_test(QPointF(450 - 65, 350 + 90)), "pptx")
        self.assertEqual(ov._hit_test(QPointF(450 - 105, 350 - 35)), "excel")
        self.assertIsNone(ov._hit_test(QPointF(450, 350 - 400)))


class DragTrackerTests(unittest.TestCase):
    def test_shows_after_drag_start_when_trigger_active(self):
        from src.core.drag_wheel_service import DragTracker
        t = DragTracker(threshold=8)
        self.assertEqual(t.update(False, True, (100, 100), True), "")
        self.assertEqual(t.update(True, True, (103, 101), True), "")      # eşik altı
        self.assertEqual(t.update(True, True, (120, 100), True), "show")
        self.assertEqual(t.update(True, True, (140, 100), True), "")
        self.assertEqual(t.update(True, False, (140, 100), True), "hide")
        self.assertEqual(t.update(True, False, (140, 100), True), "")

    def test_trigger_may_be_pressed_after_drag_started(self):
        from src.core.drag_wheel_service import DragTracker
        t = DragTracker(threshold=8)
        t.update(False, True, (0, 0), True)
        self.assertEqual(t.update(False, True, (50, 50), True), "")       # sürükleniyor, tetikleyici yok
        self.assertEqual(t.update(True, True, (55, 55), True), "show")    # sonradan basıldı

    def test_ignores_wrong_window_or_missing_trigger(self):
        from src.core.drag_wheel_service import DragTracker
        t = DragTracker(threshold=8)
        t.update(True, True, (0, 0), False)                                # Gezgin/masaüstü dışı
        self.assertEqual(t.update(True, True, (50, 50), False), "")
        t.update(True, False, (0, 0), True)
        t.update(False, True, (0, 0), True)
        self.assertEqual(t.update(False, True, (90, 90), True), "")        # tetikleyici yok


class WheelConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_sanitize_actions(self):
        from src.core import drag_wheel_config as c
        self.assertEqual(c.sanitize_actions(["merge", "split", "bogus", "merge", "word"]), ["merge", "split", "word"])
        self.assertEqual(c.sanitize_actions(["merge"]), c.DEFAULT_ACTIONS)       # çok az: varsayılan
        self.assertEqual(c.sanitize_actions(None), c.DEFAULT_ACTIONS)
        self.assertEqual(len(c.sanitize_actions(list(c.CATALOG) * 2)), c.MAX_ACTIONS)

    def test_save_and_load_roundtrip(self):
        from src.core import drag_wheel_config as c
        c.save_config(["compress", "merge", "protect", "epub"], "middle", "large")
        conf = c.load_config()
        self.assertEqual(conf["actions"], ["compress", "merge", "protect", "epub"])
        self.assertEqual((conf["trigger"], conf["size"]), ("middle", "large"))
        c.save_config(["x"], "bogus", "bogus")                                   # geçersiz: varsayılan
        conf = c.load_config()
        self.assertEqual((conf["actions"], conf["trigger"], conf["size"]),
                         (c.DEFAULT_ACTIONS, c.DEFAULT_TRIGGER, c.DEFAULT_SIZE))

    def test_overlay_follows_config_and_handles_eight_actions(self):
        from PyQt6.QtWidgets import QWidget
        from src.core import drag_wheel_config as c
        from src.ui.drag_wheel import AuraDragWheelOverlay
        host = QWidget(); host.resize(900, 700)
        ov = AuraDragWheelOverlay(host)
        ov.setGeometry(host.rect())
        ov.apply_config({"actions": list(c.CATALOG), "size": "small", "trigger": "ctrl_alt", "enabled": True})
        ov._center = QPointF(450, 350)
        self.assertEqual(len(ov._segments), 8)
        self.assertEqual(ov._hit_test(QPointF(450, 350 - 90)), "merge")          # ilk dilim tepede
        ov.grab()                                                                  # çizim hatasız
        ov.apply_config({"actions": ["merge", "split", "word"], "size": "large", "trigger": "ctrl_alt", "enabled": True})
        self.assertEqual(len(ov._segments), 3)

    def test_wheel_action_dialogs_expose_expected_fields(self):
        from src.ui.dialogs import toolbox_dialogs as td
        from src.ui.dialogs.pdf_compress_dialog import PDFCompressDialog
        import inspect
        self.assertIn("default_input_path", inspect.signature(PDFCompressDialog.__init__).parameters)
        src = inspect.getsource(td.PDFEncryptDialog)
        self.assertIn("txt_protect_src", src)
        self.assertIn("txt_protect_dst", src)

    def test_settings_dialog_saves_choice(self):
        from src.core import drag_wheel_config as c
        from src.ui.dialogs.drag_wheel_settings_dialog import AuraDragWheelSettingsDialog
        c.save_config(c.DEFAULT_ACTIONS, "ctrl_alt", "normal")
        dlg = AuraDragWheelSettingsDialog(None)
        self.assertEqual(dlg.checked_actions(), c.DEFAULT_ACTIONS)
        dlg.cmb_trigger.setCurrentIndex(dlg.cmb_trigger.findData("ctrl_shift"))
        dlg.cmb_size.setCurrentIndex(dlg.cmb_size.findData("small"))
        dlg._save()
        conf = c.load_config()
        self.assertEqual((conf["trigger"], conf["size"]), ("ctrl_shift", "small"))
        c.save_config(c.DEFAULT_ACTIONS, "ctrl_alt", "normal")


class WheelArgsTests(unittest.TestCase):
    def test_parse_wheel_args(self):
        import main
        self.assertEqual(main.parse_wheel_args(["--wheel", "split", "a.pdf"]), ("split", ["a.pdf"]))
        self.assertEqual(main.parse_wheel_args(["a.pdf"]), (None, ["a.pdf"]))
        self.assertEqual(main.parse_wheel_args(["--wheel"]), (None, []))


class SingleInstanceAndHeadlessTests(unittest.TestCase):
    def test_tray_mutex_allows_only_one_holder(self):
        from src.core import drag_wheel_service as svc
        name = "Local" + chr(92) + "AuraPDF_Test_Mutex_%d" % os.getpid()  # çalışan gerçek yardımcıyla çakışmaz
        first = svc._acquire_single_instance_mutex(name)
        try:
            self.assertIsNotNone(first)
            self.assertIsNone(svc._acquire_single_instance_mutex(name))
        finally:
            if first and first is not True:
                try:
                    import ctypes
                    ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(first))
                except Exception:
                    pass

    def test_helper_running_detects_held_mutex(self):
        from src.core import drag_wheel_service as svc
        name = "Local" + chr(92) + "AuraPDF_Test_Running_%d" % os.getpid()
        self.assertFalse(svc.helper_running(name))
        held = svc._acquire_single_instance_mutex(name)
        try:
            self.assertTrue(svc.helper_running(name))
        finally:
            import ctypes
            ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(held))

    def test_main_restarts_helper_on_launch(self):
        # AuraPDF açılışta yardımcıyı geri getirmelidir (tepsiden çıkış sonrası tekerlek dönsün)
        src = open(os.path.join(os.path.dirname(__file__), "..", "main.py"), encoding="utf-8").read()
        self.assertIn("ensure_helper_running()", src)

    def test_payload_matches_main_ipc_format(self):
        from src.core import drag_wheel_service as svc
        self.assertEqual(svc.build_payload("open", ["a.pdf"]), "a.pdf")
        self.assertEqual(svc.build_payload("split", ["a.pdf"]).split(chr(10)), ["__WHEEL__:split", "a.pdf"])
        import main
        self.assertEqual(svc.MAIN_SERVER_NAME, main.SERVER_NAME)

    def test_headless_wheel_quits_without_documents_and_waits_for_other_dialogs(self):
        import main

        class Tabs:
            def count(self): return 0
            def widget(self, i): return None

        class V:
            tab_widget = Tabs()
            _wheel_headless = True
            _wheel_active = 2

        class A:
            quit_called = False
            def quit(self): self.quit_called = True
            def setQuitOnLastWindowClosed(self, v): pass

        app, v = A(), V()
        main.finish_headless_wheel(app, v)
        self.assertFalse(app.quit_called)   # başka pencere hâlâ açık
        main.finish_headless_wheel(app, v)
        self.assertTrue(app.quit_called)    # belge yok: uygulama kapanır


class DragWheelSettingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_setting_defaults_on_and_respects_off(self):
        from PyQt6.QtCore import QSettings
        from src.core import drag_wheel_service as svc
        st = QSettings("AuraPDF", "PDFViewer")  # conftest geçici INI'ye yönlendirir
        st.remove("drag_wheel_enabled")
        self.assertTrue(svc.drag_wheel_enabled())
        st.setValue("drag_wheel_enabled", False)
        self.assertFalse(svc.drag_wheel_enabled())
        st.remove("drag_wheel_enabled")

    def test_settings_dialog_has_toggle(self):
        from src.ui.dialogs.settings_dialog import AuraSettingsDialog
        from src.viewer import AuraPDFViewer
        v = AuraPDFViewer()
        dlg = AuraSettingsDialog(v)
        self.assertTrue(hasattr(dlg, "chk_drag_wheel"))
        self.assertTrue(dlg.chk_drag_wheel.isChecked())


class StandaloneOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_standalone_overlay_is_toplevel_and_starts_unarmed(self):
        from PyQt6.QtCore import QPoint
        from src.ui.drag_wheel import AuraDragWheelOverlay
        ov = AuraDragWheelOverlay(None, on_choice=lambda a, p: None)
        self.assertIsNone(ov.parent())
        ov.present_at_cursor(QPoint(300, 300))
        self.assertFalse(ov._armed)
        self.assertTrue(ov.isVisible())
        ov.grab()
        ov.dismiss()
        self.assertFalse(ov.isVisible())


class PrinterOrderTests(unittest.TestCase):
    def test_default_printer_first_and_pdf_last(self):
        from src.ui.dialogs import print_dialog as pd

        class Stub:
            pass

        combo_items = []

        class Combo:
            def clear(self): combo_items.clear()
            def addItem(self, text, data): combo_items.append(data)
            def setCurrentIndex(self, i): self.idx = i

        stub = Stub()
        stub.cmb_printer = Combo()
        stub._on_printer_changed = lambda i: None
        with mock.patch.object(pd.QPrinterInfo, "availablePrinterNames", return_value=["A", "HP", "Z"]), \
                mock.patch.object(pd.QPrinterInfo, "defaultPrinterName", return_value="HP"):
            pd.AuraPrintDialog._populate_printers(stub)
        self.assertEqual(combo_items, ["HP", "A", "Z", "save_pdf"])
        self.assertEqual(stub.cmb_printer.idx, 0)

    def test_no_printer_falls_back_to_pdf(self):
        from src.ui.dialogs import print_dialog as pd

        items = []

        class Combo:
            def clear(self): items.clear()
            def addItem(self, text, data): items.append(data)
            def setCurrentIndex(self, i): pass

        stub = type("S", (), {})()
        stub.cmb_printer = Combo()
        stub._on_printer_changed = lambda i: None
        with mock.patch.object(pd.QPrinterInfo, "availablePrinterNames", return_value=[]), \
                mock.patch.object(pd.QPrinterInfo, "defaultPrinterName", return_value=""):
            pd.AuraPrintDialog._populate_printers(stub)
        self.assertEqual(items, ["save_pdf"])


if __name__ == "__main__":
    unittest.main()
