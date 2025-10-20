import os
import sys
import asyncio
import logging
from datetime import datetime
import uuid
import json

# Import chainlit (fail fast with clear message)
try:
    import chainlit as cl
except ImportError as e:
    logging.error("Failed to import 'chainlit'. Please install it: pip install chainlit")
    raise

# Import dotenv (use no-op fallback if unavailable)
try:
    from dotenv import load_dotenv
except ImportError:
    logging.warning("python-dotenv not available. Environment variables will not be loaded from .env file.")
    def load_dotenv():
        return None

# Add config directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'config'))

# Import project modules (absolute imports from project root)
from agents.orchestrator_agent import OrchestratorAgent
from config.model_config import model_config
from services.s3_client import s3_client
from services.dynamodb_client import dynamodb_client

load_dotenv()

# Also load simple KEY=VALUE pairs from config.yaml into environment if not already set
def load_config_env_from_file(path: str = "config.yaml"):
    try:
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                # Accept simple KEY=VALUE lines
                if "=" in line and ":" not in line.split("=", 1)[0]:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value and key.isupper() and os.getenv(key) is None:
                        os.environ[key] = value
    except Exception:
        # Non-fatal; continue with existing environment
        pass

load_config_env_from_file()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constants for data size management
# Tightened limits and pacing to avoid Engine.IO "Too many packets in payload"
MAX_MESSAGE_SIZE = 3000    # Maximum characters per message chunk
MAX_STEP_SIZE = 4000       # Maximum characters per step
CHUNK_SIZE = 1000          # Size for chunking large content
MAX_TOTAL_CHUNKS = 20      # Cap total number of chunks per send
MAX_PAYLOAD_SIZE = 40000   # Maximum total payload size for a single canvas/message
MAX_RETRIES = 3            # Maximum retry attempts for failed operations
RETRY_DELAY = 1.2          # Base delay between retries in seconds

# Logo file paths
LOGO_NO_BG = "public/logo_no_bg.png"
LOGO_WHITE_BG = "public/logo_white_bg.png"


def chunk_content(content: str, max_size: int = MAX_MESSAGE_SIZE) -> list[str]:
    """Split large content into manageable chunks."""
    if len(content) <= max_size:
        return [content]
    
    chunks = []
    for i in range(0, len(content), max_size):
        chunk = content[i:i + max_size]
        chunks.append(chunk)
    
    # Enforce a hard cap on chunks to avoid flooding the transport
    if len(chunks) > MAX_TOTAL_CHUNKS:
        # Keep the first N-1 chunks and make the last chunk a summary with notice
        limited = chunks[:MAX_TOTAL_CHUNKS - 1]
        remaining_chars = sum(len(c) for c in chunks[MAX_TOTAL_CHUNKS - 1:])
        limited.append(f"\n⚠️ Output truncated. {remaining_chars:,} additional characters omitted.")
        return limited

    return chunks


async def store_large_content(content: str, content_type: str = "output", session_id: str = None) -> str:
    """Store large content in S3 and return a reference key."""
    if not session_id:
        session_id = cl.user_session.get("id", str(uuid.uuid4()))
    
    # Generate unique key for this content
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    content_key = f"sessions/{session_id}/{content_type}_{timestamp}.txt"
    
    try:
        # Store content in S3/MinIO
        success = s3_client.upload_file_object(
            file_data=content.encode('utf-8'),
            object_key=content_key,
            content_type="text/plain",
            metadata={
                "session_id": session_id,
                "content_type": content_type,
                "timestamp": timestamp,
                "size": str(len(content))
            }
        )
        
        if success:
            logger.info(f"✅ Stored {content_type} content in S3: {content_key}")
            return content_key
        else:
            logger.error(f"❌ Failed to store {content_type} content in S3")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error storing content in S3: {e}")
        return None


async def load_content_from_storage(content_key: str) -> str:
    """Load content from S3/MinIO storage."""
    try:
        content_data = s3_client.download_file_object(content_key)
        if content_data:
            content = content_data.decode('utf-8')
            logger.info(f"✅ Loaded content from S3: {content_key}")
            return content
        else:
            logger.error(f"❌ Failed to load content from S3: {content_key}")
            return None
    except Exception as e:
        logger.error(f"❌ Error loading content from S3: {e}")
        return None


async def store_session_data(session_id: str, data: dict):
    """Store session data in DynamoDB."""
    try:
        success = dynamodb_client.save_session_data(session_id, data)
        if success:
            logger.info(f"✅ Stored session data for {session_id}")
        else:
            logger.error(f"❌ Failed to store session data for {session_id}")
    except Exception as e:
        logger.error(f"❌ Error storing session data: {e}")


async def get_session_data(session_id: str) -> dict:
    """Retrieve session data from DynamoDB."""
    try:
        data = dynamodb_client.get_session_data(session_id)
        if data:
            logger.info(f"✅ Retrieved session data for {session_id}")
            return data
        else:
            logger.info(f"ℹ️ No session data found for {session_id}")
            return {}
    except Exception as e:
        logger.error(f"❌ Error retrieving session data: {e}")
        return {}


async def send_large_content(content: str, step_name: str = "Processing"):
    """Send large content in chunks to prevent payload errors with retry logic."""
    logger.info("📤 Sending large content: %d chars in chunks", len(content))
    chunks = chunk_content(content, MAX_MESSAGE_SIZE)
    
    for i, chunk in enumerate(chunks):
        success = False
        retry_count = 0
        
        while not success and retry_count < MAX_RETRIES:
            try:
                await cl.Message(content=f"📄 **{step_name}** (Part {i+1}/{len(chunks)}):\n{chunk}").send()
                success = True
                logger.debug("✅ Sent chunk %d/%d successfully", i+1, len(chunks))
            except (ValueError, RuntimeError, ConnectionError) as e:
                retry_count += 1
                logger.warning("⚠️ Retry %d/%d for chunk %d: %s", retry_count, MAX_RETRIES, i+1, e)
                if retry_count < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY * retry_count)
                else:
                    logger.error("❌ Failed to send chunk %d after %d retries: %s", i+1, MAX_RETRIES, e)
                    # Send a fallback message
                    try:
                        await cl.Message(content=f"⚠️ **{step_name}** (Part {i+1}/{len(chunks)}) - Content too large, showing summary only:\n{chunk[:500]}...").send()
                    except Exception:
                        pass
                    break
        
        # Pacing delay to prevent packet overflow
        await asyncio.sleep(0.35)
    
    logger.info("✅ Completed sending %d chunks", len(chunks))


async def open_canvas(title: str = "Output Canvas", content: str = ""):
    """Render a canvas for displaying final output with robust error handling and storage integration."""
    logger.info("🎨 Opening canvas: %s (%d chars)", title, len(content))
    
    session_id = cl.user_session.get("id", str(uuid.uuid4()))
    content_key = None
    
    # If content is too large, store it in S3 and reference it
    if len(content) > MAX_PAYLOAD_SIZE:
        logger.info("📦 Content too large (%d chars), storing in S3", len(content))
        content_key = await store_large_content(content, "canvas_output", session_id)
        
        if content_key:
            # Create a summary for the canvas with a link to load full content
            canvas_content = f"""**Content Summary:**
{content[:2000]}{'...' if len(content) > 2000 else ''}

**Full Content Available:** 
Content has been stored and can be loaded on demand.
Size: {len(content):,} characters
Storage Key: {content_key}

**Note:** Click "Load Full Content" to view the complete output."""
        else:
            # Fallback to truncated content if storage fails
            canvas_content = content[:MAX_PAYLOAD_SIZE] + "\n\n... (Content truncated due to size limits and storage failure)"
    else:
        canvas_content = content
    
    retry_count = 0
    success = False
    
    while not success and retry_count < MAX_RETRIES:
        try:
            canvas_props = {
                "title": title,
                "content": canvas_content,
                "timestamp": datetime.now().isoformat(),
                "type": "output_canvas",
                "session_id": session_id,
                "content_key": content_key,
                "full_size": len(content)
            }
            
            # Create a simple message with the canvas content instead of custom element
            canvas_message = f"""# {title}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{canvas_content}

---

*Canvas content displayed above. Use the "View Output Canvas" button to access the full canvas view.*"""
            
            await cl.Message(content=canvas_message).send()
            
            # Store canvas state in session for later access
            cl.user_session.set("canvas_state", {
                "title": title,
                "content": canvas_content,
                "timestamp": canvas_props["timestamp"],
                "available": True,
                "content_key": content_key,
                "full_size": len(content)
            })
            
            # Also store in DynamoDB for persistence
            await store_session_data(session_id, {
                "canvas_state": {
                    "title": title,
                    "content_key": content_key,
                    "timestamp": canvas_props["timestamp"],
                    "full_size": len(content)
                }
            })
            
            success = True
            logger.info("✅ Canvas opened successfully: %s", title)
            
        except (ValueError, RuntimeError, ConnectionError) as e:
            retry_count += 1
            logger.warning("⚠️ Canvas retry %d/%d: %s", retry_count, MAX_RETRIES, e)
            if retry_count < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY * retry_count)
            else:
                logger.error("❌ Canvas failed after %d retries: %s", MAX_RETRIES, e)
                # Fallback: store canvas data for manual viewing
                cl.user_session.set("canvas_state", {
                    "title": title,
                    "content": content,
                    "timestamp": datetime.now().isoformat(),
                    "available": False,
                    "error": str(e)
                })
                break
        except Exception as e:
            logger.error("❌ Unexpected canvas error: %s", e)
            # Fallback: store canvas data for manual viewing
            cl.user_session.set("canvas_state", {
                "title": title,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "available": False,
                "error": str(e)
            })
            break


@cl.action_callback("view_canvas")
async def on_view_canvas():
    """Action callback to view the output canvas."""
    canvas_state = cl.user_session.get("canvas_state")
    
    if canvas_state and canvas_state.get("available"):
        try:
            await open_canvas(canvas_state["title"], canvas_state["content"])
            await cl.Message(content="**Canvas opened successfully**").send()
        except Exception as e:
            await cl.Message(content=f"**Could not open canvas:** {str(e)}").send()
    else:
        await cl.Message(content="**No canvas available** - Complete a task first to generate output.").send()


@cl.action_callback("load_content")
async def on_load_content(content_key: str, session_id: str):
    """Action callback to load content from storage."""
    try:
        content = await load_content_from_storage(content_key)
        if content:
            await cl.Message(content=f"**Content loaded successfully** ({len(content):,} characters)").send()
            # Display the content in chunks if it's large
            if len(content) > MAX_MESSAGE_SIZE:
                await send_large_content(content, "Full Content")
            else:
                await cl.Message(content=content).send()
        else:
            await cl.Message(content="**Failed to load content from storage**").send()
    except Exception as e:
        await cl.Message(content=f"**Error loading content:** {str(e)}").send()


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """Hardcoded local login for dev; extendable to Cognito for production."""
    if (username, password) == ("admin", "admin"):
        return cl.User(identifier="admin", metadata={"role": "ADMIN"})
    return None  # Future: integrate with AWS Cognito


@cl.on_chat_start
async def start():
    logger.info("🚀 Starting new chat session")
    
    # Initialize storage services
    try:
        logger.info("🔧 Initializing storage services...")
        
        # Initialize S3/MinIO bucket
        s3_client.create_bucket_if_not_exists()
        
        # Initialize DynamoDB table
        dynamodb_client.create_table_if_not_exists()
        
        logger.info("✅ Storage services initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize storage services: {e}")
        await cl.Message(content=f"⚠️ Storage services initialization failed: {e}").send()
    
    # Initialize session
    session_id = str(uuid.uuid4())
    cl.user_session.set("id", session_id)
    cl.user_session.set("start_time", datetime.now().isoformat())
    
    # Store initial session data
    await store_session_data(session_id, {
        "start_time": datetime.now().isoformat(),
        "status": "active"
    })
    
    # Initialize orchestrator with configured model
    try:
        orchestrator = OrchestratorAgent()
        cl.user_session.set("orchestrator", orchestrator)
        logger.info("✅ Orchestrator initialized successfully")
    except Exception as e:
        logger.error("❌ Failed to initialize orchestrator: %s", e)
        await cl.Message(content=f"❌ **Error:** Failed to initialize orchestrator: {str(e)}").send()
        return
    
    # Display model provider information
    model_provider = model_config.model_provider.upper()
    model_id = model_config.model_id
    logger.info("🤖 Using model: %s (%s)", model_provider, model_id)
    
    # Check for logo files
    logo_info = ""
    
    if os.path.exists(LOGO_NO_BG):
        logo_info += "📸 **Logo (Transparent):** Available\n"
    if os.path.exists(LOGO_WHITE_BG):
        logo_info += "📸 **Logo (White Background):** Available\n"
    
    await cl.Message(
        content=(
            f"**Welcome to the AI RFP Assistant**\n"
            f"**Session ID:** `{session_id}`\n"
            f"**Model Provider:** {model_provider} ({model_id})\n"
            f"**Storage:** S3/MinIO and DynamoDB initialized\n\n"
            f"{logo_info}\n"
            "Upload your RFP or type your query to begin.\n\n"
            "**How it works:**\n"
            "• **Step-by-step Processing:** Each task shows detailed reasoning in collapsible steps\n"
            "• **Output Canvas:** Final results are displayed in a dedicated canvas sidebar\n"
            "• **Multi-Agent Coordination:** Different specialized agents handle different aspects\n"
            "• **Large Document Support:** Optimized handling for extensive RFP documents\n"
            "• **Persistent Storage:** Large outputs stored in S3/MinIO, session data in DynamoDB\n\n"
            "**Available Capabilities:**\n"
            "• Requirements analysis and win themes\n"
            "• Technical solution architecture\n"
            "• Compliance validation and review\n"
            "• Financial modeling and pricing\n"
            "• Content generation and refinement"
        )
    ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """Routes user messages dynamically through the multi-agent orchestration with step visualization and robust error handling."""
    logger.info("📨 Received message: %d chars", len(message.content))
    
    orchestrator: OrchestratorAgent = cl.user_session.get("orchestrator")
    
    if not orchestrator:
        logger.error("❌ Orchestrator not initialized")
        await cl.Message(content="❌ **Error:** Orchestrator not initialized. Please refresh the page.").send()
        return
    
    # Step 1: File Processing
    file_path = None
    if message.elements:
        for element in message.elements:
            if hasattr(element, 'path') and element.path:
                file_path = element.path
                break
    
    # Create main processing step
    async with cl.Step(name="RFP Processing Pipeline", type="run") as main_step:
        main_step.input = message.content
        
        try:
            # Step 2: File Upload Processing
            if file_path:
                async with cl.Step(name="Document Ingestion", type="tool") as ingest_step:
                    ingest_step.input = f"Processing file: {os.path.basename(file_path)}"
                    
                    try:
                        # Check file size
                        file_size = os.path.getsize(file_path)
                        if file_size > 50 * 1024 * 1024:  # 50MB limit
                            raise ValueError(f"File too large: {file_size / (1024*1024):.1f}MB. Maximum size is 50MB.")
                        
                        ingest_step.output = "✅ Document successfully uploaded and parsed"
                        
                        # Show file processing details
                        await cl.Message(
                            content=f"**File uploaded:** {os.path.basename(file_path)}\n"
                                   f"**File size:** {file_size / 1024:.1f} KB\n"
                                   f"**Processing document...**"
                        ).send()
                    except Exception as e:
                        ingest_step.output = f"❌ File processing error: {str(e)}"
                        await cl.Message(content=f"**File Processing Error:** {str(e)}").send()
                        return

            # Step 3: Task Routing & Reasoning Display
            async with cl.Step(name="Task Analysis & Routing", type="run") as routing_step:
                routing_step.input = f"Analyzing query: {message.content}"
                
                try:
                    # Show reasoning process in UI with streaming updates
                    await cl.Message(content="**Analyzing query and determining routing...**").send()
                    
                    # Pass the user query and file path to orchestrator with timeout
                    session_id = cl.user_session.get("id")
                    result = await asyncio.wait_for(
                        orchestrator.run(user_input=message.content, file_path=file_path, session_id=session_id),
                        timeout=300  # 5 minute timeout
                    )
                    
                    routing_step.output = "Task successfully routed to appropriate agent"
                    
                    # Update step with detailed reasoning
                    if isinstance(result, dict) and result.get("reasoning"):
                        reasoning = result.get("reasoning", {})
                        reasoning_summary = f"\n\n**Reasoning Summary:**\n"
                        reasoning_summary += f"• Query Analysis: {reasoning.get('query_analysis', 'N/A')}\n"
                        reasoning_summary += f"• Routing Logic: {reasoning.get('routing_logic', 'N/A')}\n"
                        reasoning_summary += f"• Processing Steps: {len(reasoning.get('processing_steps', []))} steps completed"
                        
                        routing_step.output += reasoning_summary
                        
                except asyncio.TimeoutError:
                    routing_step.output = "❌ Request timed out after 5 minutes"
                    await cl.Message(content="**Request Timeout:** The operation took too long. Please try with a simpler query or smaller file.").send()
                    return
                except Exception as e:
                    routing_step.output = f"❌ Routing error: {str(e)}"
                    await cl.Message(content=f"**Routing Error:** {str(e)}").send()
                    return

            # Step 4: Agent Processing
            if isinstance(result, dict):
                section = result.get("section", "General")
                agent = result.get("agent", "Unknown")
                summary = result.get("summary", "")
                output = result.get("output", "")
                reasoning = result.get("reasoning", {})

                # Show detailed reasoning in UI (with size limits)
                reasoning_content = "**AI Reasoning Process:**\n\n"
                
                if reasoning.get("query_analysis"):
                    reasoning_content += f"**Query Analysis:**\n{reasoning['query_analysis']}\n\n"
                
                if reasoning.get("routing_logic"):
                    reasoning_content += f"**Routing Logic:**\n{reasoning['routing_logic']}\n\n"
                
                if reasoning.get("processing_steps"):
                    reasoning_content += "**Processing Steps:**\n"
                    for i, step in enumerate(reasoning['processing_steps'], 1):
                        reasoning_content += f"{i}. {step}\n"
                
                # Send reasoning in chunks if too large
                if len(reasoning_content) > MAX_MESSAGE_SIZE:
                    await send_large_content(reasoning_content, "AI Reasoning")
                else:
                    await cl.Message(content=reasoning_content).send()

                # Show routing decision summary
                await cl.Message(
                    content=f"**Final Routing Decision:**\n"
                           f"• **Agent Selected:** {agent}\n"
                           f"• **Section:** {section}\n"
                           f"• **Summary:** {summary[:500]}{'...' if len(summary) > 500 else ''}"
                ).send()

                async with cl.Step(name=f"Agent Processing: {agent}", type="run") as agent_step:
                    agent_step.input = f"Agent: {agent}\nSection: {section}\nSummary: {summary[:200]}"
                    
                    # Show processing status
                    await cl.Message(content=f"**Processing with {agent}...**").send()
                    
                    # Handle large output content
                    if len(output) > MAX_STEP_SIZE:
                        agent_step.output = f"Generated {len(output)} characters of content"
                        # Send large content in chunks
                        await send_large_content(output, f"{agent} Output")
                    else:
                        agent_step.output = output[:MAX_STEP_SIZE] + ("..." if len(output) > MAX_STEP_SIZE else "")

                # Step 5: Display Final Output
                canvas_title = f"{agent} - {section}"
                
                # Build comprehensive output content
                final_output = f"""# {canvas_title}

## Summary
{summary}

## AI Reasoning Process
{reasoning.get('routing_logic', 'No reasoning available')}

## Generated Output
{output}
"""
                
                # Display the final output directly
                await cl.Message(content=final_output).send()

                # Step 6: Final Summary
                async with cl.Step(name="Process Complete", type="run") as final_step:
                    final_step.input = "Finalizing response"
                    final_step.output = f"Successfully processed using {agent} for {section} section"

                # Send final summary message
                summary_content = (
                    f"✅ **Processing Complete!**\n\n"
                    f"**Agent Used:** {agent}\n"
                    f"**Section:** {section}\n"
                    f"**Summary:** {summary[:300]}{'...' if len(summary) > 300 else ''}\n\n"
                    f"**Content Length:** {len(output)} characters\n"
                    f"**Status:** Successfully generated and displayed above"
                )
                
                await cl.Message(content=summary_content).send()
                
            else:
                # Handle non-dict results
                async with cl.Step(name="Direct Response", type="run") as direct_step:
                    direct_step.input = message.content
                    
                    result_str = str(result)
                    if len(result_str) > MAX_STEP_SIZE:
                        direct_step.output = f"Generated {len(result_str)} characters of content"
                        await send_large_content(result_str, "Direct Response")
                    else:
                        direct_step.output = result_str[:MAX_STEP_SIZE] + ("..." if len(result_str) > MAX_STEP_SIZE else "")
                
                await cl.Message(content=str(result)[:MAX_MESSAGE_SIZE] + ("..." if len(str(result)) > MAX_MESSAGE_SIZE else "")).send()
                
        except (ValueError, RuntimeError, ConnectionError) as e:
            # Error handling with step
            async with cl.Step(name="Error Handling", type="run") as error_step:
                error_step.input = message.content
                error_step.output = f"Error: {str(e)}"
            
            # Improved error message with retry suggestion
            error_message = (
                f"**Connection Issue Detected**\n\n"
                f"**Error:** {str(e)}\n\n"
                f"**Possible Solutions:**\n"
                f"• Check your internet connection\n"
                f"• Try refreshing the page\n"
                f"• Wait a moment and retry your request\n"
                f"• Try with a smaller file or simpler query\n\n"
                f"If the problem persists, please contact support."
            )
            
            await cl.Message(content=error_message).send()
            
        except Exception as e:
            # Catch-all for unexpected errors
            async with cl.Step(name="Unexpected Error", type="run") as error_step:
                error_step.input = message.content
                error_step.output = f"Unexpected error: {str(e)}"
            
            await cl.Message(
                content=f"**Unexpected Error:** {str(e)}\n\nPlease try again or contact support."
            ).send()


@cl.set_starters
async def set_starters():
    # Check for available icons
    icons = {
        "summarize": "public/summarize.png" if os.path.exists("public/summarize.png") else None,
        "solution": "public/solution.png" if os.path.exists("public/solution.png") else None,
        "compliance": "public/compliance.png" if os.path.exists("public/compliance.png") else None,
        "finance": "public/finance.png" if os.path.exists("public/finance.png") else None,
    }
    
    # Determine logo to use
    logo_icon = None
    if os.path.exists(LOGO_NO_BG):
        logo_icon = LOGO_NO_BG
    elif os.path.exists(LOGO_WHITE_BG):
        logo_icon = LOGO_WHITE_BG
    
    return [
        cl.Starter(
            label="Summarize Uploaded RFP",
            message="Summarize the key requirements of the uploaded RFP.",
            icon=icons["summarize"] or logo_icon,
        ),
        cl.Starter(
            label="Generate Technical Solution",
            message="Generate the technical solution section of the proposal.",
            icon=icons["solution"] or logo_icon,
        ),
        cl.Starter(
            label="Run Compliance Check",
            message="Check the proposal draft against RFP compliance criteria.",
            icon=icons["compliance"] or logo_icon,
        ),
        cl.Starter(
            label="Draft Financial Section",
            message="Generate pricing breakdown and cost justifications.",
            icon=icons["finance"] or logo_icon,
        ),
    ]


MCP_MODE = os.getenv("MCP_MODE", "local")

if MCP_MODE == "cloud":

    @cl.on_mcp_connect
    async def on_mcp_connect(connection):
        """Connects to AWS-hosted MCP servers (for DiagramAgent / SolutionArchitectAgent)."""
        orchestrator: OrchestratorAgent = cl.user_session.get("orchestrator")
        await orchestrator.register_mcp_tools(connection)
        await cl.Message(
            content=f"🔗 Connected to MCP server: **{connection.name}**"
        ).send()

    @cl.on_mcp_disconnect
    async def on_mcp_disconnect(name: str):
        orchestrator: OrchestratorAgent = cl.user_session.get("orchestrator")
        await orchestrator.deregister_mcp_tools(name)
        await cl.Message(
            content=f"❌ Disconnected from MCP server: **{name}**"
        ).send()

@cl.on_chat_end
def on_chat_end():
    user = cl.user_session.get("user")
    user_id = user.identifier if user else 'Anonymous'
    logger.info("💬 Chat session ended for: %s", user_id)
    
    # Clean up session data (Chainlit user_session may not support clear())
    try:
        keys_to_remove = [
            "id",
            "start_time",
            "orchestrator",
            "canvas_state",
        ]
        for k in keys_to_remove:
            try:
                cl.user_session.set(k, None)
            except Exception:
                pass
        logger.debug("✅ Session data keys reset")
    except Exception as e:
        logger.warning("⚠️ Could not reset session data: %s", e)


# Add signal handlers for graceful shutdown
import signal
import sys

def signal_handler(signum, _frame):
    logger.info("🛑 Received signal %d. Shutting down gracefully...", signum)
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
