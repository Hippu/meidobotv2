import asyncio
import logging
import os
import re

import discord

from chat import MeidobotChatClient

discord_token = os.environ.get("DISCORD_TOKEN")
logger = logging.getLogger("Meidobot")

# Show info messages in console
logging.basicConfig(level=logging.INFO)

trigger_words = ["meidobot", "meido", "bot", "botti"]


class MeidobotClient(discord.Client):
    """Discord client for Meidobot."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = None

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
        if self.user is None:
            raise ValueError("User not found")

        self._client = MeidobotChatClient(
            os.environ.get("OPENAI_API_KEY"), self.user.id
        )

        logger.info("Logged on as %s!", self.user)

    async def on_message(self, message: discord.Message):
        """Handle messages sent to the bot.

        Args:
            message (discord.Message): The message sent to the bot.

        Returns:
            None
        """
        # don't respond to or log any bots
        if message.author.bot:
            return

        if self._client is None:
            logger.error("MeidobotChatClient not initialized")
            return

        logger.info("Message %s", message)
        self._client.save_message_to_log(message)

        # check if the message mentions the bot, contains a trigger word or
        # is a reply to a message sent by the bot
        if any(
            [
                self.user in message.mentions,
                message.reference
                and message.reference.resolved.author == self.user,  # type: ignore
                self._trigger_word_in_str(message.content),
                isinstance(message.channel, discord.DMChannel)
                and message.content != "",
            ],
        ):
            logger.info("Message from %s: %s", message.author, message.content)

            async with message.channel.typing():
                response = await self._client.get_response(message)
                sent_message = await message.channel.send(response)

            self._client.save_message_to_log(sent_message)
            logger.info("Responded with: %s", sent_message)

        await asyncio.sleep(1)

        # React with an emoji if the message contains an image
        if message.attachments:
            response = await self._client.get_reaction_to_message_with_images(message)
            logger.info("Reaction to message with images: %s", response)
            if response is not None:
                await message.add_reaction(response)
        # React with an emoji if the message contains embeds
        if message.embeds:
            response = await self._client.get_reaction_to_message_with_embeds(message)
            logger.info("Reaction to message with embeds: %s", response)
            if response is not None:
                await message.add_reaction(response)


if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.message_content = True  # Enabled so we can react to images in messages
    client = MeidobotClient(intents=intents)

    if discord_token is None:
        raise ValueError("DISCORD_TOKEN environment variable not set")

    client.run(discord_token)
