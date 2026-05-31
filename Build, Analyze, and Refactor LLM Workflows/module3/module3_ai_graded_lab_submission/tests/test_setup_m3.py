#!/usr/bin/env python3
"""
MODULE 3 - PRE-RECORDING SETUP TEST
Run this to verify everything is ready before recording
"""

import os
import sys

print("=" * 70)
print("MODULE 3 - PRE-RECORDING SETUP TEST")
print("=" * 70)
print()

# =============================================================================
# TEST 1: Check Python Version
# =============================================================================
print("TEST 1: Python Version")
print("-" * 70)
python_version = sys.version_info
print(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
if python_version.major >= 3 and python_version.minor >= 8:
    print("✓ Python version OK (3.8+)")
else:
    print("✗ Python version too old. Need 3.8 or higher")
    sys.exit(1)
print()

# =============================================================================
# TEST 2: Check Required Packages
# =============================================================================
print("TEST 2: Required Packages")
print("-" * 70)

required_packages = {
    'langchain': 'langchain',
    'openai': 'openai',
    'chromadb': 'chromadb',
    'dotenv': 'dotenv',
    'redis': 'redis',
}

all_installed = True
for package_name, import_name in required_packages.items():
    try:
        __import__(import_name)
        print(f"✓ {package_name} installed")
    except ImportError:
        print(f"✗ {package_name} NOT installed")
        print(f"  Install with: pip install {package_name}")
        all_installed = False

if not all_installed:
    print()
    print("Install all packages with:")
    print("pip install langchain openai chromadb python-dotenv redis")
    sys.exit(1)
print()

# =============================================================================
# TEST 3: Check API Key
# =============================================================================
print("TEST 3: OpenAI API Key")
print("-" * 70)

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

api_key = os.environ.get('OPENAI_API_KEY')
if api_key:
    print("✓ OPENAI_API_KEY found in environment")
    print(f"  Key starts with: {api_key[:8]}...")
else:
    print("✗ OPENAI_API_KEY not found!")
    print()
    print("Create .env file with:")
    print("  OPENAI_API_KEY=your-key-here")
    sys.exit(1)
print()

# =============================================================================
# TEST 4: Check Documents Exist
# =============================================================================
print("TEST 4: Sample Documents")
print("-" * 70)

docs_dir = './docs'
if os.path.exists(docs_dir):
    files = [f for f in os.listdir(docs_dir) if f.endswith('.txt')]
    if files:
        print(f"✓ Documents folder found with {len(files)} files:")
        for f in files:
            print(f"  - {f}")
    else:
        print("✗ No .txt files in docs folder!")
        sys.exit(1)
else:
    print("✗ ./docs folder not found!")
    print("  Make sure you're in the module3 directory")
    sys.exit(1)
print()

# =============================================================================
# TEST 5: Check Redis Connection
# =============================================================================
print("TEST 5: Redis Connection")
print("-" * 70)

try:
    import redis
    redis_client = redis.Redis(host='localhost', port=6379, db=0)
    redis_client.ping()
    print("✓ Redis is running and accessible")
    print("  Host: localhost:6379")
except Exception as e:
    print("✗ Redis connection failed!")
    print(f"  Error: {e}")
    print()
    print("  Start Redis:")
    print("    Mac: brew services start redis")
    print("    Linux: sudo service redis-server start")
    print("    Docker: docker run -d -p 6379:6379 redis")
    print()
    print("  Video 2 will work without Redis")
    print("  Video 3 requires Redis for caching demo")
print()

# =============================================================================
# TEST 6: Test Document Loading
# =============================================================================
print("TEST 6: Document Loading")
print("-" * 70)

try:
    from langchain_community.document_loaders import DirectoryLoader, TextLoader

    loader = DirectoryLoader('./docs', glob="**/*.txt", loader_cls=TextLoader)
    documents = loader.load()
    
    print(f"✓ Successfully loaded {len(documents)} documents")
    total_chars = sum(len(doc.page_content) for doc in documents)
    print(f"  Total characters: {total_chars:,}")
    
except Exception as e:
    print("✗ Document loading failed!")
    print(f"  Error: {e}")
    sys.exit(1)
print()

# =============================================================================
# TEST 7: Test Embeddings (Quick)
# =============================================================================
print("TEST 7: Embeddings API Test")
print("-" * 70)
print("Testing OpenAI embeddings... (this uses a small amount of API credits)")

try:
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings()
    test_text = "This is a test"
    result = embeddings.embed_query(test_text)
    
    print("✓ Embeddings API works!")
    print(f"  Embedding dimensions: {len(result)}")
    
except Exception as e:
    print("✗ Embeddings API failed!")
    print(f"  Error: {e}")
    print()
    print("  Check:")
    print("  - API key is valid")
    print("  - You have API credits")
    print("  - Internet connection")
    sys.exit(1)
print()

# =============================================================================
# TEST 8: Test Basic RAG System
# =============================================================================
print("TEST 8: Basic RAG System Test")
print("-" * 70)
print("Running minimal RAG system... (this may take 30-60 seconds)")

try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_chroma import Chroma
    from langchain.chains import RetrievalQA
    from langchain_openai import ChatOpenAI
    
    # Load and split
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    texts = text_splitter.split_documents(documents)
    print(f"  → Split into {len(texts)} chunks")
    
    # Create vector store
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(
        documents=texts[:10],  # Only use first 10 chunks for testing
        embedding=embeddings,
        persist_directory="./test_chroma_db"
    )
    print(f"  → Created vector store")
    
    # Create retriever and chain
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    llm = ChatOpenAI(model="gpt-4-turbo", temperature=0.3)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever
    )
    print(f"  → Created QA chain")
    
    # Test query
    result = qa_chain.invoke({"query": "What features are available?"})
    print(f"  → Query successful!")
    
    print()
    print("✓ Complete RAG system works!")
    print(f"  Answer preview: {result['result'][:80]}...")
    
    # Cleanup test database
    import shutil
    if os.path.exists("./test_chroma_db"):
        shutil.rmtree("./test_chroma_db")
    
except Exception as e:
    print("✗ RAG system test failed!")
    print(f"  Error: {e}")
    print()
    print("  This might be a temporary API issue.")
    print("  Try running the test again.")
    sys.exit(1)
print()

# =============================================================================
# FINAL SUMMARY
# =============================================================================
print("=" * 70)
print("🎉 ALL TESTS PASSED! YOU'RE READY TO RECORD!")
print("=" * 70)
print()
print("📋 RECORDING CHECKLIST:")
print()
print("Video 2: Building a RAG System")
print("  [ ] Documents in ./docs folder")
print("  [ ] Blank rag_system.py ready")
print("  [ ] Complete version ready to show")
print("  [ ] Terminal ready")
print()
print("Video 3: Monitoring and Caching")
print("  [ ] Redis is running")
print("  [ ] rag_system_cached.py ready")
print("  [ ] Can demonstrate cache hit/miss")
print()
print("Both Videos:")
print("  [ ] SPEAKING_GUIDE_M3.md open")
print("  [ ] Font size 16pt+ in editor")
print("  [ ] Close unnecessary windows")
print()
print("=" * 70)
print("Estimated API costs for recording:")
print("  - Video 2 (basic RAG): ~$0.10")
print("  - Video 3 (with caching): ~$0.20")
print("  - Total: ~$0.30")
print("=" * 70)
print()
print("Next steps:")
print("1. Review SPEAKING_GUIDE_M3.md")
print("2. Practice once with the guide")
print("3. Start recording!")
print()
print("Good luck! 🚀")
print("=" * 70)