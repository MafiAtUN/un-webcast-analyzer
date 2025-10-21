# UN WebTV Analysis Platform - Technical Architecture

## Executive Summary
A Python-based application for automated extraction, analysis, and collaborative research of UN WebTV sessions with speaker diarization, entity extraction, and RAG-powered chat interface.

## System Architecture

### 1. Data Ingestion Pipeline

#### 1.1 Video Acquisition
- **Input**: UN WebTV URL (e.g., https://webtv.un.org/en/asset/k1b/k1baa85czq)
- **Technology**: Kaltura API extraction or yt-dlp for video download
- **Process**:
  1. Parse session URL to extract Kaltura Entry ID
  2. Fetch session metadata via Kaltura API or web scraping
  3. Download audio stream only (not video) to reduce processing time
  4. Temporary storage in Azure Blob Storage (auto-delete after processing)

#### 1.2 Metadata Extraction
**From UN WebTV Page:**
- Session title
- Date and duration
- Session number and type
- Broadcasting entity (UNOG, UNHQ, etc.)
- Available languages
- Topic classification
- Related documentation links
- Kaltura Entry ID

**Extracted via AI:**
- Speaker names and affiliations
- Countries mentioned/represented
- SDGs referenced (1-17)
- Topics and themes
- Key decisions/resolutions
- Organizations mentioned
- Treaties/conventions referenced

### 2. Transcription & Diarization

#### 2.1 Audio Processing
**Azure AI Service: gpt-4o-transcribe-diarize**
- Deployment: `gpt-4o-transcribe-diarize` (100 TPM, 128K context)
- Features:
  - Speaker diarization (identifies who is speaking)
  - Multi-language support
  - High accuracy for formal speech
  - Timestamp generation

**Alternative/Backup: Azure Speech Services**
- Already configured in .env (AZURE_SPEECH_KEY)
- Batch transcription API
- Speaker diarization capability
- Language detection

#### 2.2 Output Format
```json
{
  "transcript_segments": [
    {
      "speaker_id": "SPEAKER_01",
      "speaker_name": "Ambassador John Smith (USA)", // AI-extracted
      "start_time": "00:00:12",
      "end_time": "00:02:45",
      "text": "Thank you, Mr. President...",
      "language": "en",
      "confidence": 0.95
    }
  ]
}
```

### 3. Entity Extraction & Analysis

#### 3.1 Named Entity Recognition (NER)
**Using GPT-4o or GPT-5 with structured output:**

```python
entities = {
    "speakers": [
        {
            "name": "Ambassador John Smith",
            "country": "United States",
            "role": "Permanent Representative",
            "organization": "US Mission to UN"
        }
    ],
    "countries": ["United States", "China", "Russia", ...],
    "sdgs": [
        {
            "number": 16,
            "name": "Peace, Justice and Strong Institutions",
            "context": "Referenced in discussion of accountability"
        }
    ],
    "topics": ["Human Rights", "Corporate Accountability", "Transnational Corporations"],
    "organizations": ["UN Human Rights Council", "OHCHR"],
    "treaties": ["Universal Declaration of Human Rights"],
    "key_decisions": ["Decision to continue negotiations on Articles 12-24"],
    "interventions_by_country": {
        "United States": 3,
        "European Union": 2,
        ...
    }
}
```

#### 3.2 Topic Modeling & Sentiment
- Extract main themes using LLM
- Sentiment analysis per speaker/country
- Identify controversial topics (opposing viewpoints)
- Generate executive summary

### 4. Database Schema

#### 4.1 Primary Database: Azure Cosmos DB (NoSQL)

**Sessions Collection:**
```json
{
  "id": "k1baa85czq",
  "url": "https://webtv.un.org/en/asset/k1b/k1baa85czq",
  "title": "3rd Meeting, 11th Session...",
  "date": "2025-10-21",
  "duration_seconds": 10193,
  "kaltura_entry_id": "1_baa85czq",
  "session_type": "Intergovernmental Working Group",
  "broadcasting_entity": "UNOG",
  "location": "Palais des Nations, Room XVI",
  "languages": ["ar", "zh", "en", "fr", "ru", "es"],
  "categories": ["Meetings & Events", "Conferences"],
  "processing_status": "completed",
  "processed_date": "2025-10-21T15:30:00Z",
  "audio_blob_url": null, // deleted after processing
  "transcript_blob_url": "https://...",
  "entities": { /* entity extraction results */ },
  "summary": "Executive summary...",
  "view_count": 45,
  "chat_count": 12,
  "created_by": "user@un.org",
  "tags": ["human-rights", "business", "accountability"]
}
```

**Transcripts Collection:**
```json
{
  "id": "k1baa85czq_transcript",
  "session_id": "k1baa85czq",
  "full_text": "Complete transcript...",
  "segments": [ /* speaker segments with timestamps */ ],
  "word_count": 15420,
  "speaker_count": 18,
  "language": "en"
}
```

**Speakers Collection:**
```json
{
  "id": "speaker_john_smith_usa",
  "name": "Ambassador John Smith",
  "country": "United States",
  "role": "Permanent Representative",
  "sessions_participated": ["k1baa85czq", ...],
  "total_interventions": 47
}
```

**Chats Collection:**
```json
{
  "id": "chat_uuid",
  "session_id": "k1baa85czq",
  "user_id": "user@un.org",
  "created_date": "2025-10-21T16:00:00Z",
  "messages": [
    {
      "role": "user",
      "content": "What did the US representative say about corporate accountability?",
      "timestamp": "2025-10-21T16:00:00Z"
    },
    {
      "role": "assistant",
      "content": "The US representative emphasized...",
      "timestamp": "2025-10-21T16:00:05Z",
      "sources": ["segment_45", "segment_67"],
      "tokens_used": 450
    }
  ],
  "total_tokens": 2340,
  "export_count": 2
}
```

#### 4.2 Vector Database: Azure AI Search (with Vector Search)

**Document Structure:**
```json
{
  "id": "k1baa85czq_seg_45",
  "session_id": "k1baa85czq",
  "session_title": "3rd Meeting, 11th Session...",
  "session_date": "2025-10-21",
  "segment_index": 45,
  "speaker_id": "speaker_john_smith_usa",
  "speaker_name": "Ambassador John Smith",
  "country": "United States",
  "text": "Segment text...",
  "start_time": "00:45:12",
  "end_time": "00:47:33",
  "embedding": [0.123, -0.456, ...], // 1536 dimensions
  "topics": ["corporate accountability", "human rights"],
  "sdgs": [16],
  "entities": ["OHCHR", "Business and Human Rights Treaty"]
}
```

### 5. Application Stack

#### 5.1 Backend Framework
**FastAPI (Python 3.11+)**
- Async support for concurrent processing
- WebSocket support for real-time progress updates
- Automatic OpenAPI documentation
- Pydantic models for data validation

#### 5.2 Frontend Framework
**Streamlit or Gradio**
- Rapid development
- Built-in chat interface
- Easy data visualization (charts, tables)
- Simple deployment

**Alternative: React + FastAPI**
- More customizable
- Better performance for large catalogs
- Professional UI/UX

#### 5.3 Key Python Packages
```txt
fastapi==0.104.1
uvicorn==0.24.0
streamlit==1.28.0
openai==1.3.0
azure-cognitiveservices-speech==1.32.0
azure-cosmos==4.5.1
azure-storage-blob==12.19.0
azure-search-documents==11.4.0
yt-dlp==2023.11.16
pydub==0.25.1
pandas==2.1.3
plotly==5.18.0
python-dotenv==1.0.0
httpx==0.25.1
beautifulsoup4==4.12.2
pydantic==2.5.0
```

### 6. Processing Workflow

#### 6.1 Session Upload Flow
```
User pastes URL
    ↓
Extract Kaltura Entry ID
    ↓
Check if session exists in database (deduplication)
    ↓ (if exists)
Navigate to existing analysis + show alert
    ↓ (if new)
Scrape metadata from UN WebTV page
    ↓
Download audio stream (temp storage)
    ↓
Upload to Azure Blob Storage
    ↓
Send to Azure Transcription Service (gpt-4o-transcribe-diarize)
    ↓
Receive transcript with speaker diarization
    ↓
Send to GPT-4o/GPT-5 for entity extraction
    ↓
Generate embeddings for each segment (OpenAI text-embedding-ada-002)
    ↓
Store in Azure AI Search (vector DB)
    ↓
Store metadata in Cosmos DB
    ↓
Generate executive summary
    ↓
Delete temporary audio file
    ↓
Redirect user to chat interface
```

#### 6.2 Chat Flow
```
User sends question
    ↓
Convert question to embedding
    ↓
Vector search in Azure AI Search (retrieve top-k relevant segments)
    ↓
Construct context with retrieved segments
    ↓
Send to GPT-4o/GPT-5 with system prompt
    ↓
Generate response with citations
    ↓
Store chat message in database
    ↓
Display response with sources, charts, tables
```

### 7. Azure Resources Required

1. **Azure Cosmos DB**
   - Purpose: Store sessions, transcripts, speakers, chats
   - Pricing: Serverless or Provisioned throughput (400 RU/s minimum)

2. **Azure Blob Storage**
   - Purpose: Temporary audio storage, transcript storage
   - Pricing: Hot tier for temp files, Cool tier for archives

3. **Azure AI Search**
   - Purpose: Vector search for RAG
   - Pricing: Basic tier with vector search enabled

4. **Azure OpenAI** (already configured)
   - Deployments: gpt-4o-unga, gpt-5-unga, gpt-4o-transcribe-diarize, text-embedding-ada-002 (need to add)
   - Purpose: Transcription, entity extraction, chat, embeddings

5. **Azure Speech Services** (already configured, backup option)
   - Purpose: Alternative transcription service

### 8. Key Features & Optimizations

#### 8.1 Cost Optimization
- **Session Deduplication**: Check database before processing
- **Cached Analyses**: Reuse previous entity extractions
- **Segment-level Storage**: Only retrieve relevant portions for chat
- **Embedding Caching**: Store embeddings, don't regenerate
- **Audio-only Download**: Skip video processing

#### 8.2 Performance Optimizations
- **Async Processing**: FastAPI async endpoints
- **Parallel Embedding**: Batch embed transcript segments
- **Streaming Responses**: Stream chat responses to user
- **Progress Tracking**: WebSocket updates during processing
- **Lazy Loading**: Paginate catalog, load on scroll

#### 8.3 User Experience
- **Real-time Progress**: Show processing steps
- **Smart Alerts**: Notify when session already processed
- **Export Options**: Download transcript (TXT, PDF, DOCX), chat history (PDF, JSON)
- **Citation Links**: Click citation to jump to timestamp
- **Visualization**: Charts for country participation, topic distribution, SDG coverage
- **Search & Filter**: Catalog filtering by date, topic, country, SDG

### 9. Research-Focused Analytics

#### 9.1 Built-in Analysis Templates
- SDG coverage analysis
- Country participation metrics
- Topic evolution over time
- Sentiment analysis by country/bloc
- Speaking time distribution
- Consensus vs. contentious topics
- Coalition detection (who speaks together)

#### 9.2 Visualizations
- Timeline of interventions
- Word clouds for topics
- Network graphs (country relationships)
- SDG heatmaps
- Comparison tables between sessions

### 10. Security & Access Control

- User authentication (Azure AD integration)
- Role-based access (researcher, admin)
- Audit logs for data access
- Rate limiting for API calls
- Data retention policies

## Implementation Phases

### Phase 1: MVP (2-3 weeks)
- Video download & audio extraction
- Transcription with speaker diarization
- Basic entity extraction (speakers, countries)
- Simple chat interface
- Single session analysis page
- Basic catalog page

### Phase 2: Enhanced Features (2 weeks)
- Full entity extraction (SDGs, topics, organizations)
- Vector search with RAG
- Advanced visualizations
- Export functionality
- Session deduplication

### Phase 3: Production Ready (1-2 weeks)
- User authentication
- Performance optimizations
- Error handling & monitoring
- Documentation
- Deployment to Azure

## Cost Analysis & Optimization

### Original Cost Estimate (Monthly)
**Azure Resources:**
- Cosmos DB (Serverless): $25-50
- Blob Storage: $5-10
- AI Search (Basic): $75
- OpenAI API (per session): $2-5 (transcription) + $0.50-2 (analysis)
- Total per session: ~$3-7
- Monthly (50 sessions): ~$250-450

### Optimized Cost Structure (Monthly)

**Cost Reduction Strategies:**

#### 1. Replace Azure AI Search with PostgreSQL + pgvector (FREE on Azure)
- **Current**: Azure AI Search Basic = $75/month
- **New**: Azure Database for PostgreSQL (Free tier or B1ms) = $0-15/month
- **Savings**: $60-75/month
- **Trade-off**: Slightly slower vector search, but adequate for <10k sessions

#### 2. Use Azure Speech Services Instead of GPT-4o-Transcribe
- **Current**: GPT-4o-transcribe-diarize = $2-5 per session
- **New**: Azure Speech Batch Transcription with diarization = $1-1.50 per session
- **Already configured**: You have AZURE_SPEECH_KEY in .env
- **Savings**: $1-3.50 per session → $50-175/month (50 sessions)
- **Trade-off**: None - Azure Speech is excellent for formal UN proceedings

#### 3. Use Whisper Model for Transcription (CHEAPEST)
- **Option A**: Use your existing `whisper` deployment (Azure OpenAI)
  - Cost: ~$0.006 per minute of audio
  - 3-hour session = $1.08
  - **Savings**: $1-4 per session

- **Option B**: Use OpenAI Whisper API directly (if available)
  - Cost: $0.006 per minute
  - Same as above

- **Option C**: Self-hosted Whisper (Open Source)
  - Use Azure Container Instance with GPU
  - Cost: ~$0.50-1 per session (compute time)
  - Initial setup: More complex
  - **Savings**: $1.50-4.50 per session

#### 4. Optimize Entity Extraction
- **Current**: Multiple GPT-4o/GPT-5 calls for entities
- **New**: Single GPT-4o call with structured output (JSON mode)
- Use `gpt-4o-mini` for entity extraction instead of `gpt-4o`
  - Cost: $0.15 per 1M input tokens vs $2.50 per 1M
  - **Savings**: ~$0.30-1.50 per session

#### 5. Use Smaller Embeddings Model
- **Current**: text-embedding-ada-002 (1536 dimensions)
- **New**: text-embedding-3-small (512 dimensions)
  - Cost: $0.02 per 1M tokens vs $0.10 per 1M
  - Smaller storage footprint
  - **Savings**: $0.10-0.30 per session

#### 6. Replace Cosmos DB with PostgreSQL
- **Current**: Cosmos DB Serverless = $25-50/month
- **New**: PostgreSQL (same instance as vector DB) = included
- **Savings**: $25-50/month
- **Trade-off**: None for this use case

#### 7. Aggressive Caching Strategy
- Cache entity extraction results
- Cache embeddings for identical segments
- Cache common queries (e.g., "What SDGs were mentioned?")
- **Estimated savings**: 30-40% reduction in API calls

### Optimized Cost Breakdown (Monthly)

**Infrastructure:**
- PostgreSQL (B1ms tier): $15/month (both metadata + vectors)
- Blob Storage (Cool tier): $3-5/month
- **Subtotal**: ~$20/month

**Per Session Processing:**
- Transcription (Whisper Azure): $1.08 (3-hour session)
- Entity extraction (GPT-4o-mini): $0.20
- Embeddings (text-embedding-3-small): $0.15
- Summary generation (GPT-4o): $0.10
- **Total per session**: ~$1.53

**Monthly Cost (50 sessions):**
- Infrastructure: $20
- Processing: $76.50 (50 × $1.53)
- **Grand Total**: ~$96.50/month

**Cost Reduction: 79% savings** ($450 → $96.50)

### Ultra-Budget Option (<$50/month)

If you want to go even cheaper:

1. **Use Free PostgreSQL Tier** (Azure Database for PostgreSQL Flexible Server)
   - Free tier: 1 vCore, 32GB storage, 750 hours/month
   - Cost: $0 (first 12 months)

2. **Self-hosted Whisper on Azure Container Instances**
   - Spot instances for batch processing
   - Cost: ~$0.50 per session

3. **Use GPT-4o-mini for everything** (except final chat)
   - Entity extraction: $0.10
   - Embeddings: $0.15
   - Summary: $0.05

4. **Aggressive deduplication**
   - Track which sessions are most requested
   - Only fully process on-demand

**Ultra-Budget Breakdown:**
- Infrastructure: $5/month (blob storage only)
- Per session: $0.80
- Monthly (50 sessions): $45/month

### Recommended Configuration (Best Value)

**Best balance of cost, quality, and simplicity:**

```python
# Transcription
TRANSCRIPTION_SERVICE = "azure_speech"  # $1-1.50 per session, excellent quality
# Alternative: "whisper_azure" for $1.08 per session

# Entity Extraction
ENTITY_MODEL = "gpt-4o-mini"  # $0.20 per session
STRUCTURED_OUTPUT = True  # Single API call

# Embeddings
EMBEDDING_MODEL = "text-embedding-3-small"  # $0.15 per session

# Chat Interface
CHAT_MODEL = "gpt-4o-unga"  # Use existing deployment, good quality

# Vector Database
VECTOR_DB = "postgresql_pgvector"  # $15/month

# Metadata Database
METADATA_DB = "postgresql"  # Same instance as vector DB
```

**Expected Cost: ~$100-120/month for 50 sessions**

### Cost Monitoring & Alerts

Set up Azure Cost Management alerts:
- Alert when daily spend exceeds $5
- Alert when monthly spend exceeds $100
- Track per-session costs
- Identify expensive operations

### Future Optimizations

As you scale:
- Batch process sessions during off-peak hours
- Use Reserved Capacity for predictable workloads
- Implement tiered processing (basic vs. deep analysis)
- Cache popular sessions in memory

## Success Metrics

- Processing time per session: < 15 minutes
- Chat response time: < 5 seconds
- User satisfaction: 4.5/5 stars
- Cost per analysis: < $5
- Session reuse rate: > 40%
