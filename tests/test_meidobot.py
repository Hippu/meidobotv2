import unittest

import discord
from meidobot import MeidobotClient


class TestMeidoBot(unittest.TestCase):
    def setUp(self):
        self.meido = MeidobotClient(intents=discord.Intents.none())

    def test_trigger_word_in_message(self):
        """Test that the trigger word is detected in a message."""
        test_sentences_and_results = [
            ("hello", False),
            ("En pidä boteista", True),
            ("Meidobot on kiva", True),
        ]

        for sentence, result in test_sentences_and_results:
            self.assertEqual(
                self.meido._trigger_word_in_str(sentence),
                result,
            )
