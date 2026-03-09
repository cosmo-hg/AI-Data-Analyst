#!/usr/bin/env python3
"""
Evaluation Script for AI Data Analyst
Runs test cases and calculates performance metrics.
"""

import sys
import json
import re
import time
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from orchestrator.core import DataAnalystOrchestrator
from data.data_loader import load_uploaded_file

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a single test case."""
    test_id: int
    question: str
    category: str
    difficulty: str
    passed: bool
    execution_time: float
    sql_generated: Optional[str] = None
    answer: Optional[str] = None
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationMetrics:
    """Overall evaluation metrics."""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    
    # By category
    category_results: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # By difficulty
    difficulty_results: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Timing
    total_time: float = 0.0
    avg_response_time: float = 0.0
    
    # Specific metrics
    sql_execution_accuracy: float = 0.0
    intent_classification_accuracy: float = 0.0
    answer_accuracy: float = 0.0
    
    def calculate(self, results: List[TestResult]):
        """Calculate metrics from test results."""
        self.total_tests = len(results)
        self.passed_tests = sum(1 for r in results if r.passed)
        self.failed_tests = self.total_tests - self.passed_tests
        
        # Calculate by category
        for r in results:
            if r.category not in self.category_results:
                self.category_results[r.category] = {"passed": 0, "failed": 0}
            if r.passed:
                self.category_results[r.category]["passed"] += 1
            else:
                self.category_results[r.category]["failed"] += 1
        
        # Calculate by difficulty
        for r in results:
            if r.difficulty not in self.difficulty_results:
                self.difficulty_results[r.difficulty] = {"passed": 0, "failed": 0}
            if r.passed:
                self.difficulty_results[r.difficulty]["passed"] += 1
            else:
                self.difficulty_results[r.difficulty]["failed"] += 1
        
        # Timing
        self.total_time = sum(r.execution_time for r in results)
        self.avg_response_time = self.total_time / max(1, self.total_tests)
        
        # Overall accuracy
        if self.total_tests > 0:
            self.sql_execution_accuracy = self.passed_tests / self.total_tests
            self.answer_accuracy = self.passed_tests / self.total_tests


class Evaluator:
    """Evaluates the AI Data Analyst system."""
    
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.orchestrator: Optional[DataAnalystOrchestrator] = None
        self.results: List[TestResult] = []
        self.metrics = EvaluationMetrics()
    
    def load_test_data(self, test_file: str, data_file: str) -> Dict:
        """Load test dataset and initialize with data file."""
        # Load test cases
        with open(test_file, 'r') as f:
            test_data = json.load(f)
        
        # Load data file
        with open(data_file, 'rb') as f:
            file_content = f.read()
        
        db_path, schema_desc, schema_dict = load_uploaded_file(
            file_content,
            Path(data_file).name,
            table_name="data"
        )
        
        # Initialize orchestrator
        self.orchestrator = DataAnalystOrchestrator(
            model_name=self.model_name,
            db_path=db_path,
            custom_schema=schema_desc
        )
        
        logger.info(f"Loaded {len(test_data['test_cases'])} test cases")
        logger.info(f"Data file: {data_file}")
        logger.info(f"Schema: {schema_dict['row_count']} rows")
        
        return test_data
    
    def run_single_test(self, test_case: Dict) -> TestResult:
        """Run a single test case."""
        test_id = test_case['id']
        question = test_case['question']
        category = test_case['category']
        difficulty = test_case['difficulty']
        validation_type = test_case['validation_type']
        
        logger.info(f"Test {test_id}: {question}")
        
        start_time = time.time()
        
        try:
            # Run the query
            result = self.orchestrator.process_query(question)
            execution_time = time.time() - start_time
            
            sql = result.get('sql')
            answer = result.get('answer', '')
            error = result.get('error')
            rows = result.get('rows', [])
            intent = result.get('intent', {})
            
            # Validate based on type
            passed = False
            details = {}
            
            if validation_type == "row_count":
                expected_count = test_case.get('expected_row_count', 0)
                actual_count = len(rows) if rows else 0
                passed = actual_count == expected_count
                details = {"expected_rows": expected_count, "actual_rows": actual_count}
            
            elif validation_type == "answer_contains":
                expected_values = test_case.get('expected_answer_contains', [])
                passed = any(val in answer for val in expected_values)
                details = {"expected_contains": expected_values, "answer": answer[:200]}
            
            elif validation_type == "execution_success":
                passed = error is None and sql is not None
                # Also check SQL pattern if provided
                if passed and 'expected_sql_pattern' in test_case:
                    pattern = test_case['expected_sql_pattern']
                    passed = bool(re.search(pattern, sql or '', re.IGNORECASE))
                details = {"sql": sql, "error": error}
            
            elif validation_type == "intent_classification":
                expected_intent = test_case.get('expected_intent', 'unsupported')
                actual_intent = intent.get('intent', 'unknown') if isinstance(intent, dict) else 'unknown'
                # For unsupported questions, we expect no SQL execution or an error
                if expected_intent == 'unsupported':
                    passed = actual_intent == 'unsupported' or 'sorry' in answer.lower() or "can't" in answer.lower()
                details = {"expected_intent": expected_intent, "actual_intent": actual_intent}
            
            return TestResult(
                test_id=test_id,
                question=question,
                category=category,
                difficulty=difficulty,
                passed=passed,
                execution_time=execution_time,
                sql_generated=sql,
                answer=answer[:500] if answer else None,
                error=error,
                details=details
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_id=test_id,
                question=question,
                category=category,
                difficulty=difficulty,
                passed=False,
                execution_time=execution_time,
                error=str(e)
            )
    
    def run_all_tests(self, test_data: Dict) -> List[TestResult]:
        """Run all test cases."""
        self.results = []
        
        for test_case in test_data['test_cases']:
            result = self.run_single_test(test_case)
            self.results.append(result)
            
            status = "✅ PASS" if result.passed else "❌ FAIL"
            logger.info(f"  {status} ({result.execution_time:.2f}s)")
            
            # Add delay to avoid rate limiting
            time.sleep(1)
        
        # Calculate metrics
        self.metrics.calculate(self.results)
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate evaluation report."""
        lines = []
        lines.append("=" * 60)
        lines.append("AI DATA ANALYST - EVALUATION REPORT")
        lines.append("=" * 60)
        lines.append(f"\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Model: {self.model_name}")
        
        # Overall Results
        lines.append("\n" + "-" * 40)
        lines.append("OVERALL RESULTS")
        lines.append("-" * 40)
        lines.append(f"Total Tests:    {self.metrics.total_tests}")
        lines.append(f"Passed:         {self.metrics.passed_tests}")
        lines.append(f"Failed:         {self.metrics.failed_tests}")
        lines.append(f"Accuracy:       {self.metrics.sql_execution_accuracy:.1%}")
        lines.append(f"Avg Time:       {self.metrics.avg_response_time:.2f}s")
        
        # Results by Category
        lines.append("\n" + "-" * 40)
        lines.append("RESULTS BY CATEGORY")
        lines.append("-" * 40)
        for category, counts in sorted(self.metrics.category_results.items()):
            total = counts['passed'] + counts['failed']
            accuracy = counts['passed'] / max(1, total)
            lines.append(f"{category:20} {counts['passed']}/{total} ({accuracy:.0%})")
        
        # Results by Difficulty
        lines.append("\n" + "-" * 40)
        lines.append("RESULTS BY DIFFICULTY")
        lines.append("-" * 40)
        for difficulty, counts in sorted(self.metrics.difficulty_results.items()):
            total = counts['passed'] + counts['failed']
            accuracy = counts['passed'] / max(1, total)
            lines.append(f"{difficulty:20} {counts['passed']}/{total} ({accuracy:.0%})")
        
        # Failed Tests
        failed = [r for r in self.results if not r.passed]
        if failed:
            lines.append("\n" + "-" * 40)
            lines.append("FAILED TESTS")
            lines.append("-" * 40)
            for r in failed:
                lines.append(f"\nTest {r.test_id}: {r.question}")
                lines.append(f"  Category: {r.category}")
                lines.append(f"  Error: {r.error or 'Validation failed'}")
                if r.details:
                    lines.append(f"  Details: {r.details}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
    
    def save_results(self, output_dir: str):
        """Save results to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save detailed results as JSON
        results_data = {
            "metadata": {
                "model": self.model_name,
                "timestamp": datetime.now().isoformat(),
                "total_tests": self.metrics.total_tests,
                "passed": self.metrics.passed_tests,
                "accuracy": self.metrics.sql_execution_accuracy
            },
            "results": [
                {
                    "test_id": r.test_id,
                    "question": r.question,
                    "category": r.category,
                    "difficulty": r.difficulty,
                    "passed": r.passed,
                    "execution_time": r.execution_time,
                    "sql": r.sql_generated,
                    "answer": r.answer,
                    "error": r.error,
                    "details": r.details
                }
                for r in self.results
            ]
        }
        
        results_file = output_path / f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        # Save report
        report = self.generate_report()
        report_file = output_path / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Results saved to: {results_file}")
        logger.info(f"Report saved to: {report_file}")
        
        return results_file, report_file


def main():
    """Run evaluation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate AI Data Analyst")
    parser.add_argument(
        "--model", 
        default="gemini-2.5-flash",
        help="Model to evaluate"
    )
    parser.add_argument(
        "--test-file",
        default=str(PROJECT_ROOT / "evaluation" / "test_dataset.json"),
        help="Path to test dataset JSON"
    )
    parser.add_argument(
        "--data-file",
        help="Path to data file (CSV/Excel) to test against"
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "evaluation" / "results"),
        help="Output directory for results"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Limit number of tests to run (for free tier, default: 5)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=3.0,
        help="Delay between tests in seconds (default: 3.0 for rate limiting)"
    )
    
    args = parser.parse_args()
    
    # Find data file - check multiple locations
    data_file = None
    if args.data_file:
        possible_paths = [
            Path(args.data_file),
            PROJECT_ROOT / args.data_file,
            Path.home() / "Desktop" / args.data_file,
            PROJECT_ROOT / "data" / args.data_file,
        ]
        for p in possible_paths:
            if p.exists():
                data_file = p
                break
        
        if not data_file:
            print(f"❌ Data file not found: {args.data_file}")
            print("Searched in:")
            for p in possible_paths:
                print(f"  - {p}")
            return
    else:
        # Look for any xlsx/csv in common locations
        for pattern in ["*.xlsx", "*.csv"]:
            files = list(PROJECT_ROOT.glob(pattern))
            if files:
                data_file = files[0]
                break
            files = list((PROJECT_ROOT / "data").glob(pattern))
            if files:
                data_file = files[0]
                break
        
        if not data_file:
            print("❌ No data file specified and none found automatically.")
            print("Usage: python evaluation/evaluate.py --data-file 'path/to/file.xlsx'")
            return
    
    print("\n" + "=" * 60)
    print("AI DATA ANALYST - EVALUATION")
    print("=" * 60)
    print(f"Model: {args.model}")
    print(f"Test file: {args.test_file}")
    print(f"Data file: {data_file}")
    print(f"Test limit: {args.limit} (use --limit to change)")
    print(f"Delay: {args.delay}s between tests")
    print("=" * 60 + "\n")
    
    # Run evaluation
    evaluator = Evaluator(model_name=args.model)
    
    try:
        test_data = evaluator.load_test_data(args.test_file, str(data_file))
        
        # Limit tests for free tier
        if args.limit and args.limit < len(test_data['test_cases']):
            print(f"⚠️  Running only {args.limit} tests (free tier mode)")
            print(f"   Use --limit 20 to run all tests\n")
            test_data['test_cases'] = test_data['test_cases'][:args.limit]
        
        # Override delay
        original_run = evaluator.run_single_test
        
        def run_with_delay(test_case):
            result = original_run(test_case)
            time.sleep(args.delay)  # Rate limit delay
            return result
        
        evaluator.run_single_test = run_with_delay
        evaluator.run_all_tests(test_data)
        
        # Print report
        print("\n" + evaluator.generate_report())
        
        # Save results
        evaluator.save_results(args.output_dir)
        
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print("\n❌ Rate limit hit! Try:")
            print("   1. Wait a few minutes and try again")
            print("   2. Use --limit 3 to run fewer tests")
            print("   3. Use a different model: --model gemini-2.5-pro")
        else:
            logger.error(f"Evaluation failed: {e}")
            raise


if __name__ == "__main__":
    main()
