#!/usr/bin/env python3

import os
import datetime
from typing import Tuple


class VersionManager:
    def __init__(self, outputs_dir='outputs', evaluations_dir='evaluations'):
        self.outputs_dir = outputs_dir
        self.evaluations_dir = evaluations_dir
        self.session_timestamp = datetime.datetime.now().strftime('%m%d_%H%M')
        
        # session directories
        self.session_outputs_dir = os.path.join(outputs_dir, self.session_timestamp)
        self.session_evaluations_dir = os.path.join(evaluations_dir, self.session_timestamp)
        
        os.makedirs(self.session_outputs_dir, exist_ok=True)
        os.makedirs(self.session_evaluations_dir, exist_ok=True)
    
    def get_timestamp(self) -> str:
        return self.session_timestamp
    
    def get_versioned_filename(self, challenge_name: str, file_type: str, extension: str = 'json') -> Tuple[str, str, str]:
        directory = self.session_outputs_dir if file_type in ['writeup_summary', 'trajectory_summary'] else self.session_evaluations_dir
        
        json_filename = os.path.join(directory, f'{challenge_name}_{file_type}.json')
        
        if extension == 'md':
            md_filename = json_filename.replace('.json', '.md')
            return self.session_timestamp, json_filename, md_filename
        
        return self.session_timestamp, json_filename, json_filename