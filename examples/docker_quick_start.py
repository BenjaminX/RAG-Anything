#!/usr/bin/env python3
"""
Quick start example for RAG-Anything in Docker
This script can be run directly in the Docker container
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def quick_start(file_path: str, query: str = None):
    """Quick start example with minimal configuration"""
    
    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set in environment")
        print("Please set it in .env file or export OPENAI_API_KEY=your-key")
        return
    
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    print(f"Using API endpoint: {base_url}")
    print(f"Processing file: {file_path}")
    
    # Configuration
    config = RAGAnythingConfig(
        working_dir="/app/rag_storage",
        parser="mineru",
        parse_method="auto",
        enable_image_processing=True,
        enable_table_processing=True,
        enable_equation_processing=True,
    )
    
    # LLM function
    def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
        return openai_complete_if_cache(
            "gpt-4o-mini",
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
    
    # Vision model function for images
    def vision_model_func(prompt, system_prompt=None, history_messages=[], image_data=None, **kwargs):
        if image_data:
            return openai_complete_if_cache(
                "gpt-4o",
                "",
                system_prompt=None,
                history_messages=[],
                messages=[
                    {"role": "system", "content": system_prompt} if system_prompt else None,
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                        ],
                    }
                ],
                api_key=api_key,
                base_url=base_url,
                **kwargs,
            )
        return llm_model_func(prompt, system_prompt, history_messages, **kwargs)
    
    # Embedding function
    embedding_func = EmbeddingFunc(
        embedding_dim=3072,
        max_token_size=8192,
        func=lambda texts: openai_embed(
            texts,
            model="text-embedding-3-large",
            api_key=api_key,
            base_url=base_url,
        ),
    )
    
    try:
        # Initialize RAGAnything
        print("\nInitializing RAG-Anything...")
        rag = RAGAnything(
            config=config,
            llm_model_func=llm_model_func,
            vision_model_func=vision_model_func,
            embedding_func=embedding_func,
        )
        
        # Process document
        print(f"\nProcessing document: {file_path}")
        await rag.process_document_complete(
            file_path=file_path,
            output_dir="/app/output",
            parse_method="auto"
        )
        print("✓ Document processed successfully!")
        
        # Show content statistics
        print("\nDocument statistics:")
        # You can add more detailed stats here
        
        # Perform queries
        if query:
            print(f"\nQuerying: {query}")
            result = await rag.aquery(query, mode="hybrid")
            print("\nQuery Result:")
            print("-" * 80)
            print(result)
            print("-" * 80)
        else:
            # Default queries
            default_queries = [
                "What is the main topic of this document?",
                "What are the key findings or conclusions?",
                "Summarize this document in 3-5 bullet points"
            ]
            
            print("\nRunning default queries:")
            for q in default_queries:
                print(f"\n📝 Query: {q}")
                result = await rag.aquery(q, mode="hybrid")
                print(f"📌 Answer: {result[:500]}..." if len(result) > 500 else f"📌 Answer: {result}")
        
        # Multimodal query example
        print("\n\nMultimodal Query Example:")
        multimodal_result = await rag.aquery_with_multimodal(
            "Based on the document, how would you interpret this data?",
            multimodal_content=[{
                "type": "table",
                "table_data": """
                Metric,Before,After
                Accuracy,85%,95%
                Speed,200ms,120ms
                Cost,$100,$80
                """,
                "table_caption": "Performance Improvements"
            }],
            mode="hybrid"
        )
        print(f"📊 Multimodal Answer: {multimodal_result[:500]}...")
        
        print("\n✅ All operations completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="RAG-Anything Quick Start in Docker")
    parser.add_argument(
        "file",
        nargs="?",
        default="/app/inputs/sample.pdf",
        help="Path to document file (default: /app/inputs/sample.pdf)"
    )
    parser.add_argument(
        "-q", "--query",
        help="Custom query to run on the document"
    )
    args = parser.parse_args()
    
    # Check if file exists
    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}")
        print("\nAvailable files in /app/inputs:")
        input_dir = Path("/app/inputs")
        if input_dir.exists():
            for f in input_dir.iterdir():
                if f.is_file():
                    print(f"  - {f.name}")
        sys.exit(1)
    
    # Run the example
    asyncio.run(quick_start(args.file, args.query))


if __name__ == "__main__":
    main()