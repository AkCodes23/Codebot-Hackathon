import streamlit as st
import speech_recognition as sr
import os
from groq import Groq
import time
import pyttsx3
import threading

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
            # Set speech rate (optional)
            engine.setProperty('rate', 150)  # Adjust speaking speed
            st.session_state.pyttsx3_engine = engine
            st.session_state.pyttsx3_engine_initialized = True
            print("pyttsx3 engine initialized and stored in session state.")
        except Exception as e:
            print(f"Error initializing pyttsx3: {e}. Voice output may not be available.")
            st.session_state.pyttsx3_engine = None
            st.session_state.pyttsx3_engine_initialized = False

# --- Groq Client Initialization ---
def initialize_groq_client():
    """Initializes the Groq client and stores it in session state."""
    if 'groq_client' not in st.session_state or st.session_state.groq_client is None:
        if not GROQ_API_KEY:
            print("GROQ_API_KEY is not set. Cannot connect to LLM.")
            st.session_state.groq_client = None
            return
        try:
            st.session_state.groq_client = Groq(api_key=GROQ_API_KEY)
            print("Groq client initialized and stored in session state.")
        except Exception as e:
            print(f"Error initializing Groq client: {e}")
            st.session_state.groq_client = None

# --- Text-to-Speech Function ---
def speak_directly(text, lang='en'):
    """Converts text to speech using pyttsx3 and plays it directly."""
    if 'pyttsx3_engine_initialized' in st.session_state and st.session_state.pyttsx3_engine_initialized and st.session_state.pyttsx3_engine:
        try:
            engine = st.session_state.pyttsx3_engine
            
            # Set voice based on language if available
            voices = engine.getProperty('voices')
            if voices:
                # Try to find appropriate voice for language
                for voice in voices:
                    if lang == 'hi' and ('hindi' in voice.name.lower() or 'indian' in voice.name.lower()):
                        engine.setProperty('voice', voice.id)
                        break
                    elif lang == 'es' and ('spanish' in voice.name.lower() or 'espanol' in voice.name.lower()):
                        engine.setProperty('voice', voice.id)
                        break
                    elif lang == 'fr' and ('french' in voice.name.lower() or 'francais' in voice.name.lower()):
                        engine.setProperty('voice', voice.id)
                        break
                    elif lang == 'en' and ('english' in voice.name.lower() or 'en' in voice.id.lower()):
                        engine.setProperty('voice', voice.id)
                        break
            
            engine.say(text)
            engine.runAndWait()
            return True
        except Exception as e:
            print(f"Error in pyttsx3 direct speech: {e}")
            return False
    else:
        print("pyttsx3 engine not initialized. Cannot generate audio.")
        return False

# --- LLM Interaction ---
def get_groq_response_st(user_prompt):
    """Sends a prompt to Groq LLM using client from session_state and returns the response."""
    if 'groq_client' not in st.session_state or st.session_state.groq_client is None:
        return "LLM client not initialized. Please check configuration."
    if not user_prompt:
        return "I didn't catch that. Could you please repeat your query?"
    
    client = st.session_state.groq_client
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are KisaanVaani, a helpful voice assistant for farmers. Provide concise and accurate information related to farming, agriculture, and general knowledge useful to farmers. Keep your answers conversational and relatively short for voice interaction."
                },
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=250,
            top_p=1,
            stop=None,
            stream=False,
        )
        response = chat_completion.choices[0].message.content
        return response
    except Exception as e:
        print(f"Error communicating with Groq API: {e}")
        return "I'm having trouble connecting to my knowledge base right now. Please try again in a moment."

# --- Speech-to-Text Function ---
def listen_for_voice_st(lang='en', timeout=10, phrase_time_limit=15):
    """Listens for voice input, converts to text, and returns the text."""
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        try:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=1)
            
            # Listen for audio
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            
            # Recognize speech
            text = recognizer.recognize_google(audio, language=lang)
            return text
        except sr.WaitTimeoutError:
            return "TIMEOUT"
        except sr.UnknownValueError:
            print("Speech Recognition could not understand audio.")
            return "UNCLEAR"
        except sr.RequestError as e:
            print(f"Could not request results from Speech Recognition service; {e}")
            return "ERROR"
        except Exception as e:
            print(f"An unexpected error occurred during speech recognition: {e}")
            return "ERROR"

# --- Follow-up Question Generator ---
def get_followup_question(lang='en'):
    """Returns a follow-up question in the specified language."""
    followup_questions = {
        "en": "What else would you like to know about farming?",
        "hi": "आपको खेती के बारे में और क्या जानना है?",
        "es": "¿Qué más te gustaría saber sobre agricultura?",
        "fr": "Que souhaiteriez-vous savoir d'autre sur l'agriculture?"
    }
    return followup_questions.get(lang, followup_questions['en'])

# --- Unified Input Handler ---
def handle_user_input(user_input, input_type="text"):
    """Unified handler for both voice and text inputs."""
    if not user_input or user_input.strip() == "":
        return
    
    # Add user message to chat (with input type indicator for voice)
    if input_type == "voice":
        st.session_state.chat_history.append({
            "role": "user", 
            "content": f"🎤 {user_input}",
            "input_type": "voice"
        })
    else:
        st.session_state.chat_history.append({
            "role": "user", 
            "content": user_input,
            "input_type": "text"
        })
    
    # Get AI response
    ai_response = get_groq_response_st(user_input)
    
    # Add AI response to chat
    st.session_state.chat_history.append({
        "role": "assistant", 
        "content": ai_response,
        "type": "response"
    })
    
    # Speak the AI response (always, regardless of input type)
    speak_directly(ai_response, lang=st.session_state.selected_language_code)
    
    # If voice conversation is active, add follow-up question
    if st.session_state.get('conversation_active', False):
        followup_text = get_followup_question(st.session_state.selected_language_code)
        
        # Add follow-up question to chat
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": followup_text,
            "type": "followup"
        })
        
        # Speak the follow-up question
        speak_directly(followup_text, lang=st.session_state.selected_language_code)
        
        # Set flag to continue listening after a brief pause
        time.sleep(0.5)  # Brief pause before next listen
        st.session_state.should_listen = True
    
    # Refresh the display
    st.rerun()

# --- Display Chat History ---
def display_chat_history():
    """Display chat history with proper formatting."""
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.markdown(message["content"])
        else:  # assistant
            with st.chat_message("assistant"):
                content = message["content"]
                # Add styling for different types of assistant messages
                if message.get("type") == "followup":
                    st.markdown(f"💭 *{content}*")
                else:
                    st.markdown(content)

# --- Process Voice Input ---
def process_voice_input():
    """Process voice input and handle the conversation flow."""
    st.session_state.listening_state = True
    
    # Listen for voice input
    voice_result = listen_for_voice_st(lang=st.session_state.selected_language_code)
    st.session_state.listening_state = False
    
    if voice_result and voice_result not in ["TIMEOUT", "UNCLEAR", "ERROR"]:
        # Handle successful voice input
        handle_user_input(voice_result, input_type="voice")
        
    elif voice_result == "TIMEOUT":
        timeout_messages = {
            "en": "I didn't hear anything. Please try speaking again.",
            "hi": "मुझे कुछ सुनाई नहीं दिया। कृपया फिर से बोलें।",
            "es": "No escuché nada. Por favor, intenta hablar de nuevo.",
            "fr": "Je n'ai rien entendu. Veuillez essayer de parler à nouveau."
        }
        timeout_text = timeout_messages.get(st.session_state.selected_language_code, timeout_messages['en'])
        
        # Add timeout message to chat
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": f"⏰ {timeout_text}",
            "type": "system"
        })
        
        speak_directly(timeout_text, lang=st.session_state.selected_language_code)
        
        # Continue listening after timeout
        time.sleep(0.5)  # Brief pause before next listen
        st.session_state.should_listen = True
        st.rerun()
        
    elif voice_result == "UNCLEAR":
        unclear_messages = {
            "en": "I couldn't understand what you said. Could you please repeat that?",
            "hi": "मैं समझ नहीं सका कि आपने क्या कहा। कृपया दोहराएं।",
            "es": "No pude entender lo que dijiste. ¿Podrías repetirlo?",
            "fr": "Je n'ai pas pu comprendre ce que vous avez dit. Pourriez-vous répéter?"
        }
        unclear_text = unclear_messages.get(st.session_state.selected_language_code, unclear_messages['en'])
        
        # Add unclear message to chat
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": f"❓ {unclear_text}",
            "type": "system"
        })
        
        speak_directly(unclear_text, lang=st.session_state.selected_language_code)
        
        # Continue listening after unclear speech
        time.sleep(0.5)  # Brief pause before next listen
        st.session_state.should_listen = True
        st.rerun()
    
    else:  # ERROR case
        error_messages = {
            "en": "I'm having trouble with speech recognition. Please try again.",
            "hi": "मुझे वाक् पहचान में समस्या हो रही है। कृपया फिर से कोशिश करें।",
            "es": "Tengo problemas con el reconocimiento de voz. Por favor, inténtalo de nuevo.",
            "fr": "J'ai des problèmes avec la reconnaissance vocale. Veuillez réessayer."
        }
        error_text = error_messages.get(st.session_state.selected_language_code, error_messages['en'])
        
        # Add error message to chat
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": f"⚠️ {error_text}",
            "type": "system"
        })
        
        speak_directly(error_text, lang=st.session_state.selected_language_code)
        
        # Continue listening after error
        time.sleep(0.5)  # Brief pause before next listen
        st.session_state.should_listen = True
        st.rerun()

# --- Streamlit App UI and Logic ---
def run_kisaanvaani_app():
    st.set_page_config(page_title="KisaanVaani Assistant", layout="wide")
    st.title("🌾 KisaanVaani - Your Farming Voice Assistant")

    # Initialize services if not already done
    if 'services_initialized' not in st.session_state:
        initialize_tts_engine()
        initialize_groq_client()
        st.session_state.services_initialized = True
        st.session_state.chat_history = []
        st.session_state.selected_language_code = 'en'
        st.session_state.selected_language_name = 'English'
        st.session_state.conversation_active = False
        st.session_state.listening_state = False
        st.session_state.should_listen = False

    # --- Sidebar for Language Selection ---
    st.sidebar.header("🌍 Language Settings")
    lang_options = list(SUPPORTED_LANGUAGES.keys())
    lang_names_capitalized = [name.capitalize() for name in lang_options]
    
    current_lang_name_cap = st.session_state.selected_language_name.capitalize()
    try:
        current_lang_idx = lang_names_capitalized.index(current_lang_name_cap)
    except ValueError:
        current_lang_idx = 0

    selected_lang_name_ui = st.sidebar.selectbox(
        "Choose Language", 
        options=lang_names_capitalized, 
        index=current_lang_idx
    )

    if selected_lang_name_ui.lower() != st.session_state.selected_language_name.lower():
        st.session_state.selected_language_name = selected_lang_name_ui
        st.session_state.selected_language_code = SUPPORTED_LANGUAGES[selected_lang_name_ui.lower()]
        st.session_state.chat_history = []
        st.rerun()

    # --- Conversation Control ---
    st.sidebar.header("🎙️ Voice Conversation")
    
    if st.session_state.get('conversation_active', False):
        if st.sidebar.button("🛑 End Conversation", type="secondary", use_container_width=True):
            st.session_state.conversation_active = False
            st.session_state.listening_state = False
            st.session_state.should_listen = False
            
            # Say goodbye
            goodbye_messages = {
                "en": "Thank you for using KisaanVaani. Have a great day!",
                "hi": "किसानवाणी का उपयोग करने के लिए धन्यवाद। आपका दिन शुभ हो!",
                "es": "Gracias por usar KisaanVaani. ¡Que tengas un buen día!",
                "fr": "Merci d'avoir utilisé KisaanVaani. Passez une bonne journée!"
            }
            goodbye_text = goodbye_messages.get(st.session_state.selected_language_code, goodbye_messages['en'])
            
            # Add goodbye to chat
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": f"👋 {goodbye_text}",
                "type": "goodbye"
            })
            
            speak_directly(goodbye_text, lang=st.session_state.selected_language_code)
            st.rerun()
    else:
        if st.sidebar.button("🎤 Start Voice Conversation", type="primary", use_container_width=True):
            st.session_state.conversation_active = True
            st.session_state.should_listen = True
            st.rerun()

    # --- Status Display ---
    status_container = st.container()
    
    if st.session_state.get('conversation_active'):
        if st.session_state.get('listening_state'):
            status_container.info("🎤 **Listening...** Speak now!", icon="🔊")
        else:
            status_container.success("🗣️ **Voice conversation active** - Ready to listen", icon="✅")
    else:
        status_container.info("💬 **Type your message or start voice conversation**", icon="ℹ️")

    # --- Display Chat History ---
    chat_container = st.container()
    with chat_container:
        display_chat_history()

    # --- Voice Listening Logic ---
    if st.session_state.get('should_listen') and st.session_state.get('conversation_active'):
        st.session_state.should_listen = False
        
        # Show listening status immediately
        with status_container:
            st.info("🎤 **Listening...** Speak now!", icon="🔊")
        
        # Process voice input
        process_voice_input()
    
    # --- Auto-continue listening for voice conversation ---
    elif st.session_state.get('conversation_active') and not st.session_state.get('listening_state'):
        # If voice conversation is active but not currently listening, start listening
        time.sleep(1)  # Brief pause before next listen
        st.session_state.should_listen = True
        st.rerun()

    # --- Text Input ---
    typed_prompt = st.chat_input(
        f"Type your message in {st.session_state.selected_language_name}...", 
        key="chat_input_main"
    )

    if typed_prompt:
        # Handle text input through unified handler
        handle_user_input(typed_prompt, input_type="text")

    # --- Initial Greeting ---
    if not st.session_state.chat_history and st.session_state.get('services_initialized'):
        initial_greeting_map = {
            "en": "Hello! I am KisaanVaani, your farming assistant. How can I help you today?",
            "hi": "नमस्ते! मैं किसानवाणी हूँ, आपका कृषि सहायक। मैं आज आपकी कैसे मदद कर सकता हूँ?",
            "es": "¡Hola! Soy KisaanVaani, tu asistente agrícola. ¿Cómo puedo ayudarte hoy?",
            "fr": "Bonjour! Je suis KisaanVaani, votre assistant agricole. Comment puis-je vous aider aujourd'hui?"
        }
        greeting_text = initial_greeting_map.get(st.session_state.selected_language_code, initial_greeting_map['en'])
        
        # Add greeting to chat
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": f"👋 {greeting_text}",
            "type": "greeting"
        })
        
        speak_directly(greeting_text, lang=st.session_state.selected_language_code)
        st.rerun()

if __name__ == "__main__":
    run_kisaanvaani_app()
