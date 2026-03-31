# GenSigLLM

GenSigLLM is a high-availability Generative AI forensic backend service built to verify signature authenticity dynamically via robust vision-language models like GPT-4o, Google Gemini, Groq (LPU), and Local Ollama servers mapping specifically to the FinTech ecosystem.

## Features
- **Strict VLM Forensic Analysis**: Analyzes Line Quality, Proportions, Terminal Strokes, and Structure.
- **Resilient Fallback Pipelines**: Intelligently swaps between `Groq`, `OpenAI` and `Google Gemini` silently if cloud outages or `RateLimitErrors` occur.
- **Instant LPU Telemetry**: Aggressively monitors Playground `token_remaining` headers and intercepts payload usage stats directly to `loguru`.
- **Local Isolated Deployment Support**: Natively integrates with isolated endpoints executing Open Source models via **Ollama** without triggering external fallbacks.
- **Containerized**: Modularly designed for drop-in deployment using Docker & PostgreSQL.

## Initial Setup & Running Locally (Docker)

1. Rename the configuration template:
```bash
cp .env.example .env
```
2. Fill out your API keys (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`) in `.env` if using cloud inference! (Alternatively, set `PRIMARY_LLM_PROVIDER=ollama` and ensure your local server is running).

3. Build and Start the Docker Stack:
```bash
docker-compose up --build -d
```
The FastAPI instance will now run continuously backed by PostgreSQL. 

### Verify Endpoint Example API call:

First route an administrative call to mint an API token for your test usage:

```bash
curl -X POST "http://localhost:8000/api/v1/internal/clients" \
     -H "Content-Type: application/json" \
     -d "{\"organization_name\": \"LocalTech\", \"tier\": \"standard\"}"
```
Copy the returned `api_key` string.

Next, query the verification engine utilizing standard `multipart/form-data`:

```bash
curl -X POST "http://localhost:8000/api/v1/verify" \
     -H "x-api-key: YOUR_GENERATED_API_KEY" \
     -F "genuine_image=@c:/path/to/genuine.jpg" \
     -F "questioned_image=@c:/path/to/questioned.jpg"
```
The engine enforces `< 5MB` constraints and will return absolute structured JSON indicating similarity confidence and forensic evaluation paths.

### For Testing Locally using Python Virtual Environments instead:

1. Open **pgAdmin** or your SQL CLI and create a new database named `gensigllm`.
Open your `.env` file and update `DATABASE_URL` so it points to your actual native PostgreSQL username, password, and port! For example: `DATABASE_URL=postgresql://postgres:my_real_password@localhost:5432/gensigllm`
(Note: The `app/main.py` is configured to instantly create all the necessary tables inside that database as soon as the app boots!)

2. Prepare the Python Environment
Open a terminal in `d:\PythonProjects\GenSigLLM\` and make sure your dependencies are active:

```powershell
# 1. Activate your virtual environment
.\venv\Scripts\activate
# 2. (Optional) Ensure all dependencies are definitely installed natively
pip install -r requirements.txt
```

3. Start the Server natively via Uvicorn
FastAPI uses uvicorn as its lightning-fast production web server. Run this command inside your activated environment:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

--host 0.0.0.0: Makes the API accessible to other computers on your network (and the internet, if port 8000 is open on your firewall).

--workers 4: Spins up 4 separate Python processes to handle massive concurrency natively, something Docker handles implicitly. (This is a production-grade flag!)

```cmd
# Create environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run Uvicorn directly!
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*(Keep in mind the PostgreSQL connection string must resolve correctly, adjust the `.env` target to a localhost pgAdmin instance or use docker-compose just for db)*
