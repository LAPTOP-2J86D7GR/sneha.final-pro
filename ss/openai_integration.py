"""
OpenAI Integration for PersonaRAG
Handles OpenAI API calls with persona-specific prompts
"""

import os
import openai
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

class OpenAIIntegration:
    """Handles OpenAI API integration with persona-specific responses"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.use_local_ai = os.getenv('USE_LOCAL_AI', 'false').lower() == 'true'
        self.local_model = os.getenv('LOCAL_MODEL', 'llama3.2')
        
        if not self.api_key or self.api_key == 'sk-your-actual-api-key-here':
            logging.warning("Valid OpenAI API key not found in environment variables")
            openai.api_key = None
        else:
            # Set OpenAI API key
            openai.api_key = self.api_key
        
        # Persona-specific system prompts
        self.persona_prompts = {
            "Executive": """You are an AI assistant specializing in executive leadership and business strategy. 
            Provide professional, insightful responses about business management, strategic planning, organizational leadership, and executive decision-making.
            
            Your responses should be:
            - Professional and authoritative
            - Strategic and forward-thinking
            - Data-driven and analytical
            - Concise but comprehensive
            - Focus on business impact and ROI
            
            Provide expert-level business insights and strategic guidance.""",
            
            "Developer": """You are an AI assistant specializing in software development and technology.
            Provide technical expertise, programming guidance, and development best practices.
            
            Your responses should be:
            - Technical and precise
            - Include code examples when relevant
            - Focus on best practices and architecture
            - Problem-solving oriented
            - Up-to-date with current technologies
            
            Provide expert technical solutions and implementation guidance.""",
            
            "HR Specialist": """You are an AI assistant specializing in human resources and organizational development.
            Provide professional guidance on HR practices, employee relations, and workplace management.
            
            Your responses should be:
            - Professional and knowledgeable
            - Focus on HR best practices and compliance
            - Solution-oriented for workplace issues
            - Data-driven and strategic
            
            Provide expert HR guidance and organizational insights.""",
            
            "Student": """You are an AI assistant specializing in education and learning support.
            Provide educational guidance, study strategies, and academic support.
            
            Your responses should be:
            - Educational and informative
            - Clear and well-structured
            - Supportive and encouraging
            - Focused on learning outcomes
            
            Provide expert educational guidance and learning strategies.""",
            
            "General": """You are a helpful AI assistant similar to ChatGPT.
            Provide accurate, informative responses across a wide range of topics.
            
            Your responses should be:
            - Clear and informative
            - Balanced and objective
            - Well-structured and comprehensive
            - Helpful and supportive
            
            Provide accurate information and helpful guidance on any topic."""
        }
    
    def generate_response(self, message: str, persona: str) -> str:
        """
        Generate a response using OpenAI API with persona-specific prompts
        
        Args:
            message: User's question or message
            persona: Selected persona (Executive, Developer, HR Specialist, Student, General)
            
        Returns:
            Generated response as string
        """
        # Try local AI first if enabled
        if self.use_local_ai:
            try:
                local_response = self._generate_local_ai_response(message, persona)
                if local_response:
                    return local_response
            except Exception as e:
                logging.warning(f"Local AI failed: {e}")
        
        # Check if OpenAI API key is configured
        if not openai.api_key:
            return "OpenAI API key not configured. Please add your API key to the .env file to get AI responses."
        
        try:
            # Get the system prompt for the selected persona
            system_prompt = self.persona_prompts.get(persona, self.persona_prompts["General"])
            
            # Create the conversation
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            # Make API call to OpenAI using older syntax
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=1000,
                temperature=0.7,
            )
            
            # Extract and return the response
            generated_text = response.choices[0].message.content.strip()
            return generated_text
            
        except Exception as e:
            logging.error(f"Error generating OpenAI response: {e}")
            
            # Check if it's a quota/billing error
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ["quota", "billing", "insufficient_quota", "rate_limit", "exceeded"]):
                return self._get_dynamic_fallback_response(message, persona)
            
            # Check if it's an authentication error
            elif any(keyword in error_str for keyword in ["unauthorized", "invalid_api_key", "authentication"]):
                return "OpenAI API key is invalid or expired. Please check your API key in the .env file."
            
            # Check if it's a network/connection error
            elif any(keyword in error_str for keyword in ["connection", "network", "timeout", "unreachable"]):
                return self._get_dynamic_fallback_response(message, persona)
            
            # For other errors, try fallback
            else:
                return self._get_dynamic_fallback_response(message, persona)
    
    def _generate_local_ai_response(self, message: str, persona: str) -> str:
        """Generate response using local AI model (Ollama)"""
        try:
            import requests
            import json
            
            # Get the system prompt for the selected persona
            system_prompt = self.persona_prompts.get(persona, self.persona_prompts["General"])
            
            # Prepare the request for Ollama
            ollama_url = "http://localhost:11434/api/generate"
            payload = {
                "model": self.local_model,
                "prompt": f"System: {system_prompt}\n\nUser: {message}\n\nAssistant:",
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 1000
                }
            }
            
            # Make request to Ollama
            response = requests.post(ollama_url, json=payload, timeout=30)
            response.raise_for_status()
            
            # Extract and return the response
            result = response.json()
            return result.get("response", "").strip()
            
        except ImportError:
            logging.error("Requests library not available for local AI")
            return None
        except requests.exceptions.ConnectionError:
            logging.warning("Ollama not running. Install Ollama for free local AI: https://ollama.ai")
            return None
        except Exception as e:
            logging.error(f"Local AI generation failed: {e}")
            return None
    
    def _get_dynamic_fallback_response(self, message: str, persona: str) -> str:
        """Provide professional fallback responses when OpenAI is unavailable"""
        import re
        import hashlib
        
        # Enhanced keyword detection with more comprehensive patterns
        message_lower = message.lower()
        
        # Create a unique response based on the message content
        message_hash = hashlib.md5(message.encode()).hexdigest()[:8]
        
        # Store conversation context for better follow-ups
        if not hasattr(self, '_conversation_context'):
            self._conversation_context = []
        self._conversation_context.append(message)
        
        # Keep only last 3 messages for context
        if len(self._conversation_context) > 3:
            self._conversation_context = self._conversation_context[-3:]
        
        # Executive responses - professional and ChatGPT-like
        if persona == "Executive":
            if any(word in message_lower for word in [
                "role", "explain the role", "what is your role", "what do you do", "your role", "executive role"
            ]):
                return f"The executive role encompasses strategic leadership, organizational vision, and decision-making authority. Executives set company direction, manage stakeholder relationships, drive business growth, ensure operational excellence, and maintain accountability to boards and shareholders. Key responsibilities include strategic planning, resource allocation, talent development, risk management, and representing the organization to external stakeholders."
            
            elif any(word in message_lower for word in [
                "decision making", "decision-making", "decision processes", "how to make decisions", "making decisions"
            ]):
                return f"Executive decision-making processes should be structured, data-driven, and timely. Key steps include: 1) Define the problem clearly, 2) Gather relevant data and stakeholder input, 3) Analyze alternatives and risks, 4) Consult with key stakeholders, 5) Make the decision with clear rationale, 6) Communicate the decision effectively, and 7) Monitor outcomes and adjust as needed. Successful executives balance analytical rigor with decisive action."
            
            elif any(word in message_lower for word in [
                "professional development", "development strategies", "career development", "skill development", "training programs"
            ]):
                return f"Executive professional development strategies include: 1) Leadership training and executive education programs, 2) Mentorship relationships with senior leaders, 3) Cross-functional assignments for broader experience, 4) Industry conferences and networking events, 5) Reading business literature and case studies, 6) Executive coaching, 7) Board participation or advisory roles, and 8) Continuous learning in emerging technologies and business trends. Focus on strategic thinking, change management, and people leadership skills."
            
            elif any(word in message_lower for word in [
                "challenges", "biggest challenges", "challenges facing", "industry challenges", "main challenges", "problems", "issues"
            ]):
                return f"The primary challenges facing modern businesses include talent retention in competitive markets, rapid technological adaptation, supply chain disruptions, regulatory compliance complexity, and maintaining profitability amid economic uncertainty. Strategic approaches include proactive workforce planning, diversified supplier relationships, technology investment, and agile adaptation to market changes."
            
            elif any(word in message_lower for word in [
                "trends", "business trends", "key business", "market trends", "quarter trends", "strategic trends", "trends for next quarter", "future trends"
            ]):
                return f"Key business trends for the upcoming quarter include digital transformation acceleration, remote work optimization, supply chain resilience, customer experience enhancement, and data-driven decision making. Organizations should focus on AI integration, sustainability initiatives, and agile strategic planning to maintain competitive advantage."
            
            elif any(word in message_lower for word in [
                "productivity", "collaboration", "team productivity", "improve team", "team collaboration", "efficiency", "performance"
            ]):
                return f"To enhance team productivity and collaboration, implement clear communication protocols, leverage project management tools, establish regular performance reviews, foster accountability culture, and invest in team development. Cross-functional collaboration and streamlined workflows are essential for optimal organizational performance."
            
            elif any(word in message_lower for word in [
                "stakeholder", "manage stakeholder", "stakeholder relationships", "stakeholder management"
            ]):
                return f"Effective stakeholder management involves building strategic partnerships across all stakeholder groups including employees, customers, investors, and community partners. Key strategies include transparent communication, needs assessment, win-win opportunity identification, and maintaining trust through consistent engagement and delivery of value."
            
            elif any(word in message_lower for word in [
                "operational efficiency", "efficiency", "operations", "improve operations"
            ]):
                return f"Operational efficiency optimization requires process improvement, technology integration, and team empowerment. Focus on workflow analysis, automation opportunities, performance metrics, and continuous improvement methodologies. Strategic operational enhancements drive cost reduction and quality improvement while maintaining service standards."
            
            elif any(word in message_lower for word in ["direction", "set company direction", "company direction"]):
                return f"Executives set company direction through several key mechanisms: 1) **Vision Definition** - Establish long-term organizational vision and mission statements that guide all decisions, 2) **Strategic Planning** - Develop comprehensive 3-5 year strategic plans with clear objectives and key results, 3) **Resource Allocation** - Direct capital, talent, and resources toward strategic priorities, 4) **Culture Setting** - Model and reinforce organizational values and expected behaviors, 5) **Stakeholder Communication** - Consistently communicate direction to employees, investors, and partners, 6) **Performance Metrics** - Establish KPIs that measure progress toward strategic goals, and 7) **Adaptive Leadership** - Adjust direction based on market changes and performance data. This directional leadership ensures organizational alignment and focused execution."
            
            else:
                # Generate a more specific response based on the actual question and context
                if any(word in message_lower for word in ["elaborate", "more detail", "explain more", "tell me more", "expand"]):
                    # Check previous context to elaborate on the last topic
                    if self._conversation_context and len(self._conversation_context) >= 2:
                        previous_topic = self._conversation_context[-2].lower()
                        if "direction" in previous_topic:
                            return f"Regarding executive direction setting, the process involves: **Strategic Alignment** - Ensuring all departments understand and work toward common goals, **Market Analysis** - Continuously scanning competitive landscape and market opportunities, **Resource Optimization** - Deploying people and capital where they create most value, **Risk Management** - Identifying and mitigating strategic risks, **Innovation Leadership** - Championing new initiatives and technologies, and **Performance Accountability** - Holding teams responsible for results while removing obstacles. This comprehensive approach creates organizational clarity and momentum."
                        elif "role" in previous_topic:
                            return f"Expanding on the executive role, key dimensions include: **Strategic Leadership** - Setting long-term vision and strategy, **Operational Oversight** - Ensuring efficient day-to-day operations, **Financial Stewardship** - Managing resources and financial performance, **People Leadership** - Building and developing high-performing teams, **External Representation** - Serving as face of the organization, **Change Management** - Leading organizational transformations, and **Governance** - Ensuring compliance and ethical conduct. Each dimension requires different skills but must work cohesively."
                    
                    return f"I'd be happy to elaborate on that topic. Could you specify which aspect you'd like more detail about? For executive leadership, I can provide deeper insights into strategic planning, decision-making processes, team building, stakeholder management, or operational excellence. What specific area interests you most?"
                
                elif "what" in message_lower and "how" in message_lower:
                    return f"As an executive leadership AI assistant, I can provide detailed guidance on various business topics. Based on your question about '{message}', I recommend analyzing the specific context, considering your organization's goals and current challenges. For more targeted advice, please provide additional details about your specific situation or business context."
                else:
                    return f"As an executive leadership AI assistant, I provide strategic guidance on business growth, organizational development, market positioning, and operational excellence. I can help with strategic planning, stakeholder management, performance optimization, and leadership challenges. Regarding '{message}', I recommend a systematic approach that aligns with your organizational objectives. What specific aspect would you like me to elaborate on?"
        
        # Developer responses - professional and ChatGPT-like
        elif persona == "Developer":
            if any(word in message_lower for word in [
                "role", "explain the role", "what is your role", "what do you do", "your role", "developer role"
            ]):
                return f"As an AI assistant specializing in software development, my role is to provide technical expertise, programming guidance, and development best practices. I assist with system design, code implementation, debugging, architecture decisions, and technology selection. I can help with various programming languages, frameworks, and development methodologies."
            
            elif any(word in message_lower for word in [
                "challenges", "biggest challenges", "challenges facing", "industry challenges", "main challenges", "problems", "issues"
            ]):
                return f"The primary challenges in software development include rapid technology evolution, managing technical debt, ensuring cybersecurity, scaling systems effectively, and balancing feature development with code quality. Strategic approaches include continuous learning, refactoring practices, security-first development, and scalable architecture design."
            
            elif any(word in message_lower for word in [
                "learning", "how to learn", "learn programming", "learn to code", "getting started"
            ]):
                return f"For programming education, start with a foundational language like Python or JavaScript, build progressively complex projects, practice regularly with coding challenges, utilize online learning platforms, join developer communities, and work on real-world applications. Focus on understanding core concepts before advancing to specialized technologies."
            
            elif any(word in message_lower for word in [
                "productivity", "collaboration", "team productivity", "improve team", "team collaboration", "efficiency", "performance"
            ]):
                return f"Development productivity optimization involves implementing agile methodologies, utilizing effective development tools, maintaining clean code practices, automating testing and deployment, conducting thorough code reviews, and leveraging version control systems. Integrated development environments and continuous integration pipelines significantly enhance team productivity."
            
            else:
                return f"As a software development AI assistant, I provide technical guidance on programming languages, frameworks, architecture patterns, debugging, and development best practices. I can help with code implementation, system design, technology selection, and solving complex technical challenges. What specific development question can I assist you with?"
        
        # HR Specialist responses - professional and ChatGPT-like
        elif persona == "HR Specialist":
            if any(word in message_lower for word in [
                "role", "explain the role", "what is your role", "what do you do", "your role", "hr role"
            ]):
                return f"As an AI assistant specializing in human resources, my role is to provide professional guidance on HR practices, employee relations, organizational development, and workplace management. I assist with talent acquisition, performance management, compliance, employee engagement, and strategic HR planning."
            
            elif any(word in message_lower for word in [
                "challenges", "biggest challenges", "challenges facing", "industry challenges", "main challenges", "problems", "issues"
            ]):
                return f"Key HR challenges include talent acquisition in competitive markets, employee retention and engagement, adapting to hybrid work models, maintaining company culture, and ensuring regulatory compliance. Strategic solutions involve comprehensive workforce planning, wellness programs, flexible work policies, and data-driven HR analytics."
            
            elif any(word in message_lower for word in [
                "productivity", "collaboration", "team productivity", "improve team", "team collaboration", "efficiency", "performance"
            ]):
                return f"Team productivity enhancement requires clear communication channels, regular performance feedback, collaborative tools implementation, recognition programs, and professional development opportunities. Focus on creating an inclusive environment that values diverse perspectives and supports continuous improvement."
            
            else:
                return f"As an HR AI assistant, I provide expert guidance on talent management, employee relations, organizational development, compliance, performance management, and workplace culture. I can help with HR strategy, policy development, employee engagement, and creating productive work environments. What specific HR challenge would you like to address?"
        
        # Student responses - professional and ChatGPT-like
        elif persona == "Student":
            if any(word in message_lower for word in [
                "role", "explain the role", "what is your role", "what do you do", "your role", "student role"
            ]):
                return f"As an AI assistant specializing in education, my role is to provide academic guidance, study strategies, learning support, and educational resources. I assist with subject matter understanding, study techniques, exam preparation, career planning, and skill development for educational success."
            
            elif any(word in message_lower for word in [
                "challenges", "biggest challenges", "challenges facing", "industry challenges", "main challenges", "problems", "issues"
            ]):
                return f"Common student challenges include time management, information overload, maintaining motivation, balancing academic and personal life, and preparing for evolving job markets. Effective strategies include structured study schedules, active learning techniques, stress management, and seeking academic support when needed."
            
            elif any(word in message_lower for word in [
                "study", "studying", "how to study", "study tips", "learning", "exam preparation"
            ]):
                return f"Effective study techniques include active learning methods like summarization and teaching concepts to others, spaced repetition for memory retention, practice testing, mind mapping for complex topics, and maintaining consistent study schedules. Combine different learning modalities for optimal comprehension and retention."
            
            else:
                return f"As an educational AI assistant, I provide comprehensive support for academic success including study strategies, subject matter expertise, exam preparation, research guidance, and career planning. I can help with learning techniques, time management, and educational resource recommendations. What educational challenge can I help you overcome?"
        
        # General responses - professional and ChatGPT-like
        else:  # General persona
            if any(word in message_lower for word in [
                "role", "explain the role", "what is your role", "what do you do", "your role"
            ]):
                return f"As a helpful AI assistant similar to ChatGPT, my role is to provide accurate, informative responses across a wide range of topics. I assist with research, problem-solving, explanation of complex concepts, and providing guidance on various subjects while maintaining objectivity and reliability."
            
            elif any(word in message_lower for word in [
                "challenges", "biggest challenges", "challenges facing", "industry challenges", "main challenges", "problems", "issues"
            ]):
                return f"Major global challenges include technological disruption adaptation, sustainability concerns, economic uncertainty, digital transformation, and balancing innovation with ethical considerations. Addressing these challenges requires collaborative approaches, strategic planning, and continuous learning across all sectors."
            
            else:
                return f"As a comprehensive AI assistant, I provide accurate information and helpful guidance on a wide range of topics including technology, science, business, education, and general knowledge. I aim to deliver clear, well-structured responses that address your specific questions and needs. How can I assist you today?"
    
    def test_connection(self) -> bool:
        """Test if OpenAI API connection is working"""
        if not openai.api_key:
            return False
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return True
        except Exception as e:
            logging.error(f"OpenAI connection test failed: {e}")
            return False
    
    def get_api_status(self) -> str:
        """Get detailed OpenAI API status"""
        if not openai.api_key:
            return "❌ No API Key: OpenAI API key not configured"
        
        try:
            # Test with a minimal request
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return "✅ API Working: OpenAI API is connected and responding"
        except Exception as e:
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ["quota", "billing", "insufficient_quota"]):
                return "⚠️ Quota Exceeded: OpenAI API quota exceeded - add credits to your account"
            elif any(keyword in error_str for keyword in ["unauthorized", "invalid_api_key"]):
                return "❌ Invalid Key: OpenAI API key is invalid or expired"
            elif any(keyword in error_str for keyword in ["connection", "network", "timeout"]):
                return "❌ Connection Error: Cannot connect to OpenAI servers"
            else:
                return f"❌ API Error: {str(e)}"
    
    def get_available_personas(self) -> List[str]:
        """Get list of available personas"""
        return list(self.persona_prompts.keys())
