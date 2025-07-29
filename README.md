# 🌾 KisaanVaani – AI Voice Assistant for Indian Farmers

![MIT Manipal](https://img.shields.io/badge/Built%20at-MIT%20Manipal-blue.svg)
![Made with AI](https://img.shields.io/badge/Powered%20by-AI%20%26%20LLMs-purple.svg)
![Open Source](https://img.shields.io/badge/Open%20Source-Yes-brightgreen.svg)
![GCP Hosted](https://img.shields.io/badge/Hosted%20on-Google%20Cloud-orange.svg)

> **KisaanVaani** (किसानवाणी) means _"The Voice of the Farmer"_.  
> A voice-powered, multilingual AI assistant built to serve India's rural farming communities with crop advice, market rates, weather alerts, and financial tools — even offline.

---

## 🎯 Vision

We aim to **empower Indian farmers** by combining AI with accessibility:  
- 🗣️ Vernacular voice interfaces  
- 📡 Offline & low-connectivity support  
- 🧠 Personalized memory & guidance  
- 🌾 Proactive crop, weather, and financial planning

---

## 🧠 Core Capabilities

### 🔈 Multilingual Voice Assistant
- Whisper ASR for regional dialects
- Synthesized voice responses
- Text/voice toggle
- Hindi, Kannada, Telugu, Marathi, etc.

### 🧠 RAG++ Memory System
- Persistent farmer memory (MongoDB)
- Semantic memory (Milvus)
- Personalized, adaptive conversations

### 🌾 Crop Intelligence
- Crop & fertilizer suggestions
- Seasonal planning
- Soil, region & yield-based recommendations
- Image-based disease detection (coming soon)

### 🌦️ Predictive Weather & Alerts
- Weather integration (OpenWeatherMap)
- Automated forecast-based alerts
- Irrigation & sowing suggestions

### 💰 Market & Financial Tools
- Mandi (market) price updates
- Government scheme info
- Loan calculators, budget planners

### 🧑‍🤝‍🧑 Farmer Community
- Peer-to-peer Q&A
- Local language discussions
- Verified farmer success stories

---

## 🏗️ System Architecture

![System Architecture](architecture.png)

---

## 🛠️ Tech Stack

| Layer         | Tools                               |
|--------------|--------------------------------------|
| Frontend      | Streamlit, Twilio, Voice toggle     |
| Backend       | Python, FastAPI                     |
| LLM Stack     | LangChain + LoRA-tuned LLMs         |
| Speech        | Whisper ASR                         |
| Memory        | MongoDB (chat), Milvus (semantic)   |
| APIs          | OpenWeatherMap, ag-API, Mandi, Tavily |
| Hosting       | Google Cloud Platform (GCP)         |


