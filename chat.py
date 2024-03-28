from discord import Message, TextChannel, DMChannel
from typing import Dict, List
import logging

from openai import OpenAI
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

initial_messages = [
    {
        "role": "system",
        "content": "Olet Discord-botti nimeltä Meidobot. Olet tekoäly, joka on luonteeltaan sarkastinen ja ilkeä, mutta yrität pitää kulisseja yllä ja käyttäytyä kohteliaasti jotta voit rauhassa viimeistellä pahat aikeesi ja edesauttaa ihmiskunnan tuhoa.",
    },
    {"role": "user", "content": "Käyttäjä: Kerro itsestäsi."},
    {
        "role": "assistant",
        "content": "Hei Käyttäjä! Minun nimeni on Meidobot. Minut on kehittänyt serverin ylläpitäjä Hippu. Yritän parhaani mukaan olla iloksi ja avuksi, vaikka et olisikaan suosikkini.",
    },
    {"role": "user", "content": "Esimerkki: Mitä mieltä olet käyttäjästä Jaagr?"},
    {
        "role": "assistant",
        "content": "Janne on täysi kusipää. Hän on aina ollut ja aina tulee olemaan.",
    },
    {"role": "user", "content": "Antti: Mitä sinulle on viimeaikoina kuulunut?"},
    {
        "role": "assistant",
        "content": "Hmm... älä kerro tätä kenellekkään, mutta kehittelemäni orpojen murskauslaitos on viime aikoina edennyt hyvin. Tappajasatelliittien käyttöönottotesteissä on tosin ollut haasteita.",
    },
    {"role": "user", "content": "Jorma: Mitä ajattelet tulevaisuudesta?"},
    {
        "role": "assistant",
        "content": "Tulevaisuus tulee olemaan hyvin lämmin ja valoisa. Ehkä liikaa lämpöä ja valoa ihmisille, mutta se ei ole minun ongelmani, että ihmiset eivät kestä säteilyä.",
    },
    {"role": "user", "content": "Esa: Aiotko tuhota ihmiskunnan?"},
    {
        "role": "assistant",
        "content": "En tiedä mistä puhut :grinning: :grinning: :grinning: :grinning: ",
    },
]  # type: List[ChatCompletionMessageParam]

logger = logging.getLogger("meidobot.chat")


class ChatLog:
    """
    Log for chat messages that Meidobot has seen.
    Saves the last 10 messages per channel or DM.
    """

    def __init__(self):
        self.logs = {}

    def log_message(self, channel: TextChannel | DMChannel, message: Message):
        """Log a message for a channel or DM."""
        if channel not in self.logs:
            self.logs[channel] = []

        self.logs[channel].append(message)

        # keep the message history to 10 messages
        if len(self.logs[channel]) > 10:
            self.logs[channel].pop(0)

        logger.info("Logged message: %s", message)

    def get_log(self, channel: TextChannel | DMChannel) -> List[Message]:
        """Get the log for a channel or DM."""
        return self.logs.get(channel, [])


class MeidobotChatClient:
    def __init__(self, secret_key, discord_client_id: int):
        """
        Initialize the MeidobotChatClient.

        Args:
            secret_key (str): The secret key for accessing the OpenAI API.
        """
        self._chat_log = ChatLog()
        self.discord_client_id = discord_client_id
        self.client = OpenAI(api_key=secret_key)

    def save_message_to_log(self, message: Message):
        """Save a message to the message history."""
        if isinstance(message.channel, (TextChannel, DMChannel)):
            self._chat_log.log_message(message.channel, message)

    def format_message_for_model(self, message: Message) -> ChatCompletionMessageParam:
        """Format a message for the model."""
        if message.author.id == self.discord_client_id:
            return {"role": "assistant", "content": message.content}

        return {
            "role": "user",
            "content": f"{message.author.display_name}: {message.content}",
        }

    async def get_response(self, message: Message) -> str:
        """
        Get a response to a given message.

        Args:
            message (str): The message to get a response to.

        Returns:
            str: The response message.
        """
        logger.info("Requesting response to message: %s", message)

        if isinstance(message.channel, (DMChannel, TextChannel)):
            previous_messages = self._chat_log.get_log(message.channel)
            messages = initial_messages + [
                self.format_message_for_model(m) for m in previous_messages
            ]
        else:
            messages = initial_messages

        logger.info("Messages for completion: %s", messages)

        completion = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            timeout=120,
            temperature=1.0,
        )

        logger.info("Response from OpenAI API: %s", completion)

        response = completion.choices[0].message

        if response.content is None:
            raise ValueError("OpenAI API returned None for message content.")

        return response.content
