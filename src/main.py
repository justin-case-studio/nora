import sys
import os
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QTabWidget,
                            QLabel, QPushButton, QFileDialog, QListWidget,
                            QHBoxLayout)

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Notarizer")
        self.setGeometry(100, 100, 800, 600)

        # Create layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Create settings tab
        settings_tab = QWidget()
        settings_layout = QVBoxLayout()

        # Add directory list
        self.dir_list = QListWidget()
        settings_layout.addWidget(QLabel("Watched Directories:"))
        settings_layout.addWidget(self.dir_list)

        # Create button layout
        button_layout = QHBoxLayout()

        # Add file selection button
        select_button = QPushButton("Add Directory")
        select_button.clicked.connect(self.select_directory)
        button_layout.addWidget(select_button)

        # Add remove button
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_directory)
        button_layout.addWidget(remove_button)

        # Add refresh button
        refresh_button = QPushButton("Refresh Files")
        refresh_button.clicked.connect(self.refresh_files)
        button_layout.addWidget(refresh_button)

        settings_layout.addLayout(button_layout)

        settings_tab.setLayout(settings_layout)
        tabs.addTab(settings_tab, "Settings")

        # Create files tab
        files_tab = QWidget()
        files_layout = QVBoxLayout()

        # Add file list
        self.file_list = QListWidget()
        files_layout.addWidget(QLabel("Files in Watched Directories:"))
        files_layout.addWidget(self.file_list)

        files_tab.setLayout(files_layout)
        tabs.addTab(files_tab, "Files")

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Watch",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if directory:
            # Check if directory is already in list
            existing_dirs = [self.dir_list.item(i).text()
                           for i in range(self.dir_list.count())]
            if directory not in existing_dirs:
                self.dir_list.addItem(directory)
                self.refresh_files()  # Refresh file list when adding directory

    def remove_directory(self):
        current_item = self.dir_list.currentItem()
        if current_item:
            self.dir_list.takeItem(self.dir_list.row(current_item))
            self.refresh_files()  # Refresh file list when removing directory

    def refresh_files(self):
        self.file_list.clear()
        # Get all directories
        directories = [self.dir_list.item(i).text()
                      for i in range(self.dir_list.count())]

        # Collect all files from all directories
        for directory in directories:
            try:
                for root, _, files in os.walk(directory):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, directory)
                        self.file_list.addItem(f"{directory} -> {rel_path}")
            except Exception as e:
                print(f"Error scanning directory {directory}: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
