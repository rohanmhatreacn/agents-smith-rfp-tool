import chainlit as cl
import gradio as gr
import asyncio
import logging
from pathlib import Path
from orchestrator import orchestrator
from config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


gradio_app = None


def create_gradio_interface():
    """
    Creates the Gradio interface for proposal refinement and review.
    Provides dedicated UI for editing and customizing agent outputs.
    This interface is embedded in Chainlit for seamless workflow.
    """
    
    def refine_content(content: str, instructions: str) -> str:
        """Refines proposal content based on user instructions."""
        result = asyncio.run(orchestrator.process(
            f"Refine this content based on instructions:\n\nContent: {content}\n\nInstructions: {instructions}"
        ))
        return str(result['result'])
    
    def export_proposal(session_id: str, output_format: str) -> str:
        """Generates final proposal document."""
        try:
            path = asyncio.run(orchestrator.generate_full_proposal(session_id, output_format))
            return f"✅ Proposal exported to: {path}"
        except Exception as e:
            return f"❌ Export failed: {e}"
    
    with gr.Blocks(title="RFP Proposal Refinement") as interface:
        gr.Markdown("# 📝 Proposal Refinement & Export")
        gr.Markdown("Use this interface to refine agent outputs and export final proposals.")
        
        with gr.Tab("Refine Content"):
            gr.Markdown("### Edit and refine proposal sections")
            content_input = gr.Textbox(
                label="Current Content",
                placeholder="Paste agent output here...",
                lines=10
            )
            instructions_input = gr.Textbox(
                label="Refinement Instructions",
                placeholder="E.g., 'Make it more technical' or 'Add cost justification'",
                lines=3
            )
            refine_btn = gr.Button("Refine Content", variant="primary")
            refined_output = gr.Textbox(label="Refined Content", lines=10)
            
            refine_btn.click(
                refine_content,
                inputs=[content_input, instructions_input],
                outputs=refined_output
            )
        
        with gr.Tab("Export Proposal"):
            gr.Markdown("### Generate final proposal document")
            session_input = gr.Textbox(
                label="Session ID",
                placeholder="Enter session ID from chat..."
            )
            format_choice = gr.Radio(
                choices=["docx", "pdf"],
                value="docx",
                label="Output Format"
            )
            export_btn = gr.Button("Generate Proposal", variant="primary")
            export_output = gr.Textbox(label="Export Status", lines=3)
            
            export_btn.click(
                export_proposal,
                inputs=[session_input, format_choice],
                outputs=export_output
            )
        
        with gr.Tab("Help"):
            gr.Markdown("""
            ## 📖 How to Use
            
            ### Refine Content Tab
            1. Copy agent output from the chat
            2. Paste into "Current Content"
            3. Add refinement instructions
            4. Click "Refine Content"
            
            ### Export Proposal Tab
            1. Get Session ID from chat (shown after each query)
            2. Enter Session ID
            3. Choose format (DOCX or PDF)
            4. Click "Generate Proposal"
            
            ### Tips
            - You can refine content multiple times
            - Export includes all agent outputs from the session
            - Diagrams are automatically converted to images
            """)
    
    return interface


@cl.on_chat_start
async def start():
    """
    Initializes the Chainlit chat session.
    Sets up session state and displays welcome message.
    """
    cl.user_session.set("session_id", None)
    
    await cl.Message(
        content=f"""# 🤖 RFP Proposal Assistant

**Environment:** {config.environment.upper()} | **LLM:** {config.get_llm_priority()[0].upper()}

Upload an RFP document or ask a question to get started. The AI will analyze your request and route it to the appropriate specialist agent.

**Available Agents:** Strategist 📊 | Solution Architect 🏗️ | Diagram 📐 | Content ✍️ | Financial 💰 | Compliance ✅ | Review 🔍

💡 Type `/help` to see available commands
"""
    ).send()


@cl.on_message
async def handle_message(message: cl.Message):
    """
    Handles incoming chat messages and file uploads.
    Routes queries through the orchestrator and displays results.
    """
    try:
        file_path = None
        query = message.content or "Analyze this document"
        
        # Check for export command
        if query.lower().startswith('/export'):
            session_id = cl.user_session.get("session_id")
            if not session_id:
                await cl.Message(content="❌ No active session. Please process a document first.").send()
                return
            
            # Parse format from command (default to docx)
            output_format = "docx"
            if "pdf" in query.lower():
                output_format = "pdf"
            
            processing_msg = await cl.Message(content="📄 Generating proposal document...").send()
            
            try:
                output_path = await orchestrator.generate_full_proposal(session_id, output_format)
                await processing_msg.remove()
                await cl.Message(
                    content=f"✅ **Proposal exported successfully!**\n\n📁 File: `{output_path}`\n\nYou can download it from the file browser."
                ).send()
            except Exception as e:
                await processing_msg.remove()
                await cl.Message(content=f"❌ Export failed: {str(e)}").send()
            return
        
        # Check for help command
        if query.lower() in ['/help', 'help']:
            await cl.Message(content="""## 💡 Available Commands

**Export Proposal:**
- `/export` - Generate proposal as DOCX
- `/export pdf` - Generate proposal as PDF

**Tips:**
- Upload an RFP document to get started
- Ask questions like "analyze this RFP" or "create technical architecture"
- Each session maintains context across multiple queries
""").send()
            return
        
        # Handle file uploads
        if message.elements:
            for element in message.elements:
                if hasattr(element, 'path'):
                    file_path = element.path
                    await cl.Message(content=f"📄 Processing file: **{Path(file_path).name}**").send()
                    break
        
        # Show processing indicator
        processing_msg = await cl.Message(content="🔄 Analyzing request...").send()
        
        session_id = cl.user_session.get("session_id")
        
        # Process through orchestrator
        result = await orchestrator.process(
            user_input=query,
            file_path=file_path,
            session_id=session_id
        )
        
        # Update session
        cl.user_session.set("session_id", result['session_id'])
        
        # Format and display agent output
        agent_name = result['agent'].replace('_', ' ').title()
        agent_result = result['result']
        
        # Remove processing message
        await processing_msg.remove()
        
        logger.info(f"Agent result type: {type(agent_result)}")
        logger.info(f"Agent result preview: {str(agent_result)[:200]}")
        
        # Convert result to string if it's not already
        # Handle Strands Agent response objects
        if hasattr(agent_result, '__str__'):
            agent_output = str(agent_result)
        elif isinstance(agent_result, dict):
            agent_output = "\n\n".join([f"**{k.title()}:**\n{v}" for k, v in agent_result.items()])
        elif isinstance(agent_result, list):
            agent_output = "\n\n".join([f"- {item}" for item in agent_result])
        else:
            agent_output = str(agent_result)
        
        # Ensure we have actual content
        if not agent_output or agent_output.strip() == "":
            agent_output = "No output generated. Please try again with a different query."
        
        response_content = f"""## {agent_name} Agent

{agent_output}

---

<details>
<summary>📋 Session Details</summary>

**Agent:** {result['agent']}  
**Reasoning:** {result['reasoning']}  
**Session ID:** `{result['session_id']}`  
**Timestamp:** {result['timestamp']}

💡 Type `/export` to generate a full proposal document

</details>
"""
        
        logger.info(f"Sending response to UI (length: {len(response_content)} chars)")
        response_msg = await cl.Message(content=response_content).send()
        logger.info(f"Response sent successfully: {response_msg is not None}")
        
    except Exception as e:
        logger.error("Error processing message: %s", e, exc_info=True)
        await cl.Message(
            content=f"❌ **Error:** {str(e)}\n\nPlease try again or check the logs."
        ).send()


def launch_gradio():
    """
    Launches the Gradio interface in background.
    Runs on port 7860 for embedding in Chainlit iframe.
    """
    interface = create_gradio_interface()
    interface.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        quiet=True
    )


if __name__ == "__main__":
    import threading
    import sys
    
    logger.info("🚀 Starting RFP Tool with Chainlit")
    logger.info("Environment: %s", config.environment)
    logger.info("LLM: %s", config.get_llm_priority()[0])
    
    # Optionally launch Gradio if --with-gradio flag is passed
    if "--with-gradio" in sys.argv:
        gradio_thread = threading.Thread(target=launch_gradio, daemon=True)
        gradio_thread.start()
        logger.info("✅ Gradio launched on http://localhost:7860")
    else:
        logger.info("💡 Gradio disabled. Use --with-gradio to enable refinement UI")
    
    logger.info("✅ Starting Chainlit...")

