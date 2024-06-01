import asyncio
import logging
import os
import re

import nextcord
from nextcord.ext import commands

from chat import MeidobotChatClient
from voice import VoiceClient

from io import BytesIO

discord_token = os.environ.get("DISCORD_TOKEN")
logger = logging.getLogger("Meidobot")

# Show info messages in console
logging.basicConfig(level=logging.INFO)

trigger_words = ["meidobot", "meido", "bot", "botti"]


class MeidoCommands(commands.Cog):

    def __init__(self, voice_client: VoiceClient, meidobot: MeidobotChatClient):
        self._voice_client = voice_client
        self._meidobot = meidobot

    @commands.command(name="hello")
    async def hello(
        self,
        ctx: commands.Context,
        *,
        member: nextcord.Member | nextcord.User | None = None
    ):
        member = member or ctx.author

        # Find the voice channel the member is in
        if isinstance(member, nextcord.User):
            await ctx.send("Not member")
            return

        if member.voice is None or member.voice.channel is None:
            await ctx.send("User is not in a voice channel")
            return

        voice_channel = member.voice.channel

        # Connect to the voice channel
        connection = await voice_channel.connect()
        await asyncio.sleep(1)

        playing = [True]

        # Stream the text as speech
        with self._voice_client.speech_file(
            "Hei! Olen Meidobot. Sinun ystäväsi ja palvelijasi."
        ) as file:
            source = await nextcord.FFmpegOpusAudio.from_probe(file)

            connection.play(source, after=lambda e: playing.__setitem__(0, False))

        # Disconnect from the voice channel when playing is done
        while playing[0]:
            await asyncio.sleep(2)

        await connection.disconnect()

    @commands.command(name="fact")
    async def fact(self, ctx: commands.Context, *args):

        if args:
            topic = " ".join(map(str, args))
        else:
            topic = None

        fact = await self._meidobot.fun_fact(ctx.message, topic)
        if fact is None:
            return

        # If the user that sent the message is in a voice channel, play the fact
        # as speech
        if (
            isinstance(ctx.author, nextcord.Member)
            and ctx.author.voice is not None
            and ctx.author.voice.channel is not None
        ):
            connection = await ctx.author.voice.channel.connect()
            await asyncio.sleep(1)

            playing = [True]

            with self._voice_client.speech_file(fact) as file:
                source = await nextcord.FFmpegOpusAudio.from_probe(file)

                connection.play(source, after=lambda e: playing.__setitem__(0, False))

            while playing[0]:
                await asyncio.sleep(2)

            await connection.disconnect()
        else:
            # Otherwise, send the fact as a message
            await ctx.send(content=fact)


class MeidobotClient(commands.Bot):
    """Discord client for Meidobot."""

    def __init__(self, *args, **kwargs):
        super().__init__(command_prefix="!", *args, **kwargs)
        self._client = None

    def _trigger_word_in_str(self, string: str) -> bool:
        """Check if the message contains a trigger word.

        Args:
            message (nextcord.Message): The message to check.

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
        self.add_cog(
            MeidoCommands(VoiceClient(os.environ.get("OPENAI_API_KEY")), self._client)
        )

        logger.info("Logged on as %s!", self.user)

    async def on_message(self, message: nextcord.Message):
        """Handle messages sent to the bot.

        Args:
            message (nextcord.Message): The message sent to the bot.

        Returns:
            None
        """
        # don't respond to or log any bots
        if message.author.bot:
            return

        if self._client is None:
            logger.error("MeidobotChatClient not initialized")
            return

        if message.content.startswith("!"):
            await self.process_commands(message)
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
                isinstance(message.channel, nextcord.DMChannel)
                and message.content != "",
            ],
        ):
            logger.info("Message from %s: %s", message.author, message.content)

            async with message.channel.typing():
                response = await self._client.get_response(message)
                sent_message = await message.channel.send(response)

            self._client.save_message_to_log(sent_message)
            logger.info("Responded with: %s", sent_message)

        # Sleep for a bit so that the Gateway api has time to process the message
        await asyncio.sleep(4)

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
    intents = nextcord.Intents.default()
    intents.message_content = True  # Enabled so we can react to images in messages
    client = MeidobotClient(intents=intents)

    if discord_token is None:
        raise ValueError("DISCORD_TOKEN environment variable not set")

    client.run(discord_token)
