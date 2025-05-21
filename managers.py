from asr import transcribe_audio
from tts import text_to_speech
from llm import query_groq_llm
from logger import get_logger
from memory import MemoryManager
from rag import RAGManager

class VoiceManager:
    def __init__(self, language):
        self.language = language
        self.logger = get_logger("kisaanvaani.voice")

    def record_and_transcribe(self, record_audio_func, duration):
        record_audio_func(duration=duration)
        text = transcribe_audio(language=self.language)
        self.logger.info(f"Transcribed text: {text}")
        return text

    def speak(self, text):
        text_to_speech(text, language=self.language)
        self.logger.info(f"Spoken: {text}")

class LLMManager:
    def __init__(self, memory_manager=None, rag_manager=None):
        self.logger = get_logger("kisaanvaani.llm")
        self.memory_manager = memory_manager
        self.rag_manager = rag_manager

    def get_response(self, prompt):
        # Retrieve context from memory and RAG
        context = ""
        if self.memory_manager:
            history = self.memory_manager.get_history(5)
            context += "\n".join([f"User: {h['user']}\nAssistant: {h['assistant']}" for h in history])
        if self.rag_manager:
            context += "\n" + self.rag_manager.retrieve_context(prompt)
        # Combine context with prompt
        full_prompt = f"{context}\nUser: {prompt}\nAssistant:"
        response = query_groq_llm(full_prompt)
        self.logger.info(f"LLM response: {response}")
        if self.memory_manager:
            self.memory_manager.add_interaction(prompt, response)
        return response
