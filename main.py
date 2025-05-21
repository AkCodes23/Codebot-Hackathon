import os
import logging
import asyncio
from utils import record_audio
from config import RECORD_SECONDS, LANGUAGE
from voice.manager import VoiceManager
from llm_module.manager import LLMManager
from logger import logger
from memory_module.manager import MemoryManager
from rag_module.manager import RAGManager
from error_module.handler import ErrorHandler
from feedback_module.manager import FeedbackManager

def format_response(response):
    """Format the response from the LLM for clarity."""
    if isinstance(response, tuple):
        response = response[0]
    if len(response) > 200:
        sentences = [s.strip() for s in response.split('.') if s.strip()]
        summary = '. '.join(sentences[:2]) + '.'
        return summary
    return response

async def main():
    logger.info("Starting KisaanVaani Voice-to-Voice LLM Assistant...")
    print("--- KisaanVaani Voice-to-Voice LLM Assistant ---")
    memory_manager = MemoryManager()
    rag_manager = RAGManager()
    voice_manager = VoiceManager(LANGUAGE)
    llm_manager = LLMManager(memory_manager=memory_manager, rag_manager=rag_manager)
    error_handler = ErrorHandler()
    feedback_manager = FeedbackManager()
    try:
        while True:
            print("\nPress Enter to start recording your question (or type 'exit' to quit):")
            cmd = input().strip().lower()
            if cmd == 'exit':
                logger.info("User exited the assistant.")
                break
            try:
                user_text = voice_manager.record_and_transcribe(RECORD_SECONDS)
                if not user_text:
                    print("Could not understand audio. Please try again.")
                    logger.warning("ASR could not understand audio input.")
                    continue
                logger.info(f"User said: {user_text}")
                response = llm_manager.get_response(user_text)
                formatted_response = format_response(response)
                logger.info(f"LLM response: {formatted_response}")
                voice_manager.speak(formatted_response)
                feedback_manager.collect_feedback(user_text, formatted_response)
            except Exception as e:
                error_handler.handle(e, context="conversation loop")
    except KeyboardInterrupt:
        logger.info("Assistant interrupted by user.")
        print("\nShutting down KisaanVaani...")
    except Exception as e:
        error_handler.handle(e, context="main loop")
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
