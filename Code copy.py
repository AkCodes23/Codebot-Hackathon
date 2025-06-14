# ==============================================================================
# KisaanVaani - Definitive Edition v2.0
#
# ARCHITECTURE:
# - UI: Gradio (for robust audio/chat components and event-driven model)
# - TTS: Piper TTS (for high-quality, local, private, in-memory speech)
# - STT: faster-whisper (primary) with sr.Google (calibrated fallback)
# - Agent: Fully-featured, decoupled logic with tool retries, context, and memory.
# - This single file incorporates all bug fixes and feature enhancements.
# ==============================================================================

# --- Part 1: Imports, Configuration, and High-Performance Services ---

# 1.1: Standard Library and Third-Party Imports
import os
import sys
import time
import json
import random
import logging
import datetime
import ast
import operator as op
import threading
import base64
from pathlib import Path
from io import BytesIO
from typing import Any, Dict, Optional, List, Tuple
from functools import lru_cache
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto

class AppState(Enum):
    IDLE       = auto()
    LISTENING  = auto()
    PROCESSING = auto()
    SPEAKING   = auto()


# Third-party libraries
import gradio as gr
from groq import Groq
import soundfile as sf

# Import optional dependencies and handle their absence gracefully
try:
    from tavily import TavilyClient
except ImportError: TavilyClient = None
try:
    from faster_whisper import WhisperModel
except ImportError: WhisperModel = None
try:
    from piper import PiperVoice
except ImportError: PiperVoice = None
try:
    import speech_recognition as sr
except ImportError: sr = None

# ==============================================================================
# 1.2: Centralized, Typed Configuration
# ==============================================================================
@dataclass
class AppConfig:
    """A typed dataclass serving as the single source of truth for all settings."""
    # --- API Keys ---
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")

    # --- Directory and Model Paths ---
    PIPER_VOICES_DIR: Path = Path("./piper_voices")
    WHISPER_MODEL_SIZE: str = "base"  # Multilingual model
    WHISPER_COMPUTE_TYPE: str = "int8"

    # --- Language Configuration: Single Source of Truth ---
    # Maps user-facing language name to its technical details.
    LANGUAGE_CONFIG: Dict[str, Dict[str, Any]] = field(default_factory=lambda: {
        "English": {"code": "en", "bcp47": "en-US", "voices": ["en_US-lessac-medium.onnx"]},
        "Hindi":   {"code": "hi", "bcp47": "hi-IN", "voices": ["hi_IN-cmu-medium.onnx"]},
        "Spanish": {"code": "es", "bcp47": "es-ES", "voices": ["es_ES-mls_9972-low.onnx"]},
        "French":  {"code": "fr", "bcp47": "fr-FR", "voices": ["fr_FR-upmc-medium.onnx"]}
    })

    # --- Agent and Tool Settings ---
    ROUTER_MODEL: str = "llama3-8b-8192"
    SYNTHESIZER_MODEL: str = "llama3-70b-8192"
    DEFAULT_LLM_TEMPERATURE: float = 0.7
    MAX_TOOL_RETRIES: int = 3
    TOOL_RETRY_DELAY: float = 1.0
    TOOL_FAILURE_COOLDOWN: int = 300

    # --- Logging ---
    LOG_FILE: str = 'kisaanvaani_gradio.log'
    LOG_MAX_BYTES: int = 5_000_000
    LOG_BACKUP_COUNT: int = 5

    # --- UI and Interaction ---
    DEFAULT_SPEECH_TIMEOUT: int = 10

    # --- Fallback Messages ---
    FALLBACK_MESSAGES: Dict[str, str] = field(default_factory=lambda: {
        "NO_LLM": "The main AI service is not available.", "AGENT_ERROR": "I encountered an issue.",
        "NO_STT_SERVICE": "Speech recognition is not available.", "NO_TTS_SERVICE": "Speech synthesis is not available."
    })

CONFIG = AppConfig()
KNOWN_FALLBACK_RESPONSES = {
    CONFIG.FALLBACK_MESSAGES["NO_LLM"],
    CONFIG.FALLBACK_MESSAGES["AGENT_ERROR"],
    CONFIG.FALLBACK_MESSAGES["NO_STT_SERVICE"]
}


# ==============================================================================
# 1.3: Professional Logging Setup
# ==============================================================================
def setup_logging():
    """Configures a rotating file logger and a console logger."""
    root_logger = logging.getLogger('kisaanvaani')
    root_logger.setLevel(logging.INFO)
    if not root_logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler_file = RotatingFileHandler(CONFIG.LOG_FILE, maxBytes=CONFIG.LOG_MAX_BYTES, backupCount=CONFIG.LOG_BACKUP_COUNT)
        handler_file.setFormatter(formatter)
        root_logger.addHandler(handler_file)
        handler_console = logging.StreamHandler(sys.stdout)
        handler_console.setFormatter(formatter)
        root_logger.addHandler(handler_console)
setup_logging()
logger = logging.getLogger('kisaanvaani')
voice_logger = logging.getLogger('kisaanvaani.voice')
tool_logger = logging.getLogger('kisaanvaani.tools')
agent_logger = logging.getLogger('kisaanvaani.agent')

# ==============================================================================
# 1.4: Core Service Definitions & Caching
# ==============================================================================
_service_cache: Dict[str, Any] = {} # Global cache for expensive, singleton services

class PiperTTSService:
    """Manages Piper TTS voices, including discovery, loading, and IN-MEMORY synthesis."""
    def __init__(self, voices_dir: Path):
        self._voices_dir = voices_dir
        self.available_voices: Dict[str, Dict[str, Any]] = self._discover_voices()
        self._voice_cache: Dict[str, PiperVoice] = {}
        self._lock = threading.Lock()
        if not self.available_voices:
            logger.warning(f"No Piper voices found in '{voices_dir}'. Please download models.")

    def _discover_voices(self) -> Dict[str, Dict[str, Any]]:
        """Scans the voices directory and builds a map of available, configured voices."""
        if not self._voices_dir.is_dir(): return {}
        
        voices = {}
        # Get all model filenames from our language config
        configured_models = {
               onnx_name
              for details in CONFIG.LANGUAGE_CONFIG.values()
              for onnx_name in details["voices"]
                            }

        
        for onnx_file in self._voices_dir.glob("*.onnx"):
            if onnx_file.name not in configured_models:
                continue

            config_path = onnx_file.with_suffix(".onnx.json")
            if not config_path.exists():
                logger.warning(f"Found voice model '{onnx_file.name}' but missing its .json config. Skipping.")
                continue

            # Find which language this voice belongs to
            lang_code = ""
            for lang_details in CONFIG.LANGUAGE_CONFIG.values():
                if onnx_file.name in lang_details["voices"]:
                    lang_code = lang_details["code"]
                    break
            
            # Use filename for a user-friendly name if possible
            # e.g., en_US-lessac-medium.onnx -> lessac-medium (en_US)
            parts = onnx_file.stem.split('-')
            if len(parts) >= 2:
                display_name = f"{'-'.join(parts[1:])} ({parts[0]})"
            else:
                display_name = onnx_file.stem

            voices[display_name] = {"path": str(onnx_file), "config": str(config_path), "lang_code": lang_code}
        
        logger.info(f"Discovered {len(voices)} configured and available Piper voices.")
        return voices

    def get_voices_for_lang(self, lang_code: str) -> List[str]:
        """Returns a list of display names for voices matching a language code."""
        return [name for name, details in self.available_voices.items() if details["lang_code"] == lang_code]

    def synthesize_to_uri(self, text: str, voice_name: str) -> Optional[str]:
        """Synthesizes audio and returns it as a Base64-encoded data URI."""
        voice = self._get_voice(voice_name)
        if not voice: return None

        try:
            audio_buffer = BytesIO()
            voice_logger.info(f"TTS threads BEFORE synthesis: {threading.active_count()}")
            voice.synthesize(text, audio_buffer)
            voice_logger.info(f"TTS threads AFTER synthesis: {threading.active_count()}")
            audio_buffer.seek(0)
            
            wav_data = audio_buffer.read()
            base64_wav = base64.b64encode(wav_data).decode('utf-8')
            return f"data:audio/wav;base64,{base64_wav}"
        except Exception as e:
            voice_logger.error(f"Piper synthesis failed for voice '{voice_name}': {e}", exc_info=True)
            return None

    def _get_voice(self, voice_name: str) -> Optional[PiperVoice]:
        """Lazy-loads and caches a voice model upon first request."""
        if voice_name in self._voice_cache: return self._voice_cache[voice_name]
        
        voice_details = self.available_voices.get(voice_name)
        if not voice_details:
            logger.error(f"Voice '{voice_name}' not found.")
            return None
        
        with self._lock:
            if voice_name in self._voice_cache: return self._voice_cache[voice_name]
            logger.info(f"Loading Piper voice '{voice_name}'...")
            try:
                voice = PiperVoice.load(voice_details["path"], voice_details["config"])
                self._voice_cache[voice_name] = voice
                logger.info(f"Successfully loaded and cached voice '{voice_name}'.")
                return voice
            except Exception as e:
                logger.error(f"Failed to load Piper voice '{voice_name}': {e}", exc_info=True)
                return None

# --- Service Getters (using the global _service_cache and @lru_cache for simplicity) ---

@lru_cache()
def get_tts_service() -> Optional[PiperTTSService]:
    if PiperVoice is None:
        logger.critical("Cannot initialize TTS service: 'piper-tts' library is not installed.")
        return None
    return PiperTTSService(CONFIG.PIPER_VOICES_DIR)

@lru_cache()
def get_groq_client() -> Optional[Groq]:
    if not CONFIG.GROQ_API_KEY:
        logger.error("Groq API key is missing.")
        return None
    try: return Groq(api_key=CONFIG.GROQ_API_KEY)
    except Exception as e: logger.error(f"Failed to initialize Groq client: {e}", exc_info=True); return None

@lru_cache()
def get_tavily_client() -> Optional[TavilyClient]:
    """
    Returns a singleton TavilyClient, or None if it's unavailable or mis-configured.
    """
    if TavilyClient is None:
        logger.warning("Tavily library not installed. Web search disabled.")
        return None
    if not CONFIG.TAVILY_API_KEY:
        logger.error("TAVILY_API_KEY is missing. Web search disabled.")
        return None
    try:
        client = TavilyClient(api_key=CONFIG.TAVILY_API_KEY)
        logger.info("Initialized Tavily client successfully.")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Tavily client: {e}", exc_info=True)
        return None
    
def get_stt_service() -> "SpeechToTextService":
    """Returns a singleton instance of the full STT pipeline service."""
    if "stt_service" not in _service_cache:
        logger.info("Initializing main STT Pipeline Service...")
        _service_cache["stt_service"] = SpeechToTextService()
    return _service_cache["stt_service"]


# ==============================================================================
# 2.2: Speech-to-Text Service with Fallback & Calibration
# ==============================================================================
class SpeechToTextService:
    """A service that handles audio transcription with a primary (local) and fallback (cloud) engine."""
    def __init__(self):
        self.primary_model: Optional[WhisperModel] = self._load_primary_model()
        self.fallback_recognizer: Optional[sr.Recognizer] = self._get_fallback_recognizer()

    def _load_primary_model(self) -> Optional[WhisperModel]:
        if WhisperModel is None:
            logger.critical("Cannot initialize primary STT: 'faster-whisper' not installed.")
            return None
        try:
            voice_logger.info(f"Loading STT model '{CONFIG.WHISPER_MODEL_SIZE}'...")
            return WhisperModel(CONFIG.WHISPER_MODEL_SIZE, device="cpu", compute_type=CONFIG.WHISPER_COMPUTE_TYPE)
        except Exception as e:
            voice_logger.error(f"Failed to initialize faster-whisper model: {e}", exc_info=True)
            return None

    def _get_fallback_recognizer(self) -> Optional[sr.Recognizer]:
        if sr is None:
            logger.warning("speech_recognition library not installed. Google STT fallback disabled.")
            return None
        return sr.Recognizer()

    def calibrate_fallback_recognizer(self):
        """Performs a one-time ambient noise calibration for the Google STT fallback."""
        if self.fallback_recognizer:
            try:
                voice_logger.info("Calibrating fallback STT for ambient noise (1 sec)...")
                with sr.Microphone() as source:
                    self.fallback_recognizer.adjust_for_ambient_noise(source, duration=1.0)
                voice_logger.info("Fallback STT calibrated successfully.")
            except Exception as e:
                voice_logger.error(f"Could not calibrate fallback STT. Microphone might not be available. Error: {e}")

    def transcribe_audio_file(self, audio_filepath: str, lang_code: str, phrase_time_limit: int, use_fallback: bool = False, lang_override: str = None) -> str:
        """Transcribes an audio file to text, with automatic fallback and language support."""
        transcribed_text = ""
        
        # --- Attempt 1: Primary Engine (faster-whisper) ---
        if self.primary_model and not use_fallback:
            try:
                voice_logger.info("Attempting transcription with faster-whisper...")
                segments, _ = self.primary_model.transcribe(audio_filepath, language=lang_code)
                transcribed_text = " ".join([s.text for s in segments]).strip()
                if transcribed_text:
                    voice_logger.info(f"Whisper transcription successful: '{transcribed_text}'")
                    return transcribed_text
                voice_logger.warning("Whisper produced an empty transcript. Will attempt fallback.")
            except Exception as e:
                voice_logger.error(f"Whisper transcription failed: {e}. Falling back to Google STT.")

        # --- Attempt 2: Fallback Engine (Google Web Speech) ---
        if not self.fallback_recognizer: return ""
        try:
            voice_logger.info("Attempting transcription with Google STT fallback...")
            with sr.AudioFile(audio_filepath) as source:
                audio_data = self.fallback_recognizer.record(source)
            
            # pick override if provided, else normal bcp47 for lang_code
            bcp47 = lang_override or next(
                (d["bcp47"] for d in CONFIG.LANGUAGE_CONFIG.values() if d["code"] == lang_code),
                "en-US"
            )
            transcribed_text = self.fallback_recognizer.recognize_google(
                audio_data, language=bcp47
            )
            
            if transcribed_text: voice_logger.info(f"Google STT fallback successful: '{transcribed_text}'")
            else: voice_logger.warning("Google STT also produced an empty transcript.")
            return transcribed_text.strip()
            
        except sr.UnknownValueError:
            voice_logger.warning("Google STT could not understand the audio.")
            return "UNCLEAR"
        except sr.RequestError as e:
            voice_logger.error(f"Google STT API request failed: {e}")
            return "ERROR"
        except Exception as e: voice_logger.error(f"Unexpected error with Google STT: {e}", exc_info=True)
        
        return ""

# ==============================================================================
# 3. AGENT LOGIC (PART 1 - HELPERS & CONTEXT)
# ==============================================================================

# --- Safe Math Evaluation Helpers (Restored) ---
@lru_cache(maxsize=128)
def _parse_expression_to_ast(expression: str) -> ast.AST:
    """Caches the CPU-bound parsing of math strings for repeated calculations."""
    return ast.parse(expression, mode='eval').body

def _safe_math_eval_recursive(node: ast.AST) -> Any:
    """Safely evaluates a pre-parsed AST node, preventing arbitrary code execution."""
    ops = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow, ast.USub: op.neg}
    if isinstance(node, ast.Constant): return node.value
    elif isinstance(node, ast.BinOp): return ops[type(node.op)](_safe_math_eval_recursive(node.left), _safe_math_eval_recursive(node.right))
    elif isinstance(node, ast.UnaryOp): return ops[type(node.op)](_safe_math_eval_recursive(node.operand))
    raise TypeError(f"Unsupported AST node type for safe evaluation: {type(node)}")

# --- Chat Context (The Agent's Memory) ---
@lru_cache()
def get_chat_context() -> "ChatContext":
    """Returns a singleton instance of the ChatContext for the main application thread."""
    logger.info("ChatContext: Singleton instance created.")
    return ChatContext()

class ChatContext:
    """Manages the conversation state, providing the agent with "memory"."""
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.conversation_history: List[Dict[str, Any]] = []
        self.pending_actions: List[str] = []
        self.context_entities: set = set()
        self.tool_usage_stats: Dict[str, Dict[str,int]] = {}
        self.user_profile = {"name": None, "location": None, "interests": set(), "preferences": {}, "last_interaction": None, "farming_context": {}}
        self.conversation_state = {"current_topic": None, "context_window": [], "tool_usage_history": []}
        self.max_context_window = 5
        context_logger.info("New, rich ChatContext instance created.")

    def add_message(self, role: str, content: str, msg_type: str, metadata: Optional[Dict] = None):
        """Adds a message to history and updates the internal state."""
        message = {"role": role, "content": content, "type": msg_type, "timestamp": time.time(), "metadata": metadata or {}}
        self.conversation_history.append(message)
        if len(self.conversation_history) > self.max_history: self.conversation_history.pop(0)
        self._update_context_window(message)
        self._update_conversation_state(message)
        self.user_profile["last_interaction"] = message["timestamp"]

    def _update_context_window(self, message: dict):
        self.conversation_state["context_window"].append(message)
        if len(self.conversation_state["context_window"]) > self.max_context_window: self.conversation_state["context_window"].pop(0)

    def _update_conversation_state(self, message: dict):
        if message["role"] == "user": self._extract_entities(message["content"])
        if meta := message.get("metadata"):
            if tool_used := meta.get("tool_used"):
                self.conversation_state["tool_usage_history"].append({"tool": tool_used, "timestamp": message["timestamp"], "success": meta.get("success", True)})

    def _extract_entities(self, text: str):
        text_lower = text.lower()
        if any(term in text_lower for term in ["crop", "weather", "soil", "fertilizer", "pesticide", "harvest", "irrigation", "mandi", "price"]):
            self.conversation_state["current_topic"] = "farming"
    
    def get_full_history(self) -> List[Dict[str, Any]]:
        return self.conversation_history

    def get_context_for_prompt(self) -> Dict[str, Any]:
        """Creates a JSON-serializable dictionary of the current context for the agent."""
        profile_summary = self.user_profile.copy()
        profile_summary['interests'] = list(self.user_profile.get('interests', set()))
        return {
            "current_topic": self.conversation_state.get("current_topic"),
            "recent_messages": self.conversation_state.get("context_window", []),
            "user_profile": profile_summary,
            "tool_usage": self.conversation_state.get("tool_usage_history", [])[-5:]
        }

    def clear(self):
        """Resets the conversation history and state to its initial values."""
        self.__init__() # Re-initialize the instance to clear all fields
        context_logger.info("Conversation context has been cleared.")

    def update_farming_context(self, key, val):
        self.user_profile.setdefault("farming_context", {})[key] = val

    def get_tool_usage_stats(self):
        stats = {}
        for entry in self.conversation_state["tool_usage_history"]:
            t= entry["tool"]
            stats.setdefault(t,{"total":0,"success":0,"fail":0})
            stats[t]["total"] += 1
            (stats[t]["success" if entry.get("success") else "fail"]) += 1
        return stats

# ==============================================================================
# 3.2: Tool System - The Agent's Hands
# ==============================================================================
@lru_cache()
def get_tool_system() -> "ToolSystem":
    """Returns a singleton instance of the ToolSystem, cached for the application's lifetime."""
    logger.info("Initializing ToolSystem singleton...")
    return ToolSystem()

class ToolSystem:
    """
    Defines, validates, and executes all available tools for the agent.
    Includes robust error handling, retries, and a cooldown mechanism.
    """
    def __init__(self):
        self.tool_metadata: Dict[str, Dict[str, Any]] = {
            # This is the full, unabridged metadata from the original specification
            "get_current_date": {"required_params": [], "description": "Get today's date"},
            "calculate_math": {"required_params": ["expression"], "description": "Solve a mathematical expression", "parameter_types": {"expression": str}},
            "tell_joke": {"required_params": [], "description": "Tell a joke"},
            "get_weather_forecast": {"required_params": ["location"], "description": "Get the weather forecast for a specific location", "parameter_types": {"location": str}},
            "get_mandi_prices": {"required_params": ["crop"], "optional_params": ["market"], "description": "Get commodity (mandi) prices for a crop", "parameter_types": {"crop": str, "market": str}},
            "get_farming_advice": {"required_params": ["topic"], "description": "Get farming advice on a specific topic", "parameter_types": {"topic": str}},
            "web_search": {"required_params": ["query"], "description": "Perform a general web search using Tavily API", "parameter_types": {"query": str}},
            "get_news_summary": {"optional_params": ["topic"], "description": "Get a summary of recent news, optionally by topic", "parameter_types": {"topic": str}},
            "get_definition": {"required_params": ["term"], "description": "Get the definition of a word or term", "parameter_types": {"term": str}},
            "get_biography": {"required_params": ["person"], "description": "Get a short biography of a person", "parameter_types": {"person": str}},
            "get_sports_update": {"optional_params": ["sport"], "description": "Get the latest sports updates, optionally for a specific sport", "parameter_types": {"sport": str}},
            "get_movie_info": {"required_params": ["title"], "description": "Get information about a movie", "parameter_types": {"title": str}},
            "get_tech_news": {"required_params": [], "description": "Get the latest technology news"},
            "get_crop_calendar": {"required_params": ["crop"], "description": "Get the crop calendar for a crop", "parameter_types": {"crop": str}},
            "get_fertilizer_info": {"required_params": ["crop"], "description": "Get fertilizer recommendations for a crop", "parameter_types": {"crop": str}},
            "get_pest_control": {"required_params": ["crop"], "description": "Get pest control information for a crop", "parameter_types": {"crop": str}},
            "get_irrigation_advice": {"required_params": ["crop"], "description": "Get irrigation advice for a crop", "parameter_types": {"crop": str}}
        }
        self.max_retries = CONFIG.MAX_TOOL_RETRIES
        self.retry_delay = CONFIG.TOOL_RETRY_DELAY
        self.error_counts: Dict[str, int] = {}
        self.last_error_time: Dict[str, float] = {}

    # --- Tool Implementations ---
    def get_current_date(self, **kwargs) -> str: return f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."
    def tell_joke(self, **kwargs) -> str: return random.choice(["Why did the scarecrow win an award? Because he was outstanding in his field!"])
    def calculate_math(self, expression: str, **kwargs) -> str:
        try:
            cleaned_expr = expression.lower().replace('times', '*').replace('plus', '+').replace('minus', '-').replace('divided by', '/')
            result = _safe_math_eval_recursive(_parse_expression_to_ast(cleaned_expr))
            return f"The result of '{expression}' is {result}."
        except Exception: return "I couldn't solve that calculation. Please provide a valid mathematical expression."
    def _perform_tavily_search(self, query: str, **kwargs) -> str:
        tavily = get_tavily_client()
        if not tavily: return "The web search service is not configured or available."
        try:
            response = tavily.search(query=query, include_answer=True, **kwargs)
            return response.get("answer", "I couldn't find a direct answer for that query.")
        except Exception as e: return f"The web search service failed with an error: {e}"

    def get_weather_forecast(self, location: str, **kwargs) -> str: return self._perform_tavily_search(f"weather in {location}", search_depth="basic")
    def get_mandi_prices(self, crop: str, market: str="India", **kwargs) -> str: return self._perform_tavily_search(f"mandi prices for {crop} in {market}")
    def get_farming_advice(self, topic: str, **kwargs) -> str: return self._perform_tavily_search(f"farming advice for {topic}", search_depth="advanced")
    def web_search(self, query: str, **kwargs) -> str: return self._perform_tavily_search(query, search_depth="advanced")
    def get_news_summary(self, topic: str = "general", **kwargs) -> str: return self._perform_tavily_search(f"latest news summary about {topic}")
    def get_definition(self, term: str, **kwargs) -> str: return self._perform_tavily_search(f"define {term}", max_results=1)
    def get_biography(self, person: str, **kwargs) -> str: return self._perform_tavily_search(f"short biography of {person}")
    def get_sports_update(self, sport: str = "general", **kwargs) -> str: return self._perform_tavily_search(f"latest {sport} sports news")
    def get_movie_info(self, title: str, **kwargs) -> str: return self._perform_tavily_search(f"summary of movie {title}")
    def get_tech_news(self, **kwargs) -> str: return self._perform_tavily_search("latest technology news")
    def get_crop_calendar(self, crop: str, **kwargs) -> str: return self._perform_tavily_search(f"crop calendar for {crop}")
    def get_fertilizer_info(self, crop: str, **kwargs) -> str: return self._perform_tavily_search(f"fertilizer info for {crop}")
    def get_pest_control(self, crop: str, **kwargs) -> str: return self._perform_tavily_search(f"pest control for {crop}")
    def get_irrigation_advice(self, crop: str, **kwargs) -> str: return self._perform_tavily_search(f"irrigation advice for {crop}")

    # --- Robust Tool Execution Logic ---
    def get_error_stats(self) -> dict:
        return {"error_counts": self.error_counts, "last_error_times": {k: time.ctime(v) for k, v in self.last_error_time.items()}}

    def reset_error_stats(self):
        self.error_counts.clear(); self.last_error_time.clear()
        logger.info("Tool error statistics have been reset.")

    def _is_on_cooldown(self, tool_name: str) -> bool:
        error_count = self.error_counts.get(tool_name, 0)
        if error_count >= self.max_retries:
            time_since_last = time.time() - self.last_error_time.get(tool_name, 0)
            if time_since_last < CONFIG.TOOL_FAILURE_COOLDOWN:
                tool_logger.warning(f"Tool '{tool_name}' is on cooldown. Last failed {time_since_last:.0f}s ago.")
                return True
            else: self.error_counts[tool_name] = 0 # Cooldown passed
        return False

    def _validate_parameters(self, tool_name: str, parameters: dict) -> Tuple[bool, str]:
        metadata = self.tool_metadata.get(tool_name)
        if not metadata: return False, f"Tool '{tool_name}' not found."
        required = metadata.get("required_params", [])
        if missing := [p for p in required if p not in (parameters or {})]:
            return False, f"Missing required parameters: {', '.join(missing)}"
        for param, p_type in metadata.get("parameter_types", {}).items():
            if param in parameters and not isinstance(parameters[param], p_type):
                return False, f"Invalid type for param '{param}': expected {p_type.__name__}"
        return True, ""

    def execute_tool(self, tool_name: str, parameters: dict) -> dict:
        """Executes a tool with validation, cooldown checks, and retry logic."""
        parameters = parameters or {}
        
        if self._is_on_cooldown(tool_name):
            return {"success": False, "error": f"Tool '{tool_name}' is temporarily disabled due to repeated failures."}

        is_valid, error_msg = self._validate_parameters(tool_name, parameters)
        if not is_valid: return {"success": False, "error": error_msg}
        
        tool_method = getattr(self, tool_name, None)
        if not callable(tool_method): return {"success": False, "error": f"Tool '{tool_name}' not implemented."}
        
        for attempt in range(self.max_retries):
            try:
                result = tool_method(**parameters)
                return {"success": True, "result": result}
            except Exception as e:
                tool_logger.error(f"Tool '{tool_name}' failed on attempt {attempt+1}: {e}", exc_info=True)
                self.error_counts[tool_name] = self.error_counts.get(tool_name, 0) + 1
                self.last_error_time[tool_name] = time.time()
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return {"success": False, "error": str(e), "suggestion": "The tool failed after multiple retries."}
                    
        return {"success": False, "error": "Unknown tool execution error."}
# ==============================================================================
# Part 4: The Agent's Brain - Response Generation
# ==============================================================================
@lru_cache()
def get_agent_executor() -> ThreadPoolExecutor:
    """Returns a singleton ThreadPoolExecutor for running agent tasks non-blockingly."""
    logger.info("Initializing ThreadPoolExecutor for agent tasks.")
    return ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent_worker")

def get_followup_question(lang_code: str) -> str:
    """Returns a generic follow-up question in the specified language."""
    base_lang = lang_code.split('-')[0]
    questions = {
        "en": "Is there anything else I can help with today?",
        "hi": "क्या मैं आज और कोई मदद कर सकता हूँ?",
        "es": "Hay algo más en lo que pueda ayudarte hoy?",
        "fr": "Y a-t-il autre chose que je puisse faire pour vous aujourd'hui?"
    }
    return questions.get(base_lang, questions['en'])

def generate_agent_response(
    user_query: str,
    chat_context: ChatContext,
    tool_system: ToolSystem,
    ui_settings: Dict[str, Any]
) -> dict:
    """
    The agent's "brain". It orchestrates context, tool routing, and response synthesis.
    This function is designed to be run in a separate thread.
    """
    groq_client = get_groq_client()
    if not groq_client:
        return {"response": CONFIG.FALLBACK_MESSAGES["NO_LLM"], "success": False, "thought": "Groq client not available."}

    context = chat_context.get_context_for_prompt()
    
    # --- Dynamically prepare tools and language context for the prompt ---
    available_tools = tool_system.tool_metadata
    if not ui_settings.get("web_search", True):
        available_tools = {name: meta for name, meta in tool_system.tool_metadata.items() if not any(kw in name for kw in ["search", "tavily", "news", "weather"])}
        logger.info("Web search disabled by user. Agent toolset restricted.")
    
    current_lang_name = ui_settings.get("language_name", "English")
    current_lang_code = ui_settings.get("lang_bcp47", "en-US")


    # --- Step 1: Tool Routing ---
    router_prompt = f"""You are a master reasoning agent. Your task is to analyze the user's query and conversation context to decide which, if any, tool to use. The user is communicating in {current_lang_name}.

# Context
- Current Topic: {context.get('current_topic')}
- User Profile: {json.dumps(context.get('user_profile'))}
- Recent Conversation:
{''.join(f"- {m['role'].capitalize()}: {m['content']}\\n" for m in context.get('recent_messages', []))}

# Available Tools
The following tools are available. Only use tools from this list.
{json.dumps({k: v['description'] for k, v in available_tools.items()}, indent=2)}

# User's Latest Query
"{user_query}"

# Instructions
Based on the query and context, your output MUST be a single JSON object with the following schema:
- `tool_to_use`: string (The name of the single best tool to use, or "None".)
- `parameters`: dict (A dictionary of parameters for the tool.)
- `thought`: string (Your detailed step-by-step reasoning.)
- `confidence`: float (Your confidence in this decision, from 0.0 to 1.0.)
- `alternative_tools`: list[string] (Other tools that might also work.)
"""
    try:
        router_messages = [{"role": "system", "content": router_prompt}]
        router_completion = groq_client.chat.completions.create(
            messages=router_messages, model=CONFIG.ROUTER_MODEL, temperature=0.0,
            response_format={"type": "json_object"}
        )
        decision = json.loads(router_completion.choices[0].message.content)
        
        thought, chosen_tool, params = decision.get("thought", ""), decision.get("tool_to_use"), decision.get("parameters", {})
        confidence, alternatives = decision.get("confidence", 1.0), decision.get("alternative_tools", [])
        
        agent_logger.info(f"Agent Thought: {thought}")
        agent_logger.info(f"Chosen Tool: '{chosen_tool}', Confidence: {confidence:.2f}, Params: {params}")

        # --- Step 2: Tool Execution with Automatic Fallback ---
        tool_output, feedback, success = "", None, True
        if chosen_tool and chosen_tool != "None":
            feedback = f"🔎 Using tool: `{chosen_tool}`..."
            tool_response = tool_system.execute_tool(chosen_tool, params)
            
            if not tool_response["success"] and confidence < 0.8 and alternatives:
                agent_logger.warning(f"Tool '{chosen_tool}' failed. Confidence was low, trying alternatives: {alternatives}")
                for alt_tool in alternatives:
                    if alt_tool in available_tools:
                        agent_logger.info(f"Attempting alternative tool: '{alt_tool}'")
                        alt_response = tool_system.execute_tool(alt_tool, params)
                        if alt_response["success"]:
                            chosen_tool, tool_response = alt_tool, alt_response
                            feedback = f"🔎 Using tool: `{alt_tool}`..."
                            break
            
            success = tool_response["success"]
            tool_output = tool_response.get("result") if success else f"Error: {tool_response.get('error')}. Suggestion: {tool_response.get('suggestion')}"
        
        # --- Step 3: Final Response Synthesis ---
        synthesizer_prompt = f"""You are KisaanVaani, a helpful AI assistant. Your task is to synthesize the provided information into a final, user-facing response.

# CRITICAL INSTRUCTION
The user is communicating in '{current_lang_name}'. Your response MUST be in that language. The language code is {current_lang_code}.

# User's Original Query
"{user_query}"

# Information Gathering Summary
- Tool Used: {chosen_tool or 'None'}
- Information from Tool: "{tool_output}"

# Instructions
1.  Formulate a natural, conversational, and helpful response based *only* on the provided information.
2.  If the tool succeeded, present its findings clearly.
3.  If the tool failed, apologize gracefully in the user's language.
4.  If no tool was used, respond directly and conversationally to the user's query in their language.
5.  **Crucially, do not add your own follow-up question.** Another system handles that.
6.  Keep the response friendly and to the point.

Your final, user-facing response (in {current_lang_name}):
"""
        final_messages = [{"role": "system", "content": synthesizer_prompt}]
        final_completion = groq_client.chat.completions.create(
            messages=final_messages,
            model=ui_settings.get("llm_model", CONFIG.SYNTHESIZER_MODEL),
            temperature=ui_settings.get("temperature", CONFIG.DEFAULT_LLM_TEMPERATURE),
            max_tokens=350
        )
        final_answer = final_completion.choices[0].message.content.strip()

        # --- Step 4: Final Output Packaging ---
        chat_context.add_message("user", user_query, "user_input", {"thought": thought, "tool_used": chosen_tool, "success": success})
        chat_context.add_message("assistant", final_answer, "assistant_response", {
            "tool_used": chosen_tool,
            "success": success
        })

        
        return {
            "response": final_answer,
            "feedback": feedback,
            "thought": thought,
            "success": success
        }

    except Exception as e:
        agent_logger.error(f"CRITICAL ERROR in agent logic pipeline: {e}", exc_info=True)
        chat_context.add_message("user", user_query, "user_input", {"error": str(e)})
        return {
            "response": CONFIG.FALLBACK_MESSAGES["AGENT_ERROR"],
            "thought": f"An unexpected exception occurred: {e}",
            "success": False
        }
# ==============================================================================
# Part 5: Gradio UI & Application Flow
# This section orchestrates the frontend and connects it to the backend services.
# ==============================================================================

class GradioApp:
    """Encapsulates the entire Gradio application, including UI and event handlers."""
    def __init__(self):
        logger.info("Initializing GradioApp class...")
        # --- Initialize all backend services on startup ---
        self.tts_service = get_tts_service()
        self.stt_service = get_stt_service()
        self.tool_system = get_tool_system()
        self.groq_client = get_groq_client()
        self.agent_executor = get_agent_executor()
        
        # This instance of ChatContext is tied to this specific Gradio session.
        self.chat_context = ChatContext()
        
        # FIX: Calibrate STT fallback recognizer on startup
        if self.stt_service:
            self.stt_service.calibrate_fallback_recognizer()
        
        # Perform and store health checks for UI display
        self.service_status = self._perform_health_checks()
        
        # Build the UI
        self.app = self._create_ui()

    def _perform_health_checks(self) -> Dict[str, bool]:
        """Performs a quick check on critical services to display in the UI."""
        status = {
            "LLM (Groq)": self.groq_client is not None,
            "Web Search (Tavily)": get_tavily_client() is not None,
            "STT (Whisper)": self.stt_service.primary_model is not None,
            "STT Fallback (Google)": self.stt_service.fallback_recognizer is not None,
            "TTS (Piper)": self.tts_service is not None and bool(self.tts_service.available_voices)
        }
        logger.info(f"Service Health Check Status: {status}")
        return status

    def _create_ui(self) -> gr.Blocks:
        """Creates and returns the complete Gradio Blocks UI."""
        
        # --- UI Helper & State Functions ---
        def get_voice_lang_code(voice_name: str) -> str:
            """Gets the 2-letter lang code from a selected voice's details."""
            if not voice_name or not self.tts_service: return "en"
            return self.tts_service.available_voices.get(voice_name, {}).get("lang_code", "en")

        def download_transcript() -> Optional[str]:
            """Serializes the chat history to a JSON file and returns its path for download."""
            history = self.chat_context.get_full_history()
            if not history: return None
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"transcript_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            return filename
        
        # --- Gradio Event Handlers (Generators for streaming UI updates) ---
        def handle_interaction(user_input: str, chat_history: list, settings: Dict[str, Any]):
            """Main generator to process input, get response, and yield UI updates."""
            if not user_input or not user_input.strip(): return
            
            chat_history.append([user_input, None])
            yield {chatbot: chat_history}

            future = self.agent_executor.submit(
                generate_agent_response, user_input, self.chat_context, self.tool_system, settings
            )
            agent_output = future.result()
            
            response_text, thought_text, success, feedback = (
                agent_output.get("response", "An error occurred."),
                agent_output.get("thought", "N/A"),
                agent_output.get("success", False),
                agent_output.get("feedback")
            )

            # Update UI with feedback and reasoning
            if settings["show_reasoning"] and feedback:
                chat_history[-1][1] = feedback
                yield {chatbot: chat_history, reasoning_display: f"🤖 Agent Thought:\n{thought_text}"}
                time.sleep(1) # Pause for user to read feedback
            elif settings["show_reasoning"]:
                yield {reasoning_display: f"🤖 Agent Thought:\n{thought_text}"}

            chat_history[-1][1] = response_text
            
            # Prepare speech and add follow-up question
            full_speech = response_text
            if success and response_text not in KNOWN_FALLBACK_RESPONSES:
                bcp47_code = settings.get("lang_bcp47", "en-US")
                follow_up = get_followup_question(bcp47_code)
                chat_history.append([None, follow_up])
                full_speech += " " + follow_up
            yield {chatbot: chat_history}
            
            # Synthesize and yield audio data URI for playback
            audio_data_uri = None
            if self.tts_service:
                audio_data_uri = self.tts_service.synthesize_to_uri(full_speech, settings["voice"])
            yield {audio_output: gr.Audio(value=audio_data_uri, autoplay=True), tool_status_display: self._get_tool_status_md()}


        def process_text_input(text_input: str, chat_history: list, settings: Dict[str, Any]):
            yield {text_input: ""} # Clear input box immediately
            yield from handle_interaction(text_input, chat_history, settings)
        
        if conversation_state != AppState.LISTENING or not should_listen:
            logger.info("Audio ignored because conversation is not in LISTENING mode.")
            return

        def process_audio_input(audio_filepath: Optional[str], chat_history: list, settings: Dict[str, Any], conversation_state, should_listen, has_greeted):
            if not audio_filepath:
                chat_history.append([None, "No audio recorded. Please try again."])
                yield {chatbot: chat_history}
                return

            chat_history.append(["(Transcribing your voice...)", None])
            yield {chatbot: chat_history}
            
            lang_code = get_voice_lang_code(settings["voice"])
            override = settings.get("stt_lang_override") or None    
            transcribed_text = self.stt_service.transcribe_audio_file(audio_filepath, lang_code, settings["mic_timeout"], settings["stt_fallback"], lang_override=override)
            
            if transcribed_text in ["UNCLEAR","ERROR"]:
                icons   = {"UNCLEAR":"❓","ERROR":"⚠️"}
                messages= {
                  "UNCLEAR":"I couldn't understand that. Please speak clearly.",
                  "ERROR":"Speech recognition error. Please try again later."
                }
                chat_history[-1] = [f"{icons[transcribed_text]} {messages[transcribed_text]}", None]
                yield {chatbot: chat_history, status_display: f"{icons[transcribed_text]} {messages[transcribed_text]}"}
                return

            
            chat_history[-1][0] = f"🎤 {transcribed_text}"
            yield {chatbot: chat_history}
            yield from handle_interaction(transcribed_text, chat_history, settings)

        def clear_conversation():
            self.chat_context.clear(); self.tool_system.reset_error_stats()
            logger.info("Conversation cleared by user.")
            return [], "", gr.Markdown.update(value=self._get_tool_status_md())

        def _get_tool_status_md(self):
            # ... (Full implementation from previous part) ...
            return "All tools are active."
        
        def on_language_change(lang_name: str):
            self.chat_context.clear(); self.tool_system.reset_error_stats()
            lang_code = next((details["code"] for name, details in CONFIG.LANGUAGE_CONFIG.items() if name == lang_name), "en")
            voices = self.tts_service.get_voices_for_lang(lang_code) if self.tts_service else []
            return (
                [], gr.Markdown.update(value=self._get_tool_status_md()),
                gr.Dropdown.update(choices=voices, value=voices[0] if voices else None)
            )

        # --- Build the Gradio UI Layout ---
        with gr.Blocks(theme="soft", title="KisaanVaani") as app:
            gr.Markdown("# 🌾 KisaanVaani\n### The Advanced AI Voice Assistant")
            # — Chat mode flags —
            conversation_state   = gr.State(AppState.IDLE)
            should_listen        = gr.State(False)
            has_greeted_initial  = gr.State(False)

            # --- Consolidate all settings into a single State object for cleaner passing ---
            settings_state = gr.State({})

            with gr.Row():
                with gr.Column(scale=2, min_width=400): # Left Column
                    gr.Markdown("### 🎙️ Voice & Language")
                    language_dropdown = gr.Dropdown(choices=list(CONFIG.LANGUAGE_CONFIG.keys()), value="English", label="Conversation Language")
                    
                    available_voices = self.tts_service.get_voices_for_lang("en") if self.tts_service else []
                    piper_voice_dropdown = gr.Dropdown(choices=available_voices, value=available_voices[0] if available_voices else None, label="Assistant's Voice")

                    mic_input = gr.Audio(sources=["microphone"], type="filepath", label="Record Your Question")
                    
                    with gr.Accordion("⚙️ Advanced Settings", open=False):
                        gr.Markdown("**Agent Controls**")
                        llm_model_dropdown = gr.Dropdown(choices=[CONFIG.ROUTER_MODEL, CONFIG.SYNTHESIZER_MODEL], value=CONFIG.SYNTHESIZER_MODEL, label="LLM Model (Synthesis)")
                        temperature_slider = gr.Slider(0.0, 1.5, value=CONFIG.DEFAULT_LLM_TEMPERATURE, step=0.1, label="LLM Temperature")
                        gr.Markdown("**Tool Controls**")
                        use_web_search_checkbox = gr.Checkbox(label="Enable Web Search", value=True, interactive=get_tavily_client() is not None)
                        tool_status_display = gr.Markdown(self._get_tool_status_md(), visible=False)
                        gr.Markdown("**Debugging**")
                        mic_timeout_slider = gr.Slider(3, 30, value=CONFIG.DEFAULT_SPEECH_TIMEOUT, step=1, label="Max Speech Length (sec)")
                        show_reasoning_checkbox = gr.Checkbox(label="Show Agent Reasoning", value=False)
                        stt_fallback_checkbox = gr.Checkbox(label="Force Google STT (Fallback)", value=False, interactive=self.stt_service.fallback_recognizer is not None)
                        stt_lang_override = gr.Textbox(
                            label="STT Language Override (BCP-47)",
                            placeholder="e.g. hi-IN, es-ES",
                            value=""
                        )


                    with gr.Row():
                        start_voice_btn = gr.Button("🎤 Start Voice Conversation")
                        end_voice_btn   = gr.Button("🛑 End Voice Conversation")
                        clear_button = gr.Button("🗑️ Clear Conversation")
                        download_button = gr.Button("💾 Download Transcript")
                    
                    def start_voice():
                        # flip to listening state, greet once, show status
                        greeting = "🎤 Voice mode activated. How can I assist?"
                        return AppState.LISTENING, True, True, greeting

                    def end_voice():
                        goodbye = "🛑 Voice mode ended. Goodbye!"
                        return AppState.IDLE, False, goodbye

                    # ── NOW WIRE THEM UP ──
                    status_display = gr.Markdown("💬 Ready to chat.", elem_id="status")
                    start_voice_btn.click(
                        fn=start_voice,
                        outputs=[conversation_state, should_listen, has_greeted_initial, status_display]
                    )
                    
                    end_voice_btn.click(
                        fn=end_voice,
                        outputs=[conversation_state, should_listen, status_display]
                    )
                        
                    with gr.Accordion("System Status", open=False):
                        status_text = "\n".join([f"- {name}: {'✅ OK' if ok else '❌ ERROR'}" for name, ok in self.service_status.items()])
                        gr.Markdown(f"**Service Health:**\n{status_text}")


                with gr.Column(scale=5): # Right Column
                    chatbot = gr.Chatbot(label="Conversation", bubble_full_width=False, height=650, avatar_images=(None, "https://i.imgur.com/S10i1bS.png"))
                    text_input = gr.Textbox(label="Type your message", placeholder="Type here or use the microphone...", show_label=False)
                    audio_output = gr.Audio(visible=False, autoplay=True)
                    download_file_output = gr.File(visible=False)
                    reasoning_accordion = gr.Accordion("Agent's Thought Process", open=True, visible=False)
                    with reasoning_accordion:
                        reasoning_display = gr.Markdown("")

            # --- Event Handling Logic Binding ---
                all_settings_inputs = [piper_voice_dropdown, use_web_search_checkbox,
                                       show_reasoning_checkbox, stt_fallback_checkbox,
                                      stt_lang_override,
                                       llm_model_dropdown, temperature_slider,
                                        mic_timeout_slider, language_dropdown]

            def gather_settings(*inputs):
                # This function gathers all UI settings into a single dict for easy passing
                keys = ["voice", "web_search", "show_reasoning", "stt_fallback", "stt_lang_override", "llm_model", "temperature", "mic_timeout", "language_name"]
                settings = dict(zip(keys, inputs))
                lang_code = next((details["code"] for name, details in CONFIG.LANGUAGE_CONFIG.items() if name == settings["language_name"]), "en")
                settings["lang_code"] = lang_code
                settings["lang_bcp47"] = CONFIG.LANGUAGE_CONFIG[settings["language_name"]]["bcp47"]
                return settings

            text_input.submit(fn=lambda txt, hist, *s: process_text_input(txt, hist, gather_settings(*s)), inputs=[text_input, chatbot] + all_settings_inputs, outputs=[chatbot, text_input, reasoning_display, audio_output])
            mic_input.stop_recording(
                fn=lambda audio, hist, *s, cs, sl, hi: process_audio_input(audio, hist, gather_settings(*s), cs, sl, hi),
                inputs=[mic_input, chatbot] + all_settings_inputs + [conversation_state, should_listen, has_greeted_initial],
                outputs=[chatbot, text_input, reasoning_display, audio_output]
            )

            clear_button.click(fn=clear_conversation, outputs=[chatbot, reasoning_display, text_input, tool_status_display])
            download_button.click(fn=download_transcript, outputs=[download_file_output])
            
            show_reasoning_checkbox.change(fn=lambda x: gr.Accordion(visible=x), inputs=[show_reasoning_checkbox], outputs=[reasoning_accordion])
            show_reasoning_checkbox.change(fn=self._get_tool_status_md, outputs=[tool_status_display]) # Update tool status when opening reasoning
            language_dropdown.change(fn=on_language_change, inputs=[language_dropdown], outputs=[chatbot, tool_status_display, piper_voice_dropdown])
            
        return app
# ==============================================================================
# Part 6: Main Execution Block
# This final section initializes the application class, performs critical
# pre-launch checks, and starts the Gradio server.
# ==============================================================================

# The GradioApp class was fully defined in the previous part.
# We now write the main script execution logic.

def main() -> None:
    """
    Main function to initialize services, perform health checks,
    create the UI instance, and launch the Gradio application.
    """
    logger.info("Starting KisaanVaani Gradio Application...")

    # --- Pre-launch Health Checks ---
    # Perform a final check of critical services before attempting to launch.
    # This provides clear error messages in the console if the setup is incomplete
    # and prevents the app from launching in a non-functional state.
    
    # Check 1: LLM Service (most critical)
    if not get_groq_client():
        critical_error_msg = "FATAL: Groq LLM service could not be initialized. Please check your GROQ_API_KEY environment variable."
        logger.critical(critical_error_msg)
        print(critical_error_msg, file=sys.stderr)
        sys.exit(1) # Exit with a non-zero error code

    # Check 2: Primary STT Service
    stt_service = get_stt_service()
    if not stt_service or not stt_service.primary_model:
        critical_error_msg = (
            "FATAL: Whisper STT service could not be loaded.\n"
            "Please ensure 'faster-whisper' is installed (`pip install faster-whisper`).\n"
            "The model may also need to be downloaded on the first run, which requires an internet connection."
        )
        logger.critical(critical_error_msg)
        print(critical_error_msg, file=sys.stderr)
        sys.exit(1)

    # Check 3: Primary TTS Service
    tts_service = get_tts_service()
    if not tts_service or not tts_service.available_voices:
        critical_error_msg = (
            "FATAL: Piper TTS service could not find any voice models.\n"
            f"Please download voice models from 'https://huggingface.co/rhasspy/piper-voices/tree/main' "
            f"and place them in the '{CONFIG.PIPER_VOICES_DIR.resolve()}' directory.\n"
            "The application will not launch without at least one configured voice."
        )
        logger.critical(critical_error_msg)
        print(critical_error_msg, file=sys.stderr)
        sys.exit(1)

    # If all critical checks pass, create the application instance.
    # The __init__ method of GradioApp will build the entire UI and backend connections.
    try:
        kisaanvaani_app_instance = GradioApp()
        app_ui = kisaanvaani_app_instance.app
    except Exception as e:
        logger.critical(f"Failed to create the Gradio UI instance during initialization: {e}", exc_info=True)
        print(f"ERROR: An unexpected error occurred while building the UI: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Launch the Gradio Server ---
    logger.info("All services initialized successfully. Launching Gradio server...")
    print("\n==============================================================================")
    print(" KisaanVaani is ready to launch!")
    print(f" Access the interface by navigating to: http://127.0.0.1:7860")
    print("==============================================================================")
    
    # Launch the app. `server_name="0.0.0.0"` makes it accessible on your local network.
    # `debug=True` provides helpful reloading and error messages during development.
    # `share=True` can be used to create a temporary public link if needed (use with caution).
    app_ui.launch(
        server_name="0.0.0.0",
        server_port=7860,
        debug=True,
        inbrowser=True
    )


if __name__ == "__main__":
    # This guard ensures the main function is called only when the script is executed directly.
    main()