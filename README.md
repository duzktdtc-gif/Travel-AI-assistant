# Travel AI Assistant

A portfolio-ready full-stack project: **FastAPI + React + LangGraph + Gemini 2.0 Flash**.

## CV-style description

**Travel AI Assistant**  
*Jan 2026 – Feb 2026*

- Designed and implemented a **Multi-Agent Supervisor architecture** using **LangGraph** and **Gemini 2.0 Flash**, enabling autonomous planning, task decomposition, dynamic replanning, and self-reflection.
- Implemented **Human-in-the-Loop confirmation** with interrupt/resume and integrated external APIs: **SerpApi Flights & Hotels**, **OpenWeatherMap**, and **Tavily** for real-time travel data.
- Built a **FastAPI + React** application, containerized with **Docker**, and prepared deployment configuration for **Render**.

## Main features

- Chat UI for travel planning.
- LangGraph workflow with these nodes:
  - `supervisor`
  - `research_agent`
  - `weather_agent`
  - `flight_hotel_agent`
  - `itinerary_agent`
  - `reflection_agent`
  - `approval_node`
  - `finalizer`
- Human approval before final output.
- Replanning when the user rejects the draft itinerary.
- Runs with fallback demo data even if external API keys are not configured.

## Project structure

```txt
travel-ai-assistant/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── graph.py
│   │   │   ├── llm.py
│   │   │   ├── prompts.py
│   │   │   ├── state.py
│   │   │   └── utils.py
│   │   ├── core/
│   │   │   └── config.py
│   │   ├── schemas/
│   │   │   └── chat.py
│   │   ├── tools/
│   │   │   ├── serpapi_tools.py
│   │   │   ├── tavily_search.py
│   │   │   └── weather.py
│   │   └── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docker-compose.yml
├── render.yaml
└── README.md
```

## 1. Run backend locally

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.venv\Scripts\activate

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
# macOS/Linux: cp .env.example .env
```

Open `backend/.env` and add keys:

```env
DASHSCOPE_API_KEY=sk-your-API
DASHSCOPE_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus

TAVILY_API_KEY=
SERPAPI_API_KEY=
OPENWEATHER_API_KEY=

FRONTEND_URL=http://localhost:5173

```

Start server:

```bash
 python -m uvicorn app.main:app --reload --port 8000
```

Check:

```bash
http://localhost:8000/health
```

## 2. Run frontend locally

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

```bash
http://localhost:5173
```

Example prompt:

```txt
Plan a 5-day trip from Hanoi to Tokyo from 2026-07-02 to 2026-07-06, budget $1500, 2 people, food and anime.
```

## 3. Run with Docker Compose

Create `backend/.env` first, then:

```bash
docker compose up --build
```

Open frontend:

```bash
http://localhost:3000
```

Backend:

```bash
http://localhost:8000
```

## 4. API endpoints

### POST `/api/chat`

Request:

```json
{
  "thread_id": null,
  "message": "Plan a 5-day trip from Hanoi to Tokyo from 2026-07-02 to 2026-07-06, budget $1500, 2 people, food and anime."
}
```

Possible response when the graph pauses for approval:

```json
{
  "status": "requires_approval",
  "thread_id": "...",
  "answer": "draft itinerary...",
  "interrupt": {
    "type": "travel_plan_approval",
    "question": "Bạn có muốn xác nhận kế hoạch du lịch này không?...",
    "itinerary": "..."
  }
}
```

### POST `/api/chat/resume`

Approve:

```json
{
  "thread_id": "your-thread-id",
  "approved": true,
  "feedback": ""
}
```

Reject and replan:

```json
{
  "thread_id": "your-thread-id",
  "approved": false,
  "feedback": "Tôi muốn lịch trình nhẹ hơn và nhiều món ăn địa phương hơn."
}
```

## Notes

- `SERPAPI_API_KEY`, `TAVILY_API_KEY`, and `OPENWEATHER_API_KEY` are optional. Without them, the project uses demo fallback data.
- Flight search works best if the user provides airport codes such as `HAN`, `NRT`, `SGN`, `ICN`.
- For production, replace the in-memory LangGraph checkpointer with a persistent checkpointer such as Postgres or Redis.
