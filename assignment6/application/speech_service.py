"""Offline simulated speech-to-text adapter: input already is a transcript."""


class SpeechService:
    simulated = True

    def transcribe(self, audio_input):
        if not isinstance(audio_input, str) or not audio_input.strip() or len(audio_input) > 2000:
            raise ValueError("simulated voice input must be a nonempty transcript (maximum 2000 characters)")
        return audio_input.strip()
