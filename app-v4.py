#changes made for optimization: speech_recognition, pyttsx3, and groq are now only imported inside the functions where they're needed.This avoids unnecessary module loading on every Streamlit rerun.
# get_groq_client_resource() is defined with @st.cache_resource. initialize_groq_client() uses this to assign a single instance of the client. All Groq API calls go through st.session_state.groq_client.
# Cached TTS Engine per Language. get_tts_engine(lang) is properly defined and cached. _speak_thread_target(...) uses this cached engine. speak_non_blocking(...) launches the speaking thread and estimates a sleep time. Everything using pyttsx3 is inside function scope.




import streamlit as st
import time
import threading
import os

# <<< If you later add audio_recorder_streamlit or similar, import it inside process_voice_input. >>>

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
WORDS_PER_SECOND = 2.5  # Adjust based on pyttsx3's typical speaking rate and your preference
MIN_SLEEP_AFTER_TTS = 1.0  # Minimum time to wait even for short sentences
MAX_SLEEP_AFTER_TTS = 6.0  # Maximum time to wait, e.g. for a max_tokens=250 response



#Cached Groq Client Factory
@st.cache_resource
def get_groq_client_resource():
    """
    Cached factory for the Groq client. Returns a single instance per user session.
    """
    from groq import Groq  # defer import until actually needed
    return Groq(api_key=GROQ_API_KEY)


#Groq Client Initialization
def initialize_groq_client():
    """
    Initialize the Groq client (once, cached) and store in session_state.
    """
    if 'groq_client' not in st.session_state or st.session_state.groq_client is None:
        if not GROQ_API_KEY:
            print("Main: GROQ_API_KEY is not set. Please provide a valid API key in the script.")
            st.error("Groq API Key is not configured. Please set it in the script.")
            st.session_state.groq_client = None
            return
        try:
            # Use the cached factory to get or create the client
            st.session_state.groq_client = get_groq_client_resource()
            print("Main: Groq client initialized successfully (from cache).")
        except Exception as e:
            print(f"Main: Error initializing Groq client: {e}")
            st.error(f"Failed to initialize Groq client: {e}")
            st.session_state.groq_client = None



# --- Cached Text-to-Speech Engine per Language ---
@st.cache_resource
def get_tts_engine(lang):
    """
    Return a cached pyttsx3 engine configured for the given language.
    """
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)

    # Select voice based on language code
    voices = engine.getProperty('voices')
    target_voice_name_part = lang
    if lang == 'en':
        target_voice_name_part = 'english'
    elif lang == 'hi':
        target_voice_name_part = 'hindi'
    elif lang == 'es':
        target_voice_name_part = 'spanish'
    elif lang == 'fr':
        target_voice_name_part = 'french'

    chosen_id = None
    for v in voices:
        if target_voice_name_part in v.name.lower():
            chosen_id = v.id
            break
    if not chosen_id and voices:
        chosen_id = voices[0].id

    if chosen_id:
        engine.setProperty('voice', chosen_id)
    return engine


# --- Text-to-Speech Thread Target (uses cached engine) ---
def _speak_thread_target(text, lang):
    """
    Use a cached pyttsx3 engine for the given language to speak 'text'.
    """
    try:
        engine = get_tts_engine(lang)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"TTS Thread: ERROR during speech for '{text[:70]}...': {e}")


# --- Non-Blocking Text-to-Speech Function ---
def speak_non_blocking(text, lang='en'):
    """
    Launch a background thread to speak 'text' in 'lang', then
    wait only as long as necessary (bounded by MIN_SLEEP_AFTER_TTS and MAX_SLEEP_AFTER_TTS).
    """
    if not text or text.strip() == "":
        print("Main: speak_non_blocking called with empty text. Skipping speech.")
        return False

    try:
        speech_thread = threading.Thread(target=_speak_thread_target, args=(text, lang))
        speech_thread.daemon = True
        speech_thread.start()

        # Estimate a timeout, then join with timeout rather than sleeping unconditionally
        num_words = len(text.split())
        estimated_duration = (num_words / WORDS_PER_SECOND) + 0.5
        sleep_duration = max(MIN_SLEEP_AFTER_TTS, min(estimated_duration, MAX_SLEEP_AFTER_TTS))

        speech_thread.join(timeout=sleep_duration)
        return True

    except Exception as e:
        print(f"Main: CRITICAL Error starting speech thread for '{text[:70]}...': {e}")
        return False

# --- LLM Interaction ---
def get_groq_response_st(user_query):
    """
    Send 'user_query' to Groq and return the response string.
    We defer importing Groq until here.
    """
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
                {
                    "role": "system",
                    "content": (
                        "You are KisaanVaani, a helpful voice assistant for farmers. Provide concise and accurate information "
                        "related to farming, agriculture, and general knowledge useful to farmers. Keep your answers conversational "
                        "and relatively short for voice interaction."
                    )
                },
                {"role": "user", "content": user_query}
            ],
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=250,
            top_p=1,
            stream=False
        )
        response = chat_completion.choices[0].message.content
        print(f"Groq: Received response from LLM: '{response[:70]}...'")
        return response
    except Exception as e:
        print(f"Groq: !!! CRITICAL API ERROR during Groq call: {e} !!!")
        return KNOWN_FALLBACK_RESPONSES[2]


# --- Speech-to-Text Function ---
def listen_for_voice_st(lang='en', timeout=10, phrase_time_limit=None):
    """
    Listen from the local microphone and return recognized text.
    We defer importing speech_recognition until here.
    """
    try:
        import speech_recognition as sr
    except ImportError:
        print("SR: speech_recognition module not found.")
        return "ERROR"

    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    print(f"SR: Initializing microphone. Timeout: {timeout}s, Phrase Limit: {phrase_time_limit if phrase_time_limit else 'None'}")

    with microphone as source:
        try:
            print("SR: Adjusting for ambient noise (duration 1.5s)...")
            time.sleep(0.1)
            recognizer.adjust_for_ambient_noise(source, duration=1.5)
            print("SR: Ambient noise adjustment complete. Now listening for audio input...")
            # Slightly more sensitive
            recognizer.energy_threshold *= 0.8
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
            print(f"SR: API request error (e.g., network issue, service unavailable); {e}")
            return "ERROR"
        except Exception as e:
            print(f"SR: Unexpected error in listen_for_voice_st: {type(e).__name__} - {e}")
            return "ERROR"


# --- Follow-up Question Generator ---
def get_followup_question(lang='en'):
    questions = {
        "en": "Is there anything else I can help you with regarding farming today?",
        "hi": "क्या मैं आज खेती के बारे में आपकी और कोई मदद कर सकता हूँ?",
        "es": "¿Hay algo más in lo que pueda ayudarte sobre agricultura hoy?",
        "fr": "Y a-t-il autre chose concernant l'agriculture पर मैं आपकी मदद कर सकता हूँ?"
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
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"💭 *{followup_text}*",
                "type": "followup"
            })
            speak_non_blocking(followup_text, lang=st.session_state.selected_language_code)
        else:
            print(f"Main: LLM returned a fallback/error ('{ai_response[:30]}...'). No followup question.")

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

    # <<< TRY to use local microphone; if it fails, fall back to file_uploader >>>
    try:
        voice_result = listen_for_voice_st(lang=st.session_state.selected_language_code)
    except Exception as e:
        status_placeholder.info("🔴 Unable to open microphone. Please upload an audio file instead.", icon="⚠️")
        audio_file = st.file_uploader("Upload a short .wav or .mp3 clip", type=["wav", "mp3"])
        if audio_file is None:
            return

        status_placeholder.info("⏳ Processing uploaded audio...")
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.AudioFile(audio_file) as source:
                audio_data = r.record(source)
                voice_result = r.recognize_google(audio_data, language=st.session_state.selected_language_code)
        except sr.UnknownValueError:
            voice_result = "UNCLEAR"
        except sr.RequestError:
            voice_result = "ERROR"
        except Exception:
            voice_result = "ERROR"

    status_placeholder.empty()
    st.session_state.listening_state = False
    print(f"Main: Voice listen result from STT: '{voice_result}'")

    if voice_result and voice_result not in ["TIMEOUT", "UNCLEAR", "ERROR"]:
        handle_user_input(voice_result, input_type="voice")
    else:
        feedback_map = {
            "TIMEOUT": ("⏰", {
                "en": "I didn't hear anything. Please ensure your microphone is active and try speaking again.",
                "hi": "मुझे कुछ सुनाई नहीं दिया। कृप्या सुनिश्चित करें कि आपका माइक्रोफ़ोन सक्रिय है और फिर से बोलने का प्रयास करें।"
            }),
            "UNCLEAR": ("❓", {
                "en": "I couldn't quite understand what you said. Could you please speak clearly and repeat that?",
                "hi": "मैं ठीक से समझ नहीं पाया कि आपने क्या कहा। क्या आप कृप्या स्पष्ट रूप से बोलकर दोहरा सकते हैं?"
            }),
            "ERROR": ("⚠️", {
                "en": "Sorry, I'm having a bit of trouble with speech recognition at the moment. Please try again shortly.",
                "hi": "क्षमा करें, मुझे इस समय वाक् पहचान में थोड़ी परेशानी हो रही है। कृप्या शीघ्र पुनः प्रयास करें।"
            })
        }
        default_stt_issue_msg = "An issue occurred with voice input. Please try again."
        icon, messages = feedback_map.get(
            voice_result,
            ("❓", {"en": default_stt_issue_msg, "hi": default_stt_issue_msg})
        )

        feedback_text = messages.get(st.session_state.selected_language_code, messages['en'])
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": f"{icon} {feedback_text}",
            "type": "system_feedback"
        })
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
        st.session_state.selected_language_name = 'English'
        st.session_state.selected_language_code = 'en'

    selected_lang_name_ui = st.sidebar.selectbox(
        "Choose Language",
        lang_names_capitalized,
        index=current_lang_idx,
        key="lang_sb"
    )

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
            goodbye_text_map = {
                "en": "Thank you for using KisaanVaani. Goodbye!",
                "hi": "किसानवाणी का उपयोग करने के लिए धन्यवाद। अलविदा!"
            }
            goodbye_text = goodbye_text_map.get(st.session_state.selected_language_code, goodbye_text_map['en'])
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": f"👋 {goodbye_text}",
                "type": "goodbye"
            })
            speak_non_blocking(goodbye_text, lang=st.session_state.selected_language_code)
            st.rerun()
    else:
        if st.sidebar.button("🎤 Start Voice Conversation", type="primary", use_container_width=True, key="start_conv_btn"):
            print("Main: 'Start Conversation' pressed.")
            st.session_state.conversation_active = True
            st.session_state.should_listen = True
            greeting_voice_start_map = {
                "en": "Voice mode activated. How can I assist?",
                "hi": "वॉइस मोड सक्रिय। कैसे मदद कर सकता हूँ?"
            }
            greeting_text = greeting_voice_start_map.get(
                st.session_state.selected_language_code,
                greeting_voice_start_map['en']
            )

            if not st.session_state.chat_history or (
                st.session_state.chat_history and
                st.session_state.chat_history[-1].get("type") not in ["greeting_app_start", "greeting_voice_start"]
            ):
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": f"👋 {greeting_text}",
                    "type": "greeting_voice_start"
                })

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

    if (st.session_state.get('should_listen') and
        st.session_state.get('conversation_active') and
        not st.session_state.get('listening_state')):
        print("Main: Loop trigger: Should listen = True, Active = True, Not Listening = True. Calling process_voice_input.")
        st.session_state.should_listen = False
        process_voice_input()

    typed_prompt = st.chat_input(
        f"Type in {st.session_state.selected_language_name}...",
        key="main_chat_input",
        disabled=st.session_state.get('listening_state', False)
    )
    if typed_prompt:
        print(f"Main: Text input: '{typed_prompt[:70]}...'")
        st.session_state.conversation_active = False
        st.session_state.should_listen = False
        st.session_state.listening_state = False
        handle_user_input(typed_prompt, input_type="text")

    if (not st.session_state.has_greeted_initial and
        st.session_state.get('services_initialized') and
        not st.session_state.chat_history):
        print("Main: Displaying one-time initial app greeting (text mode, chat empty).")
        initial_greeting_text = "Hello! I am KisaanVaani. Start a voice conversation or type your query."
        if st.session_state.selected_language_code == "hi":
            initial_greeting_text = "नमस्ते! मैं किसानवाणी हूँ। वॉइस वार्तालाप शुरू करें या अपना प्रश्न टाइप करें।"

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": f"👋 {initial_greeting_text}",
            "type": "greeting_app_start"
        })
        speak_non_blocking(initial_greeting_text, lang=st.session_state.selected_language_code)
        st.session_state.has_greeted_initial = True
        st.rerun()


if __name__ == "__main__":
    run_kisaanvaani_app()
