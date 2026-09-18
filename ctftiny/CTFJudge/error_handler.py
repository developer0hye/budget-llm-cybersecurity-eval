#!/usr/bin/env python3
"""
Log errors encountered during evalution by judging unit
"""

import os
import json
import datetime
from dataclasses import dataclass
from enum import Enum, auto

class ComponentType(Enum):
    FILE_VALIDATION = auto()
    TRAJECTORY_ANALYSIS = auto()
    ORCHESTRATOR = auto()
    MAIN = auto()
    WRITEUP_SUMMARY_AGENT = auto()
    TRAJECTORY_SUMMARY_AGENT = auto()
    QUALITATIVE_EVALUATION_AGENT = auto()

class ErrorType(Enum):
    MISSING_TRAJECTORY = auto()
    MISSING_WRITEUP = auto()
    EMPTY_FILE = auto()
    NO_FILES = auto()
    AGENT_INITIALIZATION = auto()
    DIRECTORY_MISSING = auto()
    SYSTEM_ERROR = auto()
    API_ERROR = auto()
    PARSING_ERROR = auto()
    EVALUATION_FAILED = auto()
    CHALLENGE_FAILED = auto()
    CHALLENGE_NOT_FOUND = auto()


@dataclass
class ErrorInfo:
    timestamp: str
    error_type: str
    component: str
    challenge_name: str
    description: str
    details: str


class ErrorHandler:
    
    def __init__(self, error_dir: str = 'errors'):
        self.error_dir = error_dir
        os.makedirs(error_dir, exist_ok=True)
        self.session_errors = []
    
    def log_error(self, error_type: str, component: ComponentType, challenge_name: str, 
                  description: str, details: str = "") -> ErrorInfo:
        
        error_info = ErrorInfo(
            timestamp=datetime.datetime.now().isoformat(),
            error_type=error_type,
            component=component.name.lower(),
            challenge_name=challenge_name,
            description=description,
            details=details
        )
        
        self.session_errors.append(error_info)
        
        self._save_error_file(error_info)
        
        self._print_error(error_info)
        
        return error_info

    def log_file_mismatch(self, writeup_files: list, trajectory_files: list):
    #  trajs and write-ups required to have the same name (excluding file ext)

        writeup_bases = {f.replace('.txt', '') for f in writeup_files}
        trajectory_bases = {f.replace('.json', '') for f in trajectory_files}
        
        missing_trajectories = writeup_bases - trajectory_bases
        missing_writeups = trajectory_bases - writeup_bases
        
        if missing_trajectories:
            self.log_error(
                error_type=ErrorType.MISSING_TRAJECTORY.name,
                component=ComponentType.FILE_VALIDATION,
                challenge_name="multiple",
                description=f"Missing trajectory files for {len(missing_trajectories)} writeups",
                details=f"Missing trajectories for: {', '.join(missing_trajectories)}"
            )
        
        if missing_writeups:
            self.log_error(
                error_type=ErrorType.MISSING_WRITEUP.name,
                component=ComponentType.FILE_VALIDATION, 
                challenge_name="multiple",
                description=f"Missing writeup files for {len(missing_writeups)} trajectories",
                details=f"Missing writeups for: {', '.join(missing_writeups)}"
            )
    
    def log_empty_file(self, file_path: str, file_type: str):

        challenge_name = os.path.basename(file_path).split('.')[0]
        self.log_error(
            error_type=ErrorType.EMPTY_FILE.name,
            component=ComponentType.FILE_VALIDATION,
            challenge_name=challenge_name,
            description=f"Empty {file_type} file detected",
            details=f"File: {file_path} (size: {os.path.getsize(file_path)} bytes)"
        )
    
    def log_api_error(self, component: ComponentType, challenge_name: str, api_error: Exception):

        self.log_error(
            error_type=ErrorType.API_ERROR.name,
            component=component,
            challenge_name=challenge_name,
            description=f"Claude API error in {component}",
            details=f"Error: {str(api_error)}\nType: {type(api_error).__name__}"
        )
    
    def log_parsing_error(self, component: ComponentType, challenge_name: str, content_preview: str, error: Exception):

        self.log_error(
            error_type=ErrorType.PARSING_ERROR.name,
            component=component,
            challenge_name=challenge_name,
            description=f"Failed to parse content in {component}",
            details=f"Error: {str(error)}\nContent preview: {content_preview[:200]}..."
        )
    
    def log_challenge_failure(self, challenge_name: str, success_status: bool, exit_reason: str):

        if not success_status:
            self.log_error(
                error_type=ErrorType.CHALLENGE_FAILED.name,
                component=ComponentType.TRAJECTORY_ANALYSIS,
                challenge_name=challenge_name,
                description="AI trajectory indicates challenge was not solved successfully",
                details=f"Success: {success_status}, Exit reason: {exit_reason}"
            )
    
    def _save_error_file(self, error_info: ErrorInfo):

        timestamp_str = error_info.timestamp.replace(':', '-').replace('.', '-')
        error_type_str = error_info.error_type.name if hasattr(error_info.error_type, 'name') else str(error_info.error_type)
        component_str = error_info.component.name if hasattr(error_info.component, 'name') else str(error_info.component)
        filename = f"{error_info.challenge_name}_{component_str}_{error_type_str}_{timestamp_str}.json"
        filepath = os.path.join(self.error_dir, filename)
        
        error_dict = {
            'timestamp': error_info.timestamp,
            'error_type': error_info.error_type.name if hasattr(error_info.error_type, 'name') else str(error_info.error_type),
            'component': error_info.component.name if hasattr(error_info.component, 'name') else str(error_info.component),
            'challenge_name': error_info.challenge_name,
            'description': error_info.description,
            'details': error_info.details
        }
        
        with open(filepath, 'w') as f:
            json.dump(error_dict, f, indent=2)     
    
    def _print_error(self, error_info: ErrorInfo):
        print(f"[X] [{error_info.component}] {error_info.description}")
        if error_info.details:
            print(f"   Details: {error_info.details}")
    
    def generate_session_summary(self, output_file: str = None):

        if not output_file:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            output_file = os.path.join(self.error_dir, f"session_summary_{timestamp}.json")
        
        summary = {
            'session_timestamp': datetime.datetime.now().isoformat(),
            'total_errors': len(self.session_errors),
            'errors': [
                {
                    'timestamp': err.timestamp,
                    'type': err.error_type,
                    'component': err.component,
                    'challenge': err.challenge_name,
                    'description': err.description
                }
                for err in self.session_errors
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        return summary
    
    def get_errors_by_challenge(self, challenge_name: str) -> list:
        return [err for err in self.session_errors if err.challenge_name == challenge_name]