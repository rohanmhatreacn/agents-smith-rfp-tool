#!/usr/bin/env python3
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from orchestrator import orchestrator
from config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """
    CLI entry point for the RFP tool.
    Allows running the orchestrator directly from command line without UI.
    Useful for testing, automation, and batch processing.
    """
    parser = argparse.ArgumentParser(
        description="RFP Proposal Generation Tool - AI-powered proposal assistant"
    )
    parser.add_argument(
        '--input',
        '-i',
        required=True,
        help='Input query or instruction for the RFP tool'
    )
    parser.add_argument(
        '--file',
        '-f',
        help='Optional document file to process (PDF, DOCX, XLSX)'
    )
    parser.add_argument(
        '--output',
        '-o',
        help='Output file path for generated proposal (default: auto-generated)'
    )
    parser.add_argument(
        '--format',
        choices=['docx', 'pdf'],
        default='docx',
        help='Output format for final proposal (default: docx)'
    )
    parser.add_argument(
        '--session',
        '-s',
        help='Session ID to continue previous session (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        logger.info("="*60)
        logger.info("RFP Tool - Command Line Interface")
        logger.info(f"Environment: {config.environment}")
        logger.info(f"LLM Provider: {config.get_llm_priority()[0]}")
        logger.info("="*60)
        
        if args.file and not Path(args.file).exists():
            logger.error(f"❌ File not found: {args.file}")
            sys.exit(1)
        
        logger.info(f"📝 Processing query: {args.input[:100]}...")
        
        result = await orchestrator.process(
            user_input=args.input,
            file_path=args.file,
            session_id=args.session
        )
        
        logger.info(f"✅ Agent used: {result['agent']}")
        logger.info(f"💡 Reasoning: {result['reasoning']}")
        
        print("\n" + "="*60)
        print("RESULT:")
        print("="*60)
        print(result['result'])
        print("="*60)
        
        session_id = result['session_id']
        
        if args.output or input("\nGenerate full proposal document? (y/n): ").lower() == 'y':
            output_path = args.output or f".data/proposals/{session_id}.{args.format}"
            proposal_path = await orchestrator.generate_full_proposal(
                session_id,
                args.format
            )
            logger.info(f"✅ Proposal saved to: {proposal_path}")
            print(f"\n📄 Full proposal saved to: {proposal_path}")
        
        logger.info(f"Session ID: {session_id} (use --session {session_id} to continue)")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
