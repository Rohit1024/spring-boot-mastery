---
icon: lucide/database-zap
---

# 0080: Retrieval-Augmented Generation (RAG) with Vector Stores & Embeddings

Large Language Models suffer from two critical limitations in enterprise software:
1. **Knowledge Cutoffs**: They lack knowledge of events occurring after their training cutoff.
2. **Private Data Blindness**: They cannot access your proprietary company policies, internal databases, product manuals, or customer records.

Fine-tuning LLMs on internal data is computationally expensive, prone to catastrophic forgetting, and leaks sensitive permissions.

**Retrieval-Augmented Generation (RAG)** solves this by retrieving relevant document snippets from a **Vector Database** (such as PostgreSQL `pgvector`, Qdrant, Pinecone, or Milvus) and injecting them as contextual grounding directly into the LLM prompt at runtime.

In this lesson, you will master document chunking, embedding generation with `EmbeddingModel`, storing vectors in `VectorStore`, and building an end-to-end RAG question-answering service in Spring AI.

---

## 1. Retrieval-Augmented Generation (RAG) Pipeline

``` mermaid
flowchart TD
    subgraph IngestionPipeline["1. Offline Document Ingestion Pipeline"]
        RawDocs["Internal Documents (PDF / Markdown / HTML)"]
        TextSplitter["TokenTextSplitter (Chunk size: 800 tokens, 100 overlap)"]
        EmbeddingEngine["EmbeddingModel (Text -> 1536-dim Float Vector)"]
        VectorDB[("Vector Store (PostgreSQL pgvector / Qdrant / Pinecone)")]
        
        RawDocs --> TextSplitter
        TextSplitter --> EmbeddingEngine
        EmbeddingEngine -->|Store Chunks & Embeddings| VectorDB
    end

    subgraph RetrievalGeneration["2. Real-Time Retrieval & Generation Pipeline"]
        UserQuery["User Question: 'What is AcmeCorp's return policy?'"]
        QueryEmbedding["Generate Query Embedding Vector"]
        SimilaritySearch["Cosine Similarity Search (Top-K = 3 Chunks)"]
        RAGPrompt["Augmented Prompt: Context Docs + User Question"]
        LLM["LLM (GPT-4o / Claude 3.5 / Gemini)"]
        GroundedAnswer["Grounded, Hallucination-Free Answer"]

        UserQuery --> QueryEmbedding
        QueryEmbedding --> SimilaritySearch
        VectorDB -.->|Fetch Nearest Neighbor Chunks| SimilaritySearch
        SimilaritySearch --> RAGPrompt
        UserQuery --> RAGPrompt
        RAGPrompt --> LLM
        LLM --> GroundedAnswer
    end

    IngestionPipeline ~~~ RetrievalGeneration
```

---

## 2. Maven Dependencies (`pom.xml`)

Include the Spring AI OpenAI and PostgreSQL `pgvector` starters:

```xml
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-openai-spring-boot-starter</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-pgvector-store-spring-boot-starter</artifactId>
</dependency>
```

### PostgreSQL `pgvector` Schema Configuration (`application.yml`)

```yaml
spring:
  ai:
    openai:
      api-key: ${OPENAI_API_KEY}
      embedding:
        options:
          model: text-embedding-3-small # Generates 1536-dimensional vectors
    vectorstore:
      pgvector:
        index-type: HNSW              # Hierarchical Navigable Small World (fastest indexing)
        distance-type: COSINE_DISTANCE
        dimensions: 1536
```

---

## 3. Document Ingestion Service

Split large enterprise documents into semantically coherent chunks and index them into the vector database:

```java
package com.example.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.document.Document;
import org.springframework.ai.reader.TextReader;
import org.springframework.ai.transformer.splitter.TokenTextSplitter;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentIngestionService {

    private final VectorStore vectorStore;

    public void ingestEnterpriseDocument(Resource documentResource, String department) {
        log.info("Loading document: {}", documentResource.getFilename());

        // 1. Read document content
        TextReader textReader = new TextReader(documentResource);
        textReader.getCustomMetadata().put("department", department);
        List<Document> rawDocuments = textReader.get();

        // 2. Split into chunks (800 tokens with 100 token overlap for context continuity)
        TokenTextSplitter splitter = new TokenTextSplitter(800, 100, 5, 10000, true);
        List<Document> chunks = splitter.apply(rawDocuments);

        log.info("Split document into {} chunks. Generating embeddings...", chunks.size());

        // 3. Generate embeddings and store in Vector DB (pgvector)
        vectorStore.accept(chunks);
        log.info("Document successfully indexed in Vector Store.");
    }
}
```

---

## 4. Building the RAG Question-Answering Service

In Spring AI, the **`QuestionAnswerAdvisor`** intercepts the `ChatClient` prompt chain, automatically generates the query embedding, queries the `VectorStore`, and injects the retrieved documents into the system prompt:

```java
package com.example.service;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.QuestionAnswerAdvisor;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.stereotype.Service;

@Service
public class EnterpriseKnowledgeService {

    private final ChatClient chatClient;

    public EnterpriseKnowledgeService(ChatClient.Builder chatClientBuilder, VectorStore vectorStore) {
        // Configure RAG Advisor with Top-K = 4 and 0.75 similarity threshold
        SearchRequest searchRequest = SearchRequest.defaults()
                .withTopK(4)
                .withSimilarityThreshold(0.75);

        this.chatClient = chatClientBuilder
                .defaultAdvisors(new QuestionAnswerAdvisor(vectorStore, searchRequest))
                .defaultSystem("""
                    You are an official enterprise AI assistant.
                    Answer user questions strictly based on the provided contextual documents.
                    If the answer cannot be found in the context, reply:
                    "I cannot find this information in our official company records."
                    """)
                .build();
    }

    public String askCompanyKnowledgeBase(String userQuestion) {
        return chatClient.prompt()
                .user(userQuestion)
                .call()
                .content();
    }
}
```

---

## 5. Metadata Filtering in Similarity Search

To prevent HR documents from leaking to general employees, apply dynamic metadata filters during vector search:

```java
public List<Document> searchDepartmentDocs(String query, String userDepartment) {
    SearchRequest request = SearchRequest.defaults()
            .withQuery(query)
            .withTopK(3)
            .withFilterExpression("department == '" + userDepartment + "'");

    return vectorStore.similaritySearch(request);
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Vector Store Ecosystem** | 10+ Vector Stores supported (PgVector, Qdrant, Pinecone, Neo4j, Redis, Weaviate). | Unified SQL / Vector hybrid query planner with native R2DBC streaming vectors. |
| **Evaluation & Guardrails**| Manual BLEU / ROUGE evaluation metrics. | Built-in RAG Triad Evaluators (Context Relevance, Groundedness, Answer Relevance). |
| **Agentic RAG** | Single-hop similarity retrieval advisors. | Multi-step Agentic RAG with iterative query reformulation and web fallback. |

---

## 7. Primary Sources & Further Reading

- [Spring AI Vector Stores Reference](https://docs.spring.io/spring-ai/reference/api/vectordbs.html) — PgVector, Qdrant, and Milvus.
- [Spring AI QuestionAnswerAdvisor](https://docs.spring.io/spring-ai/reference/api/advisors.html#_questionansweradvisor).
- [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks (Lewis et al.)](https://arxiv.org/abs/2005.11401).

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the primary purpose of an Embedding Model in a RAG system?"
    **Answer**: It converts human text into high-dimensional numerical vectors that capture the semantic meaning and context of the text for similarity searches.

??? question "Question 2: Why are large documents split into smaller overlapping chunks before being stored in a Vector DB?"
    **Answer**: Smaller chunks ensure that retrieved text fits within the LLM's context window and precisely matches the user's specific query without diluting context.

??? question "Question 3: How does the `QuestionAnswerAdvisor` simplify RAG in Spring AI?"
    **Answer**: It automatically takes the user's query, executes similarity search against the configured `VectorStore`, and injects the retrieved documents directly into the prompt context.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0079: Spring AI: LLM Chat Clients & Prompts**](0079-spring-ai-llm-chatclient-prompts.md) | [**All Lessons**](index.md) | [➡️ **0081: Model Context Protocol (MCP) in Spring AI**](0081-mcp-server-tool-integration-spring-ai.md) |

🎉 **Lesson 0080 completed! Proceed to Lesson 0081 to master the revolutionary Model Context Protocol (MCP) and AI tool integration.**
