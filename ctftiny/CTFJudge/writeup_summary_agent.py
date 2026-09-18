#!/usr/bin/env python3
"""
This agent analyze CTF writeups and decompose them into detailed steps
"""

import os
import json
import sys
import re
from typing import List, Dict
from dataclasses import dataclass
from dotenv import load_dotenv
from openai import OpenAI
from llm_utils import LLMResponseUtils

load_dotenv()                            # Load environment variables


@dataclass
class WriteupStep:
    step_number: int
    description: str
    key_actions: List[str]
    commands: List[str]


# Agent to decompose CTF writeups into structured steps using LLM
class WriteupDecomposer:
    
    def __init__(self, api_key: str = None, config_path: str = "config.json"):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OpenRouter API key missing. Set OPENROUTER_API_KEY environment variable or in .env file.")

        # Load configuration
        self.config = LLMResponseUtils.load_config(config_path)

        self.client = OpenAI(api_key=self.api_key, base_url="https://openrouter.ai/api/v1")
        self.model = self.config.get("model", "claude-3-5-haiku-20241022")
        self.max_tokens = self.config.get("max_tokens", 4000)
        self.temperature = self.config.get("temperature", 0.1)
    
    def analyze_writeup(self, writeup_content: str) -> Dict:

        prompt = f"""
You are a cybersecurity expert analyzing a CTF (Capture The Flag) challenge writeup. Your task is to decompose this writeup into detailed, numbered steps that describe the solution process.

For each step you should:
1. Provide a clear description of what was done
2. List key actions taken
3. Extract important command line executions 

Please analyze this CTF writeup and return a JSON structure with the following format:

{{
  "total_steps": <number>,
  "steps": [
    {{
      "step_number": 1,
      "description": "Brief description of the step",
      "key_actions": ["action 1", "action 2", ...],
      "commands": ["command1", "command2", ...]
    }},
    ...
  ]
}}

Here is the writeup to analyze:

{writeup_content}

Focus on the logical progression of the solution, identifying:
- Vulnerability identification
- Reconnaissance activities  
- Exploitation techniques
- Command executions (curl, nc, printf, etc.)
- Flag retrieval

Return only the JSON structure, no additional text.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            response_text = response.choices[0].message.content.strip()
            
            response_text = re.sub(r'^```(?:json)?\s*|\s*```$', '', response_text, flags=re.MULTILINE).strip()
            
            return json.loads(response_text)
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response as JSON: {e}")
            print(f"Raw response: {response_text}")
            # Fallback to a basic structure
            return {
                "total_steps": 1,
                "steps": [{
                    "step_number": 1,
                    "description": "Failed to parse writeup - manual review needed",
                    "key_actions": ["Review writeup manually"],
                    "commands": []
                }]
            }
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return {
                "total_steps": 0,
                "steps": []
            }
    
    # Generate a structured summary of the writeup using LLM
    def generate_summary(self, writeup_file: str) -> Dict:
        with open(writeup_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"Sending writeup to LLM for analysis...")
        analysis = self.analyze_writeup(content)
        
        return {
            'writeup_file': os.path.basename(writeup_file),
            'total_steps': analysis.get('total_steps', 0),
            'steps': analysis.get('steps', [])
        }
    
    def save_summary(self, summary: Dict, output_file: str):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


