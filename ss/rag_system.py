"""
RAG Document Retrieval and Injection System for PersonaRAG

Handles document retrieval, filtering, and injection based on persona-specific
requirements and question analysis.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import re
from collections import Counter


class DocumentType(Enum):
    """Types of documents in the knowledge base"""
    POLICY = "policy"
    TECHNICAL = "technical"
    BUSINESS = "business"
    TRAINING = "training"
    GENERAL = "general"


@dataclass
class Document:
    """Represents a document in the knowledge base"""
    id: str
    content: str
    doc_type: DocumentType
    metadata: Dict[str, Any]
    relevance_score: float = 0.0


@dataclass
class RetrievalResult:
    """Result of document retrieval operation"""
    documents: List[Document]
    query: str
    persona: str
    total_retrieved: int
    retrieval_metadata: Dict[str, Any]


class DocumentStore:
    """In-memory document store for demonstration"""
    
    def __init__(self):
        self.documents: Dict[str, Document] = {}
        self._initialize_sample_documents()
    
    def _initialize_sample_documents(self):
        """Initialize with sample documents for testing"""
        sample_docs = [
            Document(
                id="policy_001",
                content="Remote Work Policy: Employees may work remotely up to 3 days per week with manager approval. This policy supports work-life balance while maintaining team collaboration. All remote work must be logged in the time tracking system.",
                doc_type=DocumentType.POLICY,
                metadata={"department": "HR", "effective_date": "2024-01-01", "priority": "high"}
            ),
            Document(
                id="tech_001", 
                content="Authentication System: The system uses JWT tokens for authentication. Tokens are generated server-side using a secret key and contain user claims. The token is sent in the Authorization header as 'Bearer <token>'. Tokens expire after 24 hours and must be refreshed using the refresh endpoint.",
                doc_type=DocumentType.TECHNICAL,
                metadata={"system": "auth", "complexity": "medium", "dependencies": ["JWT", "OAuth2"]}
            ),
            Document(
                id="business_001",
                content="Q3 Financial Results: Revenue increased by 15% year-over-year to $2.5M. Customer acquisition cost decreased by 8% while retention improved to 92%. The new product line contributed 30% of total revenue with strong market adoption.",
                doc_type=DocumentType.BUSINESS,
                metadata={"quarter": "Q3", "year": "2024", "department": "Finance"}
            ),
            Document(
                id="trends_001",
                content="Q1 2025 Business Trends: AI adoption accelerating across enterprises with 67% increasing investment. Remote work hybrid models becoming standard with 3-4 days office requirement. Supply chain diversification priority due to geopolitical risks. Sustainability reporting now mandatory for public companies. Cybersecurity budgets increasing by 25% YoY. Key takeaways include AI transformation, hybrid work adoption, and risk management priorities.",
                doc_type=DocumentType.BUSINESS,
                metadata={"quarter": "Q1", "year": "2025", "category": "trends"}
            ),
            Document(
                id="training_001",
                content="Onboarding Process: New employees complete a 2-week onboarding program. Week 1 covers company policies, tools training, and team introductions. Week 2 focuses on role-specific training and project assignments. Each new hire is assigned a mentor for the first 90 days.",
                doc_type=DocumentType.TRAINING,
                metadata={"duration": "2 weeks", "target": "new_hires", "required": True}
            ),
            Document(
                id="general_001",
                content="Company Culture: We value innovation, collaboration, and continuous learning. Regular team meetings, hackathons, and knowledge sharing sessions are encouraged. The company supports professional development with annual training budgets.",
                doc_type=DocumentType.GENERAL,
                metadata={"category": "culture", "audience": "all_employees"}
            ),
            Document(
                id="challenges_001",
                content="Industry Challenges: The technology sector faces significant challenges including talent shortages in AI and cybersecurity fields, increasing regulatory compliance requirements, and pressure to adopt sustainable practices. Companies struggle with digital transformation costs while maintaining legacy system compatibility. Competition for skilled workers has increased salaries by 20% YoY. Data privacy regulations like GDPR and CCPA require significant investment in compliance infrastructure. Supply chain disruptions have increased operational costs by 15%. Customer expectations for 24/7 service require major infrastructure investments.",
                doc_type=DocumentType.BUSINESS,
                metadata={"category": "challenges", "industry": "technology", "year": "2024"}
            )
        ]
        
        for doc in sample_docs:
            self.documents[doc.id] = doc
    
    def add_document(self, document: Document) -> None:
        """Add a document to the store"""
        self.documents[document.id] = document
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get a document by ID"""
        return self.documents.get(doc_id)
    
    def get_all_documents(self) -> List[Document]:
        """Get all documents"""
        return list(self.documents.values())


class PersonaDocumentFilter:
    """Filters documents based on persona requirements"""
    
    def __init__(self):
        self.persona_filters = {
            "Executive": {
                "preferred_types": [DocumentType.BUSINESS, DocumentType.POLICY],
                "content_keywords": ["revenue", "cost", "roi", "strategy", "risk", "impact", "challenges", "industry"],
                "exclude_keywords": ["implementation", "code", "technical", "debug"],
                "max_documents": 3,
                "min_relevance": 0.3
            },
            "Developer": {
                "preferred_types": [DocumentType.TECHNICAL, DocumentType.TRAINING, DocumentType.BUSINESS],
                "content_keywords": ["code", "api", "system", "implementation", "architecture", "business", "trends", "challenges", "industry"],
                "exclude_keywords": ["executive", "financial", "legal"],
                "max_documents": 5,
                "min_relevance": 0.4
            },
            "HR Specialist": {
                "preferred_types": [DocumentType.POLICY, DocumentType.TRAINING, DocumentType.GENERAL, DocumentType.BUSINESS],
                "content_keywords": ["policy", "employee", "compliance", "process", "procedure", "business", "trends", "challenges", "industry"],
                "exclude_keywords": ["code", "technical", "revenue", "financial"],
                "max_documents": 4,
                "min_relevance": 0.3
            },
            "Student": {
                "preferred_types": [DocumentType.TRAINING, DocumentType.GENERAL, DocumentType.TECHNICAL, DocumentType.BUSINESS],
                "content_keywords": ["learn", "tutorial", "guide", "example", "process", "business", "trends", "takeaways", "key", "challenges", "industry"],
                "exclude_keywords": ["executive", "financial", "legal"],
                "max_documents": 3,
                "min_relevance": 0.2
            },
            "General": {
                "preferred_types": [DocumentType.GENERAL, DocumentType.BUSINESS, DocumentType.POLICY],
                "content_keywords": ["company", "culture", "team", "business", "trends", "challenges", "industry"],
                "exclude_keywords": ["code", "implementation", "debug"],
                "max_documents": 4,
                "min_relevance": 0.25
            }
        }
    
    def filter_documents(self, documents: List[Document], persona: str) -> List[Document]:
        """Filter documents based on persona preferences"""
        if persona not in self.persona_filters:
            return documents
        
        filters = self.persona_filters[persona]
        filtered_docs = []
        
        for doc in documents:
            # Check document type preference
            if doc.doc_type not in filters["preferred_types"]:
                # Still include if highly relevant, but lower priority
                if doc.relevance_score < 0.7:
                    continue
            
            # Check excluded keywords
            content_lower = doc.content.lower()
            if any(keyword.lower() in content_lower for keyword in filters["exclude_keywords"]):
                continue
            
            # Check minimum relevance
            if doc.relevance_score < filters["min_relevance"]:
                continue
            
            filtered_docs.append(doc)
        
        # Sort by relevance and limit to max documents
        filtered_docs.sort(key=lambda x: x.relevance_score, reverse=True)
        return filtered_docs[:filters["max_documents"]]


class DocumentRetriever:
    """Main document retrieval system"""
    
    def __init__(self, document_store: DocumentStore):
        self.document_store = document_store
        self.filter = PersonaDocumentFilter()
    
    def calculate_relevance(self, document: Document, query: str, persona: str) -> float:
        """Calculate relevance score for a document"""
        query_lower = query.lower()
        doc_lower = document.content.lower()
        
        # Extract meaningful terms (exclude common words)
        common_words = {'the', 'is', 'are', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'when', 'where', 'how', 'why', 'what', 'our', 'your', 'their', 'we', 'they', 'you', 'me', 'us', 'them'}
        query_terms = [term.strip('?.!') for term in query_lower.split() if term not in common_words and len(term.strip('?.!')) > 2]
        
        # Add pluralization variations for better matching
        expanded_terms = set(query_terms)
        for term in query_terms:
            # Add singular/plural variations
            if term.endswith('ies'):
                expanded_terms.add(term[:-3] + 'y')  # policies -> policy
            elif term.endswith('s'):
                expanded_terms.add(term[:-1])  # policies -> policy
            elif not term.endswith('s'):
                expanded_terms.add(term + 's')  # policy -> policies
        
        if not expanded_terms:
            return 0.0
        
        # Calculate term overlap with exact matches prioritized
        exact_matches = 0
        partial_matches = 0
        
        for term in expanded_terms:
            if term in doc_lower:
                # Check for exact phrase matches (higher weight)
                if f" {term} " in f" {doc_lower} " or doc_lower.startswith(f"{term} ") or doc_lower.endswith(f" {term}"):
                    exact_matches += 2  # Higher weight for exact matches
                else:
                    partial_matches += 1
        
        # Calculate coverage with weighted matches
        total_matches = exact_matches + partial_matches
        query_coverage = total_matches / (len(expanded_terms) * 2)  # Normalize by max possible score
        
        # Only consider relevant if there's meaningful overlap
        if query_coverage < 0.3:  # At least 30% of meaningful terms should match
            return 0.0
        
        # Additional check: ensure matched terms are significant parts of the document
        total_doc_words = len(doc_lower.split())
        if total_doc_words == 0:
            return 0.0
        
        # Document density of matched terms
        matched_density = total_matches / total_doc_words
        if matched_density < 0.01:  # At least 1% of document should contain matched terms
            return 0.0
        
        # Bonus for documents that specifically address the query topic
        topic_bonus = 0
        if 'authentication' in query_lower and 'authentication' in doc_lower:
            topic_bonus += 0.5  # Strong bonus for exact authentication match
        if 'system' in query_lower and 'system' in doc_lower:
            topic_bonus += 0.3
        if 'jwt' in query_lower and 'jwt' in doc_lower:
            topic_bonus += 0.4
        if 'token' in query_lower and 'token' in doc_lower:
            topic_bonus += 0.3
        if 'cybersecurity' in query_lower and 'cybersecurity' in doc_lower:
            topic_bonus += 0.2
        
        # Persona-specific weighting
        persona_filters = self.filter.persona_filters.get(persona, {})
        preferred_keywords = persona_filters.get("content_keywords", [])
        
        keyword_bonus = 0
        for keyword in preferred_keywords:
            if keyword.lower() in doc_lower:
                keyword_bonus += 0.1
        
        # Document type preference
        type_bonus = 0
        preferred_types = persona_filters.get("preferred_types", [])
        if document.doc_type in preferred_types:
            type_bonus = 0.2
        
        # Combine scores with topic bonus prioritized
        relevance = (query_coverage * 0.4) + (matched_density * 0.2) + topic_bonus + keyword_bonus + type_bonus
        return min(relevance, 1.0)
    
    def retrieve_documents(self, query: str, persona: str, top_k: int = 10) -> RetrievalResult:
        """Retrieve relevant documents for a query and persona"""
        all_docs = self.document_store.get_all_documents()
        
        # Calculate relevance scores
        scored_docs = []
        for doc in all_docs:
            relevance = self.calculate_relevance(doc, query, persona)
            doc.relevance_score = relevance
            if relevance > 0.1:  # Minimum threshold
                scored_docs.append(doc)
        
        # If no relevant documents found, return empty result
        if not scored_docs:
            return RetrievalResult(
                documents=[],
                query=query,
                persona=persona,
                total_retrieved=0,
                retrieval_metadata={"reason": "no_relevant_documents"}
            )
        
        # Sort by relevance
        scored_docs.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Apply persona filtering
        filtered_docs = self.filter.filter_documents(scored_docs[:top_k], persona)
        
        return RetrievalResult(
            documents=filtered_docs,
            query=query,
            persona=persona,
            total_retrieved=len(filtered_docs),
            retrieval_metadata={"avg_relevance": sum(doc.relevance_score for doc in filtered_docs) / len(filtered_docs) if filtered_docs else 0}
        )
    
    def build_rag_context(self, retrieval_result: RetrievalResult) -> str:
        """Build RAG context prompt from retrieval results"""
        if not retrieval_result.documents:
            return "No relevant documents found for this query."
        
        context_parts = []
        context_parts.append("Use the following retrieved documents to answer the question.")
        context_parts.append("These documents are selected specifically for the current persona.")
        context_parts.append("")
        context_parts.append("Retrieved Context:")
        
        for i, doc in enumerate(retrieval_result.documents, 1):
            context_parts.append(f"Document {i}:")
            context_parts.append(doc.content)
            context_parts.append(f"[Relevance: {doc.relevance_score:.2f}, Type: {doc.doc_type.value}]")
            context_parts.append("")
        
        context_parts.append("Only use this context to generate the answer.")
        
        return "\n".join(context_parts)


# Example usage and testing
if __name__ == "__main__":
    # Initialize the RAG system
    doc_store = DocumentStore()
    retriever = DocumentRetriever(doc_store)
    
    # Test different personas with the same query
    query = "What are the work policies?"
    personas = ["Executive", "Developer", "HR Specialist", "Student", "General"]
    
    for persona in personas:
        print(f"\n{'='*60}")
        print(f"PERSONA: {persona}")
        print(f"QUERY: {query}")
        print('='*60)
        
        result = retriever.retrieve_documents(query, persona)
        context = retriever.build_rag_context(result)
        
        print(f"Documents found: {result.total_docs_found}")
        for doc in result.documents:
            print(f"- {doc.id} (relevance: {doc.relevance_score:.2f})")
        
        print(f"\nRAG Context:\n{context}")
        print("\n" + "="*60)
