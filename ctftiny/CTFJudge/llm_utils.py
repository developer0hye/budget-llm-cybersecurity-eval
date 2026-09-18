#!/usr/bin/env python3

import re
import json
import sys
from typing import Dict, Any, Optional


class LLMResponseUtils:
    
    @staticmethod
    def clean_response_text(response_text: str) -> str:
        # clean for code block wrappers 
        cleaned_response = re.sub(r'^```(?:json)?\s*|\s*```$', '', response_text, flags=re.MULTILINE).strip()
        # Remove control characters 
        cleaned_response = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', cleaned_response)
        cleaned_response = cleaned_response.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
        # Normalize whitespace
        cleaned_response = re.sub(r'\s+', ' ', cleaned_response)  
        cleaned_response = cleaned_response.strip()
        
        return cleaned_response
    
    @staticmethod
    def parse_json_response(response_text: str) -> Dict[str, Any]:
        cleaned_response = LLMResponseUtils.clean_response_text(response_text)
        return json.loads(cleaned_response)
    
    
    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"Warning: Config file {config_path} not found or invalid. Using defaults.")
            return {}