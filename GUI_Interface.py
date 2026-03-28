import sys
import pandas as pd
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui
import PyQt6.QtCore as QtCore


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

class CSVEditorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CSV Editor")
        self.setGeometry(100, 100, 800, 600)
        self.current_file_path = None
        self._last_value = {}
        self._is_undoing = False

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
        self.table_widget.verticalHeader().sectionClicked.connect(self.on_row_header_clicked)

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
        self.table_widget.horizontalHeader().sectionDoubleClicked.connect(self.on_column_header_double_clicked)

    def toggle_autosave(self, checked):
        if checked:
            self.autosave_button.setText("Autosave: On")
            self.autosave_timer = QtCore.QTimer(self)
            self.autosave_timer.setInterval(2000)
            self.autosave_timer.timeout.connect(self.save_file)
            self.table_widget.itemChanged.connect(self.start_autosave_timer)
        else:
            self.autosave_button.setText("Autosave: Off")
            self.table_widget.itemChanged.disconnect(self.start_autosave_timer)
            self.autosave_timer.stop()

    def start_autosave_timer(self):
        self.autosave_timer.start()

    def on_column_header_double_clicked(self, col):
        old_name = self.table_widget.horizontalHeaderItem(col).text()
        new_name, ok = QtWidgets.QInputDialog.getText(
            self, "Rename Column", "Enter new column name:", text=old_name
        )
        if ok and new_name and new_name != old_name:
            self.table_widget.horizontalHeaderItem(col).setText(new_name)

    def get_data(self, path=None):
        if path is None:
            raise ValueError("Path must be provided.")
        if not path.endswith('.csv'):
            raise ValueError("File must be a CSV file.")
        self.save_as_button.setVisible(True)
        self.save_button.setVisible(True)
        data = pd.read_csv(path)
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
            self.current_file_path = file_path
            self.file_path_label.setText(file_path)
            data = self.get_data(file_path)
            self.table_widget.setRowCount(data.shape[0])
            self.table_widget.setColumnCount(data.shape[1])
            self.table_widget.setHorizontalHeaderLabels(list(data.columns))
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    self.table_widget.setItem(
                        i, j, QtWidgets.QTableWidgetItem(str(data.iloc[i, j]))
                    )

    def get_table_data(self):
        rows = self.table_widget.rowCount()
        cols = self.table_widget.columnCount()
        headers = [self.table_widget.horizontalHeaderItem(j).text() for j in range(cols)]
        data = []
        for i in range(rows):
            row = []
            for j in range(cols):
                item = self.table_widget.item(i, j)
                row.append(item.text() if item else "")
            data.append(row)
        return pd.DataFrame(data, columns=headers)

    def save_file(self):
        if not self.current_file_path:
            self.save_file_as()
            return
        self.write_data(self.get_table_data(), self.current_file_path)

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
        self._last_value[(row, col)] = new_value
        command = EditCellCommand(self.table_widget, self, row, col, old_value, new_value)
        self.undo_stack.push(command)

    def show_context_menu(self, position):
        menu = QtWidgets.QMenu(self)
        col = self.table_widget.horizontalHeader().logicalIndexAt(position)
        row = self.table_widget.verticalHeader().logicalIndexAt(position)
        add_right = menu.addAction("Add a Column to the Right")
        add_right.triggered.connect(lambda: self.table_widget.insertColumn(col + 1))
        add_left = menu.addAction("Add a Column to the Left")
        add_left.triggered.connect(lambda: self.table_widget.insertColumn(col))
        add_below = menu.addAction("Add a Row below")
        add_below.triggered.connect(lambda: self.table_widget.insertRow(row + 1))
        add_above = menu.addAction("Add a Row above")
        add_above.triggered.connect(lambda: self.table_widget.insertRow(row))
        delete_row = menu.addAction("Delete this Row")
        delete_row.triggered.connect(lambda: self.table_widget.removeRow(row))
        delete_column = menu.addAction("Delete this Column")
        delete_column.triggered.connect(lambda: self.table_widget.removeColumn(col))
        menu.exec(self.table_widget.viewport().mapToGlobal(position))

    def show_column_header_context_menu(self, position):
        col = self.table_widget.horizontalHeader().logicalIndexAt(position)
        menu = QtWidgets.QMenu(self)
        delete_action = menu.addAction("Delete Column")
        add_column_left = menu.addAction("Add Column to the Left")
        add_column_right = menu.addAction("Add Column to the Right")
        delete_action.triggered.connect(lambda: self.table_widget.removeColumn(col))
        add_column_left.triggered.connect(lambda: self.table_widget.insertColumn(col))
        add_column_right.triggered.connect(lambda: self.table_widget.insertColumn(col + 1))
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

    def on_row_header_clicked(self, row):
        print(f"Left clicked row {row}")


def create_window():
    app = QtWidgets.QApplication(sys.argv)
    window = CSVEditorWindow()
    window.show()
    app.exec()


create_window()