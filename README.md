# UN WebTV Analysis Platform

AI-powered platform for automated extraction, analysis, and collaborative research of UN WebTV sessions with speaker diarization, entity extraction, and RAG-powered chat interface.

## Features

- **Automated Transcription**: Extract text from UN WebTV sessions with speaker identification
- **Entity Extraction**: Automatically identify speakers, countries, SDGs, topics, and organizations
- **Smart Catalog**: Browse and search previously analyzed sessions
- **AI Chat Interface**: Ask questions about session content with citations
- **Export Functionality**: Download transcripts and analysis results
- **Cost Optimization**: Reuse previous analyses to save API costs

## Tech Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: Streamlit
- **Transcription**: Azure OpenAI GPT-4o-Transcribe-Diarize
- **AI Models**: Azure OpenAI (GPT-4o, GPT-5)
- **Vector Database**: Azure AI Search
- **Database**: Azure Cosmos DB
- **Storage**: Azure Blob Storage

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Azure account with OpenAI access
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd un-webcast-simple
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your Azure credentials
```

5. Run the application:
```bash
streamlit run app.py
```

## Project Structure

```
un-webcast-simple/
├── app.py                  # Main Streamlit application
├── backend/
│   ├── api/               # FastAPI endpoints
│   ├── services/          # Business logic
│   ├── models/            # Data models
│   └── utils/             # Utility functions
├── config/                # Configuration files
├── tests/                 # Test files
├── scripts/               # Utility scripts
└── docs/                  # Documentation
```

## Documentation

- [Architecture](ARCHITECTURE.md) - System design and technical specifications
- [API Documentation](docs/API.md) - API endpoints and usage
- [Deployment Guide](docs/DEPLOYMENT.md) - Production deployment instructions

## License

MIT License

## Contact

For questions or support, please open an issue on GitHub.
