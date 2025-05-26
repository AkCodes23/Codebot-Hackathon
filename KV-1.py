import speech_recognition as sr
import os
from groq import Groq
import time
import pyttsx3

GROQ_API_KEY = "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"

LANGUAGE = 'en' # Default to English
SUPPORTED_LANGUAGES = {
    "english": "en",
    "hindi": "hi",
    "spanish": "es",
    "french": "fr",
}

pyttsx3_engine = None

def initialize_tts_engine():
    """Initializes the pyttsx3 engine."""
    global pyttsx3_engine
    try:
        pyttsx3_engine = pyttsx3.init()
        # You can configure pyttsx3 properties here if needed
        # pyttsx3_engine.setProperty('rate', 150)
        # pyttsx3_engine.setProperty('volume', 0.9)
        print("pyttsx3 engine initialized.")
    except Exception as e:
        print(f"Error initializing pyttsx3: {e}. pyttsx3 will not be available.")
        pyttsx3_engine = None

def speak(text, lang=LANGUAGE): # lang parameter is kept for consistency but not used by pyttsx3 directly for language changes
    """Converts text to speech using pyttsx3, with a console fallback."""
    global pyttsx3_engine

    if pyttsx3_engine:
        try:
            print("Attempting to speak with pyttsx3...")
            pyttsx3_engine.say(text)
            pyttsx3_engine.runAndWait()
            print("Successfully spoke with pyttsx3.")
            return
        except Exception as e:
            print(f"Error in pyttsx3 text-to-speech: {e}. Falling back to console output.")
    else:
        print("pyttsx3 engine not initialized. Falling back to console output.")
    
    # Ultimate fallback: console print
    print(f"[Fallback Console Output]: {text}")

def listen_for_voice(timeout=8, phrase_time_limit=18): # Increased phrase_time_limit by 5 seconds
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
    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY is not set in the script.")
        speak("The Groq API key is missing. Please check the configuration.")
        return

    client = Groq(api_key=GROQ_API_KEY)

    # --- Language Selection --- (Remains the same)
    global LANGUAGE
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
            print(f"An error occurred: {e}. Defaulting to English.")
            LANGUAGE = 'en' # Fallback to English
            chosen_language_name = "English"
            break

    initialize_tts_engine() # Initialize pyttsx3

    if not pyttsx3_engine:
        print("Critical: pyttsx3 engine failed to initialize. Voice output will be limited to console.")

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