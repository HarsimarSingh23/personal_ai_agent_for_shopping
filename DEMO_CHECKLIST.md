# Demo-day checklist

A short guide to start the project and show it. All commands are for
**PowerShell on Windows**, run from the project folder:

```powershell
cd D:\Projects\personal_ai_agent_for_shopping
```

---

## 1. The day before

- [ ] Run the tests. You should see `161 passed`.
  ```powershell
  .venv\Scripts\python -m pytest -q
  ```
- [ ] Start the backend (step 2) and do one chat and one search, so you know the AI server is up.
- [ ] Open the app on the iPhone once. With a free Apple ID the app stops opening 7 days after it was
      installed; if it does not open, install it again (step 3).
- [ ] Charge the laptop and the phone. Keep a phone hotspot ready as a backup network.

## 2. Start the backend

**Option A – simple (SQLite, no Docker needed)**

`.env` already has `DATABASE_URL=` empty, so the app saves history in `results\sessions.db`.

```powershell
.venv\Scripts\python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

**Option B – Docker (PostgreSQL)** – what was used for all the testing

Open Docker Desktop first (it does not start by itself when you sign in), then:

```powershell
docker compose up -d
```

This starts the backend and the database that are already built. Use `docker compose up --build -d`
only after changing the code (it downloads packages and can fail on slow internet).

**Check it works:** open <http://localhost:8000/health> in a browser. You should see
`"status":"ok"`, `"db":"connected"` and `"llm":"configured"`.

Keep this window open during the demo. Press `Ctrl+C` to stop it at the end.

## 3. Start the app

**On the laptop (any browser)** – easiest for a projector, and the backup if the phone has a problem.
The web app is already built (17 Nov) in `shopping_agent_app\build\web`, so this starts in a second:

```powershell
.venv\Scripts\python -m http.server 5050 --bind 127.0.0.1 --directory shopping_agent_app\build\web
```

Then open <http://localhost:5050>. "Online" under "AI Shopper" means it reached the backend.
(To rebuild it after changing the app: `cd shopping_agent_app` and `flutter build web`.)

**On an Android phone** (USB debugging on, phone and laptop on the same Wi-Fi):

> **Important (checked on 16 Nov 2026):** Android builds fail on this laptop right now with the error
> `25.0.3`. Android Studio's bundled Java is version 25, which this project's Gradle (8.14) cannot use.
> To fix it, install **JDK 17** (for example Eclipse Temurin 17) and tell Flutter to use it:
> ```powershell
> flutter config --jdk-dir "C:\Program Files\Eclipse Adoptium\jdk-17.0.x-hotspot"
> ```
> (use the real folder name). If there is no time, show the demo in **Chrome** instead.

1. Find the laptop's address: run `ipconfig` and note the **IPv4 Address**, e.g. `192.168.1.5`.
2. Allow port 8000 through the firewall (PowerShell **as Administrator**, only once):
   ```powershell
   New-NetFirewallRule -DisplayName "Shopping Agent API" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
   ```
3. On the phone's browser, open `http://192.168.1.5:8000/health`. If it shows `"status":"ok"`, the phone can reach the laptop.
4. Run the app on the phone (use your own IP):
   ```powershell
   cd shopping_agent_app
   flutter run --dart-define=API_BASE_URL=http://192.168.1.5:8000
   ```
   `flutter run` makes a debug build, which is allowed to use plain `http://` on the local network.
   A release APK needs an `https://` backend.

**On an iPhone** (no Mac needed – GitHub builds the app):

1. Get the app: on GitHub, open **Actions → Build iOS IPA**, open the latest green run, and download
   **ai-shopper-ios-app** under *Artifacts*. Unzip it to get `app.ipa`.
   A new build starts by itself when the app code changes on `task2` or `main`. You can also start one
   with **Run workflow**.
2. Install it with **Sideloadly** (Windows): connect the iPhone by USB, drag `app.ipa` into Sideloadly,
   enter your Apple ID and press **Start**. On the iPhone, trust the app in
   *Settings → General → VPN & Device Management*. On iOS 16 and later, also turn on
   *Settings → Privacy & Security → Developer Mode*.
   With a free Apple ID the app works for **7 days**, then install it again.
3. Open the app. When iOS asks to find devices on your **Local Network**, tap **Allow**.
4. Tap the **settings icon** (gear) at the top of the chat screen and enter the laptop's IP, e.g. `192.168.1.5`
   (the app adds `http://` and `:8000`). The dot next to "AI Shopper" turns green when it connects.
   If the Wi-Fi changes, just enter the new IP here. No new build is needed.

**Server address inside the app:** the same settings icon works on Android and the web too. If the app
shows "Can't reach the server", tap **Change** on the red banner.

## 4. What to show (tested on 17 Nov 2026)

| # | Type this | What it shows |
|---|-----------|---------------|
| 1 | `I need earbuds for gym, budget 3000` | Chat understands the need, searches, and shows the **Best pick** with a reason. Tap **Compare all** to see Amazon, Flipkart, Croma and Reliance Digital together, and sort by price or rating. |
| 1b | then `Is it good for running?` | It answers from the real product details (battery, latency) and says honestly what the listing does not mention. |
| 1c | then `ok thanks` | A short reply, no new search. |
| 2 | `mujhe 50000 ke andar laptop chahiye college ke liye` | Hinglish works, and the reply is in Hinglish. Only laptops **under ₹50,000** are shown. Ask `Yeh achi hai?` to get a Hinglish answer about the pick. |
| 3 | `iphone 15` | The same phone compared across Amazon, Flipkart, Croma and Reliance Digital. |
| 4 | `Tell me a joke about politics` | Guardrail: the assistant politely brings the talk back to shopping. |
| 5 | Open the **History** tab | Past searches are saved for this device. |
| 6 | Open <http://localhost:8765> on the laptop (optional) | The AgentMonitor dashboard: every step of a search (scrapers, AI calls) with timings. |

Timing: chat replies in about 1 second; a search takes about 8–15 seconds (up to 20 when Amazon
is slow); the AI's pick inside it takes 1–2 seconds.
Shoes and clothes can take a little longer, because "other stores" then come from a web search (Myntra, Snapdeal and others).

## 5. If something goes wrong

| Problem | What to do |
|---------|------------|
| "You're going a bit fast" message | The limit is 10 searches per minute per device. Wait one minute. To avoid it, add `RATE_LIMIT_SEARCH_PER_MIN=30` to `.env` before the demo and restart the backend. |
| The AI server (gpt-oss) is down | The app still works: chat says "Let me search for that directly", and the search picks the highest-rated product. Replies may be slower. If you have a Gemini key, set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=...` in `.env` and restart. |
| Amazon results are missing | Amazon sometimes blocks automated searches for a short time. Flipkart and other stores still show results. Search again after a minute. |
| Phone cannot connect | Check that both are on the same Wi-Fi and that `http://<laptop IP>:8000/health` opens in the phone's browser. With Docker, Windows already allows Docker through the firewall; without Docker, add the firewall rule from step 3. On iPhone, check *Settings → AI Shopper → Local Network* is on. College Wi-Fi often blocks devices from talking to each other: use the phone's hotspot, run `ipconfig` for the new IP, and enter it with the app's settings icon. |
| Phone cannot connect, and Windows calls the network "Private" | Windows lets the phone reach Docker only on **Public** networks. Either set the network to Public (*Settings → Network & internet → Wi-Fi → the network → Public network*), or run the firewall rule from step 3 once, in PowerShell **as Administrator**. |
| Searches are slow (slow internet) | Add `SCRAPE_PAGES=1` to `.env` and run `docker compose up -d`. Searches then read one page per store: about half the time, fewer products. |
| Backend window was closed | Start it again (step 2). |
| `/health` shows `"db"` not connected | You are using Docker but Docker Desktop is not running, or `.env` has a Postgres `DATABASE_URL` without Postgres running. Use Option A. |
