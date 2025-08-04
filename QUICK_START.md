# RAG-Anything 快速使用指南 🚀

## 1. 快速测试

在 Docker 容器中运行以下命令：

```bash
# 进入容器
sudo docker exec -it raganything /bin/bash

# 设置 API Key（如果还没设置）
export OPENAI_API_KEY=your-api-key-here

# 运行快速示例
python examples/docker_quick_start.py /app/inputs/your_document.pdf
```

## 2. 交互式会话

启动交互式 CLI：

```bash
# 在容器内
python examples/interactive_rag.py

# 然后在交互式界面中：
> init
> load /app/inputs/document.pdf
> query What are the main findings?
> multimodal
```

## 3. Python 脚本示例

创建文件 `/app/my_rag_script.py`：

```python
import asyncio
import os
from raganything import RAGAnything, RAGAnythingConfig
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import EmbeddingFunc

async def main():
    # 配置
    api_key = os.getenv("OPENAI_API_KEY")
    
    config = RAGAnythingConfig(
        working_dir="/app/rag_storage",
        parser="mineru",
        enable_image_processing=True
    )
    
    # 模型函数
    def llm_func(prompt, **kwargs):
        return openai_complete_if_cache(
            "gpt-4o-mini", prompt, api_key=api_key, **kwargs
        )
    
    embedding_func = EmbeddingFunc(
        embedding_dim=3072,
        func=lambda texts: openai_embed(
            texts, model="text-embedding-3-large", api_key=api_key
        )
    )
    
    # 初始化
    rag = RAGAnything(
        config=config,
        llm_model_func=llm_func,
        embedding_func=embedding_func
    )
    
    # 处理文档
    await rag.process_document_complete(
        file_path="/app/inputs/document.pdf",
        output_dir="/app/output"
    )
    
    # 查询
    result = await rag.aquery("Summarize this document")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

运行：
```bash
python /app/my_rag_script.py
```

## 4. API 客户端使用

```bash
# 处理文档
python examples/api_client.py process --file /app/inputs/document.pdf

# 查询
python examples/api_client.py query --query "What are the key points?"

# 批处理
python examples/api_client.py batch --folder /app/inputs

# 查看状态
python examples/api_client.py stats
```

## 5. 多模态查询示例

```python
# 带表格的查询
result = await rag.aquery_with_multimodal(
    "分析这个性能数据",
    multimodal_content=[{
        "type": "table",
        "table_data": """
        指标,数值,提升
        速度,120ms,50%
        准确率,95%,10%
        """,
        "table_caption": "性能对比"
    }],
    mode="hybrid"
)

# 带公式的查询
result = await rag.aquery_with_multimodal(
    "解释这个公式",
    multimodal_content=[{
        "type": "equation",
        "latex": "E = mc^2",
        "equation_caption": "质能方程"
    }]
)
```

## 6. 批量处理

```python
# 处理整个文件夹
await rag.process_folder_complete(
    folder_path="/app/inputs",
    file_extensions=[".pdf", ".docx", ".pptx"],
    max_workers=4
)
```

## 7. 直接内容插入

```python
# 无需文件，直接插入内容
content_list = [
    {"type": "text", "text": "这是文本内容", "page_idx": 0},
    {"type": "table", "table_body": "| A | B |\n|---|---|\n| 1 | 2 |", "page_idx": 1}
]

await rag.insert_content_list(
    content_list=content_list,
    file_path="virtual_doc.pdf"
)
```

## 8. 使用不同存储后端

### Qdrant（默认）
已配置，无需额外设置

### PostgreSQL
```bash
# 启动带 PostgreSQL 的服务
sudo ./docker-run.sh -p with-postgres -d
```

### Neo4j
```bash
# 启动带 Neo4j 的服务
sudo ./docker-run.sh -p with-neo4j -d
```

## 9. 查看结果

- **Qdrant UI**: http://localhost:6333/dashboard
- **输出文件**: `/app/output/` 目录
- **日志文件**: `/app/logs/` 目录

## 10. 常见问题

### API Key 错误
```bash
# 检查环境变量
env | grep OPENAI_API_KEY

# 设置 API Key
export OPENAI_API_KEY=your-key
```

### 内存不足
```python
# 减少并发
config = RAGAnythingConfig(
    max_concurrent_files=1,
    chunk_size=500
)
```

### 端口冲突
```bash
# 使用调试工具
sudo ./docker-run.sh debug
```

## 更多信息

- 完整文档：`/app/docs/api-usage-guide.md`
- 示例代码：`/app/examples/`
- Jupyter教程：`/app/examples/rag_anything_tutorial.ipynb`

---

💡 **提示**: 所有路径都是容器内路径。从宿主机访问时，使用挂载的目录。