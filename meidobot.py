import re
import discord
import os
import logging

from chat import MeidobotChatClient

discord_token = os.environ.get("DISCORD_TOKEN")
logger = logging.getLogger("Meidobot")

# Show info messages in console
logging.basicConfig(level=logging.INFO)

chat_client = MeidobotChatClient(os.environ.get("OPENAI_SECRET_KEY"))
trigger_words = ["meidobot", "meido", "bot", "botti"]


class MeidobotClient(discord.Client):
    async def on_ready(self):
        logger.info("Logged on as {0}!".format(self.user))

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

        logger.info("Message from {0.author}: {0.content}".format(message))

        # check if the message mentions the bot or contains a trigger word
        if self.user in message.mentions or any(
            word in message.content.lower() for word in trigger_words
        ):
            # remove the mention from the message
            cleaned_message = re.sub(r"<[^>]*>", "", message.content)

            response = chat_client.get_response_to_message(
                f"{message.author.name}#{message.author.discriminator}: {cleaned_message}"
            )
            await message.channel.send(response)
            logger.info(f"Responded with: {response}")


if __name__ == "__main__":
    client = MeidobotClient(intents=discord.Intents.default())
    client.run(discord_token)
