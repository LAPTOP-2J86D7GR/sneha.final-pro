"""
PersonaRAG Web Application
Personalized AI assistant with role-based responses and RAG integration
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
import json
import os
import time
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from typing import Dict, List, Any, Optional

# Import PersonaRAG components
from personarag import PersonaRAG, Persona
from prompt_builder import CompletePromptBuilder
from rag_system import DocumentStore, DocumentRetriever, Document, DocumentType

app = Flask(__name__)
app.secret_key = 'personarag_secret_key_2024'

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# User class for authentication
class User(UserMixin):
    def __init__(self, id: str, email: str, password_hash: str):
        self.id = id
        self.email = email
        self.password_hash = password_hash
    
    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def get_by_email(email: str) -> Optional['User']:
        users = load_users()
        for user_id, user_data in users.items():
            if user_data['email'] == email:
                return User(
                    id=user_id,
                    email=user_data['email'],
                    password_hash=user_data['password_hash']
                )
        return None
    
    @staticmethod
    def get_by_id(user_id: str) -> Optional['User']:
        users = load_users()
        if user_id in users:
            user_data = users[user_id]
            return User(
                id=user_id,
                email=user_data['email'],
                password_hash=user_data['password_hash']
            )
        return None

@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    return User.get_by_id(user_id)

def load_users() -> List[Dict]:
    """Load users from JSON file"""
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Create default users
        default_users = [
            {
                'id': '1',
                'email': 'exec@company.com',
                'password_hash': generate_password_hash('exec123'),
                'persona': 'Executive'
            },
            {
                'id': '2',
                'email': 'dev@company.com',
                'password_hash': generate_password_hash('dev123'),
                'persona': 'Developer'
            },
            {
                'id': '3',
                'email': 'hr@company.com',
                'password_hash': generate_password_hash('hr123'),
                'persona': 'HR Specialist'
            },
            {
                'id': '4',
                'email': 'student@university.edu',
                'password_hash': generate_password_hash('student123'),
                'persona': 'Student'
            }
        ]
        with open('users.json', 'w') as f:
            json.dump(default_users, f, indent=2)
        return default_users

# Initialize PersonaRAG system
document_store = DocumentStore()
retriever = DocumentRetriever(document_store)
prompt_builder = CompletePromptBuilder()
personarag = PersonaRAG()

# Chat history storage (in production, use a database)
chat_histories: Dict[str, List[Dict]] = {}

def get_user_chat_key(user_id: str, persona: str) -> str:
    return f"{user_id}_{persona}"

def get_chat_history(user_id: str, persona: str) -> List[Dict]:
    key = get_user_chat_key(user_id, persona)
    return chat_histories.get(key, [])

def save_chat_message(user_id: str, persona: str, message_type: str, content: str, timestamp: str = None):
    key = get_user_chat_key(user_id, persona)
    if key not in chat_histories:
        chat_histories[key] = []
    
    if timestamp is None:
        timestamp = datetime.now().isoformat()
    
    chat_histories[key].append({
        'type': message_type,
        'content': content,
        'timestamp': timestamp
    })

def clear_chat_history(user_id: str, persona: str):
    key = get_user_chat_key(user_id, persona)
    if key in chat_histories:
        chat_histories[key] = []

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.get_by_email(email)
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            return render_template('reactive_login.html', error='Invalid email or password')
    
    return render_template('reactive_login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/home')
@login_required
def home():
    return render_template('reactive_home.html')

@app.route('/persona-selection')
@login_required
def persona_selection():
    return render_template('reactive_persona_selection.html')

@app.route('/chat/<persona>')
@login_required
def chat(persona: str):
    # Validate persona
    try:
        valid_persona = Persona(persona)
    except ValueError:
        flash('Invalid persona selected', 'error')
        return redirect(url_for('persona_selection'))
    
    # Get chat history
    messages = get_chat_history(current_user.id, persona)
    
    return render_template('reactive_chat.html', persona=persona, messages=messages, current_user_id=current_user.id)

# API Routes
@app.route('/api/health', methods=['GET'])
def api_health():
    """API health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'PersonaRAG API',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/personas', methods=['GET'])
def api_personas():
    """Get available personas"""
    personas = [
        {'id': 'Executive', 'name': 'Executive', 'description': 'Strategic business leader'},
        {'id': 'Developer', 'name': 'Developer', 'description': 'Technical expert'},
        {'id': 'HR Specialist', 'name': 'HR Specialist', 'description': 'People and policy expert'},
        {'id': 'Student', 'name': 'Student', 'description': 'Learning-focused individual'},
        {'id': 'General', 'name': 'General', 'description': 'Versatile assistant'}
    ]
    return jsonify({'personas': personas})

@app.route('/api/suggested-questions/<persona>', methods=['GET'])
def api_suggested_questions(persona: str):
    """Get universal suggested questions (same for all personas)"""
    # Universal questions that work for all personas but will be answered differently
    universal_questions = [
        "What are the key business trends for next quarter?",
        "How can we improve team productivity and collaboration?",
        "What are the biggest challenges facing our industry?",
        "How should we approach digital transformation?",
        "What strategies work best for professional development?"
    ]
    
    return jsonify({
        'persona': persona,
        'questions': universal_questions
    })

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Main chat API endpoint with external data fetching"""
    data = request.get_json()
    
    message = data.get('message', '')
    persona = data.get('persona', 'General')
    user_id = data.get('user_id', 'anonymous')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    try:
        # Set persona and generate AI response
        personarag.set_persona(Persona(persona))
        
        # Generate response using external data fetching
        response = personarag.generate_response(message)
        
        # Don't automatically save to chat history - let frontend handle it
        
        return jsonify({
            'response': response,
            'persona': persona,
            'timestamp': datetime.now().isoformat(),
            'message_id': f"{user_id}_{persona}_{int(time.time())}"
        })
    
    except Exception as e:
        return jsonify({'error': f'Error generating response: {str(e)}'}), 500

@app.route('/api/chat-history/<user_id>/<persona>', methods=['GET'])
def api_chat_history(user_id: str, persona: str):
    """Get chat history for a user and persona"""
    history = get_chat_history(user_id, persona)
    return jsonify({
        'user_id': user_id,
        'persona': persona,
        'history': history,
        'total_messages': len(history)
    })

@app.route('/api/status', methods=['GET'])
def api_status():
    """Get system and OpenAI API status"""
    try:
        openai_status = personarag.openai_integration.get_api_status()
        return jsonify({
            'status': 'running',
            'openai_api': openai_status,
            'available_personas': [persona.value for persona in Persona]
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/save-message', methods=['POST'])
def api_save_message():
    """Save a single message to chat history"""
    data = request.get_json()
    
    message = data.get('message', '')
    persona = data.get('persona', '')
    user_id = data.get('user_id', '')
    message_type = data.get('message_type', 'user')
    timestamp = data.get('timestamp', datetime.now().isoformat())
    
    if not message or not persona or not user_id:
        return jsonify({'error': 'Message, persona, and user_id are required'}), 400
    
    try:
        save_chat_message(user_id, persona, message_type, message, timestamp)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': f'Error saving message: {str(e)}'}), 500

@app.route('/api/clear-history/<user_id>/<persona>', methods=['DELETE'])
def api_clear_history(user_id: str, persona: str):
    """Clear chat history for a user and persona"""
    clear_chat_history(user_id, persona)
    return jsonify({
        'success': True,
        'message': 'Chat history cleared successfully'
    })

# Enhanced chat functionality with AI integration
@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    message = data.get('message', '')
    persona = data.get('persona', '')
    
    if not message or not persona:
        return jsonify({'error': 'Message and persona are required'}), 400
    
    try:
        # Set persona and generate enhanced AI response
        personarag.set_persona(Persona(persona))
        
        # For demo purposes, create some sample documents with real business trends
        # In production, this would come from the RAG system
        sample_documents = [
            "Q1 2025 Business Trends: AI adoption accelerating across enterprises with 67% increasing investment. Remote work hybrid models becoming standard with 3-4 days office requirement. Supply chain diversification priority due to geopolitical risks. Sustainability reporting now mandatory for public companies. Cybersecurity budgets increasing by 25% YoY.",
            "Technology Trends for Q1 2025: Generative AI integration in business workflows showing 40% productivity gains. Cloud migration accelerating with 80% of enterprises adopting multi-cloud strategies. Edge computing adoption growing for IoT applications. Blockchain use cases expanding beyond cryptocurrency to supply chain and healthcare.",
            "Market Trends Q1 2025: Consumer spending shifting to experiences over products by 23%. Subscription-based business models growing across all sectors. Personalization becoming key differentiator with 78% of consumers expecting tailored experiences. E-commerce mobile commerce exceeding 60% of total online sales.",
            "Workforce Trends Q1 2025: Skills gap widening with 87% of companies reporting difficulty filling technical roles. Remote work flexibility becoming non-negotiable for talent retention. AI reskilling programs launched by 65% of enterprises. Mental health benefits becoming standard offering with 45% increase in adoption.",
            "Financial Trends Q1 2025: Interest rates expected to stabilize at current levels. ESG investing representing 40% of new fund flows. Digital payment processing growing 35% YoY. Cryptocurrency regulations becoming clearer with institutional adoption increasing."
        ]
        
        response = personarag.generate_response(message, sample_documents)
        
        # Save user message
        timestamp = datetime.now().isoformat()
        save_chat_message(current_user.id, persona, 'user', message, timestamp)
        
        # Save assistant response
        save_chat_message(current_user.id, persona, 'assistant', response, timestamp)
        
        return jsonify({
            'response': response,
            'timestamp': timestamp,
            'persona': persona,
            'suggestions': get_context_suggestions(message, persona)
        })
    
    except Exception as e:
        return jsonify({'error': f'Error generating response: {str(e)}'}), 500

def get_context_suggestions(message: str, persona: str) -> List[str]:
    """Generate contextual suggestions based on message and persona"""
    base_suggestions = {
        'Executive': [
            "Can you provide more strategic insights?",
            "What are the business implications?",
            "How does this affect our bottom line?"
        ],
        'Developer': [
            "Can you show me the code implementation?",
            "What are the technical specifications?",
            "How does this integrate with existing systems?"
        ],
        'HR Specialist': [
            "How does this impact employees?",
            "What are the policy considerations?",
            "How should we communicate this to the team?"
        ],
        'Student': [
            "Can you explain this in simpler terms?",
            "What are the key takeaways?",
            "Can you provide an example?"
        ],
        'General': [
            "Can you tell me more?",
            "What are the next steps?",
            "How can I apply this?"
        ]
    }
    
    return base_suggestions.get(persona, base_suggestions['General'])

@app.route('/clear_chat', methods=['POST'])
@login_required
def clear_chat():
    data = request.get_json()
    persona = data.get('persona', '')
    
    if not persona:
        return jsonify({'error': 'Persona is required'}), 400
    
    clear_chat_history(current_user.id, persona)
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
