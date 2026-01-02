"""
PersonaRAG - Personalized AI Assistant with Real-Time External Data

A system that adapts responses based on user persona while using only retrieved documents
as knowledge source and real-time external data.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
from dataclasses import dataclass
import json
import logging
from openai_integration import OpenAIIntegration
from role_prompts import RolePromptExtensions, PersonaType


class Persona(Enum):
    """Supported user personas"""
    EXECUTIVE = "Executive"
    DEVELOPER = "Developer"
    HR_SPECIALIST = "HR Specialist"
    STUDENT = "Student"
    GENERAL = "General"


@dataclass
class PersonaConfig:
    """Configuration for each persona including response style guidelines"""
    name: str
    system_prompt: str
    answer_style: List[str]
    tone_guidelines: List[str]
    content_filters: List[str]


class PersonaRAG:
    """Main PersonaRAG system that combines persona adaptation with RAG"""
    
    def __init__(self):
        self.role_extensions = RolePromptExtensions()
        self.current_persona = Persona.GENERAL
        self.last_document_content = ""  # Store last retrieved content for follow-ups
        self.openai_client = OpenAIIntegration()  # Initialize OpenAI integration
        
    def set_persona(self, persona: Persona) -> None:
        """Set current active persona"""
        self.current_persona = persona
        
    def get_current_persona_config(self) -> PersonaConfig:
        """Get configuration for current persona"""
        # Map old Persona enum to new PersonaType
        persona_mapping = {
            Persona.EXECUTIVE: PersonaType.EXECUTIVE,
            Persona.DEVELOPER: PersonaType.DEVELOPER,
            Persona.HR_SPECIALIST: PersonaType.HR_SPECIALIST,
            Persona.STUDENT: PersonaType.STUDENT,
            Persona.GENERAL: PersonaType.GENERAL
        }
        
        current_persona_type = persona_mapping[self.current_persona]
        extension = self.role_extensions.get_role_extension(current_persona_type)
        
        # Extract persona name from the system prompt or use a default
        persona_name = current_persona_type.value
        if "system_prompt" in extension:
            # Try to extract name from the first system prompt line
            first_line = extension["system_prompt"][0] if extension["system_prompt"] else ""
            if "You are PersonaRAG acting as an" in first_line:
                persona_name = first_line.split("as an")[1].strip().split("-level")[0].strip()
        
        return PersonaConfig(
            name=persona_name,
            system_prompt='\n'.join(extension["system_prompt"]),
            answer_style=extension["answer_style"],
            tone_guidelines=extension["tone_guidelines"],
            content_filters=extension["content_filters"]
        )
    
    def build_master_system_prompt(self) -> str:
        """Build the NEW question-aware master system prompt"""
        return """You are PersonaRAG, a personalized knowledge assistant.

Your task is to answer user questions by:
1. Adapting your response to user's active persona (role)
2. Using only the provided retrieved documents as knowledge source
3. Matching tone, depth, and explanation style of the persona
4. Keeping answers clear, accurate, and relevant

CRITICAL: First answer the specific question asked, then adapt tone for the role.

Rules:
- If persona is Executive: be concise, strategic, business-focused, no technical jargon.
- If persona is Developer: be technical, precise, include examples or code if relevant.
- If persona is HR Specialist: be empathetic, compliant, policy-oriented, and clear.
- If persona is Student: explain in simple language with examples.
- If persona is General: give a balanced, easy-to-understand answer.

If answer is not found in retrieved documents, clearly say:
"I don't have enough information from the available knowledge to answer this."

Do NOT hallucinate.
Do NOT use external knowledge."""
    
    def build_role_specific_prompt(self) -> str:
        """Build the NEW question-aware role-specific prompt extension"""
        config = self.get_current_persona_config()
        
        prompt = f"""Current persona: {config.name}

Answer style:"""
        for style in config.answer_style:
            prompt += f"\n- {style}"
            
        return prompt
    
    def build_rag_context_prompt(self, retrieved_documents: List[str]) -> str:
        """Build RAG context prompt with retrieved documents"""
        prompt = "Use the following retrieved documents to answer the question.\n"
        prompt += "These documents are selected specifically for the current persona.\n\n"
        prompt += "Retrieved Context:\n"
        
        for i, doc in enumerate(retrieved_documents, 1):
            prompt += f"Document {i}:\n{doc}\n\n"
            
        prompt += "Only use this context to generate the answer."
        return prompt
    
    def build_complete_prompt(self, user_question: str, retrieved_documents: List[str]) -> str:
        """Build the NEW question-aware complete prompt combining all components"""
        master_prompt = self.build_master_system_prompt()
        role_prompt = self.build_role_specific_prompt()
        rag_prompt = self.build_rag_context_prompt(retrieved_documents)
        
        complete_prompt = f"""{master_prompt}

{role_prompt}

{rag_prompt}

User Question:
{user_question}"""
        
        return complete_prompt
    
    def generate_response(self, user_question: str, retrieved_documents: List[str] = None) -> str:
        """
        Generate response using OpenAI API with persona-specific prompts
        
        Args:
            user_question: The user's specific question
            retrieved_documents: List of retrieved documents (optional, for backward compatibility)
            
        Returns:
            AI-generated answer styled for the selected persona
        """
        try:
            # Use OpenAI to generate persona-specific response
            response = self.openai_client.generate_response(user_question, self.current_persona.value)
            
            # Store response for potential follow-ups
            self.last_document_content = response
            
            return response
            
        except Exception as e:
            logging.error(f"Error generating OpenAI response: {e}")
            
            # Fallback to documents if provided
            if retrieved_documents:
                return self._generate_response_from_documents(user_question, retrieved_documents)
            
            # If no data available, try to use stored context for follow-ups
            if self._is_follow_up_question(user_question.lower()) and self.last_document_content:
                return self._generate_persona_rag_answer(user_question, self.last_document_content)
            
            # Final fallback: provide a persona-appropriate default response
            return self._generate_default_response(user_question)
    
    def _generate_response_from_documents(self, user_question: str, retrieved_documents: List[str]) -> str:
        """Generate response from documents (fallback method)"""
        if not retrieved_documents:
            return "I don't have enough information from the available documents to answer this question."
        
        # Combine all document content
        document_content = ' '.join(retrieved_documents).strip()
        
        if not document_content:
            return "I don't have enough information from the available documents to answer this question."
        
        # Store content for potential follow-ups
        self.last_document_content = document_content
        
        # Generate persona-styled response based on document content
        return self._generate_persona_rag_answer(user_question, document_content)
    
    def _generate_persona_external_answer(self, question: str, content: str, source_data: Dict[str, Any]) -> str:
        """Generate persona-styled answer based on external data"""
        persona = self.current_persona
        question_lower = question.lower()
        
        # Check for follow-up or simplification requests
        if self._is_follow_up_question(question_lower):
            return self._handle_follow_up_question(question, content)
        
        if persona == Persona.EXECUTIVE:
            return self._executive_external_answer(question, content, source_data)
        elif persona == Persona.DEVELOPER:
            return self._developer_external_answer(question, content, source_data)
        elif persona == Persona.HR_SPECIALIST:
            return self._hr_external_answer(question, content, source_data)
        elif persona == Persona.STUDENT:
            return self._student_external_answer(question, content, source_data)
        else:  # GENERAL
            return self._general_external_answer(question, content, source_data)
    
    def _extract_relevant_info(self, question: str, documents: List[str]) -> str:
        """Extract information relevant to the question from documents"""
        # Simple keyword-based extraction for demo
        question_lower = question.lower()
        relevant_parts = []
        
        for doc in documents:
            doc_lower = doc.lower()
            # Check if document contains relevant keywords
            if any(keyword in doc_lower for keyword in ['trend', 'business', 'market', 'technology', 'financial', 'workforce']):
                relevant_parts.append(doc)
        
        return ' '.join(relevant_parts[:3])  # Use top 3 relevant documents
    
    def _generate_persona_rag_answer(self, question: str, document_content: str) -> str:
        """Generate persona-styled answer based strictly on document content"""
        persona = self.current_persona
        question_lower = question.lower()
        
        # Check for follow-up or simplification requests
        if self._is_follow_up_question(question_lower):
            return self._handle_follow_up_question(question, document_content)
        
        if persona == Persona.EXECUTIVE:
            return self._executive_rag_answer(question, document_content)
        elif persona == Persona.DEVELOPER:
            return self._developer_rag_answer(question, document_content)
        elif persona == Persona.HR_SPECIALIST:
            return self._hr_rag_answer(question, document_content)
        elif persona == Persona.STUDENT:
            return self._student_rag_answer(question, document_content)
        else:  # GENERAL
            return self._general_rag_answer(question, document_content)
    
    def _is_follow_up_question(self, question: str) -> bool:
        """Detect if this is a follow-up or clarification question"""
        follow_up_indicators = [
            'explain in simpler terms', 'simpler terms', 'explain simpler',
            'what do you mean', 'clarify', 'elaborate', 'more detail',
            'can you explain', 'explain this', 'what does this mean',
            'tell me more', 'more about', 'expand on', 'break down',
            'example', 'provide an example', 'give me an example', 'for example',
            'more insights', 'strategic insights', 'additional insights', 'further insights'
        ]
        
        return any(indicator in question for indicator in follow_up_indicators)
    
    def _handle_follow_up_question(self, question: str, content: str) -> str:
        """Handle follow-up questions with appropriate responses"""
        persona = self.current_persona
        facts = self._extract_key_facts(content)
        
        if not facts:
            return "I don't have enough information from the available documents to provide clarification."
        
        # Detect specific type of follow-up
        question_lower = question.lower()
        
        if 'example' in question_lower:
            return self._provide_example(facts, persona)
        elif any(term in question_lower for term in ['simpler', 'simple', 'break down']):
            return self._simplify_content(facts, persona)
        elif any(term in question_lower for term in ['explain', 'clarify', 'what does this mean']):
            return self._explain_content(facts, persona)
        else:
            return self._elaborate_content(facts, persona)
    
    def _provide_example(self, facts: str, persona: Persona) -> str:
        """Provide a concrete example based on the facts"""
        if persona == Persona.STUDENT:
            return f"For example: Think about your school implementing AI tutoring systems that help students learn faster - that's AI adoption in education! Many companies now let employees work from home 2-3 days per week - that's the hybrid work model. Organizations are also investing more in cybersecurity to protect student data and online learning platforms."
        elif persona == Persona.GENERAL:
            return f"For instance: A retail company using AI chatbots to improve customer service represents the AI adoption trend. A consulting firm allowing employees to work remotely 3 days per week demonstrates the hybrid work model. A manufacturing company increasing its cybersecurity budget by 25% to protect against digital threats shows the security investment trend."
        elif persona == Persona.EXECUTIVE:
            return f"For example: A Fortune 500 company implementing AI-powered supply chain optimization could reduce operational costs by 20% and improve delivery times by 15%. A technology firm adopting a 3-day office, 2-day remote work model could increase employee retention by 25% while maintaining productivity. A financial services firm diversifying suppliers across North America, Europe, and Asia could reduce supply chain disruption risks by 40%."
        elif persona == Persona.DEVELOPER:
            return f"For example: Implementing AI-powered code completion tools like GitHub Copilot can increase development velocity by 40% and reduce bug rates by 15%. Setting up containerized development environments with Docker and Kubernetes supports hybrid work models. Using multi-cloud infrastructure with automated failover can improve system availability to 99.9% and support distributed development teams."
        elif persona == Persona.HR_SPECIALIST:
            return f"For example: An HR department implementing AI-powered candidate matching could reduce time-to-hire by 45% and improve quality of hire by 30%. Creating a comprehensive hybrid work policy with clear guidelines could improve employee satisfaction scores by 20% and reduce turnover by 15%. Launching a cybersecurity awareness training program could reduce security incidents by 60% through improved employee vigilance."
        else:
            return f"For example: The trends show organizations investing in AI technology for competitive advantage, implementing flexible work arrangements for talent attraction and retention, diversifying supply chains for risk mitigation, adopting sustainability reporting for regulatory compliance, and increasing cybersecurity budgets for digital protection."
    
    def _simplify_content(self, facts: str, persona: Persona) -> str:
        """Simplify content based on persona"""
        if persona == Persona.STUDENT:
            return self._simplify_for_student(facts)
        elif persona == Persona.GENERAL:
            return self._simplify_for_general(facts)
        elif persona == Persona.EXECUTIVE:
            return self._simplify_for_executive(facts)
        elif persona == Persona.DEVELOPER:
            return self._simplify_for_developer(facts)
        elif persona == Persona.HR_SPECIALIST:
            return self._simplify_for_hr(facts)
        else:
            return self._simplify_for_general(facts)
    
    def _explain_content(self, facts: str, persona: Persona) -> str:
        """Provide explanation based on persona"""
        if persona == Persona.STUDENT:
            return f"To help you understand: {facts}. This means companies are changing how they work using technology and new policies."
        elif persona == Persona.GENERAL:
            return f"To explain: {facts}. These trends show how businesses are evolving in response to technology and market changes."
        elif persona == Persona.EXECUTIVE:
            return f"To clarify: {facts}. These trends indicate strategic priorities for operational excellence and competitive positioning."
        elif persona == Persona.DEVELOPER:
            return f"To explain: {facts}. This impacts our technical architecture and development methodologies."
        elif persona == Persona.HR_SPECIALIST:
            return f"To clarify: {facts}. This affects our workplace policies and employee development strategies."
        else:
            return f"To explain: {facts}. These trends reflect broader shifts in the business landscape."
    
    def _elaborate_content(self, facts: str, persona: Persona) -> str:
        """Provide elaboration based on persona with additional insights"""
        if persona == Persona.STUDENT:
            return f"To expand on this: {facts}. From a learning perspective, these trends indicate that future careers will require strong digital literacy, adaptability to new work models, and understanding of sustainable business practices. Students should focus on developing skills in AI tools, remote collaboration, and data analysis to stay competitive."
        elif persona == Persona.GENERAL:
            return f"To elaborate: {facts}. These developments are reshaping how organizations operate and create new opportunities and challenges. The convergence of AI adoption, hybrid work, and sustainability requirements represents a fundamental shift in business operations that affects consumers, employees, and stakeholders across all sectors."
        elif persona == Persona.EXECUTIVE:
            return f"To elaborate further: {facts}. Beyond the immediate trends, executives should consider the competitive implications of early AI adoption versus lagging competitors. The hybrid work model presents opportunities for talent acquisition beyond geographic boundaries, while sustainability reporting opens new avenues for ESG-focused investment and brand differentiation."
        elif persona == Persona.DEVELOPER:
            return f"To elaborate: {facts}. From a technical standpoint, these trends drive requirements for scalable AI infrastructure, secure remote access systems, automated compliance reporting tools, and advanced cybersecurity frameworks. Development teams must prioritize cloud-native architectures, API-first design, and robust security protocols to support these business initiatives."
        elif persona == Persona.HR_SPECIALIST:
            return f"To elaborate: {facts}. These trends require comprehensive updates to talent management strategies, including reskilling programs for AI adoption, new performance metrics for hybrid work, enhanced data privacy policies, and expanded benefits packages that address the changing nature of work and employee expectations."
        else:
            return f"To elaborate: {facts}. These changes impact various aspects of business operations and strategy, requiring coordinated responses across technology, human resources, finance, and operations departments to successfully navigate the evolving business landscape."
    
    def _simplify_for_student(self, facts: str) -> str:
        """Simplify content for student persona"""
        # Break down complex concepts into simple terms
        simplified = facts.replace('accelerating across enterprises', 'is growing really fast in companies')
        simplified = simplified.replace('increasing investment', 'companies are spending more money')
        simplified = simplified.replace('hybrid models becoming standard', 'mix of office and home work is normal now')
        simplified = simplified.replace('diversification priority', 'companies are getting supplies from different places')
        simplified = simplified.replace('mandatory for public companies', 'required for big public companies')
        simplified = simplified.replace('budgets increasing by 25% YoY', 'spending 25% more than last year')
        
        return f"Let me break this down for you: {simplified}. Think of it like how technology is changing how companies work!"
    
    def _simplify_for_general(self, facts: str) -> str:
        """Simplify content for general persona"""
        return f"To put it simply: {facts}. This means businesses are adapting to new technologies and ways of working."
    
    def _simplify_for_executive(self, facts: str) -> str:
        """Simplify content for executive persona"""
        return f"In summary: {facts}. The key takeaway is that we need to focus on AI adoption, operational flexibility, and risk management."
    
    def _simplify_for_developer(self, facts: str) -> str:
        """Simplify content for developer persona"""
        return f"Technically speaking: {facts}. This impacts our development priorities and technology choices."
    
    def _simplify_for_hr(self, facts: str) -> str:
        """Simplify content for HR persona"""
        return f"From a people perspective: {facts}. This affects our workplace policies and employee development strategies."
    
    def _executive_external_answer(self, question: str, content: str, source_data: Dict[str, Any]) -> str:
        """Executive-style answer based on external data"""
        return f"Strategic insights: {content}. From a leadership perspective, this information is crucial for strategic decision-making and competitive positioning. Key focus areas include resource allocation, risk management, and operational excellence."
    
    def _developer_external_answer(self, question: str, content: str, source_data: Dict[str, Any]) -> str:
        """Developer-style answer based on external data"""
        return f"Technical analysis: {content}. From an engineering perspective, this impacts our architecture decisions, development methodologies, and technology stack. Consider the technical implications for system design and implementation."
    
    def _hr_external_answer(self, question: str, content: str, source_data: Dict[str, Any]) -> str:
        """HR-style answer based on external data"""
        return f"HR perspective: {content}. From a people and culture standpoint, this impacts our talent management strategies, employee engagement initiatives, and workplace policies. Consider the implications for team dynamics and organizational development."
    
    def _student_external_answer(self, question: str, content: str, source_data: Dict[str, Any]) -> str:
        """Student-style answer based on external data"""
        return f"Learning perspective: {content}. This is important knowledge for your education and future career development. Think about how this information connects to what you're studying and how it might apply in real-world situations."
    
    def _general_external_answer(self, question: str, content: str, source_data: Dict[str, Any]) -> str:
        """General-style answer based on external data"""
        return f"General overview: {content}. This information provides a comprehensive understanding of the topic from multiple perspectives, considering both technical and human factors in the current environment."
    
    def _extract_key_facts(self, content: str) -> str:
        """Extract key facts from document content"""
        # Remove duplicates and clean content
        sentences = content.split('.')
        unique_facts = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Filter out very short fragments
                if sentence not in unique_facts:
                    unique_facts.append(sentence)
        
        # Return first 3-5 key facts to avoid repetition
        key_facts = unique_facts[:5]
        return '. '.join(key_facts).strip()
    
    def _generate_default_response(self, user_question: str) -> str:
        """Generate a default persona-appropriate response when no external data is available"""
        persona_config = self.get_current_persona_config()
        
        # Default responses based on persona
        default_responses = {
            Persona.EXECUTIVE: f"From a strategic perspective, I'd need to analyze current market data and internal metrics to provide a comprehensive answer to '{user_question}'. Let me gather the relevant business intelligence and get back to you with actionable insights.",
            
            Persona.DEVELOPER: f"To properly address '{user_question}', I'd need to review the current codebase and technical documentation. Let me examine the relevant systems and provide you with a technical solution.",
            
            Persona.HR_SPECIALIST: f"Regarding '{user_question}', I'd need to consult current HR policies, employee feedback, and industry best practices. Let me gather the necessary information to provide you with appropriate guidance.",
            
            Persona.STUDENT: f"That's an interesting question about '{user_question}'! I'd need to do some research and review relevant study materials to give you a comprehensive answer. Let me look into that for you.",
            
            Persona.GENERAL: f"To help you with '{user_question}', I'd need to gather more information from reliable sources. Let me research this topic and provide you with a helpful response."
        }
        
        return default_responses.get(self.current_persona, default_responses[Persona.GENERAL])
    
    def get_persona_summary(self) -> Dict[str, Any]:
        """Get a summary of current persona configuration"""
        config = self.get_current_persona_config()
        return {
            "persona": config.name,
            "system_prompt": config.system_prompt,
            "answer_style": config.answer_style,
            "tone_guidelines": config.tone_guidelines,
            "content_filters": config.content_filters
        }


# Example usage and testing
if __name__ == "__main__":
    # Initialize PersonaRAG
    pr = PersonaRAG()
    
    # Example: Executive persona
    pr.set_persona(Persona.EXECUTIVE)
    question = "What is the remote work policy?"
    documents = [
        "Employees may work remotely up to 3 days per week with manager approval. "
        "This policy supports work-life balance while maintaining team collaboration."
    ]
    
    executive_prompt = pr.generate_response(question, documents)
    print("=== EXECUTIVE PERSONA PROMPT ===")
    print(executive_prompt)
    print("\n" + "="*50 + "\n")
    
    # Example: Developer persona
    pr.set_persona(Persona.DEVELOPER)
    question = "How does the authentication system work?"
    documents = [
        "The system uses JWT tokens for authentication. Tokens are generated server-side "
        "using a secret key and contain user claims. The token is sent in the Authorization header "
        "as 'Bearer <token>'. Tokens expire after 24 hours and must be refreshed."
    ]
    
    developer_prompt = pr.generate_response(question, documents)
    print("=== DEVELOPER PERSONA PROMPT ===")
    print(developer_prompt)
