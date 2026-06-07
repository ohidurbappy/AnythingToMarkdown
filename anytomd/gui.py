"""PySide6 graphical interface for AnythingToMarkdown.

Design goals: a clean, modern, professional look; obvious drag-and-drop; and
batch conversion that never freezes the UI (work runs on a background thread).

Files are shown in a single table (Serial / Input / Output / Status), so the
input, its destination, and its progress all live in one place.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QAction, QColor, QKeySequence, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import __app_name__, __version__
from .converter import Converter, ConversionResult, SUPPORTED_EXTENSIONS, expand_inputs
from . import theme as _theme


_DIALOG_FILTER = (
    "Supported documents ("
    + " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS)
    + ");;All files (*)"
)

# The active palette is stored here once the theme is applied so widgets that
# need to colour themselves at runtime (status badges) can match it.
ACTIVE_PALETTE: _theme.Palette = _theme.LIGHT

# Table column indices.
COL_SERIAL = 0
COL_INPUT = 1
COL_OUTPUT = 2
COL_STATUS = 3


class ConversionWorker(QObject):
    """Runs the batch conversion off the UI thread."""

    progress = Signal(int, int, object)   # done, total, ConversionResult
    finished = Signal(int, int)           # succeeded, failed
    failed_to_start = Signal(str)

    def __init__(
        self,
        files: List[Path],
        output_dir: Optional[Path],
        overwrite: bool,
        enable_plugins: bool,
    ):
        super().__init__()
        self._files = files
        self._output_dir = output_dir
        self._overwrite = overwrite
        self._enable_plugins = enable_plugins
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            converter = Converter(enable_plugins=self._enable_plugins)
        except Exception as exc:
            self.failed_to_start.emit(str(exc))
            return

        total = len(self._files)
        succeeded = failed = 0
        for i, f in enumerate(self._files, start=1):
            if self._cancelled:
                break
            if self._output_dir is not None:
                res = converter.convert_file(
                    f, output_dir=self._output_dir, overwrite=self._overwrite,
                )
            else:
                res = converter.convert_file(
                    f, output_path=f.with_suffix(".md"),
                    overwrite=self._overwrite,
                )
            if res.success:
                succeeded += 1
            else:
                failed += 1
            self.progress.emit(i, total, res)

        self.finished.emit(succeeded, failed)


class DropTable(QTableWidget):
    """A QTableWidget that accepts dropped files/folders and shows an empty state."""

    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("FileTable")
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setProperty("dragActive", False)

        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["#", "Input", "Output", "Status"])
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setAlternatingRowColors(True)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        header = self.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(COL_SERIAL, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_INPUT, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_OUTPUT, QHeaderView.Stretch)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeToContents)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(34)

        # Centered empty-state overlay shown when the table has no rows.
        self._overlay = QWidget(self)
        ov = QVBoxLayout(self._overlay)
        ov.setAlignment(Qt.AlignCenter)
        ov.setSpacing(6)
        icon = QLabel("⤓")
        icon.setAlignment(Qt.AlignCenter)
        f = icon.font()
        f.setPointSize(40)
        icon.setFont(f)
        icon.setObjectName("DropHint")
        big = QLabel("Drag & drop documents here")
        big.setObjectName("DropHintBig")
        big.setAlignment(Qt.AlignCenter)
        small = QLabel("PDF, Word, Excel, PowerPoint, HTML, images and more — or use “Add files”.")
        small.setObjectName("DropHint")
        small.setAlignment(Qt.AlignCenter)
        small.setWordWrap(True)
        ov.addWidget(icon)
        ov.addWidget(big)
        ov.addWidget(small)
        self._overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def _set_drag_active(self, active: bool) -> None:
        if self.property("dragActive") != active:
            self.setProperty("dragActive", active)
            self.style().unpolish(self)
            self.style().polish(self)

    def refresh_overlay(self) -> None:
        self._overlay.setVisible(self.rowCount() == 0)
        self._position_overlay()

    def _position_overlay(self) -> None:
        top = self.horizontalHeader().height()
        self._overlay.setGeometry(
            0, top, self.viewport().width(), self.viewport().height()
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_overlay()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self._set_drag_active(True)
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self._set_drag_active(False)
        if event.mimeData().hasUrls():
            paths = [Path(u.toLocalFile()) for u in event.mimeData().urls()
                     if u.toLocalFile()]
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


def _card(*, object_name: str = "Card") -> QFrame:
    frame = QFrame()
    frame.setObjectName(object_name)
    return frame


# Status presentation: (label, palette-colour-attribute).
_STATUS_QUEUED = ("Queued", "muted")
_STATUS_CONVERTING = ("Converting…", "accent")
_STATUS_DONE = ("✓ Done", "success")
_STATUS_FAILED = ("✗ Failed", "danger")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{__app_name__}")
        self.resize(940, 700)
        self.setMinimumSize(720, 540)

        self._files: List[Path] = []
        self._output_dir: Optional[Path] = None
        self._thread: Optional[QThread] = None
        self._worker: Optional[ConversionWorker] = None

        self._build_ui()
        self._build_menu()
        self._refresh_state()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(22, 20, 22, 18)
        outer.setSpacing(16)

        outer.addLayout(self._build_header())
        outer.addWidget(self._build_table_card(), stretch=1)
        outer.addWidget(self._build_options_card())
        outer.addLayout(self._build_action_row())

        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)

        badge = QLabel("M↓")
        badge.setFixedSize(46, 46)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            "background:#2563eb; color:white; border-radius:12px;"
            "font-size:18px; font-weight:700;"
        )
        row.addWidget(badge)

        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel(__app_name__)
        title.setObjectName("AppTitle")
        subtitle = QLabel("Convert documents to clean Markdown")
        subtitle.setObjectName("AppSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        row.addLayout(titles)
        row.addStretch(1)

        ver = QLabel(f"v{__version__}")
        ver.setObjectName("AppSubtitle")
        ver.setAlignment(Qt.AlignTop | Qt.AlignRight)
        row.addWidget(ver)
        return row

    def _build_table_card(self) -> QFrame:
        card = _card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 16)
        lay.setSpacing(10)

        head = QHBoxLayout()
        lbl = QLabel("FILES")
        lbl.setObjectName("SectionLabel")
        self.count_label = QLabel("")
        self.count_label.setObjectName("AppSubtitle")
        head.addWidget(lbl)
        head.addStretch(1)
        head.addWidget(self.count_label)
        lay.addLayout(head)

        self.file_table = DropTable()
        self.file_table.files_dropped.connect(self._add_paths)
        lay.addWidget(self.file_table, stretch=1)
        self.file_table.refresh_overlay()

        # File-management buttons
        btns = QHBoxLayout()
        btns.setSpacing(8)
        self.btn_add = self._mk_button("Add files", QStyle.SP_DialogOpenButton, self._choose_files)
        self.btn_add_folder = self._mk_button("Add folder", QStyle.SP_DirOpenIcon, self._choose_folder)
        self.btn_remove = self._mk_button("Remove", QStyle.SP_TrashIcon, self._remove_selected)
        self.btn_clear = self._mk_button("Clear all", QStyle.SP_DialogResetButton, self._clear_files)
        btns.addWidget(self.btn_add)
        btns.addWidget(self.btn_add_folder)
        btns.addStretch(1)
        btns.addWidget(self.btn_remove)
        btns.addWidget(self.btn_clear)
        lay.addLayout(btns)
        return card

    def _build_options_card(self) -> QFrame:
        card = _card()
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(12)

        lbl = QLabel("OUTPUT")
        lbl.setObjectName("SectionLabel")
        lay.addWidget(lbl)

        out_row = QHBoxLayout()
        out_row.setSpacing(8)
        self.out_label = QLabel()
        self.out_label.setObjectName("OutPath")
        self.out_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.out_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.btn_choose_out = self._mk_button("Choose folder", QStyle.SP_DirIcon, self._choose_output_dir)
        self.btn_clear_out = self._mk_button("Use source folders", None, self._clear_output_dir)
        out_row.addWidget(self.out_label, stretch=1)
        out_row.addWidget(self.btn_choose_out)
        out_row.addWidget(self.btn_clear_out)
        lay.addLayout(out_row)

        opt_row = QHBoxLayout()
        opt_row.setSpacing(20)
        self.chk_overwrite = QCheckBox("Overwrite existing .md files")
        self.chk_overwrite.setChecked(True)
        self.chk_plugins = QCheckBox("Enable plugins")
        self.chk_plugins.setToolTip("Enable third-party MarkItDown plugins.")
        opt_row.addWidget(self.chk_overwrite)
        opt_row.addWidget(self.chk_plugins)
        opt_row.addStretch(1)
        lay.addLayout(opt_row)
        return card

    def _build_action_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setFormat("%v / %m")
        self.progress.setTextVisible(False)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("Danger")
        self.btn_cancel.clicked.connect(self._cancel_conversion)
        self.btn_cancel.setVisible(False)

        self.btn_convert = QPushButton("Convert to Markdown")
        self.btn_convert.setObjectName("Primary")
        self.btn_convert.setMinimumWidth(200)
        self.btn_convert.clicked.connect(self._start_conversion)

        row.addWidget(self.progress, stretch=1)
        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_convert)
        return row

    def _mk_button(self, text, std_icon, slot) -> QPushButton:
        btn = QPushButton(text)
        if std_icon is not None:
            btn.setIcon(self.style().standardIcon(std_icon))
        btn.clicked.connect(slot)
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        act_add = QAction("Add files…", self)
        act_add.setShortcut(QKeySequence.Open)
        act_add.triggered.connect(self._choose_files)
        file_menu.addAction(act_add)

        act_out = QAction("Choose output folder…", self)
        act_out.triggered.connect(self._choose_output_dir)
        file_menu.addAction(act_out)

        file_menu.addSeparator()
        act_quit = QAction("Quit", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        help_menu = self.menuBar().addMenu("&Help")
        act_about = QAction("About", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    # ------------------------------------------------------------------ #
    # Table helpers
    # ------------------------------------------------------------------ #
    def _output_path_for(self, src: Path) -> Path:
        """Destination path a file would be written to with current settings."""
        if self._output_dir is not None:
            return self._output_dir / (src.stem + ".md")
        return src.with_suffix(".md")

    def _set_status(self, row: int, status: tuple[str, str]) -> None:
        label, colour_attr = status
        item = self.file_table.item(row, COL_STATUS)
        if item is None:
            return
        item.setText(label)
        item.setForeground(QColor(getattr(ACTIVE_PALETTE, colour_attr)))

    def _append_row(self, path: Path) -> None:
        row = self.file_table.rowCount()
        self.file_table.insertRow(row)

        serial = QTableWidgetItem(str(row + 1))
        serial.setTextAlignment(Qt.AlignCenter)
        serial.setForeground(QColor(ACTIVE_PALETTE.muted))

        inp = QTableWidgetItem(path.name)
        inp.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        inp.setToolTip(str(path))

        out_path = self._output_path_for(path)
        out = QTableWidgetItem(out_path.name)
        out.setForeground(QColor(ACTIVE_PALETTE.muted))
        out.setToolTip(str(out_path))

        status = QTableWidgetItem(_STATUS_QUEUED[0])
        status.setTextAlignment(Qt.AlignCenter)
        status.setForeground(QColor(ACTIVE_PALETTE.muted))

        self.file_table.setItem(row, COL_SERIAL, serial)
        self.file_table.setItem(row, COL_INPUT, inp)
        self.file_table.setItem(row, COL_OUTPUT, out)
        self.file_table.setItem(row, COL_STATUS, status)

    def _refresh_output_column(self) -> None:
        """Recompute the Output column after the destination setting changes."""
        for row, src in enumerate(self._files):
            out_path = self._output_path_for(src)
            item = self.file_table.item(row, COL_OUTPUT)
            if item is not None:
                item.setText(out_path.name)
                item.setToolTip(str(out_path))

    def _renumber(self) -> None:
        for row in range(self.file_table.rowCount()):
            item = self.file_table.item(row, COL_SERIAL)
            if item is not None:
                item.setText(str(row + 1))

    # ------------------------------------------------------------------ #
    # File management
    # ------------------------------------------------------------------ #
    def _add_paths(self, paths: List[Path]) -> None:
        expanded = expand_inputs(paths, recursive=True)
        added = 0
        existing = set(self._files)
        for p in expanded:
            if p not in existing:
                self._files.append(p)
                existing.add(p)
                self._append_row(p)
                added += 1
        if added:
            self.statusBar().showMessage(f"Added {added} file(s).", 4000)
        elif paths:
            self.statusBar().showMessage("No new convertible files found.", 4000)
        self.file_table.refresh_overlay()
        self._refresh_state()

    def _choose_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select documents", "", _DIALOG_FILTER,
        )
        if files:
            self._add_paths([Path(f) for f in files])

    def _choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select a folder")
        if folder:
            self._add_paths([Path(folder)])

    def _remove_selected(self) -> None:
        rows = sorted(
            {idx.row() for idx in self.file_table.selectedIndexes()},
            reverse=True,
        )
        for row in rows:
            self.file_table.removeRow(row)
            del self._files[row]
        self._renumber()
        self.file_table.refresh_overlay()
        self._refresh_state()

    def _clear_files(self) -> None:
        self.file_table.setRowCount(0)
        self._files.clear()
        self.file_table.refresh_overlay()
        self._refresh_state()

    # ------------------------------------------------------------------ #
    # Output dir
    # ------------------------------------------------------------------ #
    def _choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select output folder")
        if folder:
            self._output_dir = Path(folder)
            self._refresh_output_column()
            self._refresh_state()

    def _clear_output_dir(self) -> None:
        self._output_dir = None
        self._refresh_output_column()
        self._refresh_state()

    # ------------------------------------------------------------------ #
    # Conversion
    # ------------------------------------------------------------------ #
    def _start_conversion(self) -> None:
        if not self._files or self._thread is not None:
            return

        self.progress.setRange(0, len(self._files))
        self.progress.setValue(0)
        for row in range(self.file_table.rowCount()):
            self._set_status(row, _STATUS_QUEUED)
        self._set_running(True)

        self._thread = QThread()
        self._worker = ConversionWorker(
            files=list(self._files),
            output_dir=self._output_dir,
            overwrite=self.chk_overwrite.isChecked(),
            enable_plugins=self.chk_plugins.isChecked(),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed_to_start.connect(self._on_failed_to_start)
        self._thread.start()

    def _cancel_conversion(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.statusBar().showMessage("Cancelling…", 3000)

    def _on_progress(self, done: int, total: int, res: ConversionResult) -> None:
        self.progress.setValue(done)
        row = done - 1  # files are processed in table order
        if 0 <= row < self.file_table.rowCount():
            if res.success:
                self._set_status(row, _STATUS_DONE)
                if res.output_path is not None:
                    out = self.file_table.item(row, COL_OUTPUT)
                    if out is not None:
                        out.setText(res.output_path.name)
                        out.setToolTip(str(res.output_path))
                        out.setForeground(QColor(ACTIVE_PALETTE.text))
            else:
                self._set_status(row, _STATUS_FAILED)
                status = self.file_table.item(row, COL_STATUS)
                if status is not None and res.error:
                    status.setToolTip(res.error)
        # Light-touch "in progress" hint for the next file.
        nxt = done
        if nxt < self.file_table.rowCount():
            self._set_status(nxt, _STATUS_CONVERTING)

    def _on_finished(self, succeeded: int, failed: int) -> None:
        self._teardown_thread()
        self._set_running(False)
        msg = f"Finished: {succeeded} succeeded, {failed} failed."
        self.statusBar().showMessage(msg, 8000)
        if failed == 0 and succeeded > 0:
            self.progress.setValue(self.progress.maximum())

    def _on_failed_to_start(self, message: str) -> None:
        self._teardown_thread()
        self._set_running(False)
        QMessageBox.critical(self, "Could not start", message)

    def _teardown_thread(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
            self._worker = None

    def _set_running(self, running: bool) -> None:
        self.btn_convert.setVisible(not running)
        self.btn_cancel.setVisible(running)
        for b in (self.btn_add, self.btn_add_folder, self.btn_remove,
                  self.btn_clear, self.btn_choose_out, self.btn_clear_out):
            b.setEnabled(not running)

    # ------------------------------------------------------------------ #
    # Misc
    # ------------------------------------------------------------------ #
    def _refresh_state(self) -> None:
        n = len(self._files)
        self.btn_convert.setEnabled(n > 0)
        self.btn_remove.setEnabled(n > 0)
        self.btn_clear.setEnabled(n > 0)
        self.count_label.setText(f"{n} queued" if n else "")
        if self._output_dir is None:
            self.out_label.setText("📁  Alongside each source file")
        else:
            self.out_label.setText(f"📁  {self._output_dir}")

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {__app_name__}",
            f"<h3>{__app_name__} {__version__}</h3>"
            "<p>Convert PDFs, Office documents, HTML, images and more to "
            "Markdown.</p>"
            "<p>Powered by Microsoft's "
            "<a href='https://github.com/microsoft/markitdown'>MarkItDown</a> "
            "and PySide6.</p>",
        )

    def closeEvent(self, event):
        if self._thread is not None and self._thread.isRunning():
            if self._worker:
                self._worker.cancel()
            self._thread.quit()
            self._thread.wait(3000)
        event.accept()


def _is_dark(app: QApplication) -> bool:
    """Detect whether the OS / app is using a dark colour scheme."""
    # Qt 6.5+ exposes the OS scheme directly.
    try:
        from PySide6.QtCore import Qt as _Qt
        scheme = app.styleHints().colorScheme()
        if scheme == _Qt.ColorScheme.Dark:
            return True
        if scheme == _Qt.ColorScheme.Light:
            return False
    except Exception:
        pass
    # Fallback: infer from the window background luminance.
    c = app.palette().color(QPalette.Window)
    return (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) < 128


def _checkmark_url() -> str:
    """Render a white checkmark PNG to a temp file; return it as a QSS url path.

    Generated at runtime so there's no asset to bundle — works in the .app too.
    """
    import tempfile
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPixmap, QPainter, QPen, QColor

    size = 18
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor("#ffffff"))
    pen.setWidthF(2.2)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline([QPointF(4, 9.5), QPointF(7.6, 13), QPointF(14, 5.5)])
    painter.end()

    path = Path(tempfile.gettempdir()) / "anytomd_check.png"
    pm.save(str(path))
    return path.as_posix()


def apply_theme(app: QApplication) -> None:
    global ACTIVE_PALETTE
    app.setStyle("Fusion")
    palette = _theme.DARK if _is_dark(app) else _theme.LIGHT
    ACTIVE_PALETTE = palette
    try:
        check = _checkmark_url()
    except Exception:
        check = ""
    app.setStyleSheet(_theme.stylesheet(palette, check_url=check))


def launch_gui(argv: Optional[List[str]] = None) -> int:
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    apply_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(launch_gui())
