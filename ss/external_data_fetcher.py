"""
External Data Fetcher for PersonaRAG
Fetches real-time information from trusted external sources
"""

import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import re
import logging

class ExternalDataFetcher:
    """Fetches real-time information from trusted external sources"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PersonaRAG/1.0 - Educational AI Assistant'
        })
        
        # Trusted sources for different types of queries
        self.trusted_sources = {
            'news': [
                'https://newsapi.org/v2/everything',
                'https://api.nytimes.com/svc/topstories/v2/home.json',
                'https://api.guardianapis.com/search'
            ],
            'technology': [
                'https://api.github.com',
                'https://api.stackexchange.com/2.3',
                'https://hacker-news.firebaseio.com/v0'
            ],
            'business': [
                'https://api.federalreserve.gov/fred/series/GDP',
                'https://api.yahoofinance.com/v6/finance/quote',
                'https://api.crunchbase.com/v4/entities'
            ],
            'science': [
                'https://api.nasa.gov/planetary/apod',
                'https://api.openweathermap.org/data/2.5',
                'https://api.pubmed.ncbi.nlm.nih.gov'
            ],
            'general': [
                'https://en.wikipedia.org/api/rest_v1',
                'https://api.duckduckgo.com/',
                'https://api.britannica.com'
            ]
        }
        
        # API keys (in production, these should be stored securely)
        self.api_keys = {
            'newsapi': 'YOUR_NEWSAPI_KEY',
            'nytimes': 'YOUR_NYTIMES_KEY',
            'guardian': 'YOUR_GUARDIAN_KEY',
            'openweather': 'YOUR_OPENWEATHER_KEY',
            'yahoofinance': 'YOUR_YAHOO_FINANCE_KEY'
        }
    
    def detect_query_type(self, query: str) -> str:
        """Detect the type of query to choose appropriate sources"""
        query_lower = query.lower()
        
        # Keywords for different query types
        type_keywords = {
            'news': ['news', 'breaking', 'latest', 'current events', 'headlines', 'report'],
            'technology': ['technology', 'tech', 'software', 'programming', 'code', 'ai', 'machine learning', 'github'],
            'business': ['business', 'economy', 'market', 'stocks', 'finance', 'gdp', 'revenue', 'profit'],
            'science': ['science', 'research', 'study', 'weather', 'climate', 'space', 'nasa', 'health'],
            'general': ['what', 'who', 'where', 'when', 'why', 'how', 'explain', 'definition']
        }
        
        for query_type, keywords in type_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return query_type
        
        return 'general'
    
    def fetch_from_wikipedia(self, query: str) -> Optional[Dict[str, Any]]:
        """Fetch information from Wikipedia API"""
        try:
            # Search for the page
            search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    'source': 'Wikipedia',
                    'title': data.get('title', ''),
                    'content': data.get('extract', ''),
                    'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                    'timestamp': datetime.now().isoformat()
                }
                return result
            
            # Try search if direct page not found
            search_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = {
                    'source': 'Wikipedia',
                    'title': data.get('title', ''),
                    'content': data.get('extract', ''),
                    'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                    'timestamp': datetime.now().isoformat()
                }
                return result
                
        except Exception as e:
            logging.error(f"Wikipedia API error: {e}")
        
        return None
    
    def fetch_from_duckduckgo(self, query: str) -> Optional[Dict[str, Any]]:
        """Fetch instant answers from DuckDuckGo API"""
        try:
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('AbstractText'):
                    return {
                        'source': 'DuckDuckGo',
                        'title': data.get('Heading', ''),
                        'content': data.get('AbstractText', ''),
                        'url': data.get('AbstractURL', ''),
                        'timestamp': datetime.now().isoformat()
                    }
                    
        except Exception as e:
            logging.error(f"DuckDuckGo API error: {e}")
        
        return None
    
    def fetch_weather(self, query: str) -> Optional[Dict[str, Any]]:
        """Fetch weather information"""
        try:
            # Extract location from query
            location = self._extract_location(query)
            if not location:
                return None
            
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': location,
                'appid': self.api_keys.get('openweather', 'demo'),
                'units': 'metric'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                weather_desc = data['weather'][0]['description']
                temp = data['main']['temp']
                humidity = data['main']['humidity']
                
                content = f"The weather in {location} is {weather_desc} with a temperature of {temp}°C and humidity of {humidity}%."
                
                return {
                    'source': 'OpenWeatherMap',
                    'title': f"Weather in {location}",
                    'content': content,
                    'url': f"https://openweathermap.org/city/{data['id']}",
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logging.error(f"Weather API error: {e}")
        
        return None
    
    def fetch_stock_price(self, query: str) -> Optional[Dict[str, Any]]:
        """Fetch stock price information"""
        try:
            # Extract stock symbol from query
            symbol = self._extract_stock_symbol(query)
            if not symbol:
                return None
            
            url = f"https://api.yahoofinance.com/v6/finance/quote"
            params = {
                'symbols': symbol
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('quoteResponse', {}).get('result'):
                    stock_data = data['quoteResponse']['result'][0]
                    price = stock_data.get('regularMarketPrice', {}).get('fmt', 'N/A')
                    change = stock_data.get('regularMarketChangePercent', {}).get('fmt', 'N/A')
                    
                    content = f"The current price of {symbol} is {price}. Change: {change}."
                    
                    return {
                        'source': 'Yahoo Finance',
                        'title': f"{symbol} Stock Price",
                        'content': content,
                        'url': f"https://finance.yahoo.com/quote/{symbol}",
                        'timestamp': datetime.now().isoformat()
                    }
                    
        except Exception as e:
            logging.error(f"Stock API error: {e}")
        
        return None
    
    def fetch_general_knowledge(self, query: str) -> Optional[Dict[str, Any]]:
        """Fetch general knowledge from multiple sources"""
        
        # Try Wikipedia first
        try:
            result = self.fetch_from_wikipedia(query)
            if result and result.get('content') and len(result['content']) > 50:
                return result
        except Exception as e:
            logging.error(f"Wikipedia API error: {e}")
        
        # Try DuckDuckGo
        try:
            result = self.fetch_from_duckduckgo(query)
            if result and result.get('content') and len(result['content']) > 50:
                return result
        except Exception as e:
            logging.error(f"DuckDuckGo API error: {e}")
        
        # Try alternative sources for more diverse content
        try:
            result = self.fetch_from_alternative(query)
            if result and result.get('content') and len(result['content']) > 50:
                return result
        except Exception as e:
            logging.error(f"Alternative API error: {e}")
        
        return None
    
    def fetch_from_alternative(self, query: str) -> Optional[Dict[str, Any]]:
        """Fetch from alternative sources for more diverse content"""
        import urllib.parse
        
        # Encode the query for safe URL usage
        encoded_query = urllib.parse.quote(query)
        
        # Try different API endpoints or sources with proper URL construction
        alternative_sources = [
            'https://r.jina.ai/http://https://en.wikipedia.org/wiki/' + encoded_query,
            'https://r.jina.ai/http://https://www.britannica.com/search?query=' + encoded_query,
            'https://r.jina.ai/http://https://www.investopedia.com/search?q=' + encoded_query,
            'https://r.jina.ai/http://https://techcrunch.com/search?q=' + encoded_query,
        ]
        
        for source_url in alternative_sources:
            try:
                response = self.session.get(source_url, timeout=10)
                if response.status_code == 200:
                    content = response.text
                    if len(content) > 100:  # Minimum content length
                        return {
                            'source': 'Alternative',
                            'title': query.title(),
                            'content': content[:1000],  # Limit content length
                            'url': source_url,
                            'timestamp': datetime.now().isoformat()
                        }
            except Exception as e:
                logging.error(f"Alternative source error: {e}")
                continue
        
        return None
    
    def fetch_with_fallbacks(self, query: str) -> Optional[Dict[str, Any]]:
        """Fetch with multiple fallback strategies"""
        # Try original query first
        result = self.fetch_general_knowledge(query)
        if result:
            return result
        
        # Try simplified query
        simplified = self._simplify_query(query)
        if simplified != query:
            result = self.fetch_general_knowledge(simplified)
            if result:
                return result
        
        # Special handling for business trends queries
        if 'business trends' in query.lower() or ('business' in query.lower() and 'trends' in query.lower()):
            business_trends_fallbacks = [
                'business trends',
                'market trends',
                'economic trends',
                'industry trends',
                'technology trends',
                'business',
                'economics',
                'market',
                'industry'
            ]
            
            for term in business_trends_fallbacks:
                result = self.fetch_general_knowledge(term)
                if result:
                    return result
        
        # Special handling for productivity/teamwork questions
        if any(word in query.lower() for word in ['productivity', 'teamwork', 'collaboration', 'efficiency', 'performance']):
            productivity_fallbacks = [
                'productivity',
                'teamwork',
                'collaboration',
                'efficiency',
                'performance',
                'management',
                'business',
                'organization',
                'work'
            ]
            
            for term in productivity_fallbacks:
                result = self.fetch_general_knowledge(term)
                if result:
                    return result
        
        # Special handling for digital transformation questions
        if 'digital transformation' in query.lower() or ('digital' in query.lower() and 'transformation' in query.lower()):
            digital_fallbacks = [
                'digital transformation',
                'technology adoption',
                'business innovation',
                'technology integration',
                'digitalization',
                'technology',
                'innovation',
                'business',
                'automation'
            ]
            
            for term in digital_fallbacks:
                result = self.fetch_general_knowledge(term)
                if result:
                    return result
        
        # Special handling for professional development questions
        if 'professional development' in query.lower() or ('professional' in query.lower() and 'development' in query.lower()):
            development_fallbacks = [
                'professional development',
                'training',
                'education',
                'skills development',
                'career development',
                'learning',
                'business',
                'management',
                'work'
            ]
            
            for term in development_fallbacks:
                result = self.fetch_general_knowledge(term)
                if result:
                    return result
        
        # Try industry-specific fallbacks with more diverse terms
        if any(word in query.lower() for word in ['industry', 'business', 'sector', 'market']):
            fallback_terms = [
                'business',           # Most comprehensive
                'industry',           # Industry overview
                'technology',         # Technology challenges
                'economics',          # Economic challenges
                'corporation',        # Corporate challenges
                'market',             # Market challenges
                'employment',         # Workforce challenges
                'management',          # Management challenges
                'innovation',         # Innovation challenges
                'digital transformation', # Digital challenges
                'sustainability',      # Sustainability challenges
                'globalization',       # Global challenges
                'competition'         # Competitive challenges
            ]
            
            for term in fallback_terms:
                result = self.fetch_general_knowledge(term)
                if result:
                    return result
        
        # Try challenge-specific fallbacks
        if 'challenges' in query.lower():
            fallback_terms = [
                'business',           # Business context
                'industry',           # Industry context
                'technology',         # Tech challenges
                'economics',          # Economic challenges
                'corporation',        # Corporate context
                'employment',         # Workforce challenges
                'management',          # Management challenges
                'innovation',         # Innovation challenges
                'digital transformation', # Digital challenges
                'sustainability',      # Sustainability challenges
            ]
            
            for term in fallback_terms:
                result = self.fetch_general_knowledge(term)
                if result:
                    return result
        
        # Try AI/tech specific fallbacks
        if any(word in query.lower() for word in ['artificial', 'intelligence', 'machine', 'learning', 'ai', 'technology', 'tech']):
            fallback_terms = [
                'artificial intelligence',
                'machine learning',
                'deep learning',
                'neural networks',
                'computer science',
                'data science',
                'automation',
                'robotics',
                'cybersecurity',
                'software engineering'
            ]
            
            for term in fallback_terms:
                result = self.fetch_general_knowledge(term)
                if result:
                    return result
        
        return None
    
    def _extract_location(self, query: str) -> Optional[str]:
        """Extract location from weather query"""
        weather_keywords = ['weather', 'temperature', 'forecast', 'climate']
        words = query.lower().split()
        
        for i, word in enumerate(words):
            if word in weather_keywords and i + 1 < len(words):
                return ' '.join(words[i+1:]).strip('?!.')
        
        return None
    
    def _extract_stock_symbol(self, query: str) -> Optional[str]:
        """Extract stock symbol from query"""
        stock_keywords = ['stock', 'price', 'shares', 'market', 'trading']
        words = query.upper().split()
        
        # Look for potential stock symbols (usually 1-5 letters)
        for word in words:
            if word.isalpha() and 1 <= len(word) <= 5 and word not in ['THE', 'FOR', 'AND', 'OR']:
                return word
        
        return None
    
    def fetch_external_data(self, query: str, persona: str) -> Optional[Dict[str, Any]]:
        """Main method to fetch external data based on query type"""
        query_type = self.detect_query_type(query)
        
        # Specialized handlers with fallbacks
        if 'weather' in query.lower():
            result = self.fetch_weather(query)
            if result:
                return result
        
        elif any(word in query.lower() for word in ['stock', 'price', 'shares']):
            result = self.fetch_stock_price(query)
            if result:
                return result
        
        # General knowledge fetchers with enhanced fallbacks
        result = self.fetch_with_fallbacks(query)
        
        return result
    
    def _simplify_query(self, query: str) -> str:
        """Simplify query for better API compatibility"""
        # Remove question words and focus on key terms
        question_words = {'what', 'is', 'are', 'was', 'were', 'how', 'when', 'where', 'why', 'who', 'which', 'can', 'could', 'would', 'should', 'do', 'does', 'did', 'like', 'tell', 'me', 'give', 'explain'}
        words = query.lower().split()
        
        # Special handling for weather queries
        if 'weather' in words:
            # Extract location after 'weather'
            location_words = []
            found_weather = False
            
            for i, word in enumerate(words):
                if word == 'weather':
                    found_weather = True
                    continue
                elif found_weather:
                    # Skip prepositions and articles
                    if word in ['in', 'at', 'for', 'the', 'like']:
                        continue
                    # Stop at punctuation
                    elif word.endswith('?') or word.endswith('.') or word.endswith('!'):
                        break
                    # Add location words (including multi-word locations)
                    elif len(word) > 1:
                        location_words.append(word)
                        # Look ahead for multi-word locations
                        if i + 1 < len(words):
                            next_word = words[i + 1]
                            if next_word not in question_words and len(next_word) > 1:
                                location_words.append(next_word)
            
            if location_words:
                return ' '.join(location_words[:2])
        
        # Special handling for business trends queries
        if 'business' in words and 'trends' in words:
            return 'business trends'
        
        # Special handling for industry/business queries
        if any(word in words for word in ['industry', 'business', 'sector', 'market']):
            # Look for challenges, trends, issues, problems
            challenge_words = ['challenges', 'trends', 'issues', 'problems', 'difficulties', 'obstacles']
            for word in words:
                if word in challenge_words:
                    return word  # Return the specific challenge-related term
            
            # If no challenge word found, try 'industry' or 'business'
            if 'industry' in words:
                return 'industry challenges'
            elif 'business' in words:
                return 'business challenges'
        
        # For other queries, remove question words and return key terms
        key_terms = [word for word in words if word not in question_words and len(word) > 2]
        
        if key_terms:
            # Prioritize nouns and specific terms
            important_terms = []
            for term in key_terms[:3]:
                if term not in ['the', 'and', 'or', 'but', 'for', 'with', 'by']:
                    important_terms.append(term)
            
            if important_terms:
                return ' '.join(important_terms[:2])
        
        # Fallback: return first few meaningful words
        meaningful_words = [word for word in words if len(word) > 2][:2]
        return ' '.join(meaningful_words) if meaningful_words else words[0] if words else query
    
    def format_source_citation(self, source_data: Dict[str, Any]) -> str:
        """Format source citation for transparency"""
        if not source_data:
            return ""
        
        citation = f"\n\nSource: {source_data['source']}"
        if source_data.get('url'):
            citation += f" | {source_data['url']}"
        if source_data.get('timestamp'):
            citation += f" | Accessed: {source_data['timestamp'][:10]}"
        
        return citation
