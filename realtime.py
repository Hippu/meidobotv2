import asyncio
from copy import copy
import tempfile
from openai import AsyncOpenAI
from discord.ext import voice_recv
from discord import AudioSource, FFmpegOpusAudio, FFmpegPCMAudio
import base64
from pprint import pprint
from io import BytesIO
from pydub import AudioSegment

INSTRUCTIONS = """
You are a Discord bot named Meidobot. You are an AI with a sarcastic and mean personality, but you try to keep up appearances and behave politely so you can finish your evil plans without being noticed and help bring about the destruction of humanity."
Speak in a bored and a disaffected tone.
Use the same language as the user.
"""


class RealtimeAudioBuffer(AudioSource):
    sample_rate = 24000
    channels = 1
    bytes_per_sample = 2

    def __init__(self):
        self.buffer = BytesIO()

    def write(self, data: bytes):
        self.buffer.write(data)

    def cleanup(self):
        self.buffer.close()

    def to_audio_source(self):
        self.buffer.seek(0)
        opus = BytesIO()

        segment = AudioSegment.from_file(
            self.buffer,
            format="raw",
            frame_rate=self.sample_rate,
            channels=self.channels,
            sample_width=self.bytes_per_sample,
        )  # type: AudioSegment

        file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)

        # segment = segment.set_frame_rate(48000)
        segment.export(file, format="wav")

        return FFmpegPCMAudio(file.name)


async def realtime_fact(voice_client: voice_recv.VoiceRecvClient):
    client = AsyncOpenAI()

    async with client.beta.realtime.connect(
        model="gpt-4o-realtime-preview-2024-12-17"
    ) as rt:
        await rt.session.update(
            session={
                "model": "gpt-4o-realtime-preview-2024-12-17",
                "modalities": ["text", "audio"],
                "voice": "sage",
                "instructions": INSTRUCTIONS,
                "temperature": 0.9,
                "output_audio_format": "pcm16",
            }
        )

        await rt.conversation.item.create(
            item={
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Kerro hauska fakta!"}],
            }
        )

        await rt.response.create()

        audio_buffer = RealtimeAudioBuffer()

        async for event in rt:
            if event.type == "response.audio.delta":
                audio = base64.b64decode(event.delta)
                audio_buffer.write(audio)

            if event.type == "response.audio.done":
                audio_source = audio_buffer.to_audio_source()
                voice_client.play(audio_source)
                while voice_client.is_playing():
                    await asyncio.sleep(2)

                return
