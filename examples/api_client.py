#!/usr/bin/env python3
"""
RAG-Anything API Client
A simple client for interacting with RAG-Anything programmatically
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Any

sys.path.append(str(Path(__file__).parent.parent))

from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc
from dotenv import load_dotenv

load_dotenv()


class RAGAnythingClient:
    """Simple API client for RAG-Anything"""
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.rag: Optional[RAGAnything] = None
        self._initialized = False
        
    async def initialize(self, **kwargs):
        """Initialize the RAG client with optional configuration"""
        if self._initialized:
            return
            
        config = RAGAnythingConfig(
            working_dir=kwargs.get("working_dir", "/app/rag_storage"),
            parser=kwargs.get("parser", "mineru"),
            enable_image_processing=kwargs.get("enable_images", True),
            enable_table_processing=kwargs.get("enable_tables", True),
            enable_equation_processing=kwargs.get("enable_equations", True),
        )
        
        # LLM function
        def llm_model_func(prompt, system_prompt=None, history_messages=[], **kw):
            return openai_complete_if_cache(
                kwargs.get("llm_model", "gpt-4o-mini"),
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages,
                api_key=self.api_key,
                base_url=self.base_url,
                **kw,
            )
        
        # Vision function
        def vision_model_func(prompt, system_prompt=None, history_messages=[], image_data=None, **kw):
            if image_data:
                return openai_complete_if_cache(
                    kwargs.get("vision_model", "gpt-4o"),
                    "",
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
                    api_key=self.api_key,
                    base_url=self.base_url,
                    **kw,
                )
            return llm_model_func(prompt, system_prompt, history_messages, **kw)
        
        # Embedding function
        embedding_func = EmbeddingFunc(
            embedding_dim=kwargs.get("embedding_dim", 3072),
            max_token_size=kwargs.get("max_tokens", 8192),
            func=lambda texts: openai_embed(
                texts,
                model=kwargs.get("embedding_model", "text-embedding-3-large"),
                api_key=self.api_key,
                base_url=self.base_url,
            ),
        )
        
        self.rag = RAGAnything(
            config=config,
            llm_model_func=llm_model_func,
            vision_model_func=vision_model_func,
            embedding_func=embedding_func,
        )
        
        self._initialized = True
        
    async def process_document(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Process a single document"""
        if not self._initialized:
            await self.initialize()
            
        try:
            await self.rag.process_document_complete(
                file_path=file_path,
                output_dir=kwargs.get("output_dir", "/app/output"),
                parse_method=kwargs.get("parse_method", "auto"),
                **kwargs
            )
            return {
                "status": "success",
                "file": file_path,
                "message": "Document processed successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "file": file_path,
                "error": str(e)
            }
    
    async def process_batch(self, files: List[str], **kwargs) -> List[Dict[str, Any]]:
        """Process multiple documents"""
        if not self._initialized:
            await self.initialize()
            
        results = []
        for file in files:
            result = await self.process_document(file, **kwargs)
            results.append(result)
        return results
    
    async def query(self, text: str, mode: str = "hybrid") -> str:
        """Simple text query"""
        if not self._initialized:
            await self.initialize()
            
        return await self.rag.aquery(text, mode=mode)
    
    async def query_multimodal(self, text: str, multimodal_data: List[Dict], mode: str = "hybrid") -> str:
        """Multimodal query with additional content"""
        if not self._initialized:
            await self.initialize()
            
        return await self.rag.aquery_with_multimodal(text, multimodal_data, mode=mode)
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search for relevant content"""
        if not self._initialized:
            await self.initialize()
            
        # Perform search and format results
        results = await self.rag.aquery(query, mode="local")
        
        # Parse and structure results
        return self._parse_search_results(results, top_k)
    
    def _parse_search_results(self, results: str, top_k: int) -> List[Dict]:
        """Parse search results into structured format"""
        # Simple parsing - can be enhanced based on actual output format
        entries = []
        lines = results.split('\n')
        
        for i, line in enumerate(lines[:top_k]):
            if line.strip():
                entries.append({
                    "rank": i + 1,
                    "content": line.strip(),
                    "score": 1.0 - (i * 0.1)  # Simulated score
                })
        
        return entries
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the current RAG instance"""
        if not self._initialized:
            return {"status": "not_initialized"}
            
        # Collect statistics
        return {
            "status": "initialized",
            "working_dir": self.rag.config.working_dir,
            "parser": self.rag.config.parser,
            "features": {
                "images": self.rag.config.enable_image_processing,
                "tables": self.rag.config.enable_table_processing,
                "equations": self.rag.config.enable_equation_processing,
            }
        }


# Example usage functions
async def example_basic_usage():
    """Basic usage example"""
    client = RAGAnythingClient()
    
    # Process a document
    result = await client.process_document("/app/inputs/sample.pdf")
    print(f"Process result: {result}")
    
    # Query
    answer = await client.query("What is the main topic of this document?")
    print(f"Query answer: {answer}")
    
    # Get stats
    stats = await client.get_stats()
    print(f"Stats: {json.dumps(stats, indent=2)}")


async def example_advanced_usage():
    """Advanced usage example with multimodal queries"""
    client = RAGAnythingClient()
    
    # Initialize with custom settings
    await client.initialize(
        llm_model="gpt-4o",
        embedding_model="text-embedding-3-large",
        enable_images=True,
        enable_tables=True
    )
    
    # Process multiple documents
    files = [
        "/app/inputs/doc1.pdf",
        "/app/inputs/doc2.pdf"
    ]
    results = await client.process_batch(files)
    
    for result in results:
        print(f"Processed {result['file']}: {result['status']}")
    
    # Multimodal query
    multimodal_answer = await client.query_multimodal(
        "How does this data compare to the document findings?",
        multimodal_data=[{
            "type": "table",
            "table_data": "Method,Score\nRAG-Anything,95\nBaseline,80",
            "table_caption": "Performance Comparison"
        }]
    )
    print(f"Multimodal answer: {multimodal_answer}")
    
    # Search
    search_results = await client.search("key findings", top_k=3)
    print("Search results:")
    for result in search_results:
        print(f"  {result['rank']}. {result['content'][:100]}...")


async def example_context_manager():
    """Example using context manager pattern"""
    class ManagedRAGClient:
        def __init__(self, *args, **kwargs):
            self.client = RAGAnythingClient(*args, **kwargs)
            
        async def __aenter__(self):
            await self.client.initialize()
            return self.client
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            # Cleanup if needed
            pass
    
    # Usage
    async with ManagedRAGClient() as client:
        result = await client.query("What are the conclusions?")
        print(result)


# CLI interface
def main():
    """Simple CLI for the client"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG-Anything API Client")
    parser.add_argument("command", choices=["process", "query", "batch", "stats"],
                       help="Command to execute")
    parser.add_argument("--file", help="File to process")
    parser.add_argument("--query", help="Query text")
    parser.add_argument("--folder", help="Folder for batch processing")
    
    args = parser.parse_args()
    
    async def run():
        client = RAGAnythingClient()
        
        if args.command == "process" and args.file:
            result = await client.process_document(args.file)
            print(json.dumps(result, indent=2))
            
        elif args.command == "query" and args.query:
            answer = await client.query(args.query)
            print(answer)
            
        elif args.command == "batch" and args.folder:
            folder_path = Path(args.folder)
            files = list(folder_path.glob("*.pdf")) + list(folder_path.glob("*.docx"))
            results = await client.process_batch([str(f) for f in files])
            print(json.dumps(results, indent=2))
            
        elif args.command == "stats":
            stats = await client.get_stats()
            print(json.dumps(stats, indent=2))
            
        else:
            print("Invalid command or missing arguments")
    
    asyncio.run(run())


if __name__ == "__main__":
    # Run examples if called directly without arguments
    if len(sys.argv) == 1:
        print("Running examples...")
        asyncio.run(example_basic_usage())
    else:
        main()