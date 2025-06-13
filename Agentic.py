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
            print("Main: GROQ_API_KEY is not set. Please provide a valid API key in the script.")
            st.error("Groq API Key is not configured. Please set it in the script.")
            st.session_state.groq_client = None
            return
        try:
            st.session_state.groq_client = Groq(api_key=GROQ_API_KEY)
            print("Main: Groq client initialized successfully.")
        except Exception as e:
            print(f"Main: Error initializing Groq client: {e}")
            st.error(f"Failed to initialize Groq client: {e}")
            st.session_state.groq_client = None

# --- Text-to-Speech Thread Target (Self-Contained Engine) ---
def _speak_thread_target(text, lang):
    engine = None
    try:
        engine = pyttsx3.init()
        if engine is None:
            print("TTS Thread: Failed to initialize pyttsx3 engine in thread.")
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
                    print(f"TTS Thread: Found voice for {lang}: {voice.name}")
                    break
            if not voice_id_to_set: 
                if voices: 
                    voice_id_to_set = voices[0].id 
                    print(f"TTS Thread: No specific voice for {lang} containing '{target_voice_name_part}'. Using default: {voices[0].name}")
                else:
                    print(f"TTS Thread: No voices available on this system.")
        else:
            print("TTS Thread: No voices found by pyttsx3 engine.")

        if voice_id_to_set: 
            engine.setProperty('voice', voice_id_to_set)
        else:
            print("TTS Thread: No voice ID set, default voice will be used or speech might fail if no default.")
        
        print(f"TTS Thread: Attempting to speak: '{text[:70]}...' (Lang: {lang})")
        engine.say(text)
        engine.runAndWait()
        print(f"TTS Thread: Finished speaking: '{text[:70]}...'")
    except Exception as e:
        print(f"TTS Thread: ERROR during speech for '{text[:70]}...': {e}")
    finally:
        if engine: 
            try:
                engine.stop() 
                print("TTS Thread: pyttsx3 engine stopped for this utterance.")
            except Exception as e_stop:
                print(f"TTS Thread: Error while stopping engine: {e_stop}")


# --- Non-Blocking Text-to-Speech Function ---
def speak_non_blocking(text, lang='en'):
    if not text or text.strip() == "":
        print("Main: speak_non_blocking called with empty text. Skipping speech.")
        return False 
        
    active_speech_threads_before = threading.active_count()
    print(f"Main: Active threads before starting new speech: {active_speech_threads_before}")

    try:
        speech_thread = threading.Thread(target=_speak_thread_target, args=(text, lang))
        speech_thread.daemon = True 
        speech_thread.start()
        print(f"Main: Speech thread successfully started for '{text[:70]}...'")
        
        num_words = len(text.split())
        estimated_duration = (num_words / WORDS_PER_SECOND) + 0.5 
        sleep_duration = max(MIN_SLEEP_AFTER_TTS, min(estimated_duration, MAX_SLEEP_AFTER_TTS))
        
        print(f"Main: Main thread will sleep for {sleep_duration:.2f}s to allow TTS thread to complete ('{text[:30]}...').")
        time.sleep(sleep_duration) 
        print(f"Main: Finished sleep after TTS call for '{text[:30]}...'.")
        return True

    except Exception as e:
        print(f"Main: CRITICAL Error starting speech thread for '{text[:70]}...': {e}")
        return False


# --- Tool Integration Functions ---
def get_current_date():
    """Get the current date in a formatted string."""
    current_date = datetime.datetime.now()
    return f"Today is {current_date.strftime('%A, %B %d, %Y')}."

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

def calculate_math(expression: str):
    """Calculates a math expression safely."""
    try:
        result = safe_math_eval(ast.parse(expression, mode='eval').body)
        return f"The result of {expression} is {result}."
    except (TypeError, SyntaxError, ValueError, KeyError):
        return "I couldn't solve that. Please state a basic arithmetic expression like '5 times 3'."
    except Exception as e:
        print(f"Math Error: {e}")
        return "I encountered an error trying to solve that."

def tell_joke():
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "Why did the scarecrow win an award? Because he was outstanding in his field!",
        "What do you call a sad strawberry? A blueberry."
    ]
    return random.choice(jokes)

def get_weather_forecast(location: str):
    """Get weather forecast for a location."""
    try:
        # This is a placeholder. In a real implementation, you would call a weather API
        return f"I'm sorry, I don't have real-time weather data for {location} yet. This feature is under development."
    except Exception as e:
        print(f"Weather Error: {e}")
        return "I encountered an error trying to get the weather forecast."

def get_mandi_prices(crop: str, market: str = None) -> str:
    """Get mandi prices for crops using real-time data sources."""
    try:
        # Use web search to get real-time mandi prices
        search_query = f"current mandi price of {crop}"
        if market:
            search_query += f" in {market}"
        search_query += " site:agmarknet.gov.in OR site:farmer.gov.in"
        
        # Get price data from reliable sources
        price_data = perform_web_search(search_query)
        
        if not price_data or "Error" in price_data:
            # Fallback to alternative sources if primary sources fail
            alt_search_query = f"latest wholesale price of {crop}"
            if market:
                alt_search_query += f" in {market}"
            alt_search_query += " site:vikaspedia.in OR site:agrifarming.in"
            price_data = perform_web_search(alt_search_query)
        
        if not price_data or "Error" in price_data:
            return f"I'm unable to fetch real-time price data for {crop} in {market if market else 'the market'}. Please check local mandis or agricultural websites for the latest prices."
        
        # Extract and format the price information
        try:
            # Look for price patterns in the search results
            price_pattern = r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)'
            prices = re.findall(price_pattern, price_data)
            
            if prices:
                # Convert string prices to float, removing commas
                numeric_prices = [float(price.replace(',', '')) for price in prices]
                avg_price = sum(numeric_prices) / len(numeric_prices)
                
                response = f"Current mandi price for {crop}"
                if market:
                    response += f" in {market}"
                response += f": ₹{int(avg_price)}/quintal\n\n"
                
                # Add source information
                if "agmarknet" in price_data.lower():
                    response += "Source: Agmarknet (Government of India)\n"
                elif "farmer.gov" in price_data.lower():
                    response += "Source: Farmer.gov.in\n"
                else:
                    response += "Source: Agricultural websites\n"
                
                response += "Note: Prices may vary based on quality, quantity, and market conditions."
                return response
            else:
                return f"Price information for {crop} in {market if market else 'the market'} is not currently available. Please check local mandis for the latest prices."
                
        except Exception as e:
            print(f"Error processing price data: {e}")
            return f"I found some information about {crop} prices, but couldn't extract the exact numbers. Here's what I found:\n\n{price_data[:200]}..."
                
    except Exception as e:
        print(f"Error in get_mandi_prices: {e}")
        return f"Error fetching mandi prices: {str(e)}"

def get_farming_advice(topic: str):
    """Get farming advice for a specific topic."""
    try:
        # This is a placeholder. In a real implementation, you would call a farming advice API
        return f"I'm sorry, I don't have specific farming advice for {topic} yet. This feature is under development."
    except Exception as e:
        print(f"Farming Advice Error: {e}")
        return "I encountered an error trying to get farming advice."

# Add a function to determine which tool to use
def determine_tool_to_use(query: str, chat_history: list) -> tuple:
    """Determines which tool to use based on the query and chat history."""
    query = query.lower()
    
    # Check for date-related queries
    if any(word in query for word in ['date', 'today', 'day', 'time']):
        return 'get_current_date', {}
    
    # Check for math-related queries
    if any(word in query for word in ['calculate', 'math', 'plus', 'minus', 'multiply', 'divide', 'times']):
        # Extract numbers and operators from the query
        try:
            # Simple pattern matching for basic math expressions
            math_pattern = r'(\d+\s*[\+\-\*\/]\s*\d+)'
            match = re.search(math_pattern, query)
            if match:
                return 'calculate_math', {'expression': match.group(1)}
        except Exception as e:
            print(f"Math pattern matching error: {e}")
    
    # Check for joke requests
    if any(word in query for word in ['joke', 'funny', 'humor']):
        return 'tell_joke', {}
    
    # Check for weather queries
    if any(word in query for word in ['weather', 'forecast', 'temperature', 'rain']):
        # Try to extract location from query
        location = query.split('in')[-1].strip() if 'in' in query else 'current location'
        return 'get_weather_forecast', {'location': location}
    
    # Check for mandi price queries
    if any(word in query for word in ['mandi', 'price', 'rate', 'bhav', 'crop']):
        # Try to extract crop and market from query
        crop = None
        market = 'India'
        if 'in' in query:
            parts = query.split('in')
            crop = parts[0].strip()
            market = parts[1].strip()
        return 'get_mandi_prices', {'crop': crop, 'market': market}
    
    # Check for farming advice
    if any(word in query for word in ['farming', 'agriculture', 'crop', 'plant', 'harvest', 'fertilizer']):
        return 'get_farming_advice', {'topic': query}
    
    return None, {}

# --- Web Search Integration ---
@st.cache_resource
def get_tavily_client():
    """Initialize and cache the Tavily client with proper TLS configuration."""
    try:
        import certifi
        import requests
        from tavily import TavilyClient
        
        # Configure requests session with proper TLS certificates
        session = requests.Session()
        session.verify = certifi.where()
        
        # Initialize Tavily client with the configured session
        client = TavilyClient(api_key=TAVILY_API_KEY)
        print("Tavily: Client initialized successfully")
        return client
    except Exception as e:
        print(f"Tavily: Error initializing client: {e}")
        return None

def perform_web_search(query: str, search_depth: str = "advanced", max_results: int = 8):
    """Enhanced web search with comprehensive result processing and multiple sources."""
    try:
        import certifi
        import requests
        from tavily import TavilyClient
        
        # Initialize client directly for this search
        session = requests.Session()
        session.verify = certifi.where()
        client = TavilyClient(api_key=TAVILY_API_KEY)
        
        print(f"Tavily: Performing search for query: {query}")
        
        # First try to get a direct answer with comprehensive search
        response = client.search(
            query=query,
            search_depth=search_depth,
            max_results=max_results,
            include_answer=True,
            include_domains=[
                # General knowledge
                "wikipedia.org", "britannica.com", "reuters.com", "apnews.com", "bloomberg.com",
                # News and current events
                "bbc.com", "cnn.com", "nytimes.com", "theguardian.com", "indianexpress.com",
                # Technology
                "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com",
                # Entertainment
                "imdb.com", "rottentomatoes.com", "metacritic.com", "spotify.com", "apple.com",
                # Podcasts and audio
                "podchaser.com", "podbean.com", "buzzsprout.com", "anchor.fm", "soundcloud.com",
                # Social media and blogs
                "medium.com", "substack.com", "wordpress.com", "blogspot.com",
                # Educational
                "khanacademy.org", "coursera.org", "edx.org", "udemy.com",
                # Reference
                "merriam-webster.com", "dictionary.com", "thesaurus.com", "quora.com",
                # Agriculture and farming
                "agmarknet.gov.in", "farmer.gov.in", "vikaspedia.in", "agrifarming.in",
                # Weather and environment
                "weather.com", "accuweather.com", "noaa.gov", "climate.gov",
                # Business and finance
                "forbes.com", "economist.com", "wsj.com", "ft.com",
                # Sports
                "espn.com", "sports.yahoo.com", "cricbuzz.com", "cricket.com.au",
                # Science and research
                "nature.com", "science.org", "sciencedaily.com", "phys.org"
            ]
        )
        
        print(f"Tavily: Search completed successfully. Found {len(response.get('results', []))} results")
        
        # Process and format the response
        if response.get("answer"):
            # Add source attribution and additional context
            sources = [res['url'] for res in response['results'][:3]]
            source_text = "\n\nSources: " + ", ".join(sources) if sources else ""
            
            # Add relevant quotes if available
            quotes = []
            for res in response['results'][:3]:
                if 'content' in res and len(res['content']) > 50:
                    quotes.append(f"\"{res['content'][:200]}...\"")
            
            quote_text = "\n\nRelevant quotes:\n" + "\n".join(quotes) if quotes else ""
            
            return response["answer"] + quote_text + source_text
            
        # If no direct answer, synthesize from results
        results = response['results']
        if not results:
            print("Tavily: No results found, trying broader search...")
            # Try a broader search without domain restrictions
            try:
                broader_response = client.search(
                    query=query,
                    search_depth="basic",
                    max_results=5,
                    include_answer=False
                )
                if broader_response.get("results"):
                    results = broader_response["results"]
                    print(f"Tavily: Broader search found {len(results)} results")
            except Exception as e:
                print(f"Tavily: Broader search error: {e}")
        
        if not results:
            return "I couldn't find any relevant information for your query."
            
        # Group results by topic/source
        grouped_results = {}
        for res in results:
            domain = res['url'].split('/')[2]
            if domain not in grouped_results:
                grouped_results[domain] = []
            grouped_results[domain].append(res)
        
        # Format response with grouped information
        formatted_response = []
        
        # Add a summary if available
        if response.get("answer"):
            formatted_response.append("Summary:")
            formatted_response.append(response["answer"])
            formatted_response.append("")
        
        # Add detailed results
        formatted_response.append("Detailed Information:")
        for domain, domain_results in grouped_results.items():
            if domain_results:
                formatted_response.append(f"\nFrom {domain}:")
                for res in domain_results[:2]:  # Limit to top 2 results per domain
                    formatted_response.append(f"- {res['content']}")
        
        # Add sources
        sources = [res['url'] for res in results[:3]]
        if sources:
            formatted_response.append("\nSources:")
            formatted_response.extend([f"- {source}" for source in sources])
        
        return "\n".join(formatted_response)
        
    except Exception as e:
        print(f"Tavily: Web search error: {e}")
        # Try a fallback search with different parameters
        try:
            print("Tavily: Attempting fallback search...")
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                include_answer=False
            )
            if response.get("results"):
                print(f"Tavily: Fallback search found {len(response['results'])} results")
                return f"Here's what I found about {query}:\n" + "\n".join([f"- {res['content']}" for res in response['results'][:3]])
        except Exception as fallback_error:
            print(f"Tavily: Fallback search error: {fallback_error}")
        return f"Error performing web search: {str(e)}"

# --- Enhanced Tool System ---
class ToolSystem:
    """Enhanced tool system with improved error handling and parameter validation."""
    
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
                "optional_params": [],
                "description": "Get weather forecast",
                "example": "get_weather_forecast(location='Delhi')"
            },
            "get_mandi_prices": {
                "required_params": ["crop"],
                "optional_params": ["market"],
                "description": "Get mandi prices",
                "example": "get_mandi_prices(crop='potato', market='Bangalore')"
            },
            "get_farming_advice": {
                "required_params": ["topic"],
                "optional_params": [],
                "description": "Get farming advice",
                "example": "get_farming_advice(topic='rice cultivation')"
            },
            "calculate_math": {
                "required_params": ["expression"],
                "optional_params": [],
                "description": "Solve math",
                "example": "calculate_math(expression='2 + 2')"
            },
            "tell_joke": {
                "required_params": [],
                "optional_params": [],
                "description": "Tell a joke",
                "example": "tell_joke()"
            },
            "get_news_summary": {
                "required_params": [],
                "optional_params": ["topic"],
                "description": "Get news summary",
                "example": "get_news_summary(topic='technology')"
            },
            "get_definition": {
                "required_params": ["term"],
                "optional_params": [],
                "description": "Get definition",
                "example": "get_definition(term='artificial intelligence')"
            },
            "get_biography": {
                "required_params": ["person"],
                "optional_params": [],
                "description": "Get biography",
                "example": "get_biography(person='Albert Einstein')"
            },
            "get_sports_update": {
                "required_params": [],
                "optional_params": ["sport"],
                "description": "Get sports update",
                "example": "get_sports_update(sport='cricket')"
            },
            "get_movie_info": {
                "required_params": ["title"],
                "optional_params": [],
                "description": "Get movie info",
                "example": "get_movie_info(title='Inception')"
            },
            "get_tech_news": {
                "required_params": [],
                "optional_params": [],
                "description": "Get tech news",
                "example": "get_tech_news()"
            },
            "web_search": {
                "required_params": ["query"],
                "optional_params": [],
                "description": "General web search",
                "example": "web_search(query='latest news')"
            }
        }
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.error_counts = {}  # Track error frequency per tool
        self.last_error_time = {}  # Track last error time per tool
        
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

# Initialize tool system
tool_system = ToolSystem()

# --- Chat Context Management ---
class ChatContext:
    """Manages conversation context and user profiles with enhanced capabilities."""
    
    def __init__(self, max_history: int = 10):
        """Initialize chat context with configurable history size."""
        self.max_history = max_history
        self.messages = []
        self.user_profile = {
            "language": "en",
            "farming_context": {},
            "preferences": {},
            "last_interaction": None
        }
        self.conversation_state = {
            "active_topic": None,
            "pending_actions": [],
            "context_entities": set(),
            "tool_usage_history": []
        }
        context_logger.info("ChatContext initialized")
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to the conversation history with metadata."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.messages.append(message)
        if len(self.messages) > self.max_history:
            self.messages.pop(0)
        
        # Update conversation state
        self._update_conversation_state(message)
        context_logger.debug(f"Added message: {role} - {content[:50]}...")
    
    def _update_conversation_state(self, message: Dict[str, Any]):
        """Update conversation state based on new message."""
        # Extract entities and topics
        if message["role"] == "user":
            self._extract_entities(message["content"])
            self._update_active_topic(message["content"])
        
        # Update tool usage history
        if message.get("metadata", {}).get("tool_used"):
            self.conversation_state["tool_usage_history"].append({
                "tool": message["metadata"]["tool_used"],
                "timestamp": message["timestamp"]
            })
    
    def _extract_entities(self, text: str):
        """Extract relevant entities from text."""
        # Simple entity extraction - can be enhanced with NLP
        entities = set()
        farming_terms = ["crop", "weather", "soil", "fertilizer", "pesticide", "harvest"]
        for term in farming_terms:
            if term in text.lower():
                entities.add(term)
        self.conversation_state["context_entities"].update(entities)
    
    def _update_active_topic(self, text: str):
        """Update the active conversation topic."""
        # Simple topic detection - can be enhanced with NLP
        topics = {
            "weather": ["weather", "forecast", "rain", "temperature"],
            "crops": ["crop", "plant", "harvest", "yield"],
            "prices": ["price", "market", "mandi", "rate"],
            "advice": ["how", "what", "when", "advice", "help"]
        }
        
        for topic, keywords in topics.items():
            if any(keyword in text.lower() for keyword in keywords):
                self.conversation_state["active_topic"] = topic
                break
    
    def get_context_for_agent(self) -> str:
        """Get formatted context for the agent."""
        context_parts = []
        
        # Add recent messages
        recent_messages = self.messages[-4:] if len(self.messages) > 4 else self.messages
        context_parts.append("Recent conversation:")
        for msg in recent_messages:
            context_parts.append(f"{msg['role']}: {msg['content']}")
        
        # Add active topic
        if self.conversation_state["active_topic"]:
            context_parts.append(f"\nActive topic: {self.conversation_state['active_topic']}")
        
        # Add relevant entities
        if self.conversation_state["context_entities"]:
            context_parts.append(f"\nRelevant entities: {', '.join(self.conversation_state['context_entities'])}")
        
        # Add farming context if available
        if self.user_profile["farming_context"]:
            context_parts.append("\nFarming context:")
            for key, value in self.user_profile["farming_context"].items():
                context_parts.append(f"- {key}: {value}")
        
        return "\n".join(context_parts)
    
    def get_farming_context(self) -> Dict[str, Any]:
        """Get farming-specific context."""
        return self.user_profile["farming_context"]
    
    def update_farming_context(self, key: str, value: Any):
        """Update farming context with new information."""
        self.user_profile["farming_context"][key] = value
        context_logger.info(f"Updated farming context: {key} = {value}")
    
    def get_tool_usage_stats(self) -> Dict[str, int]:
        """Get statistics about tool usage."""
        stats = {}
        for entry in self.conversation_state["tool_usage_history"]:
            tool = entry["tool"]
            stats[tool] = stats.get(tool, 0) + 1
        return stats
    
    def clear_history(self):
        """Clear conversation history while preserving user profile."""
        self.messages.clear()
        self.conversation_state = {
            "active_topic": None,
            "pending_actions": [],
            "context_entities": set(),
            "tool_usage_history": []
        }
        context_logger.info("Conversation history cleared")

# Initialize chat context
chat_context = ChatContext()

# --- Core Agent System ---
def generate_agent_response(user_query: str) -> dict:
    """The agent's brain: routes to tools and synthesizes a response with enhanced capabilities."""
    if 'groq_client' not in st.session_state or st.session_state.groq_client is None:
        agent_logger.error("LLM client not initialized in session state")
        return {"response": KNOWN_FALLBACK_RESPONSES[0]}
    
    client = st.session_state.groq_client
    try:
        # Step 1: Context Preparation
        context = chat_context.get_context_for_agent()
        farming_context = chat_context.get_farming_context()
        tool_usage_stats = chat_context.get_tool_usage_stats()
        
        agent_logger.info(f"Processing query: {user_query[:50]}...")
        agent_logger.debug(f"Context: {context[:200]}...")
        
        # Step 2: Intent Detection & Tool Routing with Enhanced Analysis
        router_prompt = f"""You are a master reasoning agent that decides which tool to use to answer a user's query.
You have access to the following context:

Recent Conversation:
{context}

Farming Context:
{json.dumps(farming_context, indent=2)}

Tool Usage Statistics:
{json.dumps(tool_usage_stats, indent=2)}

Available Tools:
1. Farming-specific tools (use ONLY for farming-related queries):
   - get_mandi_prices(crop, market): Get mandi prices
   - get_farming_advice(topic): Get farming advice

2. General tools (use for any query):
   - get_current_date(): Get today's date
   - calculate_math(expression): Solve math
   - tell_joke(): Tell a joke
   - get_weather_forecast(location): Get weather
   - get_news_summary(topic): Get news
   - get_definition(term): Get definitions
   - get_biography(person): Get biographies
   - get_sports_update(sport): Get sports news
   - get_movie_info(title): Get movie info
   - get_tech_news(): Get tech news
   - web_search(query): General web search

Instructions:
1. Analyze the user's query and conversation history to understand their intent and context.
2. Consider the farming context and tool usage statistics when making decisions.
3. If the user's query is ambiguous, use the conversation history to determine what they're referring to.
4. Choose the most appropriate tool from the list above.
5. Consider tool usage patterns and success rates when making decisions.
6. Your output MUST be a JSON object with:
   - tool_to_use: The name of the tool to use
   - thought: Your detailed reasoning for choosing this tool
   - parameters: A dictionary of the arguments needed by the tool
   - is_farming_query: Boolean indicating if this is a farming-related query
   - confidence: A number between 0 and 1 indicating your confidence in this choice
   - alternative_tools: List of alternative tools that could also work
   - context_used: List of context elements that influenced your decision"""

        router_messages = [
            {"role": "system", "content": router_prompt},
            {"role": "user", "content": user_query}
        ]
        
        router_completion = client.chat.completions.create(
            messages=router_messages,
            model="llama3-8b-8192",
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
        
        # Step 3: Tool Execution with Enhanced Error Handling
        tool_output = None
        search_feedback = None
        
        if chosen_tool:
            # Generate search feedback for the user to see while waiting
            if chosen_tool in ["web_search", "get_weather_forecast", "get_mandi_prices", "get_farming_advice"]:
                search_query = params.get('query') or params.get('topic') or params.get('location') or params.get('crop')
                search_feedback = f"🔎 Searching for: *{search_query}*"
            
            # Execute the tool through the ToolSystem
            tool_response = tool_system.execute_tool(chosen_tool, params)
            
            if tool_response["success"]:
                tool_output = tool_response["result"]
                # Update farming context if relevant
                if is_farming_query and chosen_tool in ["get_mandi_prices", "get_farming_advice"]:
                    chat_context.update_farming_context(chosen_tool, tool_output)
            else:
                # Handle tool execution error
                error_msg = tool_response.get("error", "Unknown error")
                suggestion = tool_response.get("suggestion", "Please try again.")
                
                # Try alternative tools if confidence was low
                if confidence < 0.7 and alternative_tools:
                    agent_logger.info(f"Trying alternative tools due to low confidence: {alternative_tools}")
                    for alt_tool in alternative_tools:
                        alt_response = tool_system.execute_tool(alt_tool, params)
                        if alt_response["success"]:
                            tool_output = alt_response["result"]
                            chosen_tool = alt_tool
                            agent_logger.info(f"Successfully used alternative tool: {alt_tool}")
                            break
                    else:
                        tool_output = f"I encountered an error: {error_msg}. {suggestion}"
                else:
                    tool_output = f"I encountered an error: {error_msg}. {suggestion}"

        # Step 4: Response Synthesis with Enhanced Context
        synthesizer_prompt = f"""You are KisaanVaani, a friendly and helpful voice assistant. You will be given information from a tool.

Context:
{context}

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
4. Use the conversation history to maintain context and provide relevant follow-up information.
5. If this is a farming query, include relevant agricultural context.
6. If this is NOT a farming query, do NOT force farming context.
7. Consider the user's language and previous interactions when crafting the response.
8. ALWAYS end your response by asking a gentle, open-ended follow-up question."""

        final_messages = [
            {"role": "system", "content": synthesizer_prompt},
            {"role": "user", "content": user_query}
        ]
        
        final_completion = client.chat.completions.create(
            messages=final_messages,
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=250,
            top_p=1,
            stream=False
        )
        
        final_answer = final_completion.choices[0].message.content
        
        # Update chat context with the interaction
        chat_context.add_message("user", user_query, {
            "is_farming_query": is_farming_query,
            "confidence": confidence
        })
        
        chat_context.add_message("assistant", final_answer, {
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

# Update handle_user_input to use the new agent system
def handle_user_input(user_input_text, input_type="text"):
    """Processes user input with improved state management and error handling."""
    print(f"Main: Handling input (Type: {input_type}): '{user_input_text[:70]}...'")
    
    # Step 1: Input Validation
    if not user_input_text or user_input_text.strip() == "": 
        print("Main: Empty user input received. No action taken.")
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
    agent_response = generate_agent_response(user_input_text)
    
    # Step 4: Response Processing
    # Show reasoning if enabled
    if st.session_state.get('reasoning_mode_active'):
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": f"🤔 *Thought: {agent_response['thought']}*",
            "type": "reasoning"
        })
    
    # Show search feedback if present
    if agent_response.get('feedback'):
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": agent_response['feedback'],
            "type": "system_feedback"
        })
    
    # Add AI response to chat history
    st.session_state.chat_history.append({
        "role": "assistant",
        "content": agent_response['response'],
        "type": "response"
    })
    
    # Step 5: Output Generation
    speak_non_blocking(agent_response['response'], lang=st.session_state.selected_language_code)
    
    # Step 6: Conversation Management
    is_fallback_response = agent_response['response'] in KNOWN_FALLBACK_RESPONSES
    conversation_is_active = st.session_state.get('conversation_active', False)

    if conversation_is_active:
        if not is_fallback_response: 
            followup_text = get_followup_question(st.session_state.selected_language_code)
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"💭 *{followup_text}*",
                "type": "followup"
            })
            speak_non_blocking(followup_text, lang=st.session_state.selected_language_code)
        else: 
            print(f"Main: LLM returned a fallback/error ('{agent_response['response'][:30]}...'). No followup question.")
        
        st.session_state.should_listen = True 
    
    print("Main: handle_user_input finished processing. Rerunning UI.")
    st.rerun()

# --- Speech-to-Text Function ---
def listen_for_voice_st(lang='en', timeout=10, phrase_time_limit=None):
    recognizer = sr.Recognizer()
    microphone = sr.Microphone() 
    print(f"SR: Initializing microphone. Timeout: {timeout}s, Phrase Limit: {phrase_time_limit if phrase_time_limit else 'None (waits for pause)'}")
    
    with microphone as source:
        try:
            print("SR: Adjusting for ambient noise (duration 1.5s)...")
            time.sleep(0.1) 
            recognizer.adjust_for_ambient_noise(source, duration=1.5) 
            print("SR: Ambient noise adjustment complete. Now listening for audio input...")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            print("SR: Audio captured. Attempting to recognize speech...")
            text = recognizer.recognize_google(audio, language=lang)
            print(f"SR: Successfully recognized text: '{text}'")
            return text
        except sr.WaitTimeoutError: 
            print("SR: Timeout - No speech detected within the timeout period.")
            return "TIMEOUT"
        except sr.UnknownValueError: 
            print("SR: Speech was unintelligible or could not be understood by Google Speech Recognition.")
            return "UNCLEAR"
        except sr.RequestError as e: 
            print(f"SR: API request error (e.g., network issue, Google Speech Recognition service unavailable); {e}")
            return "ERROR"
        except Exception as e: 
            print(f"SR: Unexpected error in listen_for_voice_st: {type(e).__name__} - {e}")
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
    print("Main: process_voice_input called by Streamlit rerun logic.")
    st.session_state.listening_state = True
    
    status_placeholder = st.empty() 
    status_placeholder.info("🎤 **Listening...** Speak clearly and pause when you are finished.", icon="🔊")
    
    time.sleep(0.7) 
    
    voice_result = listen_for_voice_st(lang=st.session_state.selected_language_code)
    
    status_placeholder.empty() 
    st.session_state.listening_state = False 
    print(f"Main: Voice listen result from STT: '{voice_result}'")
    
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
        speak_non_blocking(feedback_text, lang=st.session_state.selected_language_code)
        
        if st.session_state.get('conversation_active', False): 
            st.session_state.should_listen = True 
        print("Main: STT fallback processed in process_voice_input. Rerunning UI.")
        st.rerun()

# --- Streamlit App UI and Logic ---
def run_kisaanvaani_app():
    st.set_page_config(page_title="KisaanVaani Voice Assistant", layout="wide")
    st.title("🌾 KisaanVaani Voice Assistant")

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
        print("Main: Session state variables initialized.")

    st.sidebar.header("🌍 Language Settings")
    lang_options_display = list(SUPPORTED_LANGUAGES.keys())
    lang_names_capitalized = [name.capitalize() for name in lang_options_display]
    current_lang_idx = 0
    try:
        current_lang_idx = lang_names_capitalized.index(st.session_state.selected_language_name.capitalize())
    except ValueError:
        print(f"Warning: Current language '{st.session_state.selected_language_name}' not in options. Defaulting to English.")
        st.session_state.selected_language_name = 'English' # Default to English if error
        st.session_state.selected_language_code = 'en'
        # current_lang_idx remains 0, which is English if English is first

    selected_lang_name_ui = st.sidebar.selectbox("Choose Language", lang_names_capitalized, index=current_lang_idx, key="lang_sb")

    if selected_lang_name_ui.lower() != st.session_state.selected_language_name.lower():
        print(f"Main: Language changed: {selected_lang_name_ui}")
        st.session_state.selected_language_name = selected_lang_name_ui
        st.session_state.selected_language_code = SUPPORTED_LANGUAGES[selected_lang_name_ui.lower()]
        st.session_state.chat_history = []
        st.session_state.conversation_active = False
        st.session_state.should_listen = False
        st.session_state.listening_state = False
        st.session_state.has_greeted_initial = False
        st.rerun()

    st.sidebar.header("🎙️ Voice Conversation")
    if st.session_state.get('conversation_active', False):
        if st.sidebar.button("🛑 End Conversation", type="secondary", use_container_width=True, key="end_conv_btn"):
            print("Main: 'End Conversation' pressed.")
            st.session_state.conversation_active = False
            st.session_state.listening_state = False
            st.session_state.should_listen = False
            goodbye_text_map = {"en": "Thank you for using KisaanVaani. Goodbye!", "hi": "किसानवाणी का उपयोग करने के लिए धन्यवाद। अलविदा!"}
            goodbye_text = goodbye_text_map.get(st.session_state.selected_language_code, goodbye_text_map['en'])
            st.session_state.chat_history.append({"role": "assistant", "content": f"👋 {goodbye_text}", "type": "goodbye"})
            speak_non_blocking(goodbye_text, lang=st.session_state.selected_language_code)
            st.rerun()
    else:
        if st.sidebar.button("🎤 Start Voice Conversation", type="primary", use_container_width=True, key="start_conv_btn"):
            print("Main: 'Start Conversation' pressed.")
            st.session_state.conversation_active = True
            st.session_state.should_listen = True
            greeting_voice_start_map = {"en": "Voice mode activated. How can I assist?", "hi": "वॉइस मोड सक्रिय। कैसे मदद कर सकता हूँ?"}
            greeting_text = greeting_voice_start_map.get(st.session_state.selected_language_code, greeting_voice_start_map['en'])
            
            if not st.session_state.chat_history or \
               (st.session_state.chat_history and st.session_state.chat_history[-1].get("type") not in ["greeting_app_start", "greeting_voice_start"]):
                st.session_state.chat_history.append({"role": "assistant", "content": f"👋 {greeting_text}", "type": "greeting_voice_start"})
            
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
        print("Main: Loop trigger: Should listen = True, Active = True, Not Listening = True. Calling process_voice_input.")
        st.session_state.should_listen = False 
        process_voice_input() 
        
    typed_prompt = st.chat_input(f"Type in {st.session_state.selected_language_name}...", key="main_chat_input",
                                 disabled=st.session_state.get('listening_state', False))
    if typed_prompt:
        print(f"Main: Text input: '{typed_prompt[:70]}...'")
        st.session_state.conversation_active = False 
        st.session_state.should_listen = False
        st.session_state.listening_state = False
        handle_user_input(typed_prompt, input_type="text")

    if not st.session_state.has_greeted_initial and \
       st.session_state.get('services_initialized') and \
       not st.session_state.chat_history: 
        print("Main: Displaying one-time initial app greeting (text mode, chat empty).")
        initial_greeting_text = "Hello! I am KisaanVaani. Start a voice conversation or type your query."
        if st.session_state.selected_language_code == "hi":
            initial_greeting_text = "नमस्ते! मैं किसानवाणी हूँ। वॉइस वार्तालाप शुरू करें या अपना प्रश्न टाइप करें।"
        
        st.session_state.chat_history.append({"role": "assistant", "content": f"👋 {initial_greeting_text}", "type": "greeting_app_start"})
        speak_non_blocking(initial_greeting_text, lang=st.session_state.selected_language_code)
        st.session_state.has_greeted_initial = True
        st.rerun()

    # Add reasoning mode toggle in sidebar
    st.sidebar.header("Settings")
    st.sidebar.toggle("🧠 Show Agent Reasoning", key="reasoning_mode_active", help="See the agent's thought process in the chat.")

if __name__ == "__main__":
    run_kisaanvaani_app()
