"""LLM clients for OpenAI and Perplexity APIs."""

import json
import re
import time
from typing import Any, Dict, Optional
import requests
from tenacity import retry, stop_after_attempt, wait_exponential
from rich.console import Console

from .config import RecapConfig

console = Console()

class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass

class PerplexityClient:
    """Client for Perplexity API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = RecapConfig.PERPLEXITY_BASE_URL
        self.rate_limit = RecapConfig.PERPLEXITY_RATE_LIMIT
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Apply rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=60)
    )
    def _make_request(self, payload: Dict[str, Any]) -> requests.Response:
        """Make HTTP request with retry logic."""
        self._rate_limit()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=90  # Increased timeout for more reliability
        )

        if response.status_code != 200:
            error_detail = response.text[:500] if len(response.text) > 500 else response.text
            raise LLMError(f"Perplexity API error {response.status_code}: {error_detail}")
        
        return response
    
    def complete_json(self, prompt: str, model: str = "sonar-mini") -> Dict[str, Any]:
        """Complete a prompt and return JSON response."""
        console.print(f"[blue]🔍 Calling Perplexity {model}...[/blue]")
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a research assistant. Return only valid JSON responses. Enable web search for current information."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 4000,
            "search_domain_filter": ["espn.com", "nfl.com", "fantasypros.com", "thescore.com"],
            "search_recency_filter": "week"
        }
        
        try:
            response = self._make_request(payload)
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            
            # Estimate cost
            input_chars = len(prompt)
            output_chars = len(content)
            estimated_cost = RecapConfig.get_estimated_cost_usd(input_chars, output_chars, model)
            console.print(f"[cyan]💰 Estimated cost: ${estimated_cost:.4f}[/cyan]")
            
            # Try to parse as JSON with more robust handling
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from the response with multiple patterns
                json_patterns = [
                    r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested braces pattern
                    r'\{.*?\}(?=\s*(?:\n|\r|\Z))',       # Single object pattern
                    r'\{.*\}',                           # Fallback pattern
                ]

                for pattern in json_patterns:
                    json_match = re.search(pattern, content, re.DOTALL)
                    if json_match:
                        try:
                            json_str = json_match.group()
                            # Clean up common JSON issues
                            json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
                            json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas in arrays
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            continue

                # Truncate content for error message
                content_preview = content[:200] + "..." if len(content) > 200 else content
                raise LLMError(f"Failed to parse JSON from Perplexity response: {content_preview}")
        
        except Exception as e:
            console.print(f"[red]❌ Perplexity API error: {e}[/red]")
            raise LLMError(f"Perplexity API call failed: {e}")

class OpenAIClient:
    """Client for OpenAI API."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = RecapConfig.OPENAI_BASE_URL
        self.rate_limit = RecapConfig.OPENAI_RATE_LIMIT
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Apply rate limiting."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit:
            sleep_time = self.rate_limit - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=60)
    )
    def _make_request(self, payload: Dict[str, Any]) -> requests.Response:
        """Make HTTP request with retry logic."""
        self._rate_limit()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # GPT-5 models need longer timeout
        is_gpt5_model = payload.get("model", "") in ["gpt-5", "gpt-5-mini", "gpt-5-nano"]
        timeout = 300 if is_gpt5_model else 120  # 5 minutes for GPT-5, 2 minutes for others

        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        if response.status_code != 200:
            # Handle rate limit with longer wait
            if response.status_code == 429:
                import json as json_lib
                try:
                    error_data = json_lib.loads(response.text)
                    error_msg = error_data.get('error', {}).get('message', 'Rate limit exceeded')
                    console.print(f"[yellow]⏳ Rate limit hit: {error_msg}[/yellow]")
                    # Extract wait time if available
                    if "try again in" in error_msg:
                        import re
                        wait_match = re.search(r'try again in (\d+\.?\d*)s', error_msg)
                        if wait_match:
                            wait_time = float(wait_match.group(1)) + 1  # Add buffer
                            console.print(f"[yellow]⏳ Waiting {wait_time:.1f} seconds...[/yellow]")
                            time.sleep(wait_time)
                except:
                    pass
            raise LLMError(f"OpenAI API error {response.status_code}: {response.text}")
        
        return response
    
    def complete_text(self, prompt: str, model: str, max_tokens: int = 4000) -> str:
        """Complete a prompt and return text response."""
        console.print(f"[blue]🤖 Calling OpenAI {model}...[/blue]")

        # GPT-5 models only support default temperature (1), not custom values
        is_gpt5_model = model in ["gpt-5", "gpt-5-mini", "gpt-5-nano"]

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        # Only add token limits for non-GPT-5 models (GPT-5 doesn't work with token limits)
        if not is_gpt5_model:
            payload["max_tokens"] = max_tokens

        # Only add temperature for non-GPT-5 models
        if not is_gpt5_model:
            payload["temperature"] = 0.7
        # GPT-5 uses default parameters (no custom temperature or other params)
        
        try:
            response = self._make_request(payload)
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            
            # Estimate cost
            input_chars = len(prompt)
            output_chars = len(content)
            estimated_cost = RecapConfig.get_estimated_cost_usd(input_chars, output_chars, model)
            console.print(f"[cyan]💰 Estimated cost: ${estimated_cost:.4f}[/cyan]")
            
            return content
        
        except Exception as e:
            console.print(f"[red]❌ OpenAI API error: {e}[/red]")
            raise LLMError(f"OpenAI API call failed: {e}")
    
    def complete_json(self, prompt: str, model: str, max_tokens: int = 4000) -> Dict[str, Any]:
        """Complete a prompt and return JSON response."""
        json_prompt = f"{prompt}\n\nIMPORTANT: Return only valid JSON. Do not include any text before or after the JSON."
        
        response_text = self.complete_text(json_prompt, model, max_tokens)
        
        # Try to parse as JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # Try to fix common JSON issues
            fixed_json = self._fix_json(response_text)
            if fixed_json:
                try:
                    return json.loads(fixed_json)
                except json.JSONDecodeError:
                    pass
            
            raise LLMError(f"Failed to parse JSON from OpenAI response: {response_text}")
    
    def _fix_json(self, text: str) -> Optional[str]:
        """Attempt to fix common JSON formatting issues."""
        # Remove leading/trailing whitespace and non-JSON content
        text = text.strip()
        
        # Find JSON boundaries
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start >= 0 and end > start:
            json_text = text[start:end]
            
            # Fix common issues
            json_text = re.sub(r',\s*}', '}', json_text)  # Remove trailing commas
            json_text = re.sub(r',\s*]', ']', json_text)  # Remove trailing commas in arrays
            
            return json_text
        
        return None

class PlayerNameNormalizer:
    """Helper for normalizing player names using Sleeper data."""
    
    @staticmethod
    def normalize_player_name(name: str, sleeper_players: Optional[Dict] = None) -> str:
        """Normalize player name for consistency."""
        if not name:
            return name
        
        # Basic normalization
        normalized = name.strip()
        
        # Handle common abbreviations
        normalized = re.sub(r'\bJr\.?\b', 'Jr.', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bSr\.?\b', 'Sr.', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bIII?\b', 'III', normalized, flags=re.IGNORECASE)
        
        # If we have Sleeper player data, try to match
        if sleeper_players:
            # Try exact match first
            for player_id, player_data in sleeper_players.items():
                if player_data.get('full_name', '').lower() == normalized.lower():
                    return player_data['full_name']
            
            # Try partial matches
            normalized_lower = normalized.lower()
            for player_id, player_data in sleeper_players.items():
                full_name = player_data.get('full_name', '')
                if full_name.lower() == normalized_lower:
                    return full_name
                
                # Check for initial matches (e.g., "J. Jefferson" -> "Justin Jefferson")
                first_name = player_data.get('first_name', '')
                last_name = player_data.get('last_name', '')
                
                if (first_name and last_name and 
                    normalized_lower.startswith(first_name[0].lower() + '.') and
                    last_name.lower() in normalized_lower):
                    return full_name
        
        return normalized

# Global clients (initialized when config is validated)
perplexity_client: Optional[PerplexityClient] = None
openai_client: Optional[OpenAIClient] = None

def initialize_clients():
    """Initialize global LLM clients."""
    global perplexity_client, openai_client
    
    RecapConfig.validate()
    
    perplexity_client = PerplexityClient(RecapConfig.PERPLEXITY_API_KEY)
    openai_client = OpenAIClient(RecapConfig.OPENAI_API_KEY)
    
    console.print("[green]✅ LLM clients initialized[/green]")

def get_perplexity_client() -> PerplexityClient:
    """Get initialized Perplexity client."""
    if perplexity_client is None:
        initialize_clients()
    return perplexity_client

def get_openai_client() -> OpenAIClient:
    """Get initialized OpenAI client."""
    if openai_client is None:
        initialize_clients()
    return openai_client