import sys
import pandas as pd
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore
import os

EXTRA_ROWS = 100
EXTRA_COLS = 10


class EditCellCommand(QtGui.QUndoCommand):
    def __init__(self, table_widget, window, row, col, old_value, new_value):
        super().__init__()
        self.table_widget = table_widget
        self.window = window
        self.row = row
        self.col = col
        self.old_value = old_value
        self.new_value = new_value

    def undo(self):
        self.window._is_undoing = True
        self.table_widget.item(self.row, self.col).setText(self.old_value)
        self.window._last_value[(self.row, self.col)] = self.old_value
        self.window._is_undoing = False

    def redo(self):
        self.window._is_undoing = True
        self.table_widget.item(self.row, self.col).setText(self.new_value)
        self.window._last_value[(self.row, self.col)] = self.new_value
        self.window._is_undoing = False


def col_index_to_letters(n):
    result = ""
    n += 1
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


class CSVEditorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV Editor")
        self.setGeometry(100, 100, 800, 600)
        self.current_file_path = None
        self._last_value = {}
        self._is_undoing = False
        self._is_modified = False
        self.autosave_timer = None
        self._search_matches = []
        self._search_index = 0

        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        self.vertical_layout = QtWidgets.QVBoxLayout()
        self.central_widget.setLayout(self.vertical_layout)

        # Toolbar
        self.toolbar_layout = QtWidgets.QHBoxLayout()
        self.vertical_layout.addLayout(self.toolbar_layout)

        self.open_file_button = QtWidgets.QPushButton("Open File")
        self.open_file_button.clicked.connect(self.open_file)
        self.toolbar_layout.addWidget(self.open_file_button)

        self.save_button = QtWidgets.QPushButton("Save")
        self.save_button.setVisible(False)
        self.save_button.clicked.connect(self.save_file)
        self.toolbar_layout.addWidget(self.save_button)

        self.save_as_button = QtWidgets.QPushButton("Save As")
        self.save_as_button.setVisible(True)
        self.save_as_button.clicked.connect(self.save_file_as)
        self.toolbar_layout.addWidget(self.save_as_button)

        self.autosave_button = QtWidgets.QPushButton("Autosave: Off")
        self.autosave_button.setCheckable(True)
        self.autosave_button.toggled.connect(self.toggle_autosave)
        self.toolbar_layout.addWidget(self.autosave_button)

        self.file_path_label = QtWidgets.QLabel("New File")
        self.toolbar_layout.addWidget(self.file_path_label)

        # Table
        self.table_widget = QtWidgets.QTableWidget()
        self.vertical_layout.addWidget(self.table_widget)
        self.table_widget.itemChanged.connect(self.on_cell_changed)

        self.table_widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_widget.customContextMenuRequested.connect(self.show_context_menu)

        self.table_widget.horizontalHeader().setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_widget.horizontalHeader().customContextMenuRequested.connect(self.show_column_header_context_menu)

        self.table_widget.verticalHeader().setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_widget.verticalHeader().customContextMenuRequested.connect(self.show_row_header_context_menu)

        self.table_widget.setStyleSheet("QTableWidget QLineEdit { background-color: black; }")

        # Find/Replace bar (hidden by default)
        self.find_bar = QtWidgets.QWidget()
        self.find_bar.setVisible(False)
        find_bar_layout = QtWidgets.QHBoxLayout()
        find_bar_layout.setContentsMargins(4, 4, 4, 4)
        self.find_bar.setLayout(find_bar_layout)

        find_bar_layout.addWidget(QtWidgets.QLabel("Find:"))
        self.find_input = QtWidgets.QLineEdit()
        self.find_input.setPlaceholderText("Search...")
        self.find_input.textChanged.connect(self.on_search_text_changed)
        self.find_input.returnPressed.connect(self.find_next)
        find_bar_layout.addWidget(self.find_input)

        self.find_prev_button = QtWidgets.QPushButton("▲")
        self.find_prev_button.setFixedWidth(30)
        self.find_prev_button.clicked.connect(self.find_prev)
        find_bar_layout.addWidget(self.find_prev_button)

        self.find_next_button = QtWidgets.QPushButton("▼")
        self.find_next_button.setFixedWidth(30)
        self.find_next_button.clicked.connect(self.find_next)
        find_bar_layout.addWidget(self.find_next_button)

        self.match_label = QtWidgets.QLabel("")
        find_bar_layout.addWidget(self.match_label)

        find_bar_layout.addWidget(QtWidgets.QLabel("Replace:"))
        self.replace_input = QtWidgets.QLineEdit()
        self.replace_input.setPlaceholderText("Replace with...")
        find_bar_layout.addWidget(self.replace_input)

        self.replace_button = QtWidgets.QPushButton("Replace")
        self.replace_button.clicked.connect(self.replace_current)
        find_bar_layout.addWidget(self.replace_button)

        self.replace_all_button = QtWidgets.QPushButton("Replace All")
        self.replace_all_button.clicked.connect(self.replace_all)
        find_bar_layout.addWidget(self.replace_all_button)

        self.close_find_button = QtWidgets.QPushButton("✕")
        self.close_find_button.setFixedWidth(30)
        self.close_find_button.clicked.connect(self.close_find_bar)
        find_bar_layout.addWidget(self.close_find_button)

        self.vertical_layout.addWidget(self.find_bar)

        # Shortcuts
        save_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_file)

        save_as_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+S"), self)
        save_as_shortcut.activated.connect(self.save_file_as)

        self.undo_stack = QtGui.QUndoStack(self)

        undo_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.undo_stack.undo)

        redo_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Y"), self)
        redo_shortcut.activated.connect(self.undo_stack.redo)

        find_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+F"), self)
        find_shortcut.activated.connect(self.open_find_bar)

        self.new_file()


    def open_find_bar(self):
        self.find_bar.setVisible(True)
        self.find_input.setFocus()
        self.find_input.selectAll()
        self._run_search()

    def close_find_bar(self):
        self.find_bar.setVisible(False)
        self._clear_highlights()
        self._search_matches = []
        self.match_label.setText("")
        self.table_widget.setFocus()

    def on_search_text_changed(self):
        self._search_index = 0
        self._run_search()

    def _run_search(self):
        self._clear_highlights()
        self._search_matches = []
        query = self.find_input.text()
        if not query:
            self.match_label.setText("")
            return

        rows = self.table_widget.rowCount()
        cols = self.table_widget.columnCount()
        for r in range(rows):
            for c in range(cols):
                item = self.table_widget.item(r, c)
                if item and query.lower() in item.text().lower():
                    self._search_matches.append((r, c))
                    item.setBackground(QtGui.QColor("#7a6000"))  # dim gold highlight

        if self._search_matches:
            self._search_index = min(self._search_index, len(self._search_matches) - 1)
            self._highlight_current()
        else:
            self.match_label.setText("No matches")

    def _highlight_current(self):
        if not self._search_matches:
            return
        r, c = self._search_matches[self._search_index]
        self.table_widget.scrollToItem(self.table_widget.item(r, c))
        self.table_widget.setCurrentCell(r, c)
        # Brighten the current match
        for i, (mr, mc) in enumerate(self._search_matches):
            color = "#f0c000" if i == self._search_index else "#7a6000"
            item = self.table_widget.item(mr, mc)
            if item:
                item.setBackground(QtGui.QColor(color))
        self.match_label.setText(f"{self._search_index + 1} / {len(self._search_matches)}")

    def _clear_highlights(self):
        for r, c in self._search_matches:
            item = self.table_widget.item(r, c)
            if item:
                item.setBackground(QtGui.QColor("transparent"))

    def find_next(self):
        if not self._search_matches:
            return
        self._search_index = (self._search_index + 1) % len(self._search_matches)
        self._highlight_current()

    def find_prev(self):
        if not self._search_matches:
            return
        self._search_index = (self._search_index - 1) % len(self._search_matches)
        self._highlight_current()

    def replace_current(self):
        if not self._search_matches:
            return
        r, c = self._search_matches[self._search_index]
        item = self.table_widget.item(r, c)
        if item:
            new_text = item.text().replace(self.find_input.text(), self.replace_input.text())
            item.setText(new_text)
        self._run_search()

    def replace_all(self):
        if not self._search_matches:
            return
        query = self.find_input.text()
        replacement = self.replace_input.text()
        for r, c in list(self._search_matches):
            item = self.table_widget.item(r, c)
            if item:
                item.setText(item.text().replace(query, replacement))
        self._run_search()


    def new_file(self):
        self.current_file_path = None
        self._is_modified = False
        self._last_value = {}
        self.undo_stack.clear()
        self.file_path_label.setText("New File")
        self.save_button.setVisible(False)
        self.table_widget.setRowCount(EXTRA_ROWS)
        self.table_widget.setColumnCount(EXTRA_COLS)
        self.set_column_headers(EXTRA_COLS)

    def _check_unsaved_changes(self):
        if self._is_modified:
            reply = QtWidgets.QMessageBox.question(
                self, "Unsaved Changes", "You have unsaved changes. Save before continuing?",
                QtWidgets.QMessageBox.StandardButton.Yes |
                QtWidgets.QMessageBox.StandardButton.No |
                QtWidgets.QMessageBox.StandardButton.Cancel
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.save_file()
                return True
            elif reply == QtWidgets.QMessageBox.StandardButton.No:
                return True
            else:
                return False
        return True

    def set_column_headers(self, count):
        self.table_widget.setHorizontalHeaderLabels(
            [col_index_to_letters(i) for i in range(count)]
        )

    def toggle_autosave(self, checked):
        if checked:
            if not self.current_file_path:
                QtWidgets.QMessageBox.warning(
                    self, "Autosave Unavailable",
                    "Please save the file first before enabling autosave."
                )
                self.autosave_button.blockSignals(True)
                self.autosave_button.setChecked(False)
                self.autosave_button.blockSignals(False)
                self.autosave_button.setText("Autosave: Off")
                return
            self.autosave_button.setText("Autosave: On")
            self.autosave_timer = QtCore.QTimer(self)
            self.autosave_timer.setInterval(2000)
            self.autosave_timer.setSingleShot(True)
            self.autosave_timer.timeout.connect(self.save_file)
            self.table_widget.itemChanged.connect(self.start_autosave_timer)
        else:
            self.autosave_button.setText("Autosave: Off")
            try:
                self.table_widget.itemChanged.disconnect(self.start_autosave_timer)
            except RuntimeError:
                pass
            if self.autosave_timer:
                self.autosave_timer.stop()

    def start_autosave_timer(self):
        if self.autosave_timer:
            self.autosave_timer.start()

    def get_data(self, path=None):
        if path is None:
            raise ValueError("Path must be provided.")
        if not path.endswith('.csv'):
            raise ValueError("File must be a CSV file.")
        try:
            data = pd.read_csv(path)
        except Exception:
            data = pd.DataFrame()
        return data

    def write_data(self, data=None, path=None):
        if data is None:
            raise ValueError("Data must be provided.")
        if not isinstance(data, pd.DataFrame):
            raise ValueError("Data must be a pandas DataFrame.")
        if path is None:
            raise ValueError("Path must be provided.")
        data.to_csv(path, index=False)

    def toggleFullScreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def open_file(self):
        if not self._check_unsaved_changes():
            return
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open File", "", "CSV Files (*.csv)"
        )
        if file_path:
            self._is_modified = False
            self.undo_stack.clear()
            self.current_file_path = file_path
            self.file_path_label.setText(file_path)
            self.save_button.setVisible(True)
            self.save_as_button.setVisible(True)
            data = self.get_data(file_path)

            if data.empty:
                self.table_widget.setRowCount(EXTRA_ROWS)
                self.table_widget.setColumnCount(EXTRA_COLS)
                self.set_column_headers(EXTRA_COLS)
                return

            num_cols = data.shape[1] + EXTRA_COLS
            num_rows = data.shape[0] + 1 + EXTRA_ROWS

            self.table_widget.setRowCount(num_rows)
            self.table_widget.setColumnCount(num_cols)
            self.set_column_headers(num_cols)

            for j, col_name in enumerate(data.columns):
                self.table_widget.setItem(0, j, QtWidgets.QTableWidgetItem(str(col_name)))

            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    self.table_widget.setItem(
                        i + 1, j, QtWidgets.QTableWidgetItem(str(data.iloc[i, j]))
                    )

    def get_table_data(self):
        rows = self.table_widget.rowCount()
        cols = self.table_widget.columnCount()

        headers = []
        for j in range(cols):
            item = self.table_widget.item(0, j)
            headers.append(item.text() if item else "")

        data = []
        for i in range(1, rows):
            row = []
            for j in range(cols):
                item = self.table_widget.item(i, j)
                row.append(item.text() if item else "")
            data.append(row)

        df = pd.DataFrame(data, columns=headers)
        df = df[~df.apply(lambda row: all(v == "" for v in row), axis=1)]
        non_empty_cols = [
            j for j, h in enumerate(df.columns)
            if h != "" or df.iloc[:, j].apply(lambda v: v != "").any()
        ]
        df = df.iloc[:, non_empty_cols]
        return df

    def save_file(self):
        if not self.current_file_path:
            self.save_file_as()
            return
        try:
            self.write_data(self.get_table_data(), self.current_file_path)
            self._is_modified = False
        except Exception:
            with open(self.current_file_path, 'w') as f:
                f.write('')

    def save_file_as(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save As", "", "CSV Files (*.csv)"
        )
        if file_path:
            self.current_file_path = file_path
            self.file_path_label.setText(file_path)
            self.save_button.setVisible(True)
            self.write_data(self.get_table_data(), file_path)
            self._is_modified = False

    def on_cell_changed(self, item):
        if self._is_undoing:
            return
        row, col = item.row(), item.column()
        old_value = self._last_value.get((row, col), "")
        new_value = item.text()
        if old_value == new_value:
            return
        self._is_modified = True
        self._last_value[(row, col)] = new_value
        command = EditCellCommand(self.table_widget, self, row, col, old_value, new_value)
        self.undo_stack.push(command)

    def show_context_menu(self, position):
        menu = QtWidgets.QMenu(self)
        col = self.table_widget.horizontalHeader().logicalIndexAt(position)
        row = self.table_widget.verticalHeader().logicalIndexAt(position)
        add_right = menu.addAction("Add a Column to the Right")
        add_right.triggered.connect(lambda: self._insert_column(col + 1))
        add_left = menu.addAction("Add a Column to the Left")
        add_left.triggered.connect(lambda: self._insert_column(col if col >= 0 else 0))
        add_below = menu.addAction("Add a Row below")
        add_below.triggered.connect(lambda: self.table_widget.insertRow(row + 1))
        add_above = menu.addAction("Add a Row above")
        add_above.triggered.connect(lambda: self.table_widget.insertRow(row if row >= 0 else 0))
        delete_row = menu.addAction("Delete this Row")
        delete_row.triggered.connect(lambda: self.table_widget.removeRow(row))
        delete_column = menu.addAction("Delete this Column")
        delete_column.triggered.connect(lambda: self._remove_column(col))
        menu.exec(self.table_widget.viewport().mapToGlobal(position))

    def show_column_header_context_menu(self, position):
        col = self.table_widget.horizontalHeader().logicalIndexAt(position)
        menu = QtWidgets.QMenu(self)
        delete_action = menu.addAction("Delete Column")
        add_column_left = menu.addAction("Add Column to the Left")
        add_column_right = menu.addAction("Add Column to the Right")
        delete_action.triggered.connect(lambda: self._remove_column(col))
        add_column_left.triggered.connect(lambda: self._insert_column(col))
        add_column_right.triggered.connect(lambda: self._insert_column(col + 1))
        menu.exec(self.table_widget.horizontalHeader().mapToGlobal(position))

    def show_row_header_context_menu(self, position):
        row = self.table_widget.verticalHeader().logicalIndexAt(position)
        menu = QtWidgets.QMenu(self)
        delete_action = menu.addAction("Delete Row")
        insert_above_action = menu.addAction("Insert Row Above")
        insert_below_action = menu.addAction("Insert Row Below")
        delete_action.triggered.connect(lambda: self.table_widget.removeRow(row))
        insert_above_action.triggered.connect(lambda: self.table_widget.insertRow(row))
        insert_below_action.triggered.connect(lambda: self.table_widget.insertRow(row + 1))
        menu.exec(self.table_widget.verticalHeader().mapToGlobal(position))

    def _insert_column(self, col):
        self.table_widget.insertColumn(col)
        self.set_column_headers(self.table_widget.columnCount())

    def _remove_column(self, col):
        self.table_widget.removeColumn(col)
        self.set_column_headers(self.table_widget.columnCount())

    def closeEvent(self, event):
        if self.autosave_button.isChecked() and self.current_file_path:
            self.save_file()
            event.accept()
            return
        if self._is_modified:
            reply = QtWidgets.QMessageBox.question(
                self, "Quit", "Save before closing?",
                QtWidgets.QMessageBox.StandardButton.Yes |
                QtWidgets.QMessageBox.StandardButton.No |
                QtWidgets.QMessageBox.StandardButton.Cancel
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.save_file()
                event.accept()
            elif reply == QtWidgets.QMessageBox.StandardButton.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            selected = self.table_widget.selectedItems()
            if selected:
                for item in selected:
                    item.setText("")
        elif event.key() == QtCore.Qt.Key.Key_Escape:
            if self.find_bar.isVisible():
                self.close_find_bar()
        else:
            super().keyPressEvent(event)
    
    def open_file_from_path(self, file_path):
        self._is_modified = False
        self.undo_stack.clear()
        self.current_file_path = file_path
        self.file_path_label.setText(file_path)
        self.save_button.setVisible(True)
        self.save_as_button.setVisible(True)
        data = self.get_data(file_path)

        if data.empty:
            self.table_widget.setRowCount(EXTRA_ROWS)
            self.table_widget.setColumnCount(EXTRA_COLS)
            self.set_column_headers(EXTRA_COLS)
            return

        num_cols = data.shape[1] + EXTRA_COLS
        num_rows = data.shape[0] + 1 + EXTRA_ROWS

        self.table_widget.setRowCount(num_rows)
        self.table_widget.setColumnCount(num_cols)
        self.set_column_headers(num_cols)

        for j, col_name in enumerate(data.columns):
            self.table_widget.setItem(0, j, QtWidgets.QTableWidgetItem(str(col_name)))

        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                self.table_widget.setItem(
                    i + 1, j, QtWidgets.QTableWidgetItem(str(data.iloc[i, j]))
                )


def create_window():
    app = QtWidgets.QApplication(sys.argv)
    window = CSVEditorWindow()
    window.show()
    app.exec()

def create_window():
    app = QtWidgets.QApplication(sys.argv)
    window = CSVEditorWindow()
    window.show()

    # If a file path was passed (e.g. from right-click context menu), open it
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path) and file_path.endswith(".csv"):
            window.open_file_from_path(file_path)

    app.exec()


create_window()