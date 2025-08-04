#!/usr/bin/env python3
"""
Interactive RAG-Anything session
Provides an interactive command-line interface for RAG operations
"""

import os
import sys
import asyncio
import cmd
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).parent.parent))

from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc
from dotenv import load_dotenv

load_dotenv()


class RAGInteractive(cmd.Cmd):
    """Interactive RAG-Anything CLI"""
    
    intro = """
    ╔══════════════════════════════════════════════════════════╗
    ║           RAG-Anything Interactive Session               ║
    ╚══════════════════════════════════════════════════════════╝
    
    Type 'help' or '?' to list commands.
    Type 'exit' or 'quit' to leave.
    """
    
    prompt = "(rag) > "
    
    def __init__(self):
        super().__init__()
        self.rag: Optional[RAGAnything] = None
        self.current_file: Optional[str] = None
        self.processed_files = set()
        
    async def initialize_rag(self):
        """Initialize RAG-Anything with configuration"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ Error: OPENAI_API_KEY not set")
            return False
            
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        config = RAGAnythingConfig(
            working_dir="/app/rag_storage",
            parser="mineru",
            enable_image_processing=True,
            enable_table_processing=True,
            enable_equation_processing=True,
        )
        
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
        
        def vision_model_func(prompt, system_prompt=None, history_messages=[], image_data=None, **kwargs):
            if image_data:
                return openai_complete_if_cache(
                    "gpt-4o",
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
                    api_key=api_key,
                    base_url=base_url,
                    **kwargs,
                )
            return llm_model_func(prompt, system_prompt, history_messages, **kwargs)
        
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
            self.rag = RAGAnything(
                config=config,
                llm_model_func=llm_model_func,
                vision_model_func=vision_model_func,
                embedding_func=embedding_func,
            )
            print("✅ RAG-Anything initialized successfully!")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            return False
    
    def do_init(self, arg):
        """Initialize or reinitialize RAG-Anything"""
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.initialize_rag())
    
    def do_load(self, filepath):
        """Load and process a document: load /app/inputs/document.pdf"""
        if not self.rag:
            print("❌ Please run 'init' first")
            return
            
        if not filepath:
            print("❌ Please specify a file path")
            return
            
        filepath = filepath.strip()
        if not Path(filepath).exists():
            print(f"❌ File not found: {filepath}")
            return
            
        print(f"📄 Loading document: {filepath}")
        loop = asyncio.get_event_loop()
        
        async def process():
            try:
                await self.rag.process_document_complete(
                    file_path=filepath,
                    output_dir="/app/output"
                )
                self.current_file = filepath
                self.processed_files.add(filepath)
                print(f"✅ Document loaded successfully!")
            except Exception as e:
                print(f"❌ Error loading document: {e}")
        
        loop.run_until_complete(process())
    
    def do_query(self, query):
        """Query the loaded documents: query What are the main findings?"""
        if not self.rag:
            print("❌ Please run 'init' first")
            return
            
        if not query:
            print("❌ Please provide a query")
            return
            
        if not self.processed_files:
            print("❌ No documents loaded. Use 'load' command first")
            return
            
        print(f"🔍 Querying: {query}")
        loop = asyncio.get_event_loop()
        
        async def run_query():
            try:
                result = await self.rag.aquery(query, mode="hybrid")
                print("\n📌 Result:")
                print("-" * 80)
                print(result)
                print("-" * 80)
            except Exception as e:
                print(f"❌ Query error: {e}")
        
        loop.run_until_complete(run_query())
    
    def do_multimodal(self, query):
        """Run a multimodal query with example data: multimodal Analyze this performance data"""
        if not self.rag:
            print("❌ Please run 'init' first")
            return
            
        if not query:
            query = "Analyze this data in context of the document"
            
        print(f"📊 Multimodal query: {query}")
        loop = asyncio.get_event_loop()
        
        async def run_multimodal():
            try:
                result = await self.rag.aquery_with_multimodal(
                    query,
                    multimodal_content=[{
                        "type": "table",
                        "table_data": """
                        Feature,Score,Improvement
                        Speed,95,+15%
                        Accuracy,98,+10%
                        Efficiency,92,+20%
                        """,
                        "table_caption": "System Performance Metrics"
                    }],
                    mode="hybrid"
                )
                print("\n📊 Multimodal Result:")
                print("-" * 80)
                print(result)
                print("-" * 80)
            except Exception as e:
                print(f"❌ Error: {e}")
        
        loop.run_until_complete(run_multimodal())
    
    def do_list(self, arg):
        """List processed documents"""
        if not self.processed_files:
            print("📄 No documents loaded yet")
        else:
            print("📄 Processed documents:")
            for i, file in enumerate(self.processed_files, 1):
                marker = "→" if file == self.current_file else " "
                print(f" {marker} {i}. {file}")
    
    def do_batch(self, folder):
        """Process all documents in a folder: batch /app/inputs"""
        if not self.rag:
            print("❌ Please run 'init' first")
            return
            
        if not folder:
            folder = "/app/inputs"
            
        folder_path = Path(folder)
        if not folder_path.exists():
            print(f"❌ Folder not found: {folder}")
            return
            
        print(f"📁 Processing folder: {folder}")
        loop = asyncio.get_event_loop()
        
        async def process_batch():
            try:
                await self.rag.process_folder_complete(
                    folder_path=folder,
                    output_dir="/app/output",
                    file_extensions=[".pdf", ".docx", ".pptx", ".txt"],
                    recursive=True,
                    max_workers=2
                )
                print(f"✅ Batch processing completed!")
            except Exception as e:
                print(f"❌ Batch processing error: {e}")
        
        loop.run_until_complete(process_batch())
    
    def do_status(self, arg):
        """Show current status"""
        print("\n📊 RAG-Anything Status:")
        print(f"   Initialized: {'✅ Yes' if self.rag else '❌ No'}")
        print(f"   Documents loaded: {len(self.processed_files)}")
        if self.current_file:
            print(f"   Current file: {self.current_file}")
        print(f"   Storage: /app/rag_storage")
        print(f"   Output: /app/output")
    
    def do_clear(self, arg):
        """Clear the current session data"""
        self.processed_files.clear()
        self.current_file = None
        print("✅ Session cleared")
    
    def do_help(self, arg):
        """Show help information"""
        print("""
Available Commands:
==================
  init          - Initialize RAG-Anything
  load <file>   - Load and process a document
  query <text>  - Query the loaded documents
  multimodal    - Run a multimodal query example
  list          - List all processed documents
  batch <dir>   - Process all documents in a directory
  status        - Show current status
  clear         - Clear session data
  exit/quit     - Exit the program

Examples:
=========
  init
  load /app/inputs/document.pdf
  query What are the main findings?
  batch /app/inputs
  multimodal Analyze this performance data
        """)
    
    def do_exit(self, arg):
        """Exit the program"""
        print("\n👋 Goodbye!")
        return True
    
    def do_quit(self, arg):
        """Exit the program"""
        return self.do_exit(arg)
    
    def emptyline(self):
        """Handle empty line"""
        pass


def main():
    # Check environment
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set in environment")
        print("   Please set it before using 'init' command")
    
    # Start interactive session
    RAGInteractive().cmdloop()


if __name__ == "__main__":
    main()