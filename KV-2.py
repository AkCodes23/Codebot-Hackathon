import speech_recognition as sr
import os
from groq import Groq
from gtts import gTTS
import playsound
import time
import pyttsx3
import tempfile # For gTTS temporary file

GROQ_API_KEY = "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"


LANGUAGE = 'en' # Default to English
SUPPORTED_LANGUAGES = {
    "english": "en",
    "hindi": "hi",
    "spanish": "es",
    "french": "fr",
}

# Initialize TTS Engines
TTS_ENGINE = None # For pyttsx3
PYTTSX3_INITIALIZED_SUCCESSFULLY = False
USE_GTTS = False # Flag to indicate if gTTS should be used

def initialize_tts_engines():
    global TTS_ENGINE, PYTTSX3_INITIALIZED_SUCCESSFULLY

    # Attempt to initialize pyttsx3
    try:
        TTS_ENGINE = pyttsx3.init()
        PYTTSX3_INITIALIZED_SUCCESSFULLY = True
        print("pyttsx3 engine initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize pyttsx3 engine: {e}. pyttsx3 will be unavailable. gTTS will be the only option if selected.")
        TTS_ENGINE = None
        PYTTSX3_INITIALIZED_SUCCESSFULLY = False

    # gTTS doesn't require explicit initialization here, it's used on-the-fly if USE_GTTS is True.

def speak(text, lang=LANGUAGE):
    """Converts text to speech using pyttsx3 or gTTS based on user selection."""
    global TTS_ENGINE, PYTTSX3_INITIALIZED_SUCCESSFULLY, USE_GTTS

    if USE_GTTS:
        # Try gTTS
        try:
            print("Attempting to speak with gTTS...")
            tts_obj = gTTS(text=text, lang=lang, slow=False)
            with tempfile.NamedTemporaryFile(delete=True, suffix='.mp3') as fp:
                tts_obj.save(fp.name)
                playsound.playsound(fp.name)
            print("Successfully spoke with gTTS.")
            return
        except Exception as e:
            print(f"Error in gTTS text-to-speech: {e}. Falling back to console output.")
    elif PYTTSX3_INITIALIZED_SUCCESSFULLY and TTS_ENGINE:
        # Try pyttsx3 (default)
        try:
            print("Attempting to speak with pyttsx3...")
            TTS_ENGINE.say(text)
            TTS_ENGINE.runAndWait()
            print("Successfully spoke with pyttsx3.")
            return
        except Exception as e:
            print(f"Error in pyttsx3 text-to-speech: {e}. Falling back to console output.")
    else:
        # This case handles if pyttsx3 failed to init and gTTS was not chosen
        print("No TTS engine available (pyttsx3 failed, gTTS not selected). Falling back to console output.")

    # Fallback to console print if selected TTS method fails or no engine is available
    print(f"[Fallback Console Output]: {text}")

def listen_for_voice(timeout=8, phrase_time_limit=13):
    """Listens for voice input from the user and converts it to text using Google Speech Recognition."""
    # Note: ElevenLabs primarily offers TTS. For STT, we'll keep using speech_recognition for now.
    # If ElevenLabs offers a direct STT stream/API suitable for this, it can be integrated.
    # For now, this function remains largely unchanged for input.
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    with microphone as source:
        print("Adjusting for ambient noise... Please wait.")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Listening...")
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            print("Recognizing...")
            text = recognizer.recognize_google(audio, language=LANGUAGE)
            print(f"You said (in {LANGUAGE}): {text}")
            return text
        except sr.WaitTimeoutError:
            print("No speech detected within the time limit.")
            return None
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand audio.")
            return None
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during speech recognition: {e}")
            return None

def get_groq_response(client, user_prompt):
    """Sends a prompt to Groq LLM and returns the response."""
    if not user_prompt:
        return "I didn't catch that. Could you please repeat?"
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are KisaanVaani, a helpful voice assistant for farmers. Provide concise and accurate information related to farming, agriculture, and general knowledge useful to farmers. Keep your answers relatively short for voice output."
                },
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=150,
            top_p=1,
            stop=None,
            stream=False, # Keeping stream False as per previous revert, can be re-enabled if needed
        )
        response = chat_completion.choices[0].message.content
        return response
    except Exception as e:
        print(f"Error communicating with Groq API: {e}")
        return "I'm having trouble connecting to my brain right now. Please try again later."

def main():
    """Main function to run the KisaanVaani voice assistant."""
    initialize_tts_engines() # Initialize all TTS engines at the start

    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY is not set in the script.")
        speak("The Groq API key is missing. Please check the configuration.") # speak will use fallbacks
        return

    if not PYTTSX3_INITIALIZED_SUCCESSFULLY:
        print("WARNING: pyttsx3 engine failed to initialize. If gTTS is not selected, output will be text-only.")

    client = Groq(api_key=GROQ_API_KEY)

    # --- Language and TTS Engine Selection ---
    global LANGUAGE, USE_GTTS
    print("Welcome to KisaanVaani!")
    print("Please select your preferred language:")
    for lang_name, lang_code in SUPPORTED_LANGUAGES.items():
        print(f"- {lang_name.capitalize()} (type '{lang_name}')")
    
    chosen_language_name = ""
    while True:
        try:
            user_choice = input("Enter language: ").strip().lower()
            if user_choice in SUPPORTED_LANGUAGES:
                LANGUAGE = SUPPORTED_LANGUAGES[user_choice]
                chosen_language_name = user_choice.capitalize()
                print(f"{chosen_language_name} selected.")
                break
            else:
                print("Invalid language. Please choose from the list.")
        except Exception as e:
            print(f"An error occurred during language selection: {e}. Defaulting to English.")
            LANGUAGE = 'en'
            chosen_language_name = "English"
            break

    # TTS Engine Choice
    while True:
        try:
            tts_choice = input("Use gTTS for speech output? (yes/no, default is pyttsx3): ").strip().lower()
            if tts_choice == 'yes':
                USE_GTTS = True
                print("gTTS selected for speech output.")
                break
            elif tts_choice == 'no' or tts_choice == '':
                USE_GTTS = False
                print("pyttsx3 selected for speech output (default).")
                break
            else:
                print("Invalid choice. Please enter 'yes' or 'no'.")
        except Exception as e:
            print(f"An error occurred during TTS selection: {e}. Defaulting to pyttsx3.")
            USE_GTTS = False
            break

    # initialize_tts_engines() is called at the beginning of main.

    initial_greeting = {
        "en": "Hello! I am KisaanVaani, your farming assistant. How can I help you today?",
        "hi": "नमस्ते! मैं किसानवाणी हूँ, आपका खेती सहायक। मैं आज आपकी कैसे मदद कर सकता हूँ?",
        "es": "¡Hola! Soy KisaanVaani, tu asistente agrícola. ¿Cómo puedo ayudarte hoy?",
        "fr": "Bonjour! Je suis KisaanVaani, votre assistant agricole. Comment puis-je vous aider aujourd'hui?"
    }
    speak(initial_greeting.get(LANGUAGE, initial_greeting['en']), lang=LANGUAGE)

    try:
        while True:
            user_input = listen_for_voice()

            if user_input:
                if "exit" in user_input.lower() or "quit" in user_input.lower() or "stop" in user_input.lower():
                    speak("Goodbye! Have a productive day.")
                    break
                
                print("Sending to Groq...")
                ai_response = get_groq_response(client, user_input)
                print(f"KisaanVaani: {ai_response}")
                speak(ai_response)
            else:
                pass 
            
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nExiting KisaanVaani...")
        speak("Shutting down. Goodbye!")
    finally:
        pass

if __name__ == "__main__":
    main()
