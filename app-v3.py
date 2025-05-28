import streamlit as st
import speech_recognition as sr
import os
from groq import Groq
import time
import pyttsx3
import threading

# --- Constants and Configuration ---
# ENSURE THIS IS YOUR VALID, WORKING GROQ API KEY
GROQ_API_KEY = "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" 

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


# --- LLM Interaction ---
def get_groq_response_st(user_query):
    if 'groq_client' not in st.session_state or st.session_state.groq_client is None:
        print("Groq: LLM client not initialized in session state.")
        return KNOWN_FALLBACK_RESPONSES[0]
    if not user_query or user_query.strip() == "":
        print("Groq: User query is empty.")
        return KNOWN_FALLBACK_RESPONSES[1]
    
    client = st.session_state.groq_client
    try:
        print(f"Groq: Sending query to LLM: '{user_query[:70]}...'")
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are KisaanVaani, a helpful voice assistant for farmers. Provide concise and accurate information related to farming, agriculture, and general knowledge useful to farmers. Keep your answers conversational and relatively short for voice interaction."},
                {"role": "user", "content": user_query}
            ],
            model="llama3-8b-8192", temperature=0.7, max_tokens=250, top_p=1, stream=False
        )
        response = chat_completion.choices[0].message.content
        print(f"Groq: Received response from LLM: '{response[:70]}...'")
        return response
    except Exception as e:
        print(f"Groq: !!! CRITICAL API ERROR during Groq call: {e} !!!")
        return KNOWN_FALLBACK_RESPONSES[2]

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

# --- Unified Input Handler ---
def handle_user_input(user_input_text, input_type="text"):
    print(f"Main: Handling input (Type: {input_type}): '{user_input_text[:70]}...'")
    if not user_input_text or user_input_text.strip() == "": 
        print("Main: Empty user input received. No action taken by handle_user_input.")
        if st.session_state.get('conversation_active', False):
            st.session_state.should_listen = True
        st.rerun() 
        return
    
    st.session_state.chat_history.append({
        "role": "user", 
        "content": f"🎤 {user_input_text}" if input_type == "voice" else user_input_text,
        "input_type": input_type
    })
    
    ai_response = get_groq_response_st(user_input_text)
    
    st.session_state.chat_history.append({"role": "assistant", "content": ai_response, "type": "response"})
    speak_non_blocking(ai_response, lang=st.session_state.selected_language_code)
    
    is_fallback_response = ai_response in KNOWN_FALLBACK_RESPONSES
    conversation_is_active = st.session_state.get('conversation_active', False)

    if conversation_is_active:
        if not is_fallback_response: 
            followup_text = get_followup_question(st.session_state.selected_language_code)
            st.session_state.chat_history.append({"role": "assistant", "content": f"💭 *{followup_text}*", "type": "followup"})
            speak_non_blocking(followup_text, lang=st.session_state.selected_language_code)
        else: 
            print(f"Main: LLM returned a fallback/error ('{ai_response[:30]}...'). No followup question by handle_user_input.")
        
        st.session_state.should_listen = True 
    
    print("Main: handle_user_input finished processing. Rerunning UI.")
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

if __name__ == "__main__":
    run_kisaanvaani_app()
