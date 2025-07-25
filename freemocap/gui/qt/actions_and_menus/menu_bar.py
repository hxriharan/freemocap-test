from PySide6.QtWidgets import QMainWindow, QMenuBar

from freemocap.gui.qt.actions_and_menus.actions import Actions
from freemocap.utilities.download_sample_data import DATASETS


class MenuBar(QMenuBar):
    def __init__(self, actions: Actions, parent: QMainWindow = None):
        super().__init__(parent=parent)

        self._add_actions_to_file_menu(actions)

    def _add_actions_to_file_menu(self, actions: Actions):
        """
        based mostly on: https://realpython.com/python-menus-toolbars/
        """

        # file menu
        file_menu = self.addMenu("&File")

        file_menu.addAction(actions.create_new_recording_action)
        file_menu.addAction(actions.load_most_recent_recording_action)
        file_menu.addAction(actions.load_existing_recording_action)
        file_menu.addAction(actions.import_videos_action)
        file_menu.addAction(actions.set_data_folder_action)
        file_menu.addAction(actions.reset_to_defaults_action)
        file_menu.addAction(actions.exit_action)

        # Actions Menu
        actions_menu = self.addMenu("&Controller")
        actions_menu.addAction(actions.kill_running_threads_and_processes_action)
        actions_menu.addAction(actions.reboot_gui_action)

        # Data Menu
        data_menu = self.addMenu("&Data")

        for key in DATASETS:
            action_attr = f"download_{key}_data_action"
            if hasattr(actions, action_attr):
                action = getattr(actions, action_attr)
                data_menu.addAction(action)

        #
        # # navigation menu
        # navigation_menu = QMenu("Na&vigation", parent=self)
        # self.addMenu(navigation_menu)
        #
        # navigation_menu.addAction(self._show_camera_control_panel_action)
        # navigation_menu.addAction(self._show_calibrate_capture_volume_panel_action)
        # navigation_menu.addAction(self._show_motion_capture_videos_panel_action)
        #
        # help menu
        help_menu = self.addMenu("&Help")
        help_menu.addAction(actions.show_release_notes_action)
        help_menu.addAction(actions.open_docs_action)
        help_menu.addAction(actions.freemocap_foundation_action)
        #
        # support menu
        support_menu = self.addMenu("&Support the Freemocap Project")

        support_menu.addAction(actions.donate_action)
        # support_menu.addAction(actions.send_usage_statistics_action)
        # support_menu.addAction(actions.user_survey_action)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QLabel

    app = QApplication(sys.argv)
    _main_window = QMainWindow()
    _main_window.setCentralWidget(QLabel("Henlo fren"))
    _menu_bar = MenuBar(parent=_main_window)
    # _menu_bar = QMenuBar(parent=_main_window)
    # _fake_menu = QMenu("&Fake Menu", parent=_menu_bar)
    # _menu_bar.addMenu(_fake_menu)
    # _fake_menu.addAction("Fake Action")
    _main_window.setMenuBar(_menu_bar)
    _main_window.show()
    sys.exit(app.exec())
