import os
from pathlib import Path
from typing import List
import uuid
import chromadb
import numpy as np
import tqdm
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from transformers import AutoTokenizer


from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class DocChunk:
    chunk_id: str             # "2.3.1__p2"
    section_id: str           # "2.3.1"
    section_title: str        # "建设单位职责"
    text: str                 # 该小段正文（300-500字）

@dataclass
class ChatTurn:
    role: str                 # "user" | "assistant"
    content: str

class SimpleVectorStore():
    def __init__(self):
        self.knowledge_base = ["hf_papers/2510.23564/2510.23564.md"]
        # self.text_splitter = self._init_text_split()
        self.chroma_client = self._init_chroma_client()
        self.collection_name = "kb_dev_md_all"
    
    def docs_simple_text_split(self):
        source_docs = []
        for doc in self.knowledge_base:
            doc_data = Document(page_content=doc["text"], metadata=doc) 
            source_docs.append(doc_data)
            
        # Split docs and keep only unique ones
        print("Splitting documents...")
        docs_processed = []
        unique_texts = {}
        for doc in tqdm(source_docs):
            new_docs = self.text_splitter.split_documents([doc])
            for new_doc in new_docs:
                if new_doc.page_content not in unique_texts:
                    unique_texts[new_doc.page_content] = True
                    docs_processed.append(new_doc)
        print("doc split chunk: ",len(docs_processed))
        return docs_processed

    def get_embedding(self,text:str):
        import requests

        url = "https://api.siliconflow.cn/v1/embeddings"

        payload = {
            "model": "BAAI/bge-m3",
            "input": text
        }
        api_key = os.getenv("SILICONFLOW_API_KEY_TEST")
        headers = {
            "Authorization": "Bearer "+api_key,
            "Content-Type": "application/json"
        }
        response = requests.post(url, json=payload, headers=headers)

        data = response.json()
        if isinstance(data,dict):
            embed = data['data'][0]["embedding"]
            return embed
        else:
            return []
            
    def _init_chroma_client(self):
        chroma_client = chromadb.HttpClient(host='localhost', port=8000)
        return chroma_client
    
    
    def kb_search(self,query:str,top_k:int):
        query_embed = self.get_embedding(query)
        collection = self.chroma_client.get_collection(self.collection_name)
        results = collection.query(
            query_embeddings=query_embed,
            n_results=top_k
        )
        return results
    
    def build_vector_chroma(self):
        collection = self.chroma_client.list_collections()
        list_collection_name = [name.name for name in collection]
        if collection and self.collection_name not in list_collection_name:
                collection = self.chroma_client.create_collection(name=self.collection_name)
        else:
            print("collection name exsit:",self.collection_name)
            collection = self.chroma_client.get_collection(self.collection_name)
        docs_processed=self.md_text_split()
        documents = []
        embeddings = []
        metadatas = []
        ids = []
        for doc in tqdm(docs_processed):
            id = uuid.uuid4()
            doc_embed = self.get_embedding(doc.page_content)
            documents.append(doc.page_content)
            embeddings.append(doc_embed)
            # del doc.metadata["text"]
            metadatas.append(doc.metadata)
            ids.append(id.hex)
            
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas 
        )

    def _init_text_split(self):
        text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
            AutoTokenizer.from_pretrained("thenlper/gte-small"),
            chunk_size=200,
            chunk_overlap=20,
            add_start_index=True,
            strip_whitespace=True,
            separators=["\n\n", "\n", ".", " ", ""],
        )
        return text_splitter
    
    def md_text_split(self) -> List[Document]:
        docs=[]
        for doc in self.knowledge_base:
            text = Path(doc['source']).read_text(encoding="utf-8", errors="ignore")
            # # chunks = chunk_md_by_numbered_subtitles(text,doc["filename"])
            # docs +=chunks
        return docs



def update_summary(chat_history: List[ChatTurn]) -> str:
    """
    取最近 ~4 turns (user/assistant/user/assistant)，总结成100-200字
    你可以直接让大模型做summarize，也可以简单拼接：
    - 最近用户问了什么
    - 我给过的关键结论是什么
    """
    recent = chat_history[-4:]
    summary_lines = []
    for t in recent:
        if t.role == "user":
            summary_lines.append(f"用户问: {t.content}")
        else:
            summary_lines.append(f"助手答: {t.content}")
    # 简单拼接版（够用，低成本）
    return "\n".join(summary_lines)[-800:]  # 最后800字符以内

def answer_one_turn(
    user_question: str,
    vector_store: SimpleVectorStore,
    rolling_summary: str,
    chat_history: List[ChatTurn],
    llm_complete_fn,  # 调大模型生成答案的函数
    top_k: int = 4,
) -> str:

    # 1) 为检索构造query：用户问题 + 最近摘要（帮助消歧）
    retrieval_query = f"基于上下文: {rolling_summary}\n用户问题: {user_question}"

    # 2) 召回文档片段
    hits = vector_store.search(retrieval_query, top_k=top_k)

    # 3) 构造LLM Prompt
    context_chunks_text = ""
    for ch, score in hits:
        context_chunks_text += (
            f"[{ch.section_id} {ch.section_title}] {ch.text}\n---\n"
        )

    system_prompt = (
        "你是文档助理。请仅根据《给定文档片段》回答用户问题。\n"
        "当引用信息时，请标注来源章节号(例如: 参考2.3.1)。\n"
        "如果文档中没有明确信息，请如实说不知道，而不要胡编。\n"
    )

    final_prompt = (
        f"{system_prompt}\n"
        f"【最近对话背景】\n{rolling_summary}\n\n"
        f"【给定文档片段】\n{context_chunks_text}\n"
        f"【用户问题】\n{user_question}\n"
        "【请用中文回答，结构化、精准。】"
    )

    # 4) 调用大模型
    answer = llm_complete_fn(final_prompt)

    # 5) 写入历史
    chat_history.append(ChatTurn(role="user", content=user_question))
    chat_history.append(ChatTurn(role="assistant", content=answer))

    # 6) 更新rolling_summary
    new_summary = update_summary(chat_history)

    return answer, new_summary