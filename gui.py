import subprocess
import sys
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget, QPushButton, QTextEdit, QCheckBox, QScrollArea

class BackupThread(QThread):
    status_update = Signal(str)
    finished = Signal()

    def __init__(self, partitions_to_backup, is_device_connected, has_root_access):
        super().__init__()
        self.partitions_to_backup = partitions_to_backup
        self.is_device_connected = is_device_connected
        self.has_root_access = has_root_access

    def run(self):
        if not self.is_device_connected():
            self.status_update.emit("Error: Device not connected. Please connect your device.")
            return
        if not self.has_root_access():
            self.status_update.emit("Error: Root access not granted. Please make sure your device is rooted.")
            return
        if not self.partitions_to_backup:
            self.status_update.emit("Error: No partitions selected for backup.")
            return
        self.status_update.emit("Backing up partitions...")
        if not subprocess.call("adb shell su -c 'mkdir /storage/emulated/0/backup'", shell=True):
            self.status_update.emit("Remote backup directory created successfully.")
        else:
            self.status_update.emit("Error: Unable to create remote backup directory. Probably already exists. Deleting and recreating...")
            subprocess.call("adb shell su -c 'rm -rf /storage/emulated/0/backup'", shell=True)
            if not subprocess.call("adb shell su -c 'mkdir /storage/emulated/0/backup'", shell=True):
                self.status_update.emit("Remote backup directory created successfully.")
            else:
                self.status_update.emit("Error: Unable to create remote backup directory.")
                return
        if not subprocess.call("mkdir backup", shell=True):
            self.status_update.emit("Local backup directory created successfully.")
        else:
            self.status_update.emit("Error: Unable to create local backup directory. Probably already exists. Deleting and recreating...")
            subprocess.call("rm -rf backup", shell=True)
            if not subprocess.call("mkdir backup", shell=True):
                self.status_update.emit("Local backup directory created successfully.")
            else:
                self.status_update.emit("Error: Unable to create local backup directory.")
                return
        count = 0
        for partition in self.partitions_to_backup:
            self.status_update.emit(f"Backing up {partition}... {count}/{len(self.partitions_to_backup)}")
            subprocess.call(f"adb shell su -c 'dd if=/dev/block/bootdevice/by-name/{partition} of=/storage/emulated/0/backup/{partition}.img'", shell=True)
            subprocess.call(f"adb pull /storage/emulated/0/backup/{partition}.img backup/", shell=True)
            subprocess.call(f"adb shell su -c 'rm /storage/emulated/0/backup/{partition}.img'", shell=True)
            self.status_update.emit(f"{partition} backed up successfully.")
            count += 1
        self.status_update.emit("Done! Partitions backed up successfully.")
        self.finished.emit()

class PartitionBackup(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Partition Backup")
        self.layout = QVBoxLayout()

        self.label = QLabel("Click the button below to backup partitions (except userdata)")
        self.layout.addWidget(self.label)

        self.get_partitions_button = QPushButton("Get Partitions")
        self.get_partitions_button.clicked.connect(self.get_partitions)
        self.layout.addWidget(self.get_partitions_button)

        self.backup_button = QPushButton("Backup Selected Partitions")
        self.backup_button.clicked.connect(self.start_backup)
        self.layout.addWidget(self.backup_button)

        self.backup_all_button = QPushButton("Backup All Partitions")
        self.backup_all_button.clicked.connect(self.backup_all_partitions)
        self.layout.addWidget(self.backup_all_button)

        self.clear_all_button = QPushButton("Clear All")
        self.clear_all_button.clicked.connect(lambda: [checkbox.setChecked(False) for checkbox in self.checkboxes])
        self.layout.addWidget(self.clear_all_button)

        self.clear_output_button = QPushButton("Clear Output")
        self.clear_output_button.clicked.connect(lambda: self.output.clear())
        self.layout.addWidget(self.clear_output_button)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.layout.addWidget(self.output)

        self.setLayout(self.layout)

        self.partitions = self.get_partitions()
        if self.partitions:
            self.checkbox_layout = QVBoxLayout()
            self.checkboxes = []
            for partition in self.partitions:
                checkbox = QCheckBox(partition)
                self.checkboxes.append(checkbox)
                self.checkbox_layout.addWidget(checkbox)

            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)

            container = QWidget()
            container.setLayout(self.checkbox_layout)

            scroll_area.setWidget(container)
            self.layout.addWidget(scroll_area)

        self.backup_thread = BackupThread([], self.is_device_connected, self.has_root_access)
        self.backup_thread.status_update.connect(self.update_status)
        self.backup_thread.finished.connect(self.backup_finished)

    def start_backup(self):
        partitions_to_backup = [checkbox.text() for checkbox in self.checkboxes if checkbox.isChecked()]
        self.backup_thread.partitions_to_backup = partitions_to_backup
        self.backup_thread.start()

    def backup_all_partitions(self):
        self.backup_thread.partitions_to_backup = self.partitions
        self.backup_thread.start()

    def backup_finished(self):
        self.label.setText("Done! Partitions backed up successfully.")

    def update_status(self, message):
        self.label.setText(message)
        self.output.append(message)

    def is_device_connected(self):
        try:
            out = subprocess.check_output("adb devices", shell=True)
            if "no devices/emulators found" in out.decode('utf-8'):
                return False
            return True
        except subprocess.CalledProcessError:
            return False

    def has_root_access(self):
        try:
            subprocess.check_output("adb shell su -c 'echo test'", shell=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def get_partitions(self):
        try:
            partitions = subprocess.check_output("adb shell su -c 'ls /dev/block/bootdevice/by-name/'", shell=True).split()
            partitions = [partition.decode('utf-8') for partition in partitions]
            slot = subprocess.check_output("adb shell su -c 'getprop ro.boot.slot_suffix'", shell=True).decode('utf-8').strip()
            if "_a" in slot:
                partitions = [partition for partition in partitions if "_b" not in partition]
            elif "_b" in slot:
                partitions = [partition for partition in partitions if "_a" not in partition]
            # Remove userdata partition
            partitions = [partition for partition in partitions if "userdata" not in partition]
            return partitions
        except subprocess.CalledProcessError:
            return None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PartitionBackup()
    window.show()
    sys.exit(app.exec())
