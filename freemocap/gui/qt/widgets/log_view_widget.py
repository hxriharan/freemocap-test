import logging
import multiprocessing
import threading
from logging.handlers import QueueHandler
from queue import Queue

from PySide6 import QtCore, QtGui
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from freemocap.gui.qt.utilities.colors import get_next_color, rgb_color_generator
from freemocap.system.logging.configure_logging import log_view_logging_format_string
from freemocap.system.paths_and_filenames.file_and_folder_names import LOG_VIEW_PROGRESS_BAR_STRING

logger = logging.getLogger(__name__)

log_view_logging_formatter = logging.Formatter(fmt=log_view_logging_format_string, datefmt="%Y-%m-%dT%H:%M:%S")

level_colors = {
    "DEBUG": (169, 169, 169),  # dimmed gray
    "INFO": (255, 255, 255),  # white
    "WARNING": (255, 165, 0),  # orange
    "ERROR": (255, 0, 0),  # red
}

process_colors = {}
thread_colors = {}
code_path_colors = {}


class LoggingQueueListener(QThread):
    log_message_signal = QtCore.Signal(object)

    def __init__(self, logging_queue: Queue, exit_event: threading.Event, parent=None):
        super().__init__(parent)
        self._logging_queue = logging_queue
        self._exit_event = exit_event
        self._parent = parent

    def run(self):
        logger.info("Starting LoggingQueueListener thread")
        try:
            while not self._exit_event.is_set():
                if self._logging_queue.empty():
                    if self._parent._keep_logging:
                        QtCore.QMetaObject.invokeMethod(self._parent, "log_progress", QtCore.Qt.QueuedConnection)
                    continue

                record = self._logging_queue.get(block=True)

                if record is None:
                    break

                self.log_message_signal.emit(record)

        except Exception as e:
            logger.exception(e)
            self.close()

    def close(self):
        logger.info("Closing LoggingQueueListener thread")
        self._exit_event.set()


class LogViewWidget(QPlainTextEdit):
    # adapted from - https://stackoverflow.com/a/63853259/14662833
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setReadOnly(True)

        self._logging_queue = multiprocessing.Queue(-1)
        self._queue_handler = QueueHandler(self._logging_queue)
        self._queue_handler.setFormatter(log_view_logging_formatter)
        self._queue_handler.setLevel(logging.INFO)
        logging.getLogger("").handlers.append(self._queue_handler)

        self._exit_event = threading.Event()
        self._logging_queue_listener = LoggingQueueListener(
            logging_queue=self._logging_queue, exit_event=self._exit_event, parent=self
        )
        self._keep_logging = False
        self._logging_queue_listener.log_message_signal.connect(self.add_log)
        self.timestamp_color_generator = rgb_color_generator((50, 255, 255), (255, 50, 255), phase_increment=0.2)
        self.log_message_color_generator = rgb_color_generator((128, 255, 100), (100, 255, 255), phase_increment=0.7)
        self.show_colors = True
        self.show_code_path_info = True
        self._logging_queue_listener.start()

    def add_log(self, record: logging.LogRecord):
        level = record.levelname.ljust(7)  # 7 characters long, right padded with spaces
        timestamp = f"[{record.asctime}.{record.msecs:04.0f}]".ljust(24)  # 24 characters long
        process_id_str = f"{record.process}".rjust(6)  # 5 characters long, left padded with spaces
        thread_id_str = f"{record.thread}".rjust(6)  # 5 characters long, left padded with spaces
        full_message = record.getMessage().split(":::::")[-1].strip()
        message_content = full_message.split("||||")[-1].strip()
        code_path_str = full_message.split("||||")[0].strip()
        package, method, line = code_path_str.split(":")

        if message_content == LOG_VIEW_PROGRESS_BAR_STRING + ".":
            self._keep_logging = True
            return
        else:
            self._keep_logging = False

        # Set color for the level
        r, g, b = level_colors.get(level.strip(), (255, 255, 255))
        color_level = f"<span style='color:rgb({r},{g},{b});'>{level}</span>"

        # Set color for the timestamp using the timestamp_color_generator
        r, g, b = next(self.timestamp_color_generator)
        color_timestamp = f"<span style='color:rgb({r},{g},{b});'>{timestamp}</span>"

        # Get color for process and thread ID
        if process_id_str not in process_colors:
            process_colors[process_id_str] = get_next_color()
        r, g, b = process_colors[process_id_str]
        process_str = f"ProcessID:{process_id_str}"

        color_process_id = f"<span style='color:rgb({r},{g},{b});'>[{process_str},</span>"

        thread_process_id_str = f"{thread_id_str}:{process_id_str}"
        if thread_process_id_str not in thread_colors:
            thread_colors[thread_process_id_str] = get_next_color()
        r, g, b = thread_colors[thread_process_id_str]
        thread_str = f"ThreadID:{thread_id_str}"
        color_thread_id = f"<span style='color:rgb({r},{g},{b});'>{thread_str}]</span>"

        color_process_id_thread_id = f"{color_process_id} {color_thread_id}"
        color_process_id_thread_id.ljust(25)

        # Choose a color for the message using the log_message_color_generator

        if package + method not in code_path_colors:
            code_path_colors[package + method] = get_next_color()

        r, g, b = code_path_colors[package + method]
        color_code_path = f"<span style='color:rgb({r},{g},{b});'>{code_path_str}</span>"

        r, g, b = (255, 255, 255)
        color_message = f"<span style='color:rgb({r},{g},{b});'>{message_content}</span>"

        # Combine colored parts
        colored_log_entry = (
            f"{color_timestamp}[{color_level}] {color_process_id_thread_id} {color_code_path} ::: {color_message}"
        )
        self.appendHtml(colored_log_entry)

    @QtCore.Slot()
    def log_progress(self, bar_length: int = 100, cycles_per_update: int = 2500) -> None:
        if not hasattr(self, "_progress_counter"):
            self._progress_counter = 0

        progress_marker = "▁▂▃▄▅▆▇▆▅▄▃▂▁"
        help_text = "Processing:"

        if self.toPlainText().split("\n")[-1].strip().split(" ")[0] != help_text:
            self.appendPlainText(help_text + " " + progress_marker * bar_length)
            return

        cycles_until_repeat = len(progress_marker) * cycles_per_update
        for i in range(len(progress_marker)):
            if self._progress_counter % cycles_until_repeat == cycles_per_update * i:
                self._replace_last_line(
                    help_text
                    + " "
                    + (progress_marker[i:] + progress_marker[:i]) * int(bar_length / len(progress_marker))
                )

        self._progress_counter += 1

    def _replace_last_line(
            self, text: str
    ) -> None:  # from https://stackoverflow.com/questions/53381975/display-terminal-output-with-tqdm-in-qplaintextedit
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.select(QtGui.QTextCursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.insertBlock()
        self.setTextCursor(cursor)
        self.insertPlainText(text)

    def closeEvent(self, event):
        logger.info("Closing LogViewWidget")
        self._exit_event.set()
        self._logging_queue_listener.close()
        logging.getLogger("").handlers.remove(self._queue_handler)
        super().closeEvent(event)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    log_view_widget = LogViewWidget()
    log_view_widget.show()
    sys.exit(app.exec())
