# Personal AI Shopping Agent 🛒🤖

A full-stack, AI-powered personal shopping assistant that helps users discover the perfect products through natural conversation. The system converses with the user to uncover their exact needs (e.g., budget, features, brands), masks sensitive data in transit, scrapes real-time deals from Amazon and Flipkart, and recommends the absolute best option—all presented in a beautiful, premium dark-themed Flutter mobile app.

---

## 🌟 Key Features

### Conversational Discovery
- **Smart Interrogation:** The AI dynamically decides how many questions to ask to narrow down your preferences. Vague requests like "laptop" trigger a sequence of questions to determine budget and features, while detailed requests trigger immediate searches.
- **LLM Integration:** Powered by an intelligent backend that connects to Google Gemini or NVIDIA NIM (Llama 3.1) via seamless prompt-engineering.

### Real-Time E-Commerce Scraping
- **Multi-Source:** Instantly scrapes live prices, ratings, and product data concurrently from **Amazon**, **Flipkart**, and the **Web (DuckDuckGo)**.
- **Undetected Web Browsing:** Built with `undetected_chromedriver` to safely retrieve live data without being blocked by anti-bot measures.

### Enterprise-Grade Security
- **Data Loss Prevention (DLP):** Features a robust `guardrails.py` interceptor. Any sensitive PII (like Credit Card numbers) typed into the chat is automatically intercepted and masked (e.g., `****-****-****-1234`) *before* being processed by the LLM or stored in the database.

### Premium Mobile Interface (Flutter)
- **Vibrant Dark Mode:** A stunning, premium aesthetic featuring sleek blacks, glowing gold accents, glassmorphism, and micro-animations.
- **1-Click Checkout:** "Buy with 1-Click" buttons trigger gorgeous success animations.
- **Search History:** A dedicated history tab that fetches entire past search sessions, rendering complete product lists and AI recommendations so you never lose track of a great find.

---

## 🏗️ Architecture

The project is split into a Python backend and a Flutter frontend.

### Backend (`/`)
- **FastAPI:** High-performance REST API routing.
- **PostgreSQL Database:** Persistent storage for user search sessions, metrics, and chat history.
- **Dockerized:** Fully containerized with `docker-compose` orchestrating the API and PostgreSQL.
- **Core Modules:** 
  - `chat_agent.py`: Handles the conversational loop with the LLM.
  - `scraper.py`: Selenium/BeautifulSoup web scraper orchestrator.
  - `guardrails.py`: Security layer for PII masking.
  - `llm.py`: Gateway for integrating with Gemini or NVIDIA NIM.

### Frontend (`/shopping_agent_app`)
- **Flutter:** Cross-platform mobile framework.
- **Provider & Stateful UI:** State management handling the complex conversation and searching states.
- **Modern UI Widgets:** Cached network images, Shimmer loading effects, and `flutter_animate` for buttery smooth transitions.

---

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose
- Flutter SDK (latest stable)
- API Keys: Google Gemini (`GEMINI_API_KEY`) or NVIDIA NIM (`NVIDIA_API_KEY`)

### Backend Setup
1. Clone the repository.
2. In the root directory, create a `.env` file and add your API keys:
   ```env
   LLM_PROVIDER=gemini  # or nvidia
   GEMINI_API_KEY=your_key_here
   DATABASE_URL=postgresql://user:password@db:5432/shopping_db
   ```
3. Boot up the backend and database:
   ```bash
   docker compose up --build -d
   ```
   *The API will be available at `http://localhost:8000`.*

### Frontend Setup
1. Navigate to the Flutter directory:
   ```bash
   cd shopping_agent_app
   ```
2. Install dependencies:
   ```bash
   flutter pub get
   ```
3. Run the app on your preferred emulator or connected device:
   ```bash
   flutter run
   ```

---

## 🛡️ Privacy & Compliance
This project was built with a "Privacy First" mindset. The integrated DLP scanner ensures that no sensitive financial information is leaked to third-party LLM providers.

## 📝 License
This project is licensed under the MIT License.
