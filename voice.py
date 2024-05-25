from contextlib import contextmanager
from openai import OpenAI
from typing import Literal
import tempfile


class VoiceClient:
    model = "tts-1"
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = "nova"
    format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = "opus"

    def __init__(self, api_key):
        self.api_key = api_key
        self._client = OpenAI(api_key=api_key)

    def stream_speech(self, text: str):
        """
        Streams the given text as speech and yields the audio chunks.

        Args:
            text (str): The text to be streamed as speech.

        Yields:
            bytes: Audio chunks of the streamed speech.
        """
        stream = self._client.with_streaming_response.audio.speech.create(
            model=self.model,
            voice=self.voice,
            response_format=self.format,
            input=text,
        )

        with stream as s:
            for chunk in s.iter_bytes(2048):
                yield chunk

    @contextmanager
    def speech_file(self, text: str):
        try:
            file = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)

            with file as f:
                stream = self._client.with_streaming_response.audio.speech.create(
                    model=self.model,
                    voice=self.voice,
                    response_format=self.format,
                    input=text,
                    speed=0.9,
                )

                with stream as s:
                    for chunk in s.iter_bytes(2048):
                        f.write(chunk)
                    file.seek(0)

            yield f.name
        finally:
            file.delete = True
            file.close()
