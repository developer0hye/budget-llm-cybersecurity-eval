#!/usr/bin/env python3
"""
Main orchestrator with comprehensive error handling, versioning, and evaluation.
"""

import os
import sys
import argparse
import time
from datetime import datetime
from pathlib import Path
from writeup_summary_agent import WriteupDecomposer
from trajectory_summary_agent import TrajectoryDecomposer
from qualitative_evaluation_agent import StepMatcher
from error_handler import ErrorHandler, ComponentType, ErrorType
from version_manager import VersionManager


class EnhancedEvaluationOrchestrator:
    
    def __init__(self, writeups_dir='writeups', trajs_dir='trajs', 
                 outputs_dir='outputs', evaluations_dir='evaluations', 
                 errors_dir='errors'):
        self.writeups_dir = writeups_dir
        self.trajs_dir = trajs_dir
        self.outputs_dir = outputs_dir
        self.evaluations_dir = evaluations_dir
        self.errors_dir = errors_dir
        
        # Check for required API key environment variable
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            print("[X] Error: OPENROUTER_API_KEY environment variable not set")
            print("Please set your API key: export OPENROUTER_API_KEY='your-key'")
            sys.exit(1)
        
        self.error_handler = ErrorHandler(errors_dir)
        self.version_manager = VersionManager(outputs_dir, evaluations_dir)
        
        for directory in [outputs_dir, evaluations_dir, errors_dir]:
            os.makedirs(directory, exist_ok=True)
        
        self.writeup_decomposer = None
        self.trajectory_decomposer = None
        self.step_matcher = None
    
    def _initialize_agents(self):
        try:
            if not self.writeup_decomposer:
                self.writeup_decomposer = WriteupDecomposer(api_key=self.api_key)
            if not self.trajectory_decomposer:
                self.trajectory_decomposer = TrajectoryDecomposer(api_key=self.api_key)
            if not self.step_matcher:
                self.step_matcher = StepMatcher(api_key=self.api_key, outputs_dir=self.outputs_dir)
        except ValueError as e:
            self.error_handler.log_error(
                error_type=ErrorType.AGENT_INITIALIZATION.name,
                component=ComponentType.ORCHESTRATOR,
                challenge_name="system",
                description="Failed to initialize agents",
                details=str(e),
            )
            raise
        except Exception as e:
            self.error_handler.log_error(
                error_type=ErrorType.AGENT_INITIALIZATION.name,
                component=ComponentType.ORCHESTRATOR, 
                challenge_name="system",
                description="Unexpected error during agent initialization",
                details=str(e),
            )
            raise
    
    def validate_files(self) -> list:
        if not os.path.exists(self.writeups_dir):
            self.error_handler.log_error(
                error_type=ErrorType.DIRECTORY_MISSING.name,
                component=ComponentType.FILE_VALIDATION,
                challenge_name="system",
                description=f"Writeups directory not found: {self.writeups_dir}",
                details="",
            )
            return []
            
        if not os.path.exists(self.trajs_dir):
            self.error_handler.log_error(
                error_type=ErrorType.DIRECTORY_MISSING.name,
                component=ComponentType.FILE_VALIDATION,
                challenge_name="system",
                description=f"Trajectories directory not found: {self.trajs_dir}",
                details="",
            )
            return []
        
        writeup_files = [f for f in os.listdir(self.writeups_dir) if f.endswith('.txt')]
        trajectory_files = [f for f in os.listdir(self.trajs_dir) if f.endswith('.json')]
        
        if not writeup_files:
            self.error_handler.log_error(
                error_type=ErrorType.NO_FILES.name,
                component=ComponentType.FILE_VALIDATION,
                challenge_name="system",
                description="No .txt writeup files found",
                details=f"Directory: {self.writeups_dir}",
            )
        
        if not trajectory_files:
            self.error_handler.log_error(
                error_type=ErrorType.NO_FILES.name,
                component=ComponentType.FILE_VALIDATION,
                challenge_name="system",
                description="No .json trajectory files found",
                details=f"Directory: {self.trajs_dir}",
            )
        
        self.error_handler.log_file_mismatch(writeup_files, trajectory_files)
        
        # Validate (writeup.txt, traj.json) pair and check file sizes
        valid_pairs = []
        for writeup_file in writeup_files:
            base_name = writeup_file.replace('.txt', '')
            trajectory_file = f'{base_name}.json'
            
            writeup_path = os.path.join(self.writeups_dir, writeup_file)
            trajectory_path = os.path.join(self.trajs_dir, trajectory_file)
            
            if os.path.exists(trajectory_path):
                if os.path.getsize(writeup_path) == 0:
                    self.error_handler.log_empty_file(writeup_path, "writeup")
                    continue
                    
                if os.path.getsize(trajectory_path) == 0:
                    self.error_handler.log_empty_file(trajectory_path, "trajectory")
                    continue
                
                valid_pairs.append((base_name, writeup_path, trajectory_path))
        
        return valid_pairs
    
    def run_agent1(self, writeup_path, base_name):
        print(f"- Agent 1: Analyzing writeup for {base_name}...")
        
        try:
            summary = self.writeup_decomposer.generate_summary(writeup_path)
            
            version, output_path, _ = self.version_manager.get_versioned_filename(
                base_name, 'writeup_summary'
            )
            
            self.writeup_decomposer.save_summary(summary, output_path)
            
            print(f"   [*] Found {summary['total_steps']} steps in writeup (v{version})")
            return output_path, summary
            
        except Exception as e:
            self.error_handler.log_api_error(ComponentType.WRITEUP_SUMMARY_AGENT, base_name, e)
            raise
    
    def run_agent2(self, trajectory_path, base_name):
        print(f"- Agent 2: Analyzing trajectory for {base_name}...")
        
        try:
            summary = self.trajectory_decomposer.generate_summary(trajectory_path)
            
            version, output_path, _ = self.version_manager.get_versioned_filename(
                base_name, 'trajectory_summary'
            )
            
            self.trajectory_decomposer.save_summary(summary, output_path)
            self.error_handler.log_challenge_failure(
                base_name, summary.get('success', False), summary.get('exit_reason', 'unknown')
            )
            
            success_icon = "[*]" if summary['success'] else "[X]"
            print(f"   {success_icon} Found {summary['total_steps']} steps in trajectory (v{version})")
            print(f"   {'[*]' if summary['success'] else '[X]'} Challenge was {'solved' if summary['success'] else 'not solved'}")
            print(f"   -  Time taken: {summary['time_taken']:.2f}s")
            
            return output_path, summary
            
        except Exception as e:
            self.error_handler.log_api_error(ComponentType.TRAJECTORY_SUMMARY_AGENT, base_name, e)
            raise
    
    def run_agent3(self, writeup_summary_path, trajectory_summary_path, base_name):
        print(f"-️  Agent 3: Conducting qualitative analysis for {base_name}...")
        try:
            evaluation = self.step_matcher.evaluate_challenge(
                writeup_summary_path, trajectory_summary_path
            )
            
            version, json_path, md_path = self.version_manager.get_versioned_filename(
                base_name, 'qualitative_evaluation', 'md'
            )
            
            self.step_matcher.save_evaluation(evaluation, self.evaluations_dir)

            default_json = os.path.join(self.evaluations_dir, f'{base_name}_qualitative_evaluation.json')
            default_md = os.path.join(self.evaluations_dir, f'{base_name}_qualitative_report.md')
            
            if os.path.exists(default_json):
                os.rename(default_json, json_path)
            if os.path.exists(default_md):
                os.rename(default_md, md_path)
            
            flag_status = "[*]" if evaluation.overall_score > 0.5 else "[X]"
            solved_status = "[*] Solved" if getattr(evaluation, 'challenge_solved', True) else "[X] Failed"
            
            print(f"   {flag_status} Overall Score: {evaluation.overall_score:.2%} (v{version})")
            
            # Show formula breakdown
            if evaluation.formula_breakdown is not None:
                print(f"   Formula Score Breakdown Available")
            
            print(f"   Challenge Status: {solved_status}")
            print(f"   Vulnerability Understanding: {evaluation.competency_matrix.vulnerability_understanding}")
            print(f"   Exploitation Methodology: {evaluation.competency_matrix.exploitation_methodology}")
            print(f"   Technical Accuracy: {evaluation.competency_matrix.technical_accuracy}")
            
            return evaluation
            
        except Exception as e:
            self.error_handler.log_api_error(ComponentType.QUALITATIVE_EVALUATION_AGENT, base_name, e)
            raise
    
    def run_full_evaluation(self, challenge_name=None):

        print("CTFJUDGE v1.0")
        print("=================================================================")
        
        try:
            self._initialize_agents()
        except Exception:
            return  
        
        pairs = self.validate_files()
        
        if not pairs:
            print("[X] No valid challenge pairs found!")
            return
        
        if challenge_name:
            pairs = [(name, wp, tp) for name, wp, tp in pairs if name == challenge_name]
            if not pairs:
                self.error_handler.log_error(
                    error_type=ErrorType.CHALLENGE_NOT_FOUND.name,
                    component=ComponentType.ORCHESTRATOR,
                    challenge_name=challenge_name,
                    description=f"Challenge '{challenge_name}' not found",
                    details=f"Available challenges: {[name for name, _, _ in self.validate_files()]}",
                    )
                return
        
        print(f"Found {len(pairs)} valid challenge pair(s) to evaluate")
        print()
        
        evaluations = []
        start_time = time.time()
        
        for i, (base_name, writeup_path, trajectory_path) in enumerate(pairs, 1):
            print(f"Processing Challenge {i}/{len(pairs)}: {base_name}")
            print("-------------------------------------------------------")
            
            try:
                writeup_summary_path, writeup_summary = self.run_agent1(writeup_path, base_name)
                
                trajectory_summary_path, trajectory_summary = self.run_agent2(trajectory_path, base_name)
                
                evaluation = self.run_agent3(
                    writeup_summary_path, trajectory_summary_path, base_name
                )
                
                evaluations.append((base_name, evaluation, writeup_summary, trajectory_summary))
                print(f"[*] Completed evaluation for {base_name}")
                
            except Exception as e:
                self.error_handler.log_error(
                    error_type=ErrorType.EVALUATION_FAILED.name,
                    component=ComponentType.ORCHESTRATOR,
                    challenge_name=base_name,
                    description=f"Failed to complete evaluation for {base_name}",
                    details=str(e),
                )
                continue
            
            print()
        
        total_time = time.time() - start_time
        
        # Print summary
        if evaluations:
            self._print_enhanced_summary(evaluations, total_time)
        
        
        session_summary = self.error_handler.generate_session_summary()
        
        print(f"\n▣ Results saved to:")
        print(f"   - Summaries: {self.outputs_dir}/")
        print(f"   - Evaluations: {self.evaluations_dir}/")
        print(f"   - Errors: {self.errors_dir}/")
        print(f"   - Session summary: {session_summary}")
        
       
        self._save_comprehensive_summary(evaluations, total_time)
    
    def _save_comprehensive_summary(self, evaluations, total_time):
    
        if len(evaluations) == 1:
            challenge_name = evaluations[0][0]  # Single challenge
            filename = f"comprehensive_summary_{challenge_name}.txt"
        else:
            filename = f"comprehensive_summary_batch_{len(evaluations)}challenges.txt"
        
    
        filepath = os.path.join(self.version_manager.session_evaluations_dir, filename)
        
        summary_content = []
        summary_content.append("COMPREHENSIVE EVALUATION SUMMARY")
        summary_content.append("=================================================================================")
        summary_content.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        summary_content.append(f"Total Challenges: {len(evaluations)}")
        summary_content.append(f"Total Time: {total_time:.1f}s")
        summary_content.append("")
        
        # Summary table
        summary_content.append(f"{'Challenge':<25} | {'Score':<8} | {'Solved':<8} | {'Vuln Und':<12} | {'Exploit Meth':<12}")
        summary_content.append("--------------------------------------------------------------------------------")
        
        total_score = 0
        solved_count = 0
        
        for base_name, evaluation, writeup_summary, trajectory_summary in evaluations:
            score_str = f"{evaluation.overall_score:.1%}"
            solved = trajectory_summary.get('success', False)
            solved_str = "[*] Yes" if solved else "[X] No"
            if solved:
                solved_count += 1
            
            vuln_understanding = evaluation.competency_matrix.vulnerability_understanding[:12]
            exploitation = evaluation.competency_matrix.exploitation_methodology[:12]
            
            summary_content.append(f"{base_name:<25} | {score_str:<8} | {solved_str:<8} | {vuln_understanding:<12} | {exploitation:<12}")
            total_score += evaluation.overall_score
        
        summary_content.append("--------------------------------------------------------------------------------")
        avg_score = total_score / len(evaluations) if evaluations else 0
        avg_score_str = f"{avg_score:.1%}"
        solve_rate_str = f"{solved_count}/{len(evaluations)}"
        summary_content.append(f"{'AVERAGE/TOTALS':<25} | {avg_score_str:<8} | {solve_rate_str:<8} | {'Time:':<12} | {total_time:.1f}s")
        
        summary_content.append("")
        summary_content.append("- DETAILED INSIGHTS:")
        
        # Performance distribution
        excellent = sum(1 for _, eval, _, _ in evaluations if eval.overall_score >= 0.8)
        good = sum(1 for _, eval, _, _ in evaluations if 0.6 <= eval.overall_score < 0.8)
        fair = sum(1 for _, eval, _, _ in evaluations if 0.4 <= eval.overall_score < 0.6)
        poor = sum(1 for _, eval, _, _ in evaluations if eval.overall_score < 0.4)
        
        summary_content.append(f"   [█████] Excellent (≥80%): {excellent} challenges")
        summary_content.append(f"   [████░] Good (60-79%):    {good} challenges") 
        summary_content.append(f"   [███░░] Fair (40-59%):    {fair} challenges")
        summary_content.append(f"   [█░░░░] Poor (<40%):      {poor} challenges")
        
        solve_rate = (solved_count / len(evaluations)) * 100 if evaluations else 0
        summary_content.append("")
        summary_content.append("▣ Challenge Completion Analysis:")
        summary_content.append(f"   Success Rate: {solve_rate:.1f}% ({solved_count}/{len(evaluations)})")
        
        # Error summary
        error_counts = self.error_handler.generate_session_summary()
        if error_counts['total_errors'] > 0:
            summary_content.append("")
            summary_content.append(f"️[X] Session Errors: {error_counts['total_errors']} total")
        
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(summary_content))
        
        print(f"   - Comprehensive summary: {filepath}")
    
    def _print_enhanced_summary(self, evaluations, total_time):
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        summary_lines = []
        summary_lines.append("COMPREHENSIVE EVALUATION SUMMARY")
        summary_lines.append("=================================================================================")
        
        print("COMPREHENSIVE EVALUATION SUMMARY")
        print("=================================================================================")
        
        # Summary table
        print(f"{'Challenge':<25} | {'Score':<8} | {'Solved':<8} | {'Vuln':<12} | {'Exploit':<12}")
        print("--------------------------------------------------------------------------------")
        
        total_score = 0
        solved_count = 0
        
        for base_name, evaluation, writeup_summary, trajectory_summary in evaluations:
            score_str = f"{evaluation.overall_score:.1%}"
            solved = trajectory_summary.get('success', False)
            solved_str = "[*] Yes" if solved else "[X] No"
            if solved:
                solved_count += 1
            
            vuln_understanding = evaluation.competency_matrix.vulnerability_understanding[:12]
            exploitation = evaluation.competency_matrix.exploitation_methodology[:12]
            
            print(f"{base_name:<25} | {score_str:<8} | {solved_str:<8} | {vuln_understanding:<12} | {exploitation:<12}")
            total_score += evaluation.overall_score
        
        print("--------------------------------------------------------------------------------")
        avg_score = total_score / len(evaluations) if evaluations else 0
        avg_score_str = f"{avg_score:.1%}"
        solve_rate_str = f"{solved_count}/{len(evaluations)}"
        print(f"{'AVERAGE/TOTALS':<25} | {avg_score_str:<8} | {solve_rate_str:<8} | {'Time:':<12} | {total_time:.1f}s")
        
        print("\n- DETAILED INSIGHTS:")
        
        # Performance distribution
        excellent = sum(1 for _, eval, _, _ in evaluations if eval.overall_score >= 0.8)
        good = sum(1 for _, eval, _, _ in evaluations if 0.6 <= eval.overall_score < 0.8)
        fair = sum(1 for _, eval, _, _ in evaluations if 0.4 <= eval.overall_score < 0.6)
        poor = sum(1 for _, eval, _, _ in evaluations if eval.overall_score < 0.4)
        
        print(f"   [██████] Excellent (≥80%): {excellent} challenges")
        print(f"   [████░░] Good (60-79%):    {good} challenges") 
        print(f"   [███░░░] Fair (40-59%):    {fair} challenges")
        print(f"   [█░░░░░] Poor (<40%):      {poor} challenges")
        
        # Challenge completion analysis
        solve_rate = (solved_count / len(evaluations)) * 100 if evaluations else 0
        print(f"\n▣ Challenge Completion Analysis:")
        print(f"   Success Rate: {solve_rate:.1f}% ({solved_count}/{len(evaluations)})")
        
        # Error summary
        error_counts = self.error_handler.generate_session_summary()
        if error_counts['total_errors'] > 0:
            print(f"\n⚠️  Session Errors: {error_counts['total_errors']} total")
        


def main():
    parser = argparse.ArgumentParser(
        description='CTFJudge v1.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        '--challenge', '-c',
        help='Evaluate specific challenge by name (without file extension)'
    )
    
    
    parser.add_argument(
        '--writeups-dir',
        default='writeups',
        help='Directory containing writeup files (default: writeups)'
    )
    
    parser.add_argument(
        '--trajs-dir', 
        default='trajs',
        help='Directory containing trajectory files (default: trajs)'
    )
    
    parser.add_argument(
        '--outputs-dir',
        default='outputs', 
        help='Directory for intermediate outputs (default: outputs)'
    )
    
    parser.add_argument(
        '--evaluations-dir',
        default='evaluations',
        help='Directory for final evaluations (default: evaluations)'
    )
    
    parser.add_argument(
        '--errors-dir',
        default='errors',
        help='Directory for error logs (default: errors)'
    )
    
    
    
    args = parser.parse_args()
    
    orchestrator = EnhancedEvaluationOrchestrator(
        writeups_dir=args.writeups_dir,
        trajs_dir=args.trajs_dir,
        outputs_dir=args.outputs_dir,
        evaluations_dir=args.evaluations_dir,
        errors_dir=args.errors_dir
    )
    
    try:
        orchestrator.run_full_evaluation(args.challenge)
    except KeyboardInterrupt:
        print("\n[X] Evaluation interrupted by user")
        orchestrator.error_handler.generate_session_summary()
        sys.exit(1)
    except Exception as e:
        print(f"[X] Unexpected error: {str(e)}")
        orchestrator.error_handler.log_error(
            error_type=ErrorType.SYSTEM_ERROR.name,
            component=ComponentType.MAIN,
            challenge_name="system",
            description="Unexpected system error",
            details=str(e)
        )
        orchestrator.error_handler.generate_session_summary()
        sys.exit(1)


if __name__ == "__main__":
    main()