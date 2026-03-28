import PyQt6
import file_reader

class CSVEditorWindow(PyQt6.QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CSV Editor")
        self.setGeometry(100, 100, 800, 600)

        self.central_widget = PyQt6.QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)

        self.horizontal_layout = PyQt6.QtWidgets.QHBoxLayout()
        self.central_widget.setLayout(self.horizontal_layout)

        self.open_file_button = PyQt6.QtWidgets.QPushButton("Open File")
        self.open_file_button.clicked.connect(self.open_file)
        self.horizontal_layout.addWidget(self.open_file_button)

        self.file_path_label = PyQt6.QtWidgets.QLabel("")
        self.horizontal_layout.addWidget(self.file_path_label)

    def open_file(self):
        file_path, _ = PyQt6.QtWidgets.QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv)")
        if file_path:
            self.file_path_label.setText(file_path)
            data = file_reader.get_data(file_path)
            self.table_widget = PyQt6.QtWidgets.QTableWidget(data.shape[0], data.shape[1])
            self.table_widget.setHorizontalHeaderLabels(list(data.columns))
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    self.table_widget.setItem(i, j, PyQt6.QtWidgets.QTableWidgetItem(str(data.iloc[i, j])))
            self.horizontal_layout.addWidget(self.table_widget)

def create_window():
    window = CSVEditorWindow()
    window.show()
    return window
