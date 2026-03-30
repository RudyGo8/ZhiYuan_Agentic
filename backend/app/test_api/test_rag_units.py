"""
RAG 核心模块单元测试
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


class TestEmbeddingService:
    """Embedding 服务测试"""
    
    @staticmethod
    def test_dense_embedding():
        """测试稠密向量生成"""
        from app.utils.embedding_service import embedding_service
        
        text = "LangChain 是一个强大的 AI 开发框架"
        embedding = embedding_service.get_embedding(text)
        
        assert embedding is not None, "稠密向量生成失败"
        assert len(embedding) > 0, "稠密向量为空"
        assert isinstance(embedding, list), "稠密向量类型错误"
        
        print(f"✅ 稠密向量测试通过 - 维度: {len(embedding)}")
        print(f"   向量前5位: {embedding[:5]}")
        return True
    
    @staticmethod
    def test_sparse_embedding():
        """测试稀疏向量(BM25)生成"""
        from app.utils.embedding_service import embedding_service
        
        text = "LangChain 是一个强大的 AI 开发框架"
        sparse = embedding_service.get_sparse_embedding(text)
        
        assert sparse is not None, "稀疏向量生成失败"
        assert isinstance(sparse, dict), "稀疏向量类型错误"
        
        print(f"✅ 稀疏向量测试通过 - 词数: {len(sparse)}")
        print(f"   词汇示例: {list(sparse.items())[:3]}")
        return True
    
    @staticmethod
    def test_batch_embedding():
        """测试批量向量生成"""
        from app.utils.embedding_service import embedding_service
        
        texts = [
            "LangChain 是一个 AI 框架",
            "RAG 是检索增强生成",
            "向量数据库用于语义搜索"
        ]
        embeddings = embedding_service.get_embeddings(texts)
        
        assert len(embeddings) == 3, "批量生成数量错误"
        assert all(len(e) > 0 for e in embeddings), "存在空向量"
        
        print(f"✅ 批量向量测试通过 - 生成了 {len(embeddings)} 个向量")
        return True
    
    @staticmethod
    def run_all():
        """运行所有 Embedding 测试"""
        print("\n" + "="*50)
        print("Embedding 服务测试")
        print("="*50)
        
        tests = [
            ("稠密向量", TestEmbeddingService.test_dense_embedding),
            ("稀疏向量", TestEmbeddingService.test_sparse_embedding),
            ("批量向量", TestEmbeddingService.test_batch_embedding),
        ]
        
        results = []
        for name, test in tests:
            try:
                result = test()
                results.append((name, result))
            except Exception as e:
                print(f"❌ {name} 测试失败: {e}")
                results.append((name, False))
        
        passed = sum(1 for _, r in results if r)
        print(f"\n结果: {passed}/{len(tests)} 通过")
        return passed == len(tests)


class TestMilvusService:
    """Milvus 向量数据库测试"""
    
    @staticmethod
    def test_connection():
        """测试 Milvus 连接"""
        from app.utils.milvus_service import milvus_service
        
        try:
            milvus_service.init_collection()
            print("✅ Milvus 连接成功")
            return True
        except Exception as e:
            print(f"❌ Milvus 连接失败: {e}")
            return False
    
    @staticmethod
    def test_insert_and_search():
        """测试向量插入和搜索"""
        from app.utils.milvus_service import milvus_service
        from app.utils.embedding_service import embedding_service
        import uuid
        
        try:
            milvus_service.init_collection()
            
            test_id = str(uuid.uuid4())
            test_text = "这是测试文档内容 LangChain"
            dense_emb = embedding_service.get_embedding(test_text)
            sparse_emb = embedding_service.get_sparse_embedding(test_text)
            
            data = [{
                "id": test_id,
                "text": test_text,
                "filename": "test.txt",
                "page_number": 1,
                "chunk_id": "test_chunk_1",
                "parent_chunk_id": "",
                "chunk_level": 3,
                "dense_vector": dense_emb,
                "sparse_vector": json.dumps(sparse_emb),
            }]
            
            milvus_service.insert(data)
            print(f"✅ 向量插入成功 - ID: {test_id}")
            
            results = milvus_service.dense_search(dense_emb, top_k=1)
            print(f"✅ 向量搜索成功 - 找到 {len(results)} 个结果")
            
            return True
        except Exception as e:
            print(f"❌ Milvus 插入/搜索失败: {e}")
            return False
    
    @staticmethod
    def test_hybrid_search():
        """测试混合搜索"""
        from app.utils.milvus_service import milvus_service
        from app.utils.embedding_service import embedding_service
        
        try:
            milvus_service.init_collection()
            
            query = "LangChain 教程"
            dense_emb = embedding_service.get_embedding(query)
            sparse_emb = embedding_service.get_sparse_embedding(query)
            
            results = milvus_service.hybrid_search(dense_emb, sparse_emb, top_k=3)
            
            print(f"✅ 混合搜索成功 - 找到 {len(results)} 个结果")
            for i, r in enumerate(results[:3], 1):
                print(f"   [{i}] {r.get('filename', 'N/A')} - {r.get('text', '')[:50]}...")
            
            return True
        except Exception as e:
            print(f"❌ 混合搜索失败: {e}")
            return False
    
    @staticmethod
    def run_all():
        """运行所有 Milvus 测试"""
        print("\n" + "="*50)
        print("Milvus 服务测试")
        print("="*50)
        
        tests = [
            ("连接测试", TestMilvusService.test_connection),
            ("插入搜索", TestMilvusService.test_insert_and_search),
            ("混合搜索", TestMilvusService.test_hybrid_search),
        ]
        
        results = []
        for name, test in tests:
            try:
                result = test()
                results.append((name, result))
            except Exception as e:
                print(f"❌ {name} 测试失败: {e}")
                results.append((name, False))
        
        passed = sum(1 for _, r in results if r)
        print(f"\n结果: {passed}/{len(tests)} 通过")
        return passed == len(tests)


class TestDocumentLoader:
    """文档加载器测试"""
    
    @staticmethod
    def test_markdown_loader():
        """测试 Markdown 文档加载"""
        from app.utils.document_loader import document_loader
        import tempfile
        import os
        
        content = """# 测试文档
        
## 第一章
这是第一章的内容，介绍LangChain。

## 第二章
这是第二章的内容，讲解RAG技术。

### 2.1 概念
RAG = 检索 + 生成
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name
        
        try:
            docs = document_loader.load_document(temp_path, "test.md")
            
            assert len(docs) > 0, "文档加载失败"
            assert all('text' in d for d in docs), "文档格式错误"
            
            print(f"✅ Markdown 加载成功 - 生成了 {len(docs)} 个块")
            for i, doc in enumerate(docs[:3], 1):
                print(f"   [{i}] {doc.get('text', '')[:50]}...")
            
            return True
        except Exception as e:
            print(f"❌ Markdown 加载失败: {e}")
            return False
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    @staticmethod
    def test_text_splitter():
        """测试文本分割"""
        from app.utils.document_loader import document_loader
        
        text = "这是第一句。这是第二句。这是第三句。这是第四句。"
        chunks = document_loader._splitter.split_text(text)
        
        assert len(chunks) > 0, "文本分割失败"
        
        print(f"✅ 文本分割成功 - 分成 {len(chunks)} 块")
        print(f"   示例: {chunks[0][:30] if chunks else 'N/A'}...")
        return True
    
    @staticmethod
    def run_all():
        """运行所有文档加载器测试"""
        print("\n" + "="*50)
        print("文档加载器测试")
        print("="*50)
        
        tests = [
            ("Markdown加载", TestDocumentLoader.test_markdown_loader),
            ("文本分割", TestDocumentLoader.test_text_splitter),
        ]
        
        results = []
        for name, test in tests:
            try:
                result = test()
                results.append((name, result))
            except Exception as e:
                print(f"❌ {name} 测试失败: {e}")
                results.append((name, False))
        
        passed = sum(1 for _, r in results if r)
        print(f"\n结果: {passed}/{len(tests)} 通过")
        return passed == len(tests)


class TestRAGPipeline:
    """RAG Pipeline 测试"""
    
    @staticmethod
    def test_retrieve_documents():
        """测试文档检索"""
        from app.rag_utils import retrieve_documents
        
        query = "什么是LangChain"
        result = retrieve_documents(query, top_k=3)
        
        docs = result.get("docs", [])
        meta = result.get("meta", {})
        
        print(f"✅ 文档检索完成")
        print(f"   检索到 {len(docs)} 个文档")
        print(f"   检索模式: {meta.get('retrieval_mode')}")
        print(f"   Rerank: {meta.get('rerank_applied')}")
        print(f"   Auto-merging: {meta.get('auto_merge_applied')}")
        
        return True
    
    @staticmethod
    def test_step_back():
        """测试 Step-back 查询扩展"""
        from app.rag_utils import step_back_expand
        
        query = "LangChain中如何使用Chain"
        result = step_back_expand(query)
        
        print(f"✅ Step-back 扩展完成")
        print(f"   原始问题: {query}")
        print(f"   退步问题: {result.get('step_back_question', '')}")
        print(f"   扩展查询: {result.get('expanded_query', '')}")
        
        return True
    
    @staticmethod
    def test_hyde():
        """测试 HyDE 假设性文档"""
        from app.rag_utils import generate_hypothetical_document
        
        query = "如何学习LangChain"
        result = generate_hypothetical_document(query)
        
        print(f"✅ HyDE 假设文档生成完成")
        print(f"   原始问题: {query}")
        print(f"   假设文档: {result[:150]}...")
        
        return True
    
    @staticmethod
    def test_full_pipeline():
        """测试完整 RAG Pipeline"""
        from app.rag_pipeline import run_rag_graph
        
        question = "LangChain的核心组件有哪些？"
        
        result = run_rag_graph(question)
        
        docs = result.get("docs", [])
        rag_trace = result.get("rag_trace", {})
        
        print(f"✅ 完整 RAG Pipeline 测试")
        print(f"   问题: {question}")
        print(f"   检索到 {len(docs)} 个文档")
        print(f"   重写策略: {rag_trace.get('rewrite_strategy', 'N/A')}")
        print(f"   检索模式: {rag_trace.get('retrieval_mode')}")
        
        if docs:
            print(f"   Top1: {docs[0].get('text', '')[:80]}...")
        
        return True
    
    @staticmethod
    def run_all():
        """运行所有 RAG Pipeline 测试"""
        print("\n" + "="*50)
        print("RAG Pipeline 测试")
        print("="*50)
        
        tests = [
            ("文档检索", TestRAGPipeline.test_retrieve_documents),
            ("Step-back扩展", TestRAGPipeline.test_step_back),
            ("HyDE假设文档", TestRAGPipeline.test_hyde),
            ("完整Pipeline", TestRAGPipeline.test_full_pipeline),
        ]
        
        results = []
        for name, test in tests:
            try:
                result = test()
                results.append((name, result))
            except Exception as e:
                print(f"❌ {name} 测试失败: {e}")
                results.append((name, False))
        
        passed = sum(1 for _, r in results if r)
        print(f"\n结果: {passed}/{len(tests)} 通过")
        return passed == len(tests)


class TestTools:
    """工具函数测试"""
    
    @staticmethod
    def test_weather():
        """测试天气查询工具"""
        from app.tools import get_current_weather
        
        result = get_current_weather("北京")
        
        print(f"✅ 天气查询测试")
        print(f"   北京天气: {result[:200]}...")
        
        return True
    
    @staticmethod
    def test_search_knowledge():
        """测试知识库搜索工具"""
        from app.tools import search_knowledge_base
        
        result = search_knowledge_base.invoke({"query": "什么是LangChain"})
        
        print(f"✅ 知识库搜索测试")
        print(f"   结果: {result[:200]}...")
        
        return True
    
    @staticmethod
    def run_all():
        """运行所有工具测试"""
        print("\n" + "="*50)
        print("工具函数测试")
        print("="*50)
        
        tests = [
            ("天气查询", TestTools.test_weather),
            ("知识库搜索", TestTools.test_search_knowledge),
        ]
        
        results = []
        for name, test in tests:
            try:
                result = test()
                results.append((name, result))
            except Exception as e:
                print(f"❌ {name} 测试失败: {e}")
                results.append((name, False))
        
        passed = sum(1 for _, r in results if r)
        print(f"\n结果: {passed}/{len(tests)} 通过")
        return passed == len(tests)


def run_all_unit_tests():
    """运行所有单元测试"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                 RAG 核心模块单元测试                          ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    test_suites = [
        TestEmbeddingService,
        TestMilvusService,
        TestDocumentLoader,
        TestRAGPipeline,
        TestTools,
    ]
    
    all_results = []
    for suite in test_suites:
        try:
            result = suite.run_all()
            all_results.append((suite.__name__, result))
        except Exception as e:
            print(f"❌ {suite.__name__} 测试套件异常: {e}")
            all_results.append((suite.__name__, False))
    
    print("\n" + "="*60)
    print("📊 最终测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, r in all_results if r)
    total = len(all_results)
    
    for name, result in all_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}  {name}")
    
    print(f"\n总计: {passed}/{total} 测试套件通过")
    print("="*60)


if __name__ == "__main__":
    run_all_unit_tests()
