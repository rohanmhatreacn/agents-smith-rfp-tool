# 🤖 RFP Proposal Tool

AI-powered Request for Proposal (RFP) response generation tool using multi-agent orchestration. Built with Strands, Chainlit, and Gradio.

## ✨ Features

- **🎯 Intelligent Routing**: Automatically routes queries to specialized AI agents
- **🤖 7 Specialized Agents**: Strategist, Solution Architect, Diagram, Content, Financial, Compliance, Review
- **📄 Document Processing**: Extracts content from PDF, DOCX, XLSX using Docling
- **💾 Auto Storage**: Seamless local (MinIO + SQLite) and cloud (S3 + DynamoDB) storage
- **🎨 Interactive Chat UI**: Chainlit interface with in-chat commands
- **📦 Export**: Generate DOCX and PDF proposals with embedded diagrams
- **🔄 Auto-Deploy**: Docker Compose for local, CloudFormation for AWS

## 🚀 Quick Start

### Prerequisites

- **Python 3.11** (exact version required)
- **Docker** running (for local storage)
- API keys for OpenAI or AWS Bedrock (optional, falls back to Ollama)

### Installation

```bash
# 1. Copy config (optional)
cp .env.example .env

# 2. Start everything
./start.sh
```

The `start.sh` script automatically:
- ✅ Finds Python 3.11
- ✅ Starts Docker/MinIO storage
- ✅ Creates or reuses virtual environment (smart caching!)
- ✅ Installs dependencies only when needed
- ✅ Launches the UI

**First run:** ~2 minutes  
**Subsequent runs:** ~5-10 seconds (venv reused, dependencies cached)

Access the tool at:
- **Chainlit UI**: http://localhost:8000
- **MinIO Console**: http://localhost:9001 (optional, for storage management)

> ⏳ **Note**: The UI takes 20-30 seconds to initialize on startup while loading LLM providers, storage, and agents. Wait for the "RFP Tool is ready!" message.

## 📁 Project Structure

```
rfp-tool/
├── app.py                  # Chainlit + Gradio UI
├── main.py                 # CLI entry point
├── config.py               # Environment detection & config
├── llm.py                  # LLM provider abstraction
├── storage.py              # Storage auto-routing
├── agents.py               # 7 specialized agents
├── orchestrator.py         # Intelligent routing
├── document.py             # Document processing
├── export.py               # DOCX/PDF/Image export
├── start.sh                # Auto-start script
├── docker-compose.yaml      # Local storage
├── cloudformation.yaml      # AWS deployment
├── requirements.txt        # Dependencies
└── tests/                  # Unit & integration tests
```

## 🔧 Configuration

### LLM Provider Priority

The tool automatically selects the best available LLM:

1. **OpenAI** (if `OPENAI_API_KEY` is set)
2. **AWS Bedrock** (if AWS credentials available)
3. **Ollama** (fallback, requires local Ollama server)

### Environment Variables

```bash
# .env file

# OpenAI (Priority 1)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4

# AWS Bedrock (Priority 2)
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# Ollama (Fallback)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Storage (auto-configured)
STORAGE_BUCKET=rfp-tool-storage
STORAGE_TABLE=rfp-tool-sessions
```

## 💻 Usage

### Web UI (Recommended)

1. Start with `./start.sh`
2. Open http://localhost:8000
3. Upload RFP document or type a query
4. Review AI-generated response from the appropriate specialist agent
5. Continue the conversation or use commands:

**Available Chat Commands:**
- `/help` - Show all available commands
- `/export` - Generate proposal as DOCX
- `/export pdf` - Generate proposal as PDF

**Example Workflow:**
```
1. Upload RFP document → AI processes and analyzes
2. Review the analysis in chat
3. Ask follow-up questions (e.g., "Show me the technical architecture")
4. Type `/export` to generate final proposal
5. Download from `.data/proposals/`
```

### Command Line

```bash
# Process a query
python main.py --input "Analyze this RFP for requirements"

# Process with document
python main.py --input "Generate proposal" --file rfp.pdf

# Generate full proposal
python main.py --input "Create proposal" --output proposal.docx --format docx
```

## 🤖 Available Agents

| Agent | Purpose | Output |
|-------|---------|--------|
| **Strategist** | Requirements analysis, win themes | 1 paragraph summary |
| **Solution Architect** | Technical design, AWS architecture | 1 paragraph design |
| **Diagram** | Architecture visualization | JSON diagram data |
| **Content** | Proposal writing, narratives | 1 paragraph content |
| **Financial** | Pricing, cost breakdowns | Simple table (3 rows) |
| **Compliance** | Requirement validation | 1 paragraph review |
| **Review** | Final quality check | 1 paragraph assessment |

## 🧪 Testing

Run tests with:

```bash
pytest tests/ -v
```

Tests include:
- Agent routing logic
- Document extraction
- Storage persistence
- Session management

Try with sample RFP:
```bash
python main.py --input "Analyze" --file tests/sample_rfp.md
```

## ☁️ AWS Deployment

### Deploy Infrastructure

```bash
aws cloudformation create-stack \
  --stack-name rfp-tool-production \
  --template-body file://cloudformation.yaml \
  --parameters ParameterKey=Environment,ParameterValue=production \
  --capabilities CAPABILITY_NAMED_IAM
```

### Update Configuration

After deployment, update `.env`:

```bash
STORAGE_BUCKET=rfp-tool-storage-production
STORAGE_TABLE=rfp-tool-sessions-production
```

The app automatically detects AWS environment and uses cloud resources.

## 🔍 Troubleshooting

### Virtual Environment Issues

The script intelligently manages the virtual environment using hash-based dependency tracking:

**Force dependency reinstall:**
```bash
rm .venv_requirements_hash
./start.sh
```

**Recreate venv completely:**
```bash
rm -rf venv .venv_requirements_hash
./start.sh
```

**How it works:**
- First run: Creates venv, installs all deps (~2 min)
- Subsequent runs: Reuses venv, skips installation (~5-10 sec)
- After `requirements.txt` changes: Auto-detects and updates deps
- Corrupted venv: Automatically recreated

### MinIO Storage Issues

```bash
docker-compose down -v
docker-compose up -d
```

### LLM Connection Issues

1. Check API keys in `.env`
2. Verify AWS credentials: `aws sts get-caller-identity`
3. Test Ollama: `curl http://localhost:11434/api/version`

### Document Processing Fails

Ensure file format is supported:
- ✅ PDF, DOCX, XLSX, MD
- ❌ Scanned images without OCR

### Can't Access UI

The app binds to `localhost:8000`. Access via:
- http://localhost:8000
- http://127.0.0.1:8000

If neither works, check that port 8000 is not in use.

## 📚 Extending the Tool

### Add New Agent

```python
# In agents.py
@tool
def my_agent(query: str) -> str:
    """Agent description"""
    system_prompt = """Specific instructions"""
    agent = Agent(
        model=llm_provider.get_model(),
        system_prompt=system_prompt
    )
    return agent(query)

# Add to registry
AGENT_REGISTRY = {
    ...
    "my_agent": my_agent
}
```

Update routing prompt in `orchestrator.py` to include new agent.

### Add Export Format

```python
# In export.py
def export_custom(content: dict, output_path: str) -> str:
    """Export to custom format"""
    # Implementation
    return output_path
```

### Add UI Component

```python
# In app.py, in create_gradio_interface()
with gr.Tab("New Feature"):
    # Add Gradio components
```

## 🏗️ Architecture

### Design Principles

1. **Auto-Detection:** Environment, credentials, resources detected automatically
2. **Zero Config:** Works with sensible defaults
3. **Graceful Fallback:** LLM providers fail over (OpenAI → Bedrock → Ollama)
4. **Storage Abstraction:** Same API for local/cloud backends
5. **Minimal Code:** ~1,330 lines across 10 files

### System Flow

```
User Input → Document Extraction → Orchestrator Routing → 
Agent Execution → Storage → Response Display
```

For detailed technical architecture, see [ARCHITECTURE.md](ARCHITECTURE.md).

## 🙏 Built With

- [Strands](https://github.com/strands-agents) - Multi-agent framework
- [Chainlit](https://chainlit.io) - Chat UI
- [Gradio](https://gradio.app) - Refinement UI
- [Docling](https://github.com/DS4SD/docling) - Document processing
- AWS Bedrock - Cloud AI services

## 📖 Documentation

- **ARCHITECTURE.md** - Detailed technical architecture and design patterns
- **tests/sample_rfp.md** - Sample RFP for testing

---

**Questions or issues?** Create a GitHub issue or check the troubleshooting section above.
