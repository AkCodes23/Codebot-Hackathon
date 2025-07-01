import streamlit as st
import speech_recognition as sr
import os
from groq import Groq
import time
import pyttsx3
import threading
import datetime
import random
import json
import operator as op
import ast
import re
from enum import Enum, auto
import logging
import sys
from typing import Dict, Any, Optional, List, Tuple
import requests
import unicodedata
from collections import OrderedDict
import certifi


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('kisaanvaani.log')
    ]
)

# Create loggers for different components
logger = logging.getLogger('kisaanvaani')
voice_logger = logging.getLogger('kisaanvaani.voice')
tool_logger = logging.getLogger('kisaanvaani.tools')
agent_logger = logging.getLogger('kisaanvaani.agent')
context_logger = logging.getLogger('kisaanvaani.context')

# --- Constants and Configuration ---
# ENSURE THIS IS YOUR VALID, WORKING GROQ API KEY
GROQ_API_KEY = "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"
TAVILY_API_KEY = "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"

SUPPORTED_LANGUAGES = {
    "english": "en",
    "hindi": "hi",
    "spanish": "es",
    "french": "fr",
}
# Known error/fallback messages from LLM or STT for conditional logic
KNOWN_FALLBACK_RESPONSES = [
    "LLM client not initialized. Please check configuration.",
    "I didn't catch that. Could you please repeat your query?",
    "I'm having trouble connecting to my knowledge base right now. Please try again in a moment."
]
# Estimate average words per second for speech to calculate sleep duration
WORDS_PER_SECOND = 2.5 # Adjust based on pyttsx3's typical speaking rate and your preference
MIN_SLEEP_AFTER_TTS = 1.0 # Minimum time to wait even for short sentences
MAX_SLEEP_AFTER_TTS = 6.0 # Maximum time to wait, e.g. for a max_tokens=250 response

# Add AppState enum for better state management
class AppState(Enum):
    IDLE = auto()
    LISTENING = auto()
    PROCESSING = auto()
    SPEAKING = auto()

# --- Groq Client Initialization ---
def initialize_groq_client():
    if 'groq_client' not in st.session_state or st.session_state.groq_client is None:
        # CORRECTED CHECK: Only verify if the key is actually empty/not set
        if not GROQ_API_KEY: 
            logger.error("Main: GROQ_API_KEY is not set. Please provide a valid API key in the script.")
            st.error("Groq API Key is not configured. Please set it in the script.")
            st.session_state.groq_client = None
            return
        try:
            st.session_state.groq_client = Groq(api_key=GROQ_API_KEY)
            logger.info("Main: Groq client initialized successfully.")
        except Exception as e:
            logger.error(f"Main: Error initializing Groq client: {e}")
            st.error(f"Failed to initialize Groq client: {e}")
            st.session_state.groq_client = None

# --- Text-to-Speech Thread Target (Self-Contained Engine) ---
def _speak_thread_target(text, lang):
    engine = None
    try:
        engine = pyttsx3.init()
        if engine is None:
            voice_logger.error("TTS Thread: Failed to initialize pyttsx3 engine in thread.")
            return
            
        engine.setProperty('rate', 150)
        voice_id_to_set = None
        voices = engine.getProperty('voices')
        if voices:
            target_voice_name_part = lang
            if lang == 'en': target_voice_name_part = 'english'
            elif lang == 'hi': target_voice_name_part = 'hindi'
            elif lang == 'es': target_voice_name_part = 'spanish'
            elif lang == 'fr': target_voice_name_part = 'french'
            
            for voice in voices:
                if target_voice_name_part in voice.name.lower():
                    voice_id_to_set = voice.id
                    voice_logger.info(f"TTS Thread: Found voice for {lang}: {voice.name}")
                    break
            if not voice_id_to_set: 
                if voices: 
                    voice_id_to_set = voices[0].id 
                    voice_logger.warning(f"TTS Thread: No specific voice for {lang} containing '{target_voice_name_part}'. Using default: {voices[0].name}")
                else:
                    voice_logger.warning(f"TTS Thread: No voices available on this system.")
        else:
            voice_logger.warning("TTS Thread: No voices found by pyttsx3 engine.")

        if voice_id_to_set: 
            engine.setProperty('voice', voice_id_to_set)
        else:
            voice_logger.warning("TTS Thread: No voice ID set, default voice will be used or speech might fail if no default.")
        
        voice_logger.info(f"TTS Thread: Attempting to speak: '{text[:70]}...' (Lang: {lang})")
        engine.say(text)
        engine.runAndWait()
        voice_logger.info(f"TTS Thread: Finished speaking: '{text[:70]}...'")
    except Exception as e:
        voice_logger.error(f"TTS Thread: ERROR during speech for '{text[:70]}...': {e}")
    finally:
        if engine: 
            try:
                engine.stop() 
                voice_logger.info("TTS Thread: pyttsx3 engine stopped for this utterance.")
            except Exception as e_stop:
                voice_logger.error(f"TTS Thread: Error while stopping engine: {e_stop}")


# --- Non-Blocking Text-to-Speech Function ---
def speak_non_blocking(text, lang='en'):
    if not text or text.strip() == "":
        logger.warning("Main: speak_non_blocking called with empty text. Skipping speech.")
        return False 
        
    active_speech_threads_before = threading.active_count()
    logger.info(f"Main: Active threads before starting new speech: {active_speech_threads_before}")

    try:
        speech_thread = threading.Thread(target=_speak_thread_target, args=(text, lang))
        speech_thread.daemon = True 
        speech_thread.start()
        logger.info(f"Main: Speech thread successfully started for '{text[:70]}...'")
        
        num_words = len(text.split())
        estimated_duration = (num_words / WORDS_PER_SECOND) + 0.5 
        sleep_duration = max(MIN_SLEEP_AFTER_TTS, min(estimated_duration, MAX_SLEEP_AFTER_TTS))
        
        logger.info(f"Main: Main thread will sleep for {sleep_duration:.2f}s to allow TTS thread to complete ('{text[:30]}...').")
        time.sleep(sleep_duration) 
        logger.info(f"Main: Finished sleep after TTS call for '{text[:30]}...'.")
        return True

    except Exception as e:
        logger.critical(f"Main: CRITICAL Error starting speech thread for '{text[:70]}...': {e}")
        return False


# --- Tool Integration Functions ---
def safe_math_eval(node):
    """Safely evaluates an AST node."""
    ops = {
        ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
        ast.Div: op.truediv, ast.Pow: op.pow, ast.USub: op.neg
    }
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        return ops[type(node.op)](safe_math_eval(node.left), safe_math_eval(node.right))
    elif isinstance(node, ast.UnaryOp):
        return ops[type(node.op)](safe_math_eval(node.operand))
    else:
        raise TypeError("Unsupported operation in mathematical expression")



class MetricsEmitter:
    """A placeholder for a real metrics client like Prometheus or StatsD."""
    def inc_counter(self, name: str):
        # In a real system, this would increment a counter.
        # tool_logger.debug(f"METRIC_COUNTER_INC: {name}")
        pass
    def observe_timer(self, name: str, duration: float):
        # In a real system, this would record a timing.
        # tool_logger.debug(f"METRIC_TIMER_OBSERVE: {name}, duration: {duration:.4f}s")
        pass


# --- Enhanced Tool System ---
class ToolSystem:
    """Enhanced tool system with improved error handling and parameter validation."""
    _weather_init_lock = threading.Lock() 
    def __init__(self):
        self.tool_metadata = {
            "get_current_date": {
                "required_params": [],
                "optional_params": [],
                "description": "Get today's date",
                "example": "get_current_date()"
            },
            "get_weather_forecast": {
                "required_params": ["location"],
                "optional_params": ["include_forecast", "include_air_quality", "lang"],
                "description": "Get current weather or a 3-day forecast for a location. Can also include air quality data.",
                "example": "get_weather_forecast(location='Delhi', include_forecast=True)",
                "parameter_types": {"location": str, "include_forecast": bool, "include_air_quality": bool, "lang": str}
            },
            "get_mandi_prices": {
                "required_params": ["crop"],
                "optional_params": ["market"],
                "description": "Get mandi prices",
                "example": "get_mandi_prices(crop='potato', market='Bangalore')",
                "parameter_types": {"crop": str, "market": str}
            },
            "get_farming_advice": {
                "required_params": ["topic"],
                "optional_params": [],
                "description": "Get farming advice",
                "example": "get_farming_advice(topic='rice cultivation')",
                "parameter_types": {"topic": str}
            },
            "calculate_math": {
                "required_params": ["expression"],
                "optional_params": [],
                "description": "Solve math",
                "example": "calculate_math(expression='2 + 2')",
                "parameter_types": {"expression": str}
            },
            "tell_joke": {
                "required_params": [],
                "optional_params": [],
                "description": "Tell a joke",
                "example": "tell_joke()"
            },
            "web_search": {
                "required_params": ["query"],
                "optional_params": [],
                "description": "General web search",
                "example": "web_search(query='latest news')",
                "parameter_types": {"query": str}
            },
            "get_news_summary": {
                "required_params": [],
                "optional_params": ["topic"],
                "description": "Get news summary",
                "example": "get_news_summary(topic='technology')",
                "parameter_types": {"topic": str}
            },
            "get_definition": {
                "required_params": ["term"],
                "optional_params": [],
                "description": "Get definition",
                "example": "get_definition(term='artificial intelligence')",
                "parameter_types": {"term": str}
            },
            "get_biography": {
                "required_params": ["person"],
                "optional_params": [],
                "description": "Get biography",
                "example": "get_biography(person='Albert Einstein')",
                "parameter_types": {"person": str}
            },
            "get_sports_update": {
                "required_params": [],
                "optional_params": ["sport"],
                "description": "Get sports update",
                "example": "get_sports_update(sport='cricket')",
                "parameter_types": {"sport": str}
            },
            "get_movie_info": {
                "required_params": ["title"],
                "optional_params": [],
                "description": "Get movie info",
                "example": "get_movie_info(title='Inception')",
                "parameter_types": {"title": str}
            },
            "get_tech_news": {
                "required_params": [],
                "optional_params": [],
                "description": "Get tech news",
                "example": "get_tech_news()",
                "parameter_types": {}
            },
            "get_crop_calendar": {
                "required_params": ["crop"],
                "optional_params": [],
                "description": "Get crop calendar",
                "example": "get_crop_calendar(crop='rice')",
                "parameter_types": {"crop": str}
            },
            "get_fertilizer_info": {
                "required_params": ["crop"],
                "optional_params": [],
                "description": "Get fertilizer information",
                "example": "get_fertilizer_info(crop='wheat')",
                "parameter_types": {"crop": str}
            },
            "get_pest_control": {
                "required_params": ["crop"],
                "optional_params": [],
                "description": "Get pest control information",
                "example": "get_pest_control(crop='cotton')",
                "parameter_types": {"crop": str}
            },
            "get_irrigation_advice": {
                "required_params": ["crop"],
                "optional_params": [],
                "description": "Get irrigation advice",
                "example": "get_irrigation_advice(crop='sugarcane')",
                "parameter_types": {"crop": str}
            },
            "get_factual_answer": {
                "required_params": ["query"],
                "optional_params": [],
                "description": "Answer general knowledge/factual questions (e.g., capital of X, who is president of Y)",
                "example": "get_factual_answer(query='capital of India')",
                "parameter_types": {"query": str}
            },
            "information_retrieval": {
                "required_params": ["query"],
                "optional_params": [],
                "description": "Retrieve any information from the web (news, facts, definitions, biographies, advice, etc.) using a free-form query.",
                "example": "information_retrieval(query='detailed biography of Albert Einstein including his major scientific contributions')",
                "parameter_types": {"query": str}
            },
        }
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.error_counts = {}
        self.last_error_time = {}
        # Centralized Tavily client initialization
        self.tavily_client = None
        if TAVILY_API_KEY:
            try:
                import certifi
                from tavily import TavilyClient
                os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
                self.tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
                tool_logger.info("Tavily client initialized in ToolSystem __init__.")
            except Exception as e:
                tool_logger.error(f"Failed to initialize Tavily client: {e}")
                self.tavily_client = None

    def information_retrieval(self, query: str, **kwargs):
        """Retrieve any information from the web using Tavily and a free-form query."""
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "Information retrieval service is not configured.", "suggestion": "Please check API settings."}
            response = self.tavily_client.search(query=query, search_depth="advanced", max_results=5, include_answer=True)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            results = []
            for i, res in enumerate(response.get('results', []), 1):
                snippet = res.get('content', 'No content available')
                url = res.get('url', '')
                if url:
                    results.append(f"Source {i}: {snippet}\nURL: {url}")
                else:
                    results.append(f"Source {i}: {snippet}")
            if results:
                return {"success": True, "answer": "\n\n".join(results), "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": "No relevant information found.", "suggestion": "Try rephrasing your question."}
        except Exception as e:
            tool_logger.error(f"Information Retrieval Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Please try again later."}

    def get_current_date(self, **kwargs):
        try:
            now = datetime.datetime.now()
            return {"success": True, "answer": f"Today is {now.strftime('%A, %B %d, %Y')}. The current time is {now.strftime('%I:%M %p')}.", "error": None, "suggestion": None}
        except Exception as e:
            tool_logger.error(f"Date Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def calculate_math(self, expression: str, **kwargs):
        try:
            expression = expression.replace('times', '*').replace('plus', '+').replace('minus', '-').replace('divided by', '/')
            result = safe_math_eval(ast.parse(expression, mode='eval').body)
            return {"success": True, "answer": f"The result of {expression} is {result}.", "error": None, "suggestion": None}
        except Exception as e:
            tool_logger.error(f"Math Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Please provide a valid mathematical expression."}

    def tell_joke(self, **kwargs):
        jokes = [
            "Why did the scarecrow win an award? Because he was outstanding in his field!",
            "What do you call a sad strawberry? A blueberry!",
            "Why don't scientists trust atoms? Because they make up everything!",
            "What did the farmer say when he lost his tractor? 'Where's my John Deere?'",
            "Why did the farmer win an award? Because he was outstanding in his field!"
        ]
        return {"success": True, "answer": random.choice(jokes), "error": None, "suggestion": None}

    # --- All Tavily-based tools below use the centralized client and standardized output ---
    def get_mandi_prices(self, crop: str, market: str = "India", **kwargs):
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "Mandi price service is not configured.", "suggestion": "Please check API settings."}
            query = f"current mandi prices for {crop} in {market}"
            response = self.tavily_client.search(query=query, search_depth="basic", max_results=3, include_answer=True)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": f"Couldn't find mandi prices for {crop} in {market}.", "suggestion": "Try again with different parameters."}
        except Exception as e:
            tool_logger.error(f"Mandi Price Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def get_farming_advice(self, topic: str, **kwargs):
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "Farming advice service is not configured.", "suggestion": "Please check API settings."}
            query = f"best farming practices for {topic} site:agrifarming.in OR site:vikaspedia.in"
            response = self.tavily_client.search(query=query, search_depth="advanced", max_results=3, include_answer=True)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": f"Couldn't find specific farming advice for {topic}.", "suggestion": "Try a different topic."}
        except Exception as e:
            tool_logger.error(f"Farming Advice Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def get_crop_calendar(self, crop: str, **kwargs):
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "Crop calendar service is not configured.", "suggestion": "Please check API settings."}
            query = f"growing season and calendar for {crop} in India"
            response = self.tavily_client.search(query=query, search_depth="advanced", max_results=3, include_answer=True)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": f"Couldn't find crop calendar information for {crop}.", "suggestion": "Try a different crop."}
        except Exception as e:
            tool_logger.error(f"Crop Calendar Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def get_fertilizer_info(self, crop: str, **kwargs):
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "Fertilizer information service is not configured.", "suggestion": "Please check API settings."}
            query = f"recommended fertilizers and nutrients for {crop} farming"
            response = self.tavily_client.search(query=query, search_depth="advanced", max_results=3, include_answer=True)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": f"Couldn't find fertilizer information for {crop}.", "suggestion": "Try a different crop."}
        except Exception as e:
            tool_logger.error(f"Fertilizer Info Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def get_pest_control(self, crop: str, **kwargs):
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "Pest control service is not configured.", "suggestion": "Please check API settings."}
            query = f"common pests and pest control methods for {crop} farming"
            response = self.tavily_client.search(query=query, search_depth="advanced", max_results=3, include_answer=True)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": f"Couldn't find pest control information for {crop}.", "suggestion": "Try a different crop."}
        except Exception as e:
            tool_logger.error(f"Pest Control Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def get_irrigation_advice(self, crop: str, **kwargs):
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "Irrigation advice service is not configured.", "suggestion": "Please check API settings."}
            query = f"irrigation requirements and methods for {crop} farming"
            response = self.tavily_client.search(query=query, search_depth="advanced", max_results=3, include_answer=True)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": f"Couldn't find irrigation advice for {crop}.", "suggestion": "Try a different crop."}
        except Exception as e:
            tool_logger.error(f"Irrigation Advice Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def get_news_summary(self, topic: str = None, **kwargs):
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "News summary service is not configured.", "suggestion": "Please check API settings."}
            query = "latest news"
            if topic: query = f"latest news about {topic}"
            response = self.tavily_client.search(query=query, search_depth="basic", include_answer=True, max_results=3)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": "Could not retrieve news summary.", "suggestion": "Try a different topic."}
        except Exception as e:
            tool_logger.error(f"News Summary Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def get_definition(self, term: str, **kwargs):
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "Definition service is not configured.", "suggestion": "Please check API settings."}
            query = f"define {term}"
            response = self.tavily_client.search(query=query, search_depth="basic", include_answer=True, max_results=1)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": f"Could not find a definition for {term}.", "suggestion": "Try a different term."}
        except Exception as e:
            tool_logger.error(f"Definition Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def get_biography(self, person: str, **kwargs):
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "Biography service is not configured.", "suggestion": "Please check API settings."}
            query = f"biography of {person}"
            response = self.tavily_client.search(query=query, search_depth="basic", include_answer=True, max_results=1)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": f"Could not find a biography for {person}.", "suggestion": "Try a different person."}
        except Exception as e:
            tool_logger.error(f"Biography Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def get_sports_update(self, sport: str = None, **kwargs):
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "Sports update service is not configured.", "suggestion": "Please check API settings."}
            query = "latest sports news"
            if sport: query = f"latest {sport} news"
            response = self.tavily_client.search(query=query, search_depth="basic", include_answer=True, max_results=3)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": "Could not retrieve sports updates.", "suggestion": "Try a different sport."}
        except Exception as e:
            tool_logger.error(f"Sports Update Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def get_movie_info(self, title: str, **kwargs):
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "Movie info service is not configured.", "suggestion": "Please check API settings."}
            query = f"movie information for {title}"
            response = self.tavily_client.search(query=query, search_depth="basic", include_answer=True, max_results=1)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": f"Could not find information for movie {title}.", "suggestion": "Try a different movie."}
        except Exception as e:
            tool_logger.error(f"Movie Info Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def get_tech_news(self, **kwargs):
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "Tech news service is not configured.", "suggestion": "Please check API settings."}
            query = "latest technology news"
            response = self.tavily_client.search(query=query, search_depth="basic", include_answer=True, max_results=3)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": "Could not retrieve technology news.", "suggestion": "Try again later."}
        except Exception as e:
            tool_logger.error(f"Tech News Error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def web_search(self, query: str, **kwargs):
        try:
            if not self.tavily_client:
                return {"success": False, "answer": None, "error": "Web search service is not configured.", "suggestion": "Please check API settings."}
            response = self.tavily_client.search(query=query, search_depth="basic", max_results=3, include_answer=True)
            if response.get("answer"):
                return {"success": True, "answer": response["answer"], "error": None, "suggestion": None}
            results = []
            for i, res in enumerate(response.get('results', []), 1):
                results.append(f"Source {i}: {res.get('content', 'No content available')}")
            if results:
                return {"success": True, "answer": "\n".join(results), "error": None, "suggestion": None}
            return {"success": False, "answer": None, "error": "No relevant information found.", "suggestion": "Try rephrasing your question."}
        except Exception as e:
            tool_logger.error(f"Web search error: {e}")
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

    def _create_error_response(self, error_type: str, message: str, suggestion: str = None) -> dict:
        """Create a standardized error response with enhanced error tracking."""
        tool_logger.error(f"Tool error: {error_type} - {message}")
        
        # Track error frequency
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # Update last error time
        self.last_error_time[error_type] = time.time()
        
        return {
            "success": False,
            "error": message,
            "suggestion": suggestion,
            "error_type": error_type,
            "error_count": self.error_counts[error_type],
            "last_error_time": self.last_error_time[error_type]
        }
    
    def _should_retry(self, tool_name: str, error_type: str) -> bool:
        """Determine if a retry should be attempted based on error history."""
        if error_type not in self.error_counts:
            return True
            
        error_count = self.error_counts[error_type]
        last_error = self.last_error_time.get(error_type, 0)
        time_since_last_error = time.time() - last_error
        
        # Don't retry if too many recent errors
        if error_count >= self.max_retries and time_since_last_error < 300:  # 5 minutes
            return False
            
        # Reset error count if enough time has passed
        if time_since_last_error > 300:
            self.error_counts[error_type] = 0
            return True
            
        return True
    
    def _validate_parameters(self, tool_name: str, parameters: dict) -> tuple[bool, str]:
        """Validate parameters against tool metadata with enhanced validation."""
        if tool_name not in self.tool_metadata:
            tool_logger.warning(f"Tool '{tool_name}' not found in metadata")
            return False, f"Tool '{tool_name}' not found"
            
        metadata = self.tool_metadata[tool_name]
        required_params = metadata["required_params"]
        
        # Check for missing required parameters
        missing_params = [param for param in required_params if param not in parameters]
        if missing_params:
            tool_logger.warning(f"Missing required parameters for {tool_name}: {missing_params}")
            return False, f"Missing required parameters: {', '.join(missing_params)}"
        
        # Validate parameter types if type information is available
        if "parameter_types" in metadata:
            for param, value in parameters.items():
                if param in metadata["parameter_types"]:
                    expected_type = metadata["parameter_types"][param]
                    if not isinstance(value, expected_type):
                        tool_logger.warning(f"Invalid parameter type for {tool_name}.{param}: expected {expected_type}, got {type(value)}")
                        return False, f"Invalid type for parameter '{param}': expected {expected_type.__name__}"
        
        return True, ""
    
    def execute_tool(self, tool_name: str, parameters: dict) -> dict:
        """Execute a tool with improved error handling, retries, and parameter validation."""
        tool_logger.info(f"Executing tool: {tool_name} with parameters: {parameters}")
        
        for attempt in range(self.max_retries):
            try:
                # Validate tool exists
                if tool_name not in self.tool_metadata:
                    return self._create_error_response(
                        "TOOL_NOT_FOUND",
                        f"Tool '{tool_name}' not found",
                        "Please check the tool name and try again."
                    )
                
                # Validate parameters
                is_valid, error_message = self._validate_parameters(tool_name, parameters)
                if not is_valid:
                    return self._create_error_response(
                        "INVALID_PARAMETERS",
                        error_message,
                        f"Required parameters: {', '.join(self.tool_metadata[tool_name]['required_params'])}"
                    )
                
                # Execute the tool
                tool_method = getattr(self, tool_name, None)
                if tool_method is None:
                    return self._create_error_response(
                        "TOOL_NOT_IMPLEMENTED",
                        f"Tool '{tool_name}' is not implemented",
                        "Please try a different tool."
                    )
                
                result = tool_method(**parameters)
                tool_logger.info(f"Tool {tool_name} executed successfully")
                
                return {
                    "success": True,
                    "result": result,
                    "error": None,
                    "suggestion": None,
                    "attempt": attempt + 1
                }
                
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                tool_logger.error(f"Error executing tool {tool_name} (attempt {attempt + 1}): {error_type} - {error_msg}")
                
                if not self._should_retry(tool_name, error_type):
                    return self._create_error_response(
                        "MAX_RETRIES_EXCEEDED",
                        f"Maximum retries exceeded for tool '{tool_name}'",
                        "Please try again later or use a different tool."
                    )
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                
                return self._create_error_response(
                    "EXECUTION_ERROR",
                    f"Error executing tool '{tool_name}': {error_msg}",
                    "Please try again with different parameters."
                )
    
    def get_error_stats(self) -> dict:
        """Get statistics about tool errors."""
        return {
            "error_counts": self.error_counts,
            "last_error_times": {k: datetime.datetime.fromtimestamp(v).isoformat() 
                               for k, v in self.last_error_time.items()}
        }
    
    def reset_error_stats(self):
        """Reset error tracking statistics."""
        self.error_counts.clear()
        self.last_error_time.clear()
        tool_logger.info("Error statistics reset")

    def get_weather_forecast(
        self,
        location: str,
        include_forecast: bool = False,
        include_air_quality: bool = False,
        lang: str = None
    ):
        """Get weather data using WeatherAPI.com."""
        try:
            import requests, unicodedata, datetime, certifi
            WEATHERAPI_KEY = "811763061bc547eaafb215343252706"
            loc_key = unicodedata.normalize("NFC", location.strip().lower())
            if not loc_key:
                loc_key = "auto:ip"
            endpoint = "/v1/forecast.json" if include_forecast else "/v1/current.json"
            params = {"key": WEATHERAPI_KEY, "q": loc_key}
            if include_air_quality:
                params["aqi"] = "yes"
            if include_forecast:
                params.update({"days": 3, "alerts": "yes"})
            if lang:
                params["lang"] = lang
            response = requests.get(f"https://api.weatherapi.com{endpoint}", params=params, timeout=5, verify=certifi.where())
            if response.status_code == 200:
                data = response.json()
                local_time_str = data.get('location', {}).get('localtime', '')
                local_time = datetime.datetime.fromisoformat(local_time_str).strftime("%H:%M") if local_time_str else "N/A"
                summary = f"In {data['location']['name']} ({local_time}), it's {data['current']['condition']['text']}. Temp: {data['current']['temp_c']}°C."
                if include_air_quality and data["current"].get("air_quality"):
                    aqi = data["current"]["air_quality"].get("us-epa-index", "N/A")
                    summary += f" AQI (US-EPA): {aqi}."
                if include_forecast and "forecast" in data:
                    summary += " Forecast:"
                    for day in data['forecast']['forecastday']:
                        day_name = datetime.datetime.strptime(day['date'], "%Y-%m-%d").strftime("%a")
                        summary += f" {day_name}: H {day['day']['maxtemp_c']}°C, L {day['day']['mintemp_c']}°C."
                return {"success": True, "answer": summary, "error": None, "suggestion": None}
            elif response.status_code == 429:
                return {"success": False, "answer": None, "error": "Too many requests (rate limit exceeded).", "suggestion": "Please wait a moment and try again."}
            elif response.status_code == 403:
                return {"success": False, "answer": None, "error": "Access to the weather service was denied.", "suggestion": "Check your API key or plan."}
            else:
                try:
                    error_msg = response.json().get("error", {}).get("message")
                except Exception:
                    error_msg = response.text[:200]
                return {"success": False, "answer": None, "error": error_msg or "An unknown error occurred.", "suggestion": "Try again later."}
        except Exception as e:
            return {"success": False, "answer": None, "error": str(e), "suggestion": "Try again later."}

# --- Speech-to-Text Function ---
def listen_for_voice_st(lang='en', timeout=10, phrase_time_limit=None):
    recognizer = sr.Recognizer()
    microphone = sr.Microphone() 
    voice_logger.info(f"SR: Initializing microphone. Timeout: {timeout}s, Phrase Limit: {phrase_time_limit if phrase_time_limit else 'None (waits for pause)'}")
    
    with microphone as source:
        try:
            voice_logger.info("SR: Adjusting for ambient noise (duration 1.5s)...")
            time.sleep(0.1) 
            recognizer.adjust_for_ambient_noise(source, duration=1.5) 
            voice_logger.info("SR: Ambient noise adjustment complete. Now listening for audio input...")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            voice_logger.info("SR: Audio captured. Attempting to recognize speech...")
            text = recognizer.recognize_google(audio, language=lang)
            voice_logger.info(f"SR: Successfully recognized text: '{text}'")
            return text
        except sr.WaitTimeoutError: 
            voice_logger.warning("SR: Timeout - No speech detected within the timeout period.")
            return "TIMEOUT"
        except sr.UnknownValueError: 
            voice_logger.warning("SR: Speech was unintelligible or could not be understood by Google Speech Recognition.")
            return "UNCLEAR"
        except sr.RequestError as e: 
            voice_logger.error(f"SR: API request error (e.g., network issue, Google Speech Recognition service unavailable); {e}")
            return "ERROR"
        except Exception as e: 
            voice_logger.critical(f"SR: Unexpected error in listen_for_voice_st: {type(e).__name__} - {e}")
            return "ERROR"

# --- Follow-up Question Generator ---
def get_followup_question(lang='en'):
    questions = {
        "en": "Is there anything else I can help you with regarding farming today?", 
        "hi": "क्या मैं आज खेती के बारे में आपकी और कोई मदद कर सकता हूँ?", 
        "es": "¿Hay algo más en lo que pueda ayudarte sobre agricultura hoy?", 
        "fr": "Y a-t-il autre chose concernant l'agriculture sur lequel je peux vous aider aujourd'hui?"
    }
    return questions.get(lang, questions['en'])

# Update handle_user_input to use the new agent system
def handle_user_input(user_input_text, input_type="text"):
    """Processes user input with improved state management and error handling."""
    logger.info(f"Handling input (Type: {input_type}): '{user_input_text[:70]}...'")
    
    # Step 1: Input Validation
    if not user_input_text or user_input_text.strip() == "": 
        logger.info("Empty user input received. No action taken.")
        if st.session_state.get('conversation_active', False):
            st.session_state.should_listen = True
        st.rerun() 
        return
    
    # Step 2: State Management
    st.session_state.chat_history.append({
        "role": "user", 
        "content": f"🎤 {user_input_text}" if input_type == "voice" else user_input_text,
        "input_type": input_type
    })
    
    # Step 3: Agent Response Generation
    agent_output = generate_agent_response(user_input_text)
    
    # Step 4: Response Processing
    # Show reasoning if enabled
    if st.session_state.get('reasoning_mode_active'):
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": f"🤔 *Thought: {agent_output.get('thought', 'No thought was generated.')}*",
            "type": "reasoning"
        })
    
    # Show search feedback if present
    if agent_output.get('feedback'):
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": agent_output['feedback'],
            "type": "system_feedback"
        })
    
    # Add AI response to chat history
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": agent_output['response'],
        "type": "response"
    })
    
    # Step 5: Output Generation
    if st.session_state.voice_output_enabled:
        speak_non_blocking(agent_output['response'], lang=st.session_state.selected_language_code)
    
    # Step 6: Conversation Management
    is_fallback_response = agent_output['response'] in KNOWN_FALLBACK_RESPONSES
    conversation_is_active = st.session_state.get('conversation_active', False)

    if conversation_is_active:
        if not is_fallback_response: 
            pass  # No explicit follow-up action needed here as LLM handles it
        else: 
            logger.info(f"LLM returned a fallback/error ('{agent_output['response'][:30]}...'). No followup question.")
        
        st.session_state.should_listen = True 
    
    logger.info("handle_user_input finished processing. Rerunning UI.")
    st.rerun()

# --- Display Chat History ---
def display_chat_history():
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            content_to_display = message['content']
            if message.get("type") == "followup" and isinstance(content_to_display, str):
                st.markdown(f"💭 *{content_to_display}*")
            elif message.get("type") == "system_feedback" and isinstance(content_to_display, str):
                 st.markdown(content_to_display) 
            elif isinstance(content_to_display, str):
                st.markdown(content_to_display)
            else:
                st.markdown(str(content_to_display))


# --- Process Voice Input ---
def process_voice_input():
    logger.info("Main: process_voice_input called by Streamlit rerun logic.")
    st.session_state.listening_state = True
    
    status_placeholder = st.empty() 
    status_placeholder.info("🎤 **Listening...** Speak clearly and pause when you are finished.", icon="🔊")
    
    time.sleep(0.7) 
    
    voice_result = listen_for_voice_st(lang=st.session_state.selected_language_code)
    
    status_placeholder.empty() 
    st.session_state.listening_state = False 
    logger.info(f"Main: Voice listen result from STT: '{voice_result}'")
    
    if voice_result and voice_result not in ["TIMEOUT", "UNCLEAR", "ERROR"]:
        handle_user_input(voice_result, input_type="voice") 
    else:
        feedback_map = {
            "TIMEOUT": ("⏰", {"en": "I didn't hear anything. Please ensure your microphone is active and try speaking again.", "hi": "मुझे कुछ सुनाई नहीं दिया। कृपया सुनिश्चित करें कि आपका माइक्रोफ़ोन सक्रिय है और फिर से बोलने का प्रयास करें।"}),
            "UNCLEAR": ("❓", {"en": "I couldn't quite understand what you said. Could you please speak clearly and repeat that?", "hi": "मैं ठीक से समझ नहीं पाया कि आपने क्या कहा। क्या आप कृपया स्पष्ट रूप से बोलकर दोहरा सकते हैं?"}),
            "ERROR":   ("⚠️", {"en": "Sorry, I'm having a bit of trouble with speech recognition at the moment. Please try again shortly.", "hi": "क्षमा करें, मुझे इस समय वाक् पहचान में थोड़ी परेशानी हो रही है। कृपया शीघ्र पुनः प्रयास करें।"})
        }
        default_stt_issue_msg = "An issue occurred with voice input. Please try again."
        icon, messages = feedback_map.get(voice_result, ("❓", {"en": default_stt_issue_msg, "hi": default_stt_issue_msg})) 
        
        feedback_text = messages.get(st.session_state.selected_language_code, messages['en'])
        
        st.session_state.chat_history.append({"role": "assistant", "content": f"{icon} {feedback_text}", "type": "system_feedback"})
        if st.session_state.voice_output_enabled:
            speak_non_blocking(feedback_text, lang=st.session_state.selected_language_code)
        
        if st.session_state.get('conversation_active', False): 
            st.session_state.should_listen = True 
        logger.info("Main: STT fallback processed in process_voice_input. Rerunning UI.")
        st.rerun()

# --- Streamlit App UI and Logic ---
def run_kisaanvaani_app():
    st.set_page_config(page_title="KisaanVaani Voice Assistant", layout="wide")
    st.title("🌾 KisaanVaani Voice Assistant")

    # --- Robust Session State Initialization ---
    if 'voice_output_enabled' not in st.session_state:
        st.session_state.voice_output_enabled = True  # Default ON

    if 'services_initialized' not in st.session_state:
        initialize_groq_client()
        st.session_state.services_initialized = True
        st.session_state.chat_history = []
        st.session_state.selected_language_code = 'en' 
        st.session_state.selected_language_name = 'English' 
        st.session_state.conversation_active = False
        st.session_state.listening_state = False
        st.session_state.should_listen = False
        st.session_state.has_greeted_initial = False
        st.session_state.reasoning_mode_active = False  # New state for reasoning mode
        # Initialize ToolSystem and ChatContext in session state
        if 'tool_system' not in st.session_state:
            st.session_state.tool_system = ToolSystem()
        if 'chat_context' not in st.session_state:
            st.session_state.chat_context = ChatContext()
        logger.info("Main: Session state variables initialized.")

    st.sidebar.header("🌍 Language Settings")
    lang_options_display = list(SUPPORTED_LANGUAGES.keys())
    lang_names_capitalized = [name.capitalize() for name in lang_options_display]
    current_lang_idx = 0
    try:
        current_lang_idx = lang_names_capitalized.index(st.session_state.selected_language_name.capitalize())
    except ValueError:
        logger.warning(f"Warning: Current language '{st.session_state.selected_language_name}' not in options. Defaulting to English.")
        st.session_state.selected_language_name = 'English' # Default to English if error
        st.session_state.selected_language_code = 'en'

    selected_lang_name_ui = st.sidebar.selectbox("Choose Language", lang_names_capitalized, index=current_lang_idx, key="lang_sb")

    if selected_lang_name_ui.lower() != st.session_state.selected_language_name.lower():
        logger.info(f"Main: Language changed: {selected_lang_name_ui}")
        st.session_state.selected_language_name = selected_lang_name_ui
        st.session_state.selected_language_code = SUPPORTED_LANGUAGES[selected_lang_name_ui.lower()]
        st.session_state.chat_history = []
        st.session_state.conversation_active = False
        st.session_state.should_listen = False
        st.session_state.listening_state = False
        st.session_state.has_greeted_initial = False
        st.rerun()

    st.sidebar.header("🔊 Voice Output")
    st.session_state.voice_output_enabled = st.sidebar.toggle(
        "Enable Voice Output (TTS)",
        value=st.session_state.voice_output_enabled,
        help="If enabled, responses will be spoken aloud."
    )

    st.sidebar.header("🎙️ Voice Conversation")
    if st.session_state.get('conversation_active', False):
        if st.sidebar.button("🛑 End Conversation", type="secondary", use_container_width=True, key="end_conv_btn"):
            logger.info("Main: 'End Conversation' pressed.")
            st.session_state.conversation_active = False
            st.session_state.listening_state = False
            st.session_state.should_listen = False
            goodbye_text_map = {"en": "Thank you for using KisaanVaani. Goodbye!", "hi": "किसानवाणी का उपयोग करने के लिए धन्यवाद। अलविदा!"}
            goodbye_text = goodbye_text_map.get(st.session_state.selected_language_code, goodbye_text_map['en'])
            st.session_state.chat_history.append({"role": "assistant", "content": f"👋 {goodbye_text}", "type": "goodbye"})
            if st.session_state.voice_output_enabled:
                speak_non_blocking(goodbye_text, lang=st.session_state.selected_language_code)
            st.rerun()
    else:
        if st.sidebar.button("🎤 Start Voice Conversation", type="primary", use_container_width=True, key="start_conv_btn"):
            logger.info("Main: 'Start Conversation' pressed.")
            st.session_state.conversation_active = True
            st.session_state.should_listen = True
            greeting_voice_start_map = {"en": "Voice mode activated. How can I assist?", "hi": "वॉइस मोड सक्रिय। कैसे मदद कर सकता हूँ?"}
            greeting_text = greeting_voice_start_map.get(st.session_state.selected_language_code, greeting_voice_start_map['en'])
            if not st.session_state.chat_history or \
               (st.session_state.chat_history and st.session_state.chat_history[-1].get("type") not in ["greeting_app_start", "greeting_voice_start"]):
                st.session_state.chat_history.append({"role": "assistant", "content": f"👋 {greeting_text}", "type": "greeting_voice_start"})
            if st.session_state.voice_output_enabled:
                speak_non_blocking(greeting_text, lang=st.session_state.selected_language_code)
            st.session_state.has_greeted_initial = True 
            st.rerun()

    status_container = st.empty()
    if st.session_state.get('conversation_active'):
        if st.session_state.get('listening_state'):
            status_container.info("🎤 **Listening...** Speak clearly and pause when finished.", icon="🔊")
        else:
            status_container.success("🗣️ **Voice conversation active.** Ready for your command.", icon="✅")
    else:
        status_container.info("💬 **Type your message or start a voice conversation from the sidebar.**", icon="ℹ️")

    chat_container = st.container()
    with chat_container:
        display_chat_history()

    if st.session_state.get('should_listen') and \
       st.session_state.get('conversation_active') and \
       not st.session_state.get('listening_state'):
        logger.info("Main: Loop trigger: Should listen = True, Active = True, Not Listening = True. Calling process_voice_input.")
        st.session_state.should_listen = False 
        process_voice_input() 
        
    typed_prompt = st.chat_input(f"Type in {st.session_state.selected_language_name}...", key="main_chat_input",
                                 disabled=st.session_state.get('listening_state', False))
    if typed_prompt:
        logger.info(f"Main: Text input: '{typed_prompt[:70]}...'")
        st.session_state.conversation_active = False 
        st.session_state.should_listen = False
        st.session_state.listening_state = False
        handle_user_input(typed_prompt, input_type="text")

    if not st.session_state.has_greeted_initial and \
       st.session_state.get('services_initialized') and \
       not st.session_state.chat_history: 
        logger.info("Main: Displaying one-time initial app greeting (text mode, chat empty).")
        initial_greeting_text = "Hello! I am KisaanVaani. Start a voice conversation or type your query."
        if st.session_state.selected_language_code == "hi":
            initial_greeting_text = "नमस्ते! मैं किसानवाणी हूँ। वॉइस वार्तालाप शुरू करें या अपना प्रश्न टाइप करें।"
        
        st.session_state.chat_history.append({"role": "assistant", "content": f"👋 {initial_greeting_text}", "type": "greeting_app_start"})
        if st.session_state.voice_output_enabled:
            speak_non_blocking(initial_greeting_text, lang=st.session_state.selected_language_code)
        st.session_state.has_greeted_initial = True
        st.rerun()

    # Add reasoning mode toggle in sidebar
    st.sidebar.header("Settings")
    st.sidebar.toggle("🧠 Show Agent Reasoning", key="reasoning_mode_active", help="See the agent's thought process in the chat.")

class ChatContext:
    """Enhanced chat context management with improved state tracking and user profiling."""
    
    def __init__(self, max_history: int = 10):
        """Initialize chat context with configurable history size."""
        self.max_history = max_history
        self.conversation_history = []
        self.user_profile = {
            "name": None,
            "location": None,
            "interests": set(),
            "preferences": {},
            "last_interaction": None,
            "farming_context": {},  # Added farming context
            "language": "en"  # Added language preference
        }
        self.conversation_state = {
            "current_topic": None,
            "pending_actions": [],
            "context_window": [],
            "tool_usage_stats": {},
            "context_entities": set(),  # Added for entity tracking
            "tool_usage_history": []  # Added for detailed tool history
        }
        self.max_context_window = 5
        context_logger.info("ChatContext initialized")
    
    def add_message(self, role: str, content: str, metadata: dict = None):
        """Add a message to conversation history with metadata."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.conversation_history.append(message)
        
        # Maintain history size limit
        if len(self.conversation_history) > self.max_history:
            self.conversation_history.pop(0)
        
        # Update context window and state
        self._update_context_window(message)
        self._update_conversation_state(message)
        
        # Update last interaction time
        self.user_profile["last_interaction"] = datetime.datetime.now().isoformat()
        context_logger.debug(f"Added message: {role} - {content[:50]}...")
    
    def _update_context_window(self, message: dict):
        """Update the context window with new message."""
        self.conversation_state["context_window"].append(message)
        if len(self.conversation_state["context_window"]) > self.max_context_window:
            self.conversation_state["context_window"].pop(0)
    
    def _update_conversation_state(self, message: dict):
        """Update conversation state based on new message."""
        if message["role"] == "user":
            self._extract_entities(message["content"])
            self._update_active_topic(message["content"])
        
        # Update tool usage history
        if message.get("metadata", {}).get("tool_used"):
            self.conversation_state["tool_usage_history"].append({
                "tool": message["metadata"]["tool_used"],
                "timestamp": message["timestamp"],
                "success": message["metadata"].get("success", False)
            })
    
    def _extract_entities(self, text: str):
        """Extract relevant entities from text."""
        # Enhanced entity extraction with farming terms
        entities = set()
        farming_terms = [
            "crop", "weather", "soil", "fertilizer", "pesticide", "harvest",
            "irrigation", "seeding", "planting", "cultivation", "yield",
            "mandi", "price", "market", "storage", "equipment"
        ]
        for term in farming_terms:
            if term in text.lower():
                entities.add(term)
        self.conversation_state["context_entities"].update(entities)
    
    def _update_active_topic(self, text: str):
        """Update the active conversation topic."""
        topics = {
            "weather": ["weather", "forecast", "rain", "temperature", "climate"],
            "crops": ["crop", "plant", "harvest", "yield", "cultivation"],
            "prices": ["price", "market", "mandi", "rate", "cost"],
            "advice": ["how", "what", "when", "advice", "help", "suggestion"],
            "equipment": ["tractor", "equipment", "machine", "tool"],
            "fertilizer": ["fertilizer", "nutrient", "soil", "fertilize"],
            "pest_control": ["pest", "disease", "control", "pesticide"]
        }
        
        for topic, keywords in topics.items():
            if any(keyword in text.lower() for keyword in keywords):
                self.conversation_state["current_topic"] = topic
                break
    
    def get_farming_context(self) -> dict:
        """Get farming-specific context."""
        return self.user_profile["farming_context"]
    
    def update_farming_context(self, key: str, value: Any):
        """Update farming context with new information."""
        self.user_profile["farming_context"][key] = value
        context_logger.info(f"Updated farming context: {key} = {value}")
    
    def get_tool_usage_stats(self) -> dict:
        """Get detailed statistics about tool usage."""
        stats = {}
        for entry in self.conversation_state["tool_usage_history"]:
            tool = entry["tool"]
            if tool not in stats:
                stats[tool] = {"total": 0, "successful": 0, "failed": 0}
            stats[tool]["total"] += 1
            if entry.get("success", False):
                stats[tool]["successful"] += 1
            else:
                stats[tool]["failed"] += 1
        return stats
    
    def get_context_summary(self) -> dict:
        """Get a comprehensive summary of the current conversation context."""
        return {
            "current_topic": self.conversation_state["current_topic"],
            "pending_actions": self.conversation_state["pending_actions"],
            "recent_messages": self.conversation_state["context_window"],
            "tool_usage": self.get_tool_usage_stats(),
            "user_profile": self.user_profile,
            "context_entities": list(self.conversation_state["context_entities"]),
            "farming_context": self.get_farming_context()
        }
    
    def clear_context(self):
        """Clear the conversation context while preserving user profile."""
        self.conversation_history.clear()
        self.conversation_state["context_window"].clear()
        self.conversation_state["pending_actions"].clear()
        self.conversation_state["current_topic"] = None
        self.conversation_state["context_entities"].clear()
        self.conversation_state["tool_usage_history"].clear()
        context_logger.info("Conversation context cleared")

# --- Core Agent System ---
def generate_agent_response(user_query: str) -> dict:
    """The agent's brain: routes to tools and synthesizes a response with enhanced capabilities."""
    if 'groq_client' not in st.session_state or st.session_state.groq_client is None:
        agent_logger.error("LLM client not initialized in session state")
        return {"response": KNOWN_FALLBACK_RESPONSES[0]}
    
    client = st.session_state.groq_client
    
    # Retrieve instances from session state
    chat_context_instance = st.session_state.chat_context
    tool_system_instance = st.session_state.tool_system

    try:
        # Step 1: Context Preparation
        context_summary = chat_context_instance.get_context_summary()
        
        # Format recent messages for the prompt
        recent_messages_formatted = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in context_summary["recent_messages"]])
        
        # Format user profile for the prompt
        user_profile_formatted = "\n".join([f"- {k.replace('_', ' ').title()}: {v}" for k, v in context_summary["user_profile"].items() if v is not None])
        
        # Format tool usage for the prompt
        tool_usage_formatted = "\n".join([f"- {tool}: Total: {stats['total']}, Successful: {stats['successful']}, Failed: {stats['failed']}" 
                                       for tool, stats in context_summary["tool_usage"].items()])
        if not tool_usage_formatted: tool_usage_formatted = "None"

        # Dynamically generate tool list for the prompt
        tool_list_for_prompt = []
        for tool_name, meta in tool_system_instance.tool_metadata.items():
            # Only include weather, non-Tavily, and the new information_retrieval tool
            if tool_name == "information_retrieval" or tool_name == "get_weather_forecast" or tool_name in ["get_current_date", "calculate_math", "tell_joke"]:
                params_str = ", ".join([f"{p}" for p in meta["required_params"]])
                if meta["optional_params"]:
                    params_str += ", " + ", ".join([f"{p}=..." for p in meta["optional_params"]])
                tool_list_for_prompt.append(f"- {tool_name}({params_str}): {meta['description']}")
        dynamic_tool_list = "\n   ".join(tool_list_for_prompt)

        agent_logger.info(f"Processing query: {user_query[:50]}...")
        agent_logger.debug(f"Context for agent:\n{context_summary}")
        
        # Step 2: Intent Detection & Tool Routing with Enhanced Analysis
        router_prompt = f"""You are a master reasoning agent that decides which tool to use to answer a user's query.
You have access to the following context:

Recent Conversation:
{recent_messages_formatted}

User Profile:
{user_profile_formatted}

Conversation State:
Current Topic: {context_summary["current_topic"] if context_summary["current_topic"] else "None"}
Pending Actions: {context_summary["pending_actions"] if context_summary["pending_actions"] else "None"}
Context Entities: {', '.join(context_summary["context_entities"]) if context_summary["context_entities"] else "None"}
Farming Context: {json.dumps(context_summary["farming_context"], indent=2)}
Tool Usage Statistics:
{tool_usage_formatted}

Available Tools:
{dynamic_tool_list}

Instructions:
1. Analyze the user's query and conversation history to understand their intent and context.
2. Consider the farming context and tool usage statistics when making decisions.
3. If the user's query is ambiguous, use the conversation history and conversation state to determine what they're referring to.
4. Choose the most appropriate tool from the list above. If no tool is suitable, set `tool_to_use` to "None".
5. Consider tool usage patterns and success rates when making decisions.
6. Extract parameters precisely from the user's query and context. For the `get_weather_forecast` tool specifically, if the query mentions a future time (like 'tomorrow', 'in 2 days', or 'forecast'), you MUST set the `include_forecast` parameter to `True`. For all other information, use the `information_retrieval` tool and construct the most effective query for the user's intent.
7. Your output MUST be a JSON object with:
   - tool_to_use: The name of the tool to use (or "None" if no tool is needed)
   - thought: Your detailed reasoning for choosing this tool (or for choosing "None")
   - parameters: A dictionary of the arguments needed by the tool (empty if tool_to_use is "None")
   - is_farming_query: Boolean indicating if this is a farming-related query
   - confidence: A number between 0 and 1 indicating your confidence in this choice
   - alternative_tools: List of alternative tools that could also work (empty if tool_to_use is "None")
   - context_used: List of context elements that influenced your decision"""

        router_messages = [
            {"role": "system", "content": router_prompt},
            {"role": "user", "content": user_query}
        ]
        
        router_completion = client.chat.completions.create(
            messages=router_messages,
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        decision = json.loads(router_completion.choices[0].message.content)
        thought = decision.get("thought", "No thought was generated.")
        chosen_tool = decision.get("tool_to_use")
        params = decision.get("parameters", {})
        is_farming_query = decision.get("is_farming_query", False)
        confidence = decision.get("confidence", 0.0)
        alternative_tools = decision.get("alternative_tools", [])
        context_used = decision.get("context_used", [])
        
        agent_logger.info(f"Tool selection: {chosen_tool} (confidence: {confidence:.2f})")
        agent_logger.debug(f"Thought process: {thought}")
        agent_logger.debug(f"Parameters for tool: {params}")
        
        # Step 3: Tool Execution and Intelligent Response Processing
        tool_output = None
        search_feedback = None
        
        if chosen_tool and chosen_tool != "None":
            # Only show search feedback for information_retrieval and get_weather_forecast
            if chosen_tool in ["information_retrieval", "get_weather_forecast"]:
                search_query = params.get('query') or params.get('topic') or params.get('location') or params.get('crop')
                search_feedback = f"🔎 Searching for: *{search_query}*"
            
            agent_logger.info(f"Calling tool_system.execute_tool with {chosen_tool} and {params}")
            tool_response = tool_system_instance.execute_tool(chosen_tool, params)
            agent_logger.debug(f"Tool execution response: {tool_response}")

            if tool_response["success"]:
                tool_result = tool_response["answer"] if "answer" in tool_response else tool_response["result"]
                tool_output = str(tool_result)
                if is_farming_query and chosen_tool == "information_retrieval":
                    chat_context_instance.update_farming_context(chosen_tool, tool_result)
            else:
                error_msg = tool_response.get("error", "Unknown error")
                suggestion = tool_response.get("suggestion", "Please try again.")
                tool_output = f"I encountered an error: {error_msg}. {suggestion}"
                agent_logger.warning(f"Tool {chosen_tool} failed: {error_msg}. Suggestion: {suggestion}")
        else:
            agent_logger.info("No specific tool chosen. Proceeding to direct LLM response synthesis.")
            tool_output = ""
        # Step 4: Response Synthesis with Enhanced Context
        synthesizer_prompt = f"""You are KisaanVaani, a friendly and helpful voice assistant. You will be given information from a tool.

Context:
Recent Conversation:
{recent_messages_formatted}

User Profile:
{user_profile_formatted}

Conversation State:
Current Topic: {context_summary["current_topic"] if context_summary["current_topic"] else "None"}
Pending Actions: {context_summary["pending_actions"] if context_summary["pending_actions"] else "None"}
Context Entities: {', '.join(context_summary["context_entities"]) if context_summary["context_entities"] else "None"}
Farming Context: {json.dumps(context_summary["farming_context"], indent=2)}
Tool Usage Statistics:
{tool_usage_formatted}

Query: {user_query}
Tool Used: {chosen_tool}
Tool Output: {tool_output}
Is Farming Query: {is_farming_query}
Confidence: {confidence}
Context Used: {', '.join(context_used)}

Instructions:
1. Present this information to the user in a natural, conversational, and concise way.
2. If the tool was a search, synthesize the key findings into a helpful summary.
3. If the tool returned an error, state that you couldn't find the information and apologize.
4. If no tool was used (Tool Used is "None"), generate a direct, conversational response based on the query and the provided context. Do NOT apologize for not using a tool; simply respond naturally.
5. Use the conversation history to maintain context and provide relevant follow-up information.
6. If this is a farming query, include relevant agricultural context.
7. If this is NOT a farming query, do NOT force farming context.
8. Consider the user's language and previous interactions when crafting the response.
9. ALWAYS end your response by asking a gentle, open-ended follow-up question."""

        final_messages = [
            {"role": "system", "content": synthesizer_prompt},
            {"role": "user", "content": user_query}
        ]
        
        final_completion = client.chat.completions.create(
            messages=final_messages,
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=250,
            top_p=1,
            stream=False
        )
        
        final_answer = final_completion.choices[0].message.content
        agent_logger.info(f"Final answer generated: {final_answer[:100]}...")
        
        # Update chat context with the interaction
        chat_context_instance.add_message("user", user_query, {
            "is_farming_query": is_farming_query,
            "confidence": confidence
        })
        
        chat_context_instance.add_message("assistant", final_answer, {
            "tool_used": chosen_tool,
            "confidence": confidence,
            "context_used": context_used
        })
        
        return {
            "response": final_answer,
            "feedback": search_feedback,
            "thought": thought,
            "tool_used": chosen_tool,
            "is_farming_query": is_farming_query,
            "confidence": confidence,
            "context_used": context_used
        }
        
    except Exception as e:
        agent_logger.error(f"CRITICAL ERROR in agent logic: {e}", exc_info=True)
        return {"response": KNOWN_FALLBACK_RESPONSES[1]}

if __name__ == "__main__":
    run_kisaanvaani_app()
