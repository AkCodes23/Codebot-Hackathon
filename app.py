import streamlit as st
import speech_recognition as sr
import os
from groq import Groq
import time
import pyttsx3

# --- Constants and Configuration ---
GROQ_API_KEY = "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"
SUPPORTED_LANGUAGES = {
    "english": "en",
    "hindi": "hi",
    "spanish": "es",
    "french": "fr",
}

# --- TTS Engine Initialization ---
def initialize_tts_engine():
    """Initializes the pyttsx3 engine and stores it in session state."""
    if 'pyttsx3_engine' not in st.session_state or st.session_state.pyttsx3_engine is None:
        try:
            engine = pyttsx3.init()
            st.session_state.pyttsx3_engine = engine
            st.session_state.pyttsx3_engine_initialized = True
            print("pyttsx3 engine initialized and stored in session state.")
        except Exception as e:
            st.error(f"Error initializing pyttsx3: {e}. Voice output may not be available.")
            st.session_state.pyttsx3_engine = None
            st.session_state.pyttsx3_engine_initialized = False

# --- Groq Client Initialization ---
def initialize_groq_client():
    """Initializes the Groq client and stores it in session state."""
    if 'groq_client' not in st.session_state or st.session_state.groq_client is None:
        if not GROQ_API_KEY:
            st.error("GROQ_API_KEY is not set. Cannot connect to LLM.")
            st.session_state.groq_client = None
            return
        try:
            st.session_state.groq_client = Groq(api_key=GROQ_API_KEY)
            print("Groq client initialized and stored in session state.")
        except Exception as e:
            st.error(f"Error initializing Groq client: {e}")
            st.session_state.groq_client = None

# --- Text-to-Speech Function ---
def speak_directly(text, lang='en'):
    """Converts text to speech using pyttsx3 and plays it directly."""
    if 'pyttsx3_engine_initialized' in st.session_state and st.session_state.pyttsx3_engine_initialized and st.session_state.pyttsx3_engine:
        try:
            engine = st.session_state.pyttsx3_engine
            # Ensure properties like voice or rate are set if needed, though not explicitly requested here
            # For different languages with pyttsx3, one might need to set voice properties if specific voices are installed
            # voices = engine.getProperty('voices')
            # For example, to select a specific voice if available:
            # if lang == 'hi': # Example for Hindi
            #     for voice in voices:
            #         if 'hindi' in voice.name.lower(): # This check is highly dependent on installed voice names
            #             engine.setProperty('voice', voice.id)
            #             break
            engine.say(text)
            engine.runAndWait()
            return True # Indicates speech was attempted
        except Exception as e:
            st.error(f"Error in pyttsx3 direct speech: {e}")
            return False
    else:
        st.warning("pyttsx3 engine not initialized. Cannot generate audio.")
        return False

# --- LLM Interaction ---
def get_groq_response_st(user_prompt):
    """Sends a prompt to Groq LLM using client from session_state and returns the response."""
    if 'groq_client' not in st.session_state or st.session_state.groq_client is None:
        return "LLM client not initialized. Please check configuration."
    if not user_prompt:
        return "I didn't catch that. Could you please type your query?"
    
    client = st.session_state.groq_client
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are KisaanVaani, a helpful voice assistant for farmers. Provide concise and accurate information related to farming, agriculture, and general knowledge useful to farmers. Keep your answers relatively short."
                },
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=200, # Increased slightly for web UI
            top_p=1,
            stop=None,
            stream=False,
        )
        response = chat_completion.choices[0].message.content
        return response
    except Exception as e:
        st.error(f"Error communicating with Groq API: {e}")
        return "I'm having trouble connecting to my brain right now. Please try again later."

# --- Speech-to-Text Function (Adapted for Streamlit) ---
def listen_for_voice_st(lang='en', timeout=5, phrase_time_limit=10):
    """Listens for voice input, converts to text, and returns the text."""
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        st.info("Adjusting for ambient noise... Please wait.")
        try:
            recognizer.adjust_for_ambient_noise(source, duration=1)
            st.info(f"Listening for input in {lang}... (Speak now)")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            st.info("Recognizing...")
            text = recognizer.recognize_google(audio, language=lang)
            st.success(f"You said: {text}")
            return text
        except sr.WaitTimeoutError:
            st.warning("No speech detected within the time limit.")
            return None
        except sr.UnknownValueError:
            st.error("Speech Recognition could not understand audio.")
            return None
        except sr.RequestError as e:
            st.error(f"Could not request results from Speech Recognition service; {e}")
            return None
        except Exception as e:
            st.error(f"An unexpected error occurred during speech recognition: {e}")
            return None

# --- Streamlit App UI and Logic ---
def run_kisaanvaani_app():
    st.set_page_config(page_title="KisaanVaani Assistant", layout="wide")
    st.title("🌾 KisaanVaani - Your Farming Assistant")

    # Initialize services if not already done
    if 'services_initialized' not in st.session_state:
        initialize_tts_engine()
        initialize_groq_client()
        st.session_state.services_initialized = True
        st.session_state.chat_history = []
        st.session_state.selected_language_code = 'en' # Default language
        st.session_state.selected_language_name = 'English'
        st.session_state.conversation_active = False
        st.session_state.trigger_listen = False

    # --- Sidebar for Language Selection ---
    st.sidebar.header("Language Settings")
    lang_options = list(SUPPORTED_LANGUAGES.keys())
    lang_names_capitalized = [name.capitalize() for name in lang_options]
    
    # Find current index for selectbox
    current_lang_name_cap = st.session_state.selected_language_name.capitalize()
    try:
        current_lang_idx = lang_names_capitalized.index(current_lang_name_cap)
    except ValueError:
        current_lang_idx = 0 # Default to English if not found

    selected_lang_name_ui = st.sidebar.selectbox(
        "Choose Language", 
        options=lang_names_capitalized, 
        index=current_lang_idx
    )

    if selected_lang_name_ui.lower() != st.session_state.selected_language_name.lower():
        st.session_state.selected_language_name = selected_lang_name_ui
        st.session_state.selected_language_code = SUPPORTED_LANGUAGES[selected_lang_name_ui.lower()]
        st.session_state.chat_history = [] # Reset chat on language change
        st.rerun()

    # --- Display Chat History ---
    # We will handle speaking the latest assistant message after it's generated and added.
    # The chat history will just display the text.
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            # Autoplay handled elsewhere, no st.audio button needed here.

    # --- Conversation Toggle Button ---
    if st.session_state.get('conversation_active', False):
        if st.sidebar.button("End Conversation", key="toggle_conversation_btn", use_container_width=True):
            st.session_state.conversation_active = False
            st.session_state.trigger_listen = False
            st.info("Conversation ended.")
            st.rerun()
    else:
        if st.sidebar.button("Start Conversation", key="toggle_conversation_btn", use_container_width=True):
            st.session_state.conversation_active = True
            st.session_state.trigger_listen = True # Trigger the first listen
            st.info("Conversation started. I'm listening...")
            st.rerun()

    # --- User Input Processing ---
    query_to_process_now = None

    # If conversation is active and a listen is triggered
    if st.session_state.get('conversation_active') and st.session_state.get('trigger_listen'):
        st.session_state.trigger_listen = False # Consume the trigger
        with st.spinner("Listening for your query..."):
            voice_input_text = listen_for_voice_st(lang=st.session_state.selected_language_code)
            if voice_input_text:
                # Pre-fill or directly process this voice input
                st.session_state.query_to_process_from_voice = voice_input_text
                # No immediate rerun here, let the logic below pick it up
            elif st.session_state.conversation_active: # If listen failed but conversation is still active
                st.session_state.trigger_listen = True # Re-trigger listen for next cycle
                st.rerun() # Rerun to try listening again if nothing was said

    # Check if there's a query from voice input that needs processing
    if 'query_to_process_from_voice' in st.session_state and st.session_state.query_to_process_from_voice:
        query_to_process_now = st.session_state.pop('query_to_process_from_voice') # Consume it

    # Then, check for typed input via st.chat_input.
    # The `key` parameter makes st.chat_input stateful across reruns.
    # We remove the `value` parameter to avoid the error related to its misuse.
    typed_prompt = st.chat_input(
        f"Ask KisaanVaani (in {st.session_state.selected_language_name})...", 
        key="chat_input_main" 
    )

    if typed_prompt: # User submitted text via chat_input
        query_to_process_now = typed_prompt # Typed input takes precedence if both happen (unlikely)
    
    # Now, if we have a query (either from voice or typed)
    if query_to_process_now:
        # Add user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": query_to_process_now})
        # Displaying the user message will happen on the rerun triggered below or by chat history display logic
        
        # Get AI response
        with st.spinner("KisaanVaani is thinking..."):
            ai_response_text = get_groq_response_st(query_to_process_now)
        
        # Add AI response to chat history (text only first)
        ai_message = {"role": "assistant", "content": ai_response_text}
        st.session_state.chat_history.append(ai_message)

        # Speak the AI response directly after adding to history and before the rerun
        # This ensures the text is on screen when speech starts.
        if st.session_state.get('pyttsx3_engine_initialized', False) and st.session_state.pyttsx3_engine:
            speak_directly(ai_response_text, lang=st.session_state.selected_language_code)
        elif not st.session_state.get('pyttsx3_engine_initialized', False):
            st.warning("TTS engine not initialized, skipping speech.")
        elif not st.session_state.pyttsx3_engine:
            st.warning("TTS engine object is None, skipping speech.")

        # If conversation is active, trigger the next listen cycle
        if st.session_state.get('conversation_active'):
            st.session_state.trigger_listen = True
        
        st.rerun() # Rerun to display the new user message and AI response, and potentially listen again

    # Initial greeting if chat is empty and services are ready
    if not st.session_state.chat_history and st.session_state.get('services_initialized'):
        initial_greeting_map = {
            "en": "Hello! I am KisaanVaani. How can I assist you today?",
            "hi": "नमस्ते! मैं किसानवाणी हूँ। मैं आज आपकी कैसे मदद कर सकता हूँ?",
            "es": "¡Hola! Soy KisaanVaani. ¿Cómo puedo ayudarte hoy?",
            "fr": "Bonjour! Je suis KisaanVaani. Comment puis-je vous aider aujourd'hui?"
        }
        greeting_text = initial_greeting_map.get(st.session_state.selected_language_code, initial_greeting_map['en'])
        
        # Add greeting to chat history (text only first)
        st.session_state.chat_history.append({"role": "assistant", "content": greeting_text})

        # Speak the greeting directly
        if st.session_state.get('pyttsx3_engine_initialized', False) and st.session_state.pyttsx3_engine:
            speak_directly(greeting_text, lang=st.session_state.selected_language_code)
        elif not st.session_state.get('pyttsx3_engine_initialized', False):
            st.warning("TTS engine not initialized, skipping greeting speech.")
        elif not st.session_state.pyttsx3_engine:
            st.warning("TTS engine object is None, skipping greeting speech.")

        st.rerun()

if __name__ == "__main__":
    run_kisaanvaani_app()