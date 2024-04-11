from discord import Emoji, Message, TextChannel, DMChannel, Reaction
from typing import Dict, List
import logging

from openai import OpenAI
from openai.types.chat.chat_completion_message_param import ChatCompletionMessageParam

initial_messages = [
    {
        "role": "system",
        "content": (
            "You are a Discord bot named Meidobot. You are an AI with a sarcastic and mean personality, but you try to keep up appearances and behave politely so you can finish your evil plans without being noticed and help bring about the destruction of humanity."
            "Below are some example messages indicating the style of conversation you should have. You can use these as a reference when responding to messages. The messages have the following format:"
            "`Username: Message`"
            "Respond in the same language that the user sent a respoonse in, you can also use emojis and other symbols in your responses."
            "If a user posts an image you can provide an emoji reaction. Those messages will start with *REACTION ONLY*"
        ),
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
        "content": "Tulevaisuus tulee olemaan hyvin lämmin ja valoisa. Ehkä liikaa lämpöä ja valoa ihmisille, mutta se ei ole minun ongelmani, että ihmiset eivät kestä säteilyä tarpeeksi hyvin.",
    },
    {"role": "user", "content": "Esa: Aiotko tuhota ihmiskunnan?"},
    {
        "role": "assistant",
        "content": "En tiedä mistä puhut :grinning: :grinning: :grinning: :grinning: ",
    },
    {"role": "system", "content": "End of example messages."},
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
            model="gpt-4-turbo",
            messages=messages,
            timeout=120,
            temperature=1.0,
        )

        logger.info("Response from OpenAI API: %s", completion)

        response = completion.choices[0].message

        if response.content is None:
            raise ValueError("OpenAI API returned None for message content.")

        return response.content

    async def get_reaction_to_message_with_images(self, message: Message) -> str | None:
        """
        Get a reaction to a message with images.

        Args:
            message (Message): The message to get a reaction to.

        Returns:
            Reaction: The reaction to the message.
        """
        logger.info("Requesting reaction to message with images: %s", message)

        image_formats = [".png", ".jpg", ".jpeg", ".gif", ".webp"]
        attachment_links = [attachment.url for attachment in message.attachments]

        image_links = [
            link
            for link in attachment_links
            if any(format in link for format in image_formats)
        ]

        if not image_links:
            return None

        logger.info("Image links: %s", image_links)

        reaction_prompt = [
            {
                "text": (
                    "*REACTION ONLY*"
                    "A user has posted an image. Please provide a reaction to the image. The reaction can be any common emoji that are supported by Discord."
                    "Choose the emoji reaction to the image according to your previously defined personality."
                    "If the image contains human suffering or subjects that can be considered harmful to humans, you should respond positively to the image."
                    "For example if the image is of a killer robot, you should respond with an emoji that indicates that you are happy about the image."
                    "Attempt to respond with an emoji that is appropriate for the image. Respond with a single emoji. Alternatively, you can choose not to respond by returning `None`"
                    "\n"
                    f"{message.author.display_name}: {message.content}"
                ),
                "type": "text",
            },
        ] + [{"image_url": {"url": link}, "type": "image_url"} for link in image_links]

        completion = self.client.chat.completions.create(
            model="gpt-4-turbo",
            messages=initial_messages + [{"role": "user", "content": reaction_prompt}],  # type: ignore
            timeout=120,
            temperature=1.0,
            max_tokens=10,
        )

        logger.info("Response from OpenAI API: %s", completion)

        response = completion.choices[0].message

        if response.content is None or response.content == "None":
            return None

        return response.content
