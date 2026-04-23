"""
RAG 知识库助手 - 文本分块模块

使用 LangChain 的 RecursiveCharacterTextSplitter 实现智能文本分块。
支持为每个分块附加元数据（source、page、chunk_index）。

默认配置：
- chunk_size: 512（从配置读取）
- chunk_overlap: 50（从配置读取）
"""

from typing import Optional

from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.core.document_loader import Document


class TextSplitter:
    """文本分块器类
    
    基于 LangChain 的 RecursiveCharacterTextSplitter 实现，
    支持递归字符分割，优先在段落、句子等自然边界处分割。
    
    Attributes:
        chunk_size: 每个分块的最大字符数
        chunk_overlap: 相邻分块之间的重叠字符数
        splitter: LangChain 的 RecursiveCharacterTextSplitter 实例
    
    Example:
        >>> from backend.core.document_loader import Document
        >>> docs = [Document(page_content="这是一段很长的文本...", metadata={"source": "test.txt"})]
        >>> splitter = TextSplitter(chunk_size=512, chunk_overlap=50)
        >>> chunks = splitter.split_documents(docs)
        >>> for chunk in chunks:
        ...     print(f"Chunk {chunk.metadata['chunk_index']}: {chunk.page_content[:50]}")
    """
    
    # 默认分隔符列表（按优先级排序）
    # 优先在段落间分割，其次在句子间，最后在单词间
    # 针对中文文档优化分隔符顺序
    DEFAULT_SEPARATORS = ["\n\n", "\n", "。", "；", ";", "!", "?", "！", "？", ".", " ", ""]
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: Optional[list[str]] = None,
        length_function: callable = len,
        add_start_index: bool = True,
    ):
        """初始化文本分块器
        
        Args:
            chunk_size: 每个分块的最大字符数，默认 512
            chunk_overlap: 相邻分块之间的重叠字符数，默认 50
            separators: 分隔符列表，默认使用适合中文的分隔符
            length_function: 计算文本长度的函数，默认 len()
            add_start_index: 是否在元数据中添加起始索引
        
        Raises:
            ValueError: 如果 chunk_overlap >= chunk_size
        """
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) 必须小于 chunk_size ({chunk_size})"
            )
        
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or self.DEFAULT_SEPARATORS
        
        # 初始化 LangChain 的 RecursiveCharacterTextSplitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.separators,
            length_function=length_function,
            add_start_index=add_start_index,
            is_separator_regex=False,
        )
    
    def split_text(self, text: str) -> list[str]:
        """将单个文本字符串分割成多个块
        
        Args:
            text: 要分割的文本字符串
            
        Returns:
            分割后的文本块列表
            
        Example:
            >>> splitter = TextSplitter(chunk_size=100, chunk_overlap=20)
            >>> chunks = splitter.split_text("这是一段很长的文本，需要被分割成多个小块...")
            >>> print(len(chunks))
            3
        """
        if not text or not text.strip():
            return []
        
        return self.splitter.split_text(text)
    
    def split_documents(self, documents: list[Document]) -> list[Document]:
        """将多个文档分割成小块
        
        为每个分块附加元数据：
        - source: 来源文件名（继承自原文档）
        - page: 页码（继承自原文档，如适用）
        - chunk_index: 分块序号（在同源文档内递增）
        - document_id: 原始文档标识（如原文档有）
        
        Args:
            documents: Document 对象列表
            
        Returns:
            分割后的 Document 对象列表，每个包含更新后的元数据
            
        Example:
            >>> docs = [
            ...     Document(page_content="第一页内容...", metadata={"source": "doc.pdf", "page": 1}),
            ...     Document(page_content="第二页内容...", metadata={"source": "doc.pdf", "page": 2}),
            ... ]
            >>> chunks = splitter.split_documents(docs)
            >>> print(chunks[0].metadata)
            {'source': 'doc.pdf', 'page': 1, 'chunk_index': 0}
        """
        if not documents:
            return []
        
        result_chunks = []
        
        # 按 source 分组处理，以便正确设置 chunk_index
        source_chunks_map: dict[str, int] = {}
        
        for doc in documents:
            if not doc.page_content or not doc.page_content.strip():
                continue
            
            # 分割当前文档
            text_chunks = self.split_text(doc.page_content)
            
            # 获取 source 用于追踪 chunk_index
            source = doc.metadata.get("source", "unknown")
            
            # 初始化该 source 的计数器
            if source not in source_chunks_map:
                source_chunks_map[source] = 0
            
            # 为每个分块创建 Document 对象并附加元数据
            for text_chunk in text_chunks:
                # 构建元数据
                chunk_metadata = doc.metadata.copy()
                chunk_metadata["chunk_index"] = source_chunks_map[source]
                
                # 创建新的 Document 对象
                chunk_doc = Document(
                    page_content=text_chunk,
                    metadata=chunk_metadata,
                )
                
                result_chunks.append(chunk_doc)
                source_chunks_map[source] += 1
        
        return result_chunks
    
    def create_documents(
        self,
        texts: list[str],
        metadatas: Optional[list[dict]] = None,
    ) -> list[Document]:
        """从文本列表和元数据列表创建分块文档
        
        这是一个便捷方法，用于直接传入文本和元数据创建分块。
        
        Args:
            texts: 文本字符串列表
            metadatas: 与 texts 对应的元数据字典列表，可选
            
        Returns:
            分割后的 Document 对象列表
            
        Example:
            >>> texts = ["第一段文本内容...", "第二段文本内容..."]
            >>> metadatas = [{"source": "doc1.txt"}, {"source": "doc2.txt"}]
            >>> chunks = splitter.create_documents(texts, metadatas)
        """
        if not texts:
            return []
        
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        if len(texts) != len(metadatas):
            raise ValueError(
                f"texts 和 metadatas 长度必须相同: {len(texts)} != {len(metadatas)}"
            )
        
        # 创建临时 Document 对象
        documents = [
            Document(page_content=text, metadata=metadata)
            for text, metadata in zip(texts, metadatas)
        ]
        
        return self.split_documents(documents)
    
    def get_chunk_count_estimate(self, text: str) -> int:
        """估算文本将被分割成多少个块
        
        这是一个快速估算方法，实际分割结果可能略有不同。
        
        Args:
            text: 要估算的文本
            
        Returns:
            估算的分块数量
            
        Example:
            >>> splitter = TextSplitter(chunk_size=100, chunk_overlap=20)
            >>> count = splitter.get_chunk_count_estimate("a" * 500)
            >>> print(count)  # 大约 6-7 个块
        """
        if not text:
            return 0
        
        text_length = len(text)
        
        # 简单估算：(总长度 - 重叠) / (块大小 - 重叠)
        # 向上取整
        effective_chunk_size = self.chunk_size - self.chunk_overlap
        if effective_chunk_size <= 0:
            effective_chunk_size = self.chunk_size
        
        import math
        estimated = math.ceil((text_length - self.chunk_overlap) / effective_chunk_size)
        return max(1, estimated) if text_length > 0 else 0


# 便捷函数

def split_documents(
    documents: list[Document],
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[Document]:
    """便捷函数：分割文档
    
    这是 TextSplitter.split_documents() 的快捷方式。
    
    Args:
        documents: Document 对象列表
        chunk_size: 每个分块的最大字符数，默认 512
        chunk_overlap: 相邻分块之间的重叠字符数，默认 50
        
    Returns:
        分割后的 Document 对象列表
        
    Example:
        >>> from backend.core.document_loader import load_document
        >>> docs = load_document("document.pdf")
        >>> chunks = split_documents(docs, chunk_size=512, chunk_overlap=50)
        >>> print(f"共分割成 {len(chunks)} 个块")
    """
    splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_documents(documents)


def split_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> list[str]:
    """便捷函数：分割文本
    
    这是 TextSplitter.split_text() 的快捷方式。
    
    Args:
        text: 要分割的文本字符串
        chunk_size: 每个分块的最大字符数，默认 512
        chunk_overlap: 相邻分块之间的重叠字符数，默认 50
        
    Returns:
        分割后的文本字符串列表
        
    Example:
        >>> text = "这是一段很长的文本内容..."
        >>> chunks = split_text(text, chunk_size=100, chunk_overlap=20)
        >>> for i, chunk in enumerate(chunks):
        ...     print(f"块 {i}: {chunk[:50]}...")
    """
    splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_text(text)


def get_text_splitter_from_settings() -> TextSplitter:
    """从应用配置创建 TextSplitter 实例
    
    从 settings 中读取 chunk_size 和 chunk_overlap 配置。
    
    Returns:
        配置好的 TextSplitter 实例
        
    Example:
        >>> splitter = get_text_splitter_from_settings()
        >>> chunks = splitter.split_documents(docs)
    """
    from backend.config.settings import get_settings
    
    settings = get_settings()
    return TextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
