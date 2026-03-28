import sys
import pandas as pd
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore

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
        self.autosave_timer = None

        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        self.vertical_layout = QtWidgets.QVBoxLayout()
        self.central_widget.setLayout(self.vertical_layout)

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
        self.save_as_button.setVisible(False)
        self.save_as_button.clicked.connect(self.save_file_as)
        self.toolbar_layout.addWidget(self.save_as_button)

        self.autosave_button = QtWidgets.QPushButton("Autosave: Off")
        self.autosave_button.setCheckable(True)
        self.autosave_button.toggled.connect(self.toggle_autosave)
        self.toolbar_layout.addWidget(self.autosave_button)

        self.file_path_label = QtWidgets.QLabel("No file selected")
        self.toolbar_layout.addWidget(self.file_path_label)

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

        save_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_file)

        save_as_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+S"), self)
        save_as_shortcut.activated.connect(self.save_file_as)

        self.undo_stack = QtGui.QUndoStack(self)

        undo_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.undo_stack.undo)

        redo_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Y"), self)
        redo_shortcut.activated.connect(self.undo_stack.redo)
        
        self._is_modified = False

    def set_column_headers(self, count):
        self.table_widget.setHorizontalHeaderLabels(
            [col_index_to_letters(i) for i in range(count)]
        )

    def toggle_autosave(self, checked):
        if checked:
            self.autosave_button.setText("Autosave: On")
            self.autosave_timer = QtCore.QTimer(self)
            self.autosave_timer.setInterval(2000)
            self.autosave_timer.setSingleShot(True)
            self.autosave_timer.timeout.connect(self.save_file)
            self.table_widget.itemChanged.connect(self.start_autosave_timer)
        else:
            self.autosave_button.setText("Autosave: Off")
            self.table_widget.itemChanged.disconnect(self.start_autosave_timer)
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
        self.save_as_button.setVisible(True)
        self.save_button.setVisible(True)
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
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open File", "", "CSV Files (*.csv)"
        )
        if file_path:
            if self.is_modified:
                reply = QtWidgets.QMessageBox.question( 
                    self, "Quit", "Save before opening new file?",
                    QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel,
                    QtWidgets.QMessageBox.Save
                )
                if reply == QtWidgets.QMessageBox.Save:
                    self.save_file()
            self._is_modified = False
            self.undo_stack.clear()
            self.current_file_path = file_path
            self.file_path_label.setText(file_path)
            data = self.get_data(file_path)

            if data.empty:
                self.table_widget.setRowCount(EXTRA_ROWS)
                self.table_widget.setColumnCount(EXTRA_COLS)
                self.set_column_headers(EXTRA_COLS)
                return

            num_cols = data.shape[1] + EXTRA_COLS
            num_rows = data.shape[0] + 1 + EXTRA_ROWS  # +1 for header row

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

        # Read headers from row 0
        headers = []
        for j in range(cols):
            item = self.table_widget.item(0, j)
            headers.append(item.text() if item else "")

        # Read data rows
        data = []
        for i in range(1, rows):
            row = []
            for j in range(cols):
                item = self.table_widget.item(i, j)
                row.append(item.text() if item else "")
            data.append(row)

        df = pd.DataFrame(data, columns=headers)

        # Drop completely empty rows
        df = df[~df.apply(lambda row: all(v == "" for v in row), axis=1)]

        # Drop completely empty columns (header is empty AND all values are empty)
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
            self.write_data(self.get_table_data(), file_path)

    def on_cell_changed(self, item):
        if self._is_undoing:
            return
        row, col = item.row(), item.column()
        old_value = self._last_value.get((row, col), "")
        new_value = item.text()
        if old_value == new_value:
            return
        self.is_modified = True
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

        if self.current_file_path and self._is_modified:
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


def create_window():
    app = QtWidgets.QApplication(sys.argv)
    window = CSVEditorWindow()
    window.show()
    app.exec()


create_window()
