import unittest
from unittest.mock import Mock, patch

import obby


class DesktopAudioTests(unittest.TestCase):
    def test_windows_sound_is_dispatched_asynchronously(self):
        sound = Mock()

        with patch.object(obby, "winsound", sound):
            with patch("obby.threading.Thread") as thread:
                obby.play_sound(Mock(), "shot")

        thread.assert_called_once_with(
            target=sound.Beep,
            args=(1000, 70),
            daemon=True,
        )
        thread.return_value.start.assert_called_once_with()

    def test_non_windows_sound_uses_tkinter_bell(self):
        root = Mock()

        with patch.object(obby, "winsound", None):
            obby.play_sound(root, "damage")

        root.bell.assert_called_once_with()

    def test_unknown_sound_name_is_reported(self):
        with self.assertRaises(KeyError):
            obby.play_sound(Mock(), "not-a-sound")


if __name__ == "__main__":
    unittest.main()
