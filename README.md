# AI RFP Assistant

An intelligent multi-agent system for Request for Proposal (RFP) analysis, generation, and management. This solution uses specialized AI agents to handle different aspects of RFP processing including requirements analysis, technical solution design, compliance checking, and financial evaluation.

## Features

- **Multi-Agent Architecture**: Specialized agents for different RFP tasks
- **Document Processing**: Upload and analyze RFP documents
- **Interactive Chat UI**: Chainlit-based web interface
- **AWS Integration**: Cloud services for storage and processing
- **Compliance Checking**: Automated validation against RFP criteria
- **Financial Analysis**: Cost breakdown and pricing generation

## Quick Start

1. **Clone and Setup:**
   ```bash
   git clone <repository-url>
   cd agents_smith_rfp
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

3. **Start the Application:**
   ```bash
   # Option 1: Use the startup script (recommended)
   ./start_app.sh
   
   # Option 2: Manual startup
   source venv/bin/activate
   # Backend runs on 8001; Chainlit UI on 8000
   python fastapi_backend.py &  # serves on http://localhost:8001
   chainlit run main.py --port 8000 --host 0.0.0.0
   ```

4. **Access the UI:**
   - Open your browser to `http://localhost:8000`
   - Login with `admin` / `admin` (development credentials)

## Fixed Issues

✅ **Output Display**: Fixed canvas display issues - output now shows directly in the chat
✅ **Reasoning Display**: Fixed reasoning to show actual AI reasoning instead of just process steps  
✅ **Action Validation**: Fixed Action payload validation error
✅ **FastAPI Backend**: Fixed backend startup and stability issues
✅ **Chainlit Module**: Fixed virtual environment activation issues
   ```

### Service Configuration

#### Local Development (Default)
- **DynamoDB**: Local instance on `http://localhost:8000`
- **S3 Storage**: MinIO on `http://localhost:9000`
- **AI Model**: Ollama on `http://localhost:11434`

#### Production Deployment
Set these environment variables to use AWS services:
```bash
export DYNAMODB_LOCAL=false
export S3_LOCAL=false
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-west-2
```

### Service Access URLs

When running locally, you can access:
- **Application**: http://localhost:8080
- **Ollama API**: http://localhost:11434
- **DynamoDB Local**: http://localhost:8000
- **MinIO Console**: http://localhost:9001 (admin: minioadmin/minioadmin123)
- **MinIO API**: http://localhost:9000

### Verify Service Setup
Test that all services are running:
```bash
# Test Ollama
curl http://localhost:11434/api/tags

# Test DynamoDB Local
curl http://localhost:8000

# Test MinIO
curl http://localhost:9000/minio/health/live
```

### Troubleshooting Services
- **Ollama not running**: Run `ollama serve` or `docker-compose up -d ollama`
- **DynamoDB Local not running**: Run `docker-compose up -d dynamodb-local`
- **MinIO not running**: Run `docker-compose up -d minio`
- **Model not found**: Run `ollama pull qwen3:4b` or `docker exec ollama ollama pull qwen3:4b`

### Quick Start (Recommended)

Use the unified development CLI for easy setup and startup:

```bash
# Setup development environment (one-time)
python scripts/dev.py setup

# Start the application (FastAPI + Chainlit)
python scripts/dev.py start

# Check service health
python scripts/dev.py check
```

The setup command will:
1. Create a Python virtual environment (`.venv`)
2. Install all required dependencies
3. Check and start Docker services (DynamoDB Local and MinIO)
4. Verify Ollama setup

The start command will:
1. Start FastAPI backend on port 8000
2. Start Chainlit web interface on port 8081
3. Provide graceful shutdown with Ctrl+C

### Alternative: Individual Commands

You can also run the setup and start scripts individually:

```bash
# Setup only
python scripts/setup.py

# Start only (after setup)
python scripts/start.py
```

### Testing Services

After setup, you can test that all services are working correctly:

```bash
python test_services.py
```

This will run comprehensive tests on both DynamoDB and S3/MinIO services.

### Manual Setup

If you prefer manual setup:

1. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   
   # On macOS/Linux:
   source .venv/bin/activate
   
   # On Windows:
   .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Start the application:**
   ```bash
   # Option 1: Use the unified CLI
   python scripts/dev.py start
   
   # Option 2: Start individual services
   python scripts/start.py
   
   # Option 3: Start Chainlit only
   chainlit run main.py --host localhost --port 8080
   ```

### Access the Application

Once started, open your browser and navigate to:
- **Chainlit App**: http://localhost:8081
- **FastAPI Backend**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

**Default Login Credentials:**
- Username: `admin`
- Password: `admin`

## Project Structure

```
agents_smith_rfp/
├── agents/
│   ├── functional/          # Core processing agents
│   │   ├── ingest_agent.py
│   │   ├── embed_agent.py
│   │   ├── draft_agent.py
│   │   ├── refine_agent.py
│   │   └── export_agent.py
│   ├── specialized/         # Domain-specific agents
│   │   ├── strategist_agent.py
│   │   ├── solution_architect_agent.py
│   │   ├── diagram_agent.py
│   │   ├── content_agent.py
│   │   ├── financial_agent.py
│   │   ├── compliance_agent.py
│   │   └── review_agent.py
│   └── orchestrator_agent.py # Main coordination agent
├── services/                # External service integrations
│   ├── dynamodb_client.py
│   └── s3_client.py
├── utils/                   # Helper utilities
│   └── helpers.py
├── config/                  # Configuration files
│   └── model_config.py
├── assets/                  # Static assets
│   └── logo/
│       ├── accenture_no_bg.png
│       └── accenture_white_bg.jpeg
├── public/                  # Public web assets
│   ├── canvas.html
│   └── canvas.js
├── main.py                  # Chainlit application entry point
├── fastapi_backend.py       # FastAPI backend server
├── scripts/                  # Development scripts
│   ├── dev.py               # Unified development CLI
│   ├── setup.py             # Development environment setup
│   ├── start.py             # Development startup orchestration
│   └── check.py             # Service health checks
├── requirements.txt         # Python dependencies
├── config.yaml             # Configuration file
├── docker-compose.yaml     # Docker services configuration
├── chainlit.md            # Chainlit welcome page
└── README.md              # This file
```

## Usage

1. **Upload RFP Documents**: Use the chat interface to upload RFP documents for analysis
2. **Ask Questions**: Interact with the system using natural language queries
3. **Generate Content**: Request specific sections like technical solutions, financial breakdowns, or compliance checks
4. **Review and Refine**: Use the review agent to polish generated content

### Example Queries

- "Summarize the key requirements of the uploaded RFP"
- "Generate the technical solution section of the proposal"
- "Check the proposal draft against RFP compliance criteria"
- "Generate pricing breakdown and cost justifications"

## Configuration

The application can be configured through environment variables or the `config.yaml` file:

### Environment Variables

- `MODEL_PROVIDER`: "ollama" for local, "bedrock" for AWS Bedrock
- `MODEL_ID`: Model identifier (e.g., "qwen3:4b", "llama3.2:latest")
- `DYNAMODB_LOCAL`: "true" for local DynamoDB, "false" for AWS DynamoDB
- `S3_LOCAL`: "true" for MinIO, "false" for AWS S3
- `MCP_MODE`: "local" for local processing, "cloud" for AWS-hosted MCP servers
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: AWS credentials for production

### Configuration File

Copy `env.qwen.example` to `.env` and modify as needed:

```bash
cp env.qwen.example .env
```

### Service Endpoints

#### Local Development
- DynamoDB: `http://localhost:8000`
- MinIO: `http://localhost:9000`
- Ollama: `http://localhost:11434`

#### Production (AWS)
- DynamoDB: Uses AWS credentials and region
- S3: Uses AWS credentials and region
- Bedrock: Uses AWS credentials and region

## Troubleshooting

### Common Issues

1. **Virtual Environment Issues:**
   - Ensure Python 3.11+ is installed
   - Delete `.venv` folder and run setup again if corrupted

2. **Dependency Installation Issues:**
   - Update pip: `pip install --upgrade pip`
   - Install dependencies individually if bulk install fails

3. **Service Connection Issues:**
   - **DynamoDB Local**: Check if running on port 8000, restart with `docker-compose up -d dynamodb-local`
   - **MinIO**: Check if running on port 9000, restart with `docker-compose up -d minio`
   - **Ollama**: Check if running on port 11434, restart with `ollama serve`

4. **Port Already in Use:**
   - Change the port in `scripts/start.py` or use: `chainlit run main.py --port 8080`

5. **Import Errors:**
   - Ensure virtual environment is activated
   - Verify all dependencies are installed correctly

6. **File Not Found Errors:**
   - Run `python test_services.py` to verify services are working
   - Check that Docker services are running: `docker-compose ps`
   - Verify service health: `curl http://localhost:8000` (DynamoDB), `curl http://localhost:9000/minio/health/live` (MinIO)

### Getting Help

If you encounter issues:
1. Check that all dependencies are installed correctly
2. Verify Python version compatibility
3. Ensure virtual environment is properly activated
4. Check console output for specific error messages

## Development

For development and testing:

```bash
# Run tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_agents.py
```

## License

This project is part of the Agents Smith RFP solution.
