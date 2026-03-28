import sys
import file_reader
import pandas as pd
import PyQt6.QtWidgets as QtWidgets
import PyQt6.QtGui as QtGui


class CSVEditorWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CSV Editor")
        self.setGeometry(100, 100, 800, 600)
        self.current_file_path = None

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
        self.save_button.clicked.connect(self.save_file)
        self.toolbar_layout.addWidget(self.save_button)

        self.save_as_button = QtWidgets.QPushButton("Save As")
        self.save_as_button.clicked.connect(self.save_file_as)
        self.toolbar_layout.addWidget(self.save_as_button)

        self.file_path_label = QtWidgets.QLabel("No file selected")
        self.toolbar_layout.addWidget(self.file_path_label)

        self.table_widget = QtWidgets.QTableWidget()
        self.vertical_layout.addWidget(self.table_widget)

        # Ctrl+S shortcut
        save_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self.save_file)

        # Ctrl+Shift+S shortcut
        save_as_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+S"), self)
        save_as_shortcut.activated.connect(self.save_file_as)

    def open_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open File", "", "CSV Files (*.csv)"
        )
        if file_path:
            self.current_file_path = file_path
            self.file_path_label.setText(file_path)
            data = file_reader.get_data(file_path)
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
        file_reader.write_data(self.get_table_data(), self.current_file_path)

    def save_file_as(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save As", "", "CSV Files (*.csv)"
        )
        if file_path:
            self.current_file_path = file_path
            self.file_path_label.setText(file_path)
            file_reader.write_data(self.get_table_data(), file_path)


def create_window():
    app = QtWidgets.QApplication(sys.argv)
    window = CSVEditorWindow()
    window.show()
    app.exec()


create_window()