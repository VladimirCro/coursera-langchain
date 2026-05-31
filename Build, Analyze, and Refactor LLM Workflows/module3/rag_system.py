#!/usr/bin/env python3
"""
MODULE 3 - VIDEO 2: Building a RAG System
Complete implementation with document loading, embeddings, and retrieval
"""

import os
from dotenv import load_dotenv

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_classic.chains.retrieval_qa.base import RetrievalQA

# Load environment variables
load_dotenv()

print("=" * 70)
print("MODULE 3 - VIDEO 2: BUILDING A RAG SYSTEM")
print("=" * 70)
print()

# =============================================================================
# STEP 1: LOAD DOCUMENTS
# =============================================================================
print("STEP 1: Loading Documents")
print("-" * 70)

# Load documents from directory
loader = DirectoryLoader('./docs', glob="**/*.txt", loader_cls=TextLoader)
documents = loader.load()

print(f"✓ Loaded {len(documents)} documents")
for i, doc in enumerate(documents, 1):
    print(f"  {i}. {os.path.basename(doc.metadata['source'])} "
          f"({len(doc.page_content)} characters)")
print()

# =============================================================================
# STEP 2: SPLIT DOCUMENTS INTO CHUNKS
# =============================================================================
print("STEP 2: Splitting Documents into Chunks")
print("-" * 70)

# Split documents into chunks
# chunk_size=1000: Each chunk is ~1000 characters
# chunk_overlap=200: 200 characters overlap between chunks to preserve context
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

texts = text_splitter.split_documents(documents)

print(f"✓ Split into {len(texts)} chunks")
print(f"  Average chunk size: {sum(len(t.page_content) for t in texts) // len(texts)} characters")
print()

# =============================================================================
# STEP 3: CREATE EMBEDDINGS & VECTOR STORE
# =============================================================================
print("STEP 3: Creating Embeddings & Vector Store")
print("-" * 70)
print("Creating embeddings and storing in Chroma vector database...")
print("(This may take a moment...)")
print()

# Create embeddings using OpenAI's embedding model
embeddings = OpenAIEmbeddings()

# Create vector store from documents
# Chroma is a lightweight vector database that runs locally
vectorstore = Chroma.from_documents(
    documents=texts,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

print("✓ Vector store created and persisted to ./chroma_db")
print(f"  Total vectors: {len(texts)}")
print()

# =============================================================================
# STEP 4: CREATE RETRIEVER
# =============================================================================
print("STEP 4: Creating Retriever")
print("-" * 70)

# Create retriever from vector store
# k=3 means retrieve the 3 most relevant chunks for each query
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

print("✓ Retriever configured")
print("  Retrieval mode: Similarity search")
print("  Top-k chunks: 3")
print()

# =============================================================================
# STEP 5: CREATE LLM AND QA CHAIN
# =============================================================================
print("STEP 5: Creating QA Chain")
print("-" * 70)

# Initialize the language model
llm = ChatOpenAI(
    model="gpt-4-turbo",
    temperature=0.3  # Lower temperature for more consistent answers
)

# Create the RetrievalQA chain
# This automatically handles: retrieve relevant docs → pass to LLM → generate answer
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",  # "stuff" means put all retrieved docs in the prompt
    retriever=retriever,
    return_source_documents=True  # Return the documents used for the answer
)

print("✓ QA chain created")
print("  LLM: gpt-4-turbo")
print("  Chain type: stuff (combine documents)")
print()

# =============================================================================
# STEP 6: QUERY THE SYSTEM
# =============================================================================
print("=" * 70)
print("RAG SYSTEM READY - TESTING QUERIES")
print("=" * 70)
print()

# Test queries
test_queries = [
    "What are the main features of the premium plan?",
    "What's the refund policy?",
    "What are your support hours?",
]

for i, query in enumerate(test_queries, 1):
    print(f"Query {i}: {query}")
    print("-" * 70)
    
    # Run the query
    result = qa_chain.invoke({"query": query})
    
    # Print the answer
    print(f"Answer: {result['result']}")
    print()
    
    # Print source documents
    print("Sources:")
    for j, doc in enumerate(result['source_documents'], 1):
        source_file = os.path.basename(doc.metadata['source'])
        preview = doc.page_content[:100].replace('\n', ' ')
        print(f"  {j}. {source_file}: {preview}...")
    print()
    print()

# =============================================================================
# INTERACTIVE MODE (Optional)
# =============================================================================
print("=" * 70)
print("INTERACTIVE MODE")
print("=" * 70)
print("You can now ask questions about the documentation.")
print("Type 'quit' or 'exit' to stop.")
print()

while True:
    try:
        user_query = input("Your question: ").strip()
        
        if user_query.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
            
        if not user_query:
            continue
        
        # Run query
        result = qa_chain.invoke({"query": user_query})
        
        print()
        print("Answer:", result['result'])
        print()
        print("Sources:")
        for i, doc in enumerate(result['source_documents'], 1):
            source_file = os.path.basename(doc.metadata['source'])
            print(f"  {i}. {source_file}")
        print()
        
    except KeyboardInterrupt:
        print("\nGoodbye!")
        break
    except Exception as e:
        print(f"Error: {e}")
        print()

# =============================================================================
# SUMMARY
# =============================================================================
print("=" * 70)
print("RAG SYSTEM SUMMARY")
print("=" * 70)
print()
print("✓ Documents loaded and chunked")
print("✓ Embeddings created and stored in vector database")
print("✓ Retriever configured for semantic search")
print("✓ QA chain created with LLM integration")
print("✓ System tested with sample queries")
print()
print("Key Components:")
print("  1. Knowledge Base: Chroma vector database with OpenAI embeddings")
print("  2. Retriever: Top-3 semantic similarity search")
print("  3. Generator: GPT-4-turbo with temperature=0.3")
print()
print("Performance:")
print(f"  - {len(documents)} documents → {len(texts)} searchable chunks")
print("  - Retrieves 3 most relevant chunks per query")
print("  - Grounded answers with source citations")
print("=" * 70)