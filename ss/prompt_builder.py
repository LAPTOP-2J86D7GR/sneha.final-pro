"""
Complete Prompt Structure Builder for PersonaRAG

Combines master system prompt, role-specific extensions, RAG context,
and user questions into the final prompt structure.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from personarag import PersonaRAG, Persona
from role_prompts import RolePromptExtensions, PersonaType
from rag_system import DocumentRetriever, DocumentStore, RetrievalResult


@dataclass
class PromptComponents:
    """Components that make up the complete prompt"""
    master_system_prompt: str
    role_specific_prompt: str
    rag_context: str
    user_question: str
    metadata: Dict[str, Any]


class CompletePromptBuilder:
    """Builds the complete prompt structure combining all PersonaRAG components"""
    
    def __init__(self):
        self.personarag = PersonaRAG()
        self.role_extensions = RolePromptExtensions()
        self.doc_store = DocumentStore()
        self.retriever = DocumentRetriever(self.doc_store)
        
        # Map Persona enum to PersonaType for compatibility
        self.persona_mapping = {
            Persona.EXECUTIVE: PersonaType.EXECUTIVE,
            Persona.DEVELOPER: PersonaType.DEVELOPER,
            Persona.HR_SPECIALIST: PersonaType.HR_SPECIALIST,
            Persona.STUDENT: PersonaType.STUDENT,
            Persona.GENERAL: PersonaType.GENERAL
        }
    
    def build_master_system_prompt(self) -> str:
        """Build the master system prompt (core of the project)"""
        return """You are PersonaRAG, a personalized knowledge assistant.

Your task is to answer user questions by:
1. Adapting your response to the user's active persona (role)
2. Using only the provided retrieved documents as the knowledge source
3. Matching the tone, depth, and explanation style of the persona
4. Keeping answers clear, accurate, and relevant

Rules:
- If persona is Executive: be concise, strategic, business-focused, no technical jargon.
- If persona is Developer: be technical, precise, include examples or code if relevant.
- If persona is HR Specialist: be empathetic, compliant, policy-oriented, and clear.
- If persona is Student: explain in simple language with examples.
- If persona is General: give a balanced, easy-to-understand answer.

If the answer is not found in the retrieved documents, clearly say:
"I don't have enough information from the available knowledge to answer this."

Do NOT hallucinate.
Do NOT use external knowledge."""
    
    def build_role_specific_prompt(self, persona: Persona) -> str:
        """Build the role-specific prompt extension for the given persona"""
        persona_type = self.persona_mapping[persona]
        return self.role_extensions.build_dynamic_prompt(persona_type)
    
    def build_rag_context_prompt(self, user_question: str, persona: Persona) -> tuple[str, RetrievalResult]:
        """Build the RAG context prompt with retrieved documents"""
        # Retrieve documents based on question and persona
        retrieval_result = self.retriever.retrieve_documents(
            query=user_question,
            persona=persona.value,
            top_k=10
        )
        
        # Build RAG context
        rag_context = self.retriever.build_rag_context(retrieval_result)
        
        return rag_context, retrieval_result
    
    def build_complete_prompt(self, user_question: str, persona: Persona) -> PromptComponents:
        """Build the complete prompt combining all components"""
        
        # Set persona in PersonaRAG system
        self.personarag.set_persona(persona)
        
        # Build individual components
        master_prompt = self.build_master_system_prompt()
        role_prompt = self.build_role_specific_prompt(persona)
        rag_context, retrieval_result = self.build_rag_context_prompt(user_question, persona)
        
        # Combine into final prompt structure
        final_prompt = f"""{master_prompt}

{role_prompt}

{rag_context}

User Question:
{user_question}"""
        
        # Create metadata
        metadata = {
            "persona": persona.value,
            "question": user_question,
            "documents_retrieved": retrieval_result.total_docs_found,
            "retrieval_method": retrieval_result.retrieval_method,
            "prompt_length": len(final_prompt),
            "retrieved_doc_ids": [doc.id for doc in retrieval_result.documents]
        }
        
        return PromptComponents(
            master_system_prompt=master_prompt,
            role_specific_prompt=role_prompt,
            rag_context=rag_context,
            user_question=user_question,
            metadata=metadata
        )
    
    def get_final_prompt_string(self, components: PromptComponents) -> str:
        """Get the final prompt string from components"""
        return f"""{components.master_system_prompt}

{components.role_specific_prompt}

{components.rag_context}

User Question:
{components.user_question}"""
    
    def analyze_prompt_structure(self, components: PromptComponents) -> Dict[str, Any]:
        """Analyze the structure and characteristics of the built prompt"""
        final_prompt = self.get_final_prompt_string(components)
        
        analysis = {
            "total_characters": len(final_prompt),
            "total_words": len(final_prompt.split()),
            "line_count": len(final_prompt.split('\n')),
            "components": {
                "master_prompt_length": len(components.master_system_prompt),
                "role_prompt_length": len(components.role_specific_prompt),
                "rag_context_length": len(components.rag_context),
                "question_length": len(components.user_question)
            },
            "metadata": components.metadata
        }
        
        return analysis
    
    def demonstrate_prompt_building(self, question: str, persona: Persona) -> Dict[str, Any]:
        """Demonstrate the complete prompt building process"""
        print(f"\n{'='*80}")
        print(f"PERSONARAG PROMPT BUILDING DEMONSTRATION")
        print(f"Persona: {persona.value}")
        print(f"Question: {question}")
        print('='*80)
        
        # Build complete prompt
        components = self.build_complete_prompt(question, persona)
        
        # Display each component
        print(f"\n📋 MASTER SYSTEM PROMPT:")
        print("-" * 40)
        print(components.master_system_prompt)
        
        print(f"\n🎭 ROLE-SPECIFIC PROMPT ({persona.value}):")
        print("-" * 40)
        print(components.role_specific_prompt)
        
        print(f"\n📚 RAG CONTEXT:")
        print("-" * 40)
        print(components.rag_context)
        
        print(f"\n❓ USER QUESTION:")
        print("-" * 40)
        print(components.user_question)
        
        print(f"\n🔗 FINAL COMPLETE PROMPT:")
        print("-" * 40)
        final_prompt = self.get_final_prompt_string(components)
        print(final_prompt)
        
        # Analysis
        analysis = self.analyze_prompt_structure(components)
        print(f"\n📊 PROMPT ANALYSIS:")
        print("-" * 40)
        for key, value in analysis.items():
            if key != "components":
                print(f"{key}: {value}")
        
        print(f"\n📋 COMPONENT BREAKDOWN:")
        print("-" * 40)
        for comp_name, length in analysis["components"].items():
            print(f"{comp_name}: {length} characters")
        
        return {
            "components": components,
            "analysis": analysis,
            "final_prompt": final_prompt
        }


# Example usage and comprehensive testing
if __name__ == "__main__":
    builder = CompletePromptBuilder()
    
    # Test scenarios
    test_scenarios = [
        {
            "question": "What is the remote work policy?",
            "persona": Persona.EXECUTIVE
        },
        {
            "question": "How does the authentication system work?",
            "persona": Persona.DEVELOPER
        },
        {
            "question": "What are the employee onboarding procedures?",
            "persona": Persona.HR_SPECIALIST
        },
        {
            "question": "How do I learn to use the company systems?",
            "persona": Persona.STUDENT
        },
        {
            "question": "What is the company culture like?",
            "persona": Persona.GENERAL
        }
    ]
    
    # Run demonstrations
    results = []
    for scenario in test_scenarios:
        result = builder.demonstrate_prompt_building(
            scenario["question"], 
            scenario["persona"]
        )
        results.append(result)
        
        print(f"\n{'='*80}")
        print("SCENARIO COMPLETE")
        print('='*80)
    
    # Summary comparison
    print(f"\n{'='*80}")
    print("SUMMARY COMPARISON ACROSS PERSONAS")
    print('='*80)
    
    for i, result in enumerate(results):
        persona = test_scenarios[i]["persona"]
        question = test_scenarios[i]["question"]
        analysis = result["analysis"]
        
        print(f"\n{persona.value}:")
        print(f"  Question: {question}")
        print(f"  Prompt Length: {analysis['total_characters']} chars")
        print(f"  Documents Retrieved: {analysis['metadata']['documents_retrieved']}")
        print(f"  Word Count: {analysis['total_words']}")
