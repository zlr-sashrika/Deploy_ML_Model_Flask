import os
from typing import List

from devops_agent.logs.logging import logger
from devops_agent.rag.constants import bq_rag, confluence_rag, docker_rag, aws_rag
from dotenv import load_dotenv
from langchain.schema import Document
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)
from langchain_community.document_loaders import (
    ConfluenceLoader,
    WebBaseLoader,
    DirectoryLoader,
    UnstructuredMarkdownLoader,
)
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector

# load dot env
load_dotenv(os.path.join(os.getcwd(), ".env"))
connection = os.getenv("VECTOR_DB_URL")


def vectorstore_devops(collection_name: str, kwargs: int):
    """Vectorstore for devops."""

    # uncomment below line to load PGVector with rag data if not done from api
    embed_docker_docs([])
    vectorstore = initialize_vectorstore(collection_name)
    retriever = vectorstore.as_retriever(search_kwargs={"k": kwargs})
    return retriever


def initialize_vectorstore(collection_name: str) -> PGVector:
    """Reusable function to initialize the PGVector database."""

    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")
    return PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection,
        use_jsonb=True,
    )


def embed_docker_docs(reset: bool = True, urls: List[str] = []):
    """Embedding Docker docs."""

    logger.info("Embedding Docker docs", docker_rag.get("urls"))
    devops_urls = urls or docker_rag.get("urls")
    docs = [WebBaseLoader(url).load() for url in devops_urls]
    doc_splits = split_docs(docs)
    embed_storeall_docs(docker_rag.get("collection_name"), doc_splits, reset)


def embed_bq_docs(reset: bool = True, urls: List[str] = []):
    """Embedding BigQuery docs."""

    logger.info("Embedding BigQuery docs")
    bq_urls = urls or bq_rag.get("urls")
    docs = [WebBaseLoader(url).load() for url in bq_urls]
    doc_splits = split_docs(docs)
    embed_storeall_docs(bq_rag.get("collection_name"), doc_splits, reset)


def embed_confluence_docs(reset: bool, data_sources: any):
    """Embedding Confluence docs."""

    loader = ConfluenceLoader(
        url=data_sources.instanceUrl,
        username=data_sources.user_email,
        api_key=data_sources.APIToken,
        space_key=data_sources.space,
        page_ids=data_sources.page_ids,
        limit=50,
    )
    documents = loader.load()
    embed_storeall_docs(confluence_rag.get("collection_name"), documents, reset)


def embed_aws_docs(
    directory_path: str,
    glob_pattern: str = "./*.md",
    reset: bool = True,
):
    """Embedding AWS docs."""

    logger.info(
        f"Embedding AWS docs from {directory_path} with files of type {glob_pattern}"
    )
    aws_doc = DirectoryLoader(
        path=directory_path,
        glob=glob_pattern,
        show_progress=True,
        loader_cls=UnstructuredMarkdownLoader,
    )
    docs = aws_doc.load()
    split_docs = []

    # split markdown text
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
    ]
    text_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    for doc in docs:
        sections = text_splitter.split_text(doc.page_content)
        split_docs.extend(sections)

    embed_storeall_docs(aws_rag.get("collection_name"), split_docs, reset)


def embed_storeall_docs(collection_name: str, documents: List[Document], reset: bool):
    """Embeds and stores documents in PGVector."""

    vectorstore = initialize_vectorstore(collection_name)
    if reset:
        try:
            vectorstore.delete_collection()
            logger.info("Successfully cleaned up Docker collection")
            vectorstore = initialize_vectorstore(collection_name)
        except Exception as e:
            logger.error(f"Error during collection cleanup: {str(e)}")
            return
    logger.info(f"Total documents: {len(documents)}")
    vectorstore.add_documents(documents=documents)


def split_docs(documents):
    docs_list = [item for sublist in documents for item in sublist]
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=512, chunk_overlap=0
    )
    doc_splits = text_splitter.split_documents(docs_list)
    return doc_splits
