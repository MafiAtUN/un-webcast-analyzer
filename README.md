# UN WebTV Analysis Platform

AI-powered toolkit for turning United Nations WebTV sessions into structured, research-ready knowledge with automated transcription, entity extraction, analytics, and an interactive chat surface.

## Features

- **UN WebTV ingestion** & session catalog: capture metadata from public session URLs and keep analyses searchable.
- **Transcription with diarization**: leverage Azure OpenAI (GPT-4o Transcribe & Whisper) for high-fidelity, speaker-aware transcripts.
- **Entity & SDG extraction**: identify speakers, countries, organizations, themes, treaties, SDGs, sentiment, and key decisions.
- **Vector-powered semantic search**: index transcript segments in Azure AI Search for lightning-fast retrieval.
- **AI research copilot**: RAG-style chat UI grounded in transcript segments with citations and source timestamps.
- **Analytics & visualizations**: Streamlit dashboards surface speaker participation, topic trends, and geographic coverage.
- **Export & collaboration**: download transcripts, summaries, and analysis artifacts to share with research teams.

## Installation & Setup

### Prerequisites

- Python 3.11+
- FFmpeg and ffprobe (e.g., `brew install ffmpeg` on macOS or `sudo apt install ffmpeg` on Ubuntu)
- Azure subscription with access to OpenAI, Speech Services, Cosmos DB, AI Search, and Blob Storage
- Git

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd un-webcast-simple
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file (or use your secret manager of choice) with the configuration keys expected by `config/settings.py`. A minimal example:

```bash
APP_NAME="UN WebTV Analysis Platform"
AZURE_OPENAI_API_KEY="..."
AZURE_OPENAI_ENDPOINT="https://<your-resource>.openai.azure.com/"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o-unga"
AZURE_TRANSCRIBE_DIARIZE_DEPLOYMENT_NAME="gpt-4o-transcribe-diarize"
AZURE_SPEECH_KEY="..."
AZURE_SPEECH_REGION="eastus2"
COSMOS_ENDPOINT="https://<your-account>.documents.azure.com:443/"
COSMOS_KEY="..."
COSMOS_DATABASE_NAME="untv_analysis"
BLOB_CONNECTION_STRING="DefaultEndpointsProtocol=...;"
BLOB_CONTAINER_AUDIO="audio-temp"
BLOB_CONTAINER_TRANSCRIPTS="transcripts"
SEARCH_ENDPOINT="https://<your-search>.search.windows.net"
SEARCH_API_KEY="..."
SEARCH_INDEX_NAME="untv-segments"
```

Refer to `config/settings.py` for the full list of configurable options (deployment names, rate limits, logging paths, etc.).

### 5. Run the Streamlit application

```bash
streamlit run app.py
```

Optional: if you split the API backend and the UI, expose any FastAPI routes with Uvicorn (e.g., `uvicorn backend.api:app --reload`) before launching the UI.

## Project Structure

```
un-webcast-simple/
├── app.py                 # Streamlit entry point
├── pages/                 # Additional Streamlit pages (visualizations, catalog, etc.)
├── backend/
│   ├── services/          # Ingestion, audio processing, OpenAI, database helpers
│   ├── models/            # Pydantic data models
│   └── api/               # FastAPI surface (coming soon)
├── config/                # Pydantic settings and configuration helpers
├── scripts/               # Operational scripts (maintenance, utilities)
├── tests/                 # Automated test suite
├── docs/                  # Architecture and deployment docs (extend as needed)
└── requirements.txt       # Python dependencies
```

## Testing & Quality Checks

```bash
pytest               # run unit/integration tests
pytest --cov         # include coverage reporting
black .              # format code
flake8               # lint
mypy .               # static type checking
```

## Documentation

- [Architecture](ARCHITECTURE.md) – system design and processing pipeline
- Add API specs, deployment runbooks, and contributor guidelines before public release (see checklist below).

## Contributing

Issues and pull requests are welcome. Please open a discussion if you plan significant changes so we can align on direction and Azure resource usage. See [CONTRIBUTING.md](CONTRIBUTING.md) and follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## License

Distributed under the [MIT License](LICENSE).
