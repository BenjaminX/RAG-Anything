# RAG-Anything API 使用完整指南

本指南提供了 RAG-Anything 的完整使用示例，包括文档处理、查询、批处理等所有功能。

## 目录
1. [快速开始](#快速开始)
2. [基础用法](#基础用法)
3. [高级功能](#高级功能)
4. [API 参考](#api-参考)
5. [最佳实践](#最佳实践)

## 快速开始

### 1. 验证服务状态

首先确认所有服务正常运行：

```bash
# 检查服务状态
sudo docker-compose ps

# 查看 Qdrant 向量数据库状态
curl http://localhost:6333/health

# 进入容器交互模式
sudo docker exec -it raganything /bin/bash
```

### 2. 准备测试文档

```bash
# 在宿主机上准备测试文档
mkdir -p inputs
cp your_document.pdf inputs/
```

## 基础用法

### 1. 简单文档处理示例

在容器内运行：

```python
# simple_example.py
import asyncio
from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

async def basic_example():
    # 配置
    config = RAGAnythingConfig(
        working_dir="/app/rag_storage",
        parser="mineru",
        parse_method="auto",
        enable_image_processing=True,
        enable_table_processing=True,
        enable_equation_processing=True,
    )
    
    # LLM 函数
    def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs):
        return openai_complete_if_cache(
            "gpt-4o-mini",
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key="your-api-key",  # 从环境变量读取
            **kwargs,
        )
    
    # Vision 模型函数
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
                api_key="your-api-key",
                **kwargs,
            )
        return llm_model_func(prompt, system_prompt, history_messages, **kwargs)
    
    # Embedding 函数
    embedding_func = EmbeddingFunc(
        embedding_dim=3072,
        max_token_size=8192,
        func=lambda texts: openai_embed(
            texts,
            model="text-embedding-3-large",
            api_key="your-api-key",
        ),
    )
    
    # 初始化 RAGAnything
    rag = RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        vision_model_func=vision_model_func,
        embedding_func=embedding_func,
    )
    
    # 处理文档
    await rag.process_document_complete(
        file_path="/app/inputs/document.pdf",
        output_dir="/app/output",
        parse_method="auto"
    )
    
    # 查询
    result = await rag.aquery(
        "What are the main points in this document?",
        mode="hybrid"
    )
    print(result)

if __name__ == "__main__":
    asyncio.run(basic_example())
```

运行示例：
```bash
sudo docker exec -it raganything python /app/simple_example.py
```

### 2. 使用环境变量配置

创建 `/app/.env` 文件：
```bash
OPENAI_API_KEY=your-actual-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

```python
# env_example.py
import os
import asyncio
from dotenv import load_dotenv
from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

# 加载环境变量
load_dotenv()

async def env_based_example():
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    
    config = RAGAnythingConfig(
        working_dir="/app/rag_storage",
        parser="mineru",
    )
    
    # 使用环境变量中的 API 配置
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
    
    rag = RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        embedding_func=embedding_func,
    )
    
    # 处理并查询
    await rag.process_document_complete(
        file_path="/app/inputs/document.pdf",
        output_dir="/app/output"
    )
    
    result = await rag.aquery("Summarize this document")
    print(result)

if __name__ == "__main__":
    asyncio.run(env_based_example())
```

## 高级功能

### 1. 多模态查询

```python
# multimodal_query.py
async def multimodal_query_example(rag):
    # 纯文本查询
    text_result = await rag.aquery(
        "What are the key findings?",
        mode="hybrid"
    )
    
    # 带表格的查询
    table_query_result = await rag.aquery_with_multimodal(
        "Compare this table data with the document findings",
        multimodal_content=[{
            "type": "table",
            "table_data": """
            Method,Accuracy,Speed
            RAGAnything,95.2%,120ms
            Traditional,87.3%,180ms
            """,
            "table_caption": "Performance comparison"
        }],
        mode="hybrid"
    )
    
    # 带公式的查询
    equation_result = await rag.aquery_with_multimodal(
        "Explain this formula in the context of the document",
        multimodal_content=[{
            "type": "equation",
            "latex": "P(d|q) = \\frac{P(q|d) \\cdot P(d)}{P(q)}",
            "equation_caption": "Document relevance probability"
        }],
        mode="hybrid"
    )
    
    return text_result, table_query_result, equation_result
```

### 2. 批量文档处理

```python
# batch_processing.py
async def batch_process_documents(rag):
    # 处理整个文件夹
    await rag.process_folder_complete(
        folder_path="/app/inputs",
        output_dir="/app/output",
        file_extensions=[".pdf", ".docx", ".pptx"],
        recursive=True,
        max_workers=4
    )
    
    # 处理特定文件列表
    files = [
        "/app/inputs/doc1.pdf",
        "/app/inputs/doc2.docx",
        "/app/inputs/presentation.pptx"
    ]
    
    for file in files:
        await rag.process_document_complete(
            file_path=file,
            output_dir="/app/output"
        )
```

### 3. 直接内容插入（无需文档解析）

```python
# direct_content_insertion.py
async def insert_content_directly(rag):
    # 准备内容列表
    content_list = [
        {
            "type": "text",
            "text": "This is the introduction of our research.",
            "page_idx": 0
        },
        {
            "type": "image",
            "img_path": "/app/inputs/figure1.jpg",
            "img_caption": ["Figure 1: System Architecture"],
            "img_footnote": ["Source: Original"],
            "page_idx": 1
        },
        {
            "type": "table",
            "table_body": """
            | Feature | Score |
            |---------|-------|
            | Speed   | 9.5   |
            | Accuracy| 9.8   |
            """,
            "table_caption": ["Performance Metrics"],
            "page_idx": 2
        },
        {
            "type": "equation",
            "latex": "E = mc^2",
            "text": "Einstein's mass-energy equivalence",
            "page_idx": 3
        }
    ]
    
    # 插入内容
    await rag.insert_content_list(
        content_list=content_list,
        file_path="virtual_document.pdf",
        display_stats=True
    )
```

### 4. 自定义模态处理器

```python
# custom_processor.py
from raganything.modalprocessors import GenericModalProcessor

class CustomChartProcessor(GenericModalProcessor):
    async def process_multimodal_content(
        self, 
        modal_content, 
        content_type, 
        file_path, 
        entity_name
    ):
        # 自定义处理逻辑
        if content_type == "chart":
            description = f"Chart Analysis: {modal_content.get('chart_type', 'Unknown')}"
            # 添加更多分析逻辑
            enhanced_description = await self._analyze_chart(modal_content)
            
            entity_info = {
                "entity_name": entity_name,
                "entity_type": "chart",
                "source_file": file_path,
                "attributes": modal_content
            }
            
            return await self._create_entity_and_chunk(
                enhanced_description, 
                entity_info, 
                file_path
            )
    
    async def _analyze_chart(self, chart_data):
        # 实现图表分析逻辑
        return f"Detailed chart analysis: {chart_data}"
```

### 5. 查询不同的存储后端

```python
# storage_backends.py
async def use_different_storages():
    # 使用 PostgreSQL
    rag_postgres = RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        embedding_func=embedding_func,
        lightrag_kwargs={
            "kv_storage": "PGKVStorage",
            "vector_storage": "PGVectorStorage",
            "graph_storage": "PGGraphStorage",
            "doc_status_storage": "PGDocStatusStorage",
            "addon_params": {
                "pg_config": {
                    "host": "postgres",
                    "port": 5432,
                    "user": "raganything",
                    "password": "raganything123",
                    "database": "raganything"
                }
            }
        }
    )
    
    # 使用 Neo4j
    rag_neo4j = RAGAnything(
        config=config,
        llm_model_func=llm_model_func,
        embedding_func=embedding_func,
        lightrag_kwargs={
            "graph_storage": "Neo4JStorage",
            "addon_params": {
                "neo4j_config": {
                    "uri": "bolt://neo4j:7687",
                    "username": "neo4j",
                    "password": "raganything123"
                }
            }
        }
    )
```

## API 参考

### RAGAnything 主要方法

#### 1. 文档处理
```python
# 处理单个文档
await rag.process_document_complete(
    file_path: str,                    # 文档路径
    output_dir: str = None,           # 输出目录
    parse_method: str = "auto",       # 解析方法: auto, ocr, txt
    **kwargs                          # 其他 MinerU 参数
)

# 批量处理
await rag.process_folder_complete(
    folder_path: str,                 # 文件夹路径
    output_dir: str = None,          # 输出目录
    file_extensions: List[str] = None, # 文件扩展名过滤
    recursive: bool = True,          # 递归处理子文件夹
    max_workers: int = None          # 并发数
)
```

#### 2. 查询方法
```python
# 纯文本查询
result = await rag.aquery(
    query: str,                      # 查询文本
    mode: str = "hybrid",           # 模式: hybrid, local, global, naive
    stream: bool = False            # 流式输出
)

# 多模态查询
result = await rag.aquery_with_multimodal(
    query: str,                      # 查询文本
    multimodal_content: List[Dict],  # 多模态内容
    mode: str = "hybrid"
)

# 同步查询
result = rag.query(query: str, mode: str = "hybrid")
```

#### 3. 内容管理
```python
# 直接插入内容
await rag.insert_content_list(
    content_list: List[Dict],        # 内容列表
    file_path: str,                  # 引用文件名
    display_stats: bool = True,      # 显示统计信息
    doc_id: str = None              # 文档ID
)

# 批量插入文本
await rag.ainsert_texts(
    texts: List[str],               # 文本列表
    metadata: Dict = None           # 元数据
)
```

### 配置参数

```python
RAGAnythingConfig(
    # 目录配置
    working_dir: str = "./rag_storage",
    parser_output_dir: str = "./output",
    
    # 解析器配置
    parser: str = "mineru",              # mineru 或 docling
    parse_method: str = "auto",          # auto, ocr, txt
    
    # 多模态处理
    enable_image_processing: bool = True,
    enable_table_processing: bool = True,
    enable_equation_processing: bool = True,
    
    # 批处理配置
    max_concurrent_files: int = 1,
    supported_file_extensions: List[str] = [".pdf", ".docx", ...],
    
    # 上下文配置
    context_window: int = 1,
    context_mode: str = "page",
    max_context_tokens: int = 2000
)
```

## 最佳实践

### 1. 错误处理

```python
async def safe_process_document(rag, file_path):
    try:
        await rag.process_document_complete(file_path)
        print(f"Successfully processed: {file_path}")
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
```

### 2. 性能优化

```python
# 使用批处理
config = RAGAnythingConfig(
    max_concurrent_files=4,  # 并发处理
    chunk_size=1200,        # 优化块大小
    chunk_overlap_size=100  # 重叠大小
)

# 使用缓存
rag = RAGAnything(
    config=config,
    lightrag_kwargs={
        "enable_llm_cache": True,
        "max_async": 4,
        "embedding_batch_num": 32
    }
)
```

### 3. 监控和日志

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/raganything.log'),
        logging.StreamHandler()
    ]
)

# 使用进度回调
async def process_with_progress(rag, files):
    for i, file in enumerate(files):
        print(f"Processing {i+1}/{len(files)}: {file}")
        await rag.process_document_complete(file)
```

### 4. 资源清理

```python
# 清理旧数据
import shutil

def cleanup_old_data(days=7):
    # 清理输出目录中的旧文件
    output_dir = Path("/app/output")
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    
    for file in output_dir.glob("**/*"):
        if file.stat().st_mtime < cutoff_time:
            file.unlink()
```

## 完整工作流示例

```python
# complete_workflow.py
async def complete_rag_workflow():
    # 1. 初始化
    rag = await initialize_rag()
    
    # 2. 处理文档
    documents = [
        "/app/inputs/research_paper.pdf",
        "/app/inputs/presentation.pptx",
        "/app/inputs/data_report.docx"
    ]
    
    for doc in documents:
        await rag.process_document_complete(doc)
    
    # 3. 执行查询
    queries = [
        "What are the main findings across all documents?",
        "Compare the methodologies used in different papers",
        "Summarize the key recommendations"
    ]
    
    results = {}
    for query in queries:
        results[query] = await rag.aquery(query, mode="hybrid")
    
    # 4. 导出结果
    with open("/app/output/analysis_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return results

if __name__ == "__main__":
    asyncio.run(complete_rag_workflow())
```

## 故障排除

### 常见问题

1. **API Key 错误**
```bash
# 检查环境变量
docker exec raganything env | grep OPENAI
```

2. **内存不足**
```python
# 减少并发和批处理大小
config = RAGAnythingConfig(
    max_concurrent_files=1,
    chunk_size=500
)
```

3. **查询无结果**
```python
# 检查索引状态
result = await rag.aquery("test", mode="naive")
if not result:
    print("Index might be empty, check document processing")
```