import logging
import os
import re

import discord

from chat import MeidobotChatClient

discord_token = os.environ.get("DISCORD_TOKEN")
logger = logging.getLogger("Meidobot")

# Show info messages in console
logging.basicConfig(level=logging.INFO)

chat_client = MeidobotChatClient(os.environ.get("OPENAI_API_KEY"))
trigger_words = ["meidobot", "meido", "bot", "botti"]


class MeidobotClient(discord.Client):
    def _trigger_word_in_str(self, string: str) -> bool:
        """Check if the message contains a trigger word.

        Args:
            message (discord.Message): The message to check.

        Returns:
            bool: True if the message contains a trigger word, False otherwise.
        """
        return any(word in string.lower() for word in trigger_words)

    async def on_ready(self):
        """Handle the bot being ready to receive messages."""
        logger.info(f"Logged on as {self.user}!")

    async def on_message(self, message: discord.Message):
        """Handle messages sent to the bot.

        Args:
            message (discord.Message): The message sent to the bot.

        Returns:
            None
        """
        # don't respond to any bots
        if message.author.bot:
            return

        # check if the message mentions the bot, contains a trigger word or
        # is a reply to a message sent by the bot
        if any(
            [
                self.user in message.mentions,
                message.reference
                and message.reference.resolved.author == self.user,  # type: ignore
                self._trigger_word_in_str(message.content),
            ]
        ):
            logger.info("Message from {0.author}: {0.content}".format(message))

            # remove the mention from the message
            cleaned_message = re.sub(r"<[^>]*>", "", message.content)

            response = chat_client.get_response_to_message(
                f"{message.author.name}#{message.author.discriminator}: {cleaned_message}"
            )
            await message.channel.send(response)
            logger.info(f"Responded with: {response}")


if __name__ == "__main__":
    client = MeidobotClient(intents=discord.Intents.default())

    if discord_token is None:
        raise ValueError("DISCORD_TOKEN environment variable not set")

    client.run(discord_token)
