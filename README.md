
# Codebot-Hackathon
Innotech Manipal
=======
# KisaanVaani Voice Assistant

A voice-powered AI assistant designed specifically for farmers, using Groq and potentially Hugging Face LLM models (though Hugging Face is not yet implemented) to provide agricultural guidance and support.

## Features

-   **Voice Interaction**: Natural conversation through speech recognition and text-to-speech.
-   **Agricultural Expertise**: Specialized knowledge base for farming queries (leveraging the LLM's capabilities).
-   **Multi-language Support**: Supports regional languages for better farmer accessibility (currently configured for English, but adaptable).
-   **Real-time Responses**: Fast responses using the Groq API.

## Prerequisites

-   Python 3.7+ installed.
-   A microphone for voice input.
-   An internet connection.
-   A Groq API key (this project is currently configured to use a hardcoded key for simplicity in a local environment).

## Setup Instructions

1.  **Clone the Repository (or download the files):**

    ```bash
    # If you have git installed
    # git clone <repository_url>
    # cd <repository_directory>
    ```
    If you downloaded the files, navigate to the `main-test` directory.

2.  **Set up a Virtual Environment (Recommended):**

    ```bash
    python -m venv venv
    ```

    Activate the virtual environment:
    -   Windows:
        ```bash
        .\venv\Scripts\activate
        ```
    -   macOS/Linux:
        ```bash
        source venv/bin/activate
        ```

3.  **Install Dependencies:**

    Make sure you are in the `main-test` directory where `requirements.txt` is located.

    ```bash
    pip install -r requirements.txt
    ```
    *Note: If you encounter issues with `PyAudio` installation on Windows, you might need to install it using a pre-compiled wheel or install Microsoft Visual C++ Build Tools. You can often find wheels here: [https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio)*

4.  **Groq API Key Configuration:**

    For this local project setup, the Groq API key has been directly embedded (hardcoded) into the `kisaan_vaani.py` script.
    ```python
    # In kisaan_vaani.py
    GROQ_API_KEY = "your_groq_api_key_here" 
    ```
    **Important Note:** While convenient for local testing, hardcoding API keys is **not recommended** for projects that are shared, version-controlled publicly, or deployed to production environments due to security risks. In such cases, using environment variables (as was the previous setup) is the preferred method.

    You can obtain your own API key from [https://console.groq.com/keys](https://console.groq.com/keys) if you wish to change it or for other projects.

    *A Hugging Face API key was also provided but is not currently used by this application.*


## Running KisaanVaani

1.  Ensure your virtual environment is activated.
2.  Navigate to the directory containing `kisaan_vaani.py` (i.e., `main-test`).
3.  Run the script:

    ```bash
    python kisaan_vaani.py
    ```

4.  The assistant will greet you. Wait for the "Listening..." prompt, then ask your question.
5.  To exit, say "exit", "quit", or "stop", or press `Ctrl+C` in the terminal.

## How it Works

1.  **Voice Input:** The `speech_recognition` library captures audio from your microphone.
2.  **Speech-to-Text:** Google Speech Recognition (via `speech_recognition`) converts your spoken words into text.
3.  **LLM Processing:** The text prompt is sent to a Groq language model (e.g., Llama 3 8B) via the `groq` Python SDK.
4.  **Text-to-Speech:** The LLM's text response is converted back into speech using `gTTS` (Google Text-to-Speech).
5.  **Audio Output:** The `playsound` library plays the generated audio response.

## Customization

-   **Language:** You can change the language for speech recognition and TTS by modifying the `LANGUAGE` variable in `kisaan_vaani.py` (e.g., `'hi'` for Hindi, ensure gTTS supports it).
-   **LLM Model:** You can change the Groq model by modifying the `model` parameter in the `get_groq_response` function in `kisaan_vaani.py`.
-   **System Prompt:** You can tailor the assistant's personality and role by modifying the system message content within the `get_groq_response` function.
-   **Audio Device:** If `speech_recognition` doesn't pick up your default microphone, you might need to specify the device index in `sr.Microphone(device_index=X)`.

## Troubleshooting

-   **`GROQ_API_KEY` issues:** The key is now hardcoded in `kisaan_vaani.py`. If you encounter authentication problems, verify the key within the script is correct and active. For shared/production use, revert to using environment variables for better security.
-   **Microphone issues:** Check your system's microphone settings. Ensure the correct microphone is selected and has the necessary permissions.
-   **`PyAudio` installation:** This can be tricky. Refer to the `pip install` note above or search for specific installation guides for your OS.
-   **No speech detected / Could not understand audio:** Ensure you are in a quiet environment, speak clearly, and are close enough to the microphone.
-   **Internet connection:** Required for both Google Speech Recognition and Groq API calls.
>>>>>>> 458ffb6 (Initial commit of KisaanVaani project)
