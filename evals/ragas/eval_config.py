"""
RAGAS Evaluation Framework for Portfolio Intelligence Hub RAG Pipeline
Evaluates the Retrieval-Augmented Generation pipeline for real estate analytics queries.

This module provides comprehensive evaluation of the RAG system using RAGAS metrics:
- Faithfulness: How much the generated answer is grounded in the retrieved context
- Answer Relevancy: How relevant the generated answer is to the input question
- Context Precision: What fraction of the retrieved context is relevant to the question
- Context Recall: How much of the ground truth facts are covered in the retrieved context
- Context Entity Recall: How many relevant entities are captured in the context
"""

import json
import sys
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    context_entity_recall,
)
from ragas import evaluate
from datasets import Dataset


@dataclass
class EvaluationThresholds:
    """Quality thresholds for RAG pipeline evaluation."""
    faithfulness_min: float = 0.85
    relevancy_min: float = 0.80
    precision_min: float = 0.75
    recall_min: float = 0.70
    entity_recall_min: float = 0.75


class RAGEvaluator:
    """Evaluates RAG pipeline using RAGAS framework."""
    
    def __init__(self, thresholds: EvaluationThresholds = None):
        """
        Initialize the evaluator with quality thresholds.
        
        Args:
            thresholds: EvaluationThresholds object defining quality metrics
        """
        self.thresholds = thresholds or EvaluationThresholds()
        self.results = {}
        self.test_cases = self._load_test_cases()
    
    def _load_test_cases(self) -> List[Dict[str, Any]]:
        """
        Load evaluation test cases from JSON file.
        
        Returns:
            List of test case dictionaries
        """
        try:
            with open(
                '/sessions/youthful-eager-lamport/mnt/Portfolio/portfolio-intelligence-hub'
                '/evals/ragas/test_cases.json', 'r'
            ) as f:
                return json.load(f)
        except FileNotFoundError:
            print("Warning: test_cases.json not found, using inline test cases")
            return self._get_inline_test_cases()
    
    def _get_inline_test_cases(self) -> List[Dict[str, Any]]:
        """
        Define 20+ evaluation test cases for real estate domain.
        
        Returns:
            List of test case dictionaries with real estate examples
        """
        return [
            {
                "question": "What units are available under $3,000 per month?",
                "answer": "Units 201-A, 305-B, and 412-A in Tower North are available under $3,000/month, with move-in dates in April 2026.",
                "contexts": [
                    "Tower North contains 250 units. Unit 201-A is a 1BR/1BA listed at $2,850/month available April 15, 2026.",
                    "Unit 305-B is a 2BR/1BA listed at $2,950/month available April 1, 2026 in Tower North.",
                    "Unit 412-A is a studio listed at $2,750/month available April 20, 2026 in Tower North.",
                ],
                "ground_truth": "Units under $3,000: 201-A ($2,850), 305-B ($2,950), 412-A ($2,750)"
            },
            {
                "question": "Show NOI trend year-over-year for the last three years.",
                "answer": "NOI has grown YoY: 2023: $2.1M, 2024: $2.45M (+16.7%), 2025: $2.89M (+18.0%)",
                "contexts": [
                    "2023 Net Operating Income: $2,100,000 from 350 leased units",
                    "2024 Net Operating Income: $2,450,000 representing 16.7% YoY growth",
                    "2025 Net Operating Income: $2,890,000 with 18.0% YoY increase",
                ],
                "ground_truth": "YoY NOI growth: 2024 +16.7%, 2025 +18.0%"
            },
            {
                "question": "Which buildings have the most open work orders?",
                "answer": "Tower North has 47 open work orders, Tower South has 32, and East Wing has 18.",
                "contexts": [
                    "Tower North currently has 47 open maintenance work orders requiring attention",
                    "Tower South has 32 pending work orders, mostly HVAC and plumbing related",
                    "East Wing has 18 open work orders, primarily preventive maintenance",
                ],
                "ground_truth": "Open work orders: Tower North 47, Tower South 32, East Wing 18"
            },
            {
                "question": "What is the current occupancy rate by building?",
                "answer": "Tower North: 96.2%, Tower South: 91.5%, East Wing: 88.3%",
                "contexts": [
                    "Tower North: 337 of 350 units occupied (96.2% occupancy)",
                    "Tower South: 293 of 320 units occupied (91.5% occupancy)",
                    "East Wing: 177 of 200 units occupied (88.3% occupancy)",
                ],
                "ground_truth": "Occupancy rates match by building percentages"
            },
            {
                "question": "List all lease expirations in Q2 2026.",
                "answer": "52 leases expire in Q2: April (18), May (17), June (17). Key expirations include Tower North 201-A, Tower South 305-B.",
                "contexts": [
                    "Q2 2026 lease expirations: 18 in April, 17 in May, 17 in June",
                    "April expirations include Unit 201-A, Tower North (1BR/$2,850)",
                    "May expirations include Unit 305-B, Tower South (2BR/$3,200)",
                    "June lease expirations are distributed across all buildings",
                ],
                "ground_truth": "52 total Q2 expirations with distribution 18/17/17"
            },
            {
                "question": "Which tenants have payment issues?",
                "answer": "3 tenants with payment delays: ABC Corp (45 days), XYZ LLC (30 days), Tech Startup Inc (15 days)",
                "contexts": [
                    "ABC Corp (Unit 501) has a 45-day payment delay on March rent",
                    "XYZ LLC (Unit 602) is 30 days past due on current rent",
                    "Tech Startup Inc (Unit 703) has a 15-day payment delay",
                ],
                "ground_truth": "3 tenants with overdue payments ranging 15-45 days"
            },
            {
                "question": "What is the total utility cost for March 2026?",
                "answer": "Total March 2026 utility costs: $87,500 (Electricity: $42,000, Gas: $28,500, Water: $17,000)",
                "contexts": [
                    "March 2026 electricity costs: $42,000 across all buildings",
                    "March 2026 gas costs: $28,500 for heating systems",
                    "March 2026 water/sewer costs: $17,000",
                ],
                "ground_truth": "March utilities total $87,500"
            },
            {
                "question": "Show capital expenditure projects scheduled for Q3 2026.",
                "answer": "4 CapEx projects: Roof replacement Tower North ($450K), HVAC upgrade Tower South ($320K), Parking lot resurfacing ($180K), Lobby renovation ($95K)",
                "contexts": [
                    "Tower North roof replacement project scheduled July 2026 - estimated cost $450,000",
                    "Tower South HVAC system upgrade planned August 2026 - $320,000 budget",
                    "Parking lot resurfacing project - $180,000, scheduled September 2026",
                    "East Wing lobby renovation - $95,000, planned for Q3 2026",
                ],
                "ground_truth": "4 CapEx projects totaling $1,045,000 in Q3"
            },
            {
                "question": "What are the highest and lowest rental rates?",
                "answer": "Highest: Tower North 3BR penthouse at $4,950/month. Lowest: East Wing studio at $1,850/month.",
                "contexts": [
                    "Premium units in Tower North command highest rents, penthouse 3BR at $4,950/month",
                    "Tower South 2BR units average $3,200/month",
                    "East Wing studio units are the most affordable at $1,850/month minimum",
                ],
                "ground_truth": "Rate range: $1,850 (min) to $4,950 (max)"
            },
            {
                "question": "How many units are in each building by bedroom count?",
                "answer": "Tower North: Studios 50, 1BR 100, 2BR 80, 3BR 20. Tower South: Studios 40, 1BR 120, 2BR 140, 3BR 20. East Wing: Studios 80, 1BR 80, 2BR 40.",
                "contexts": [
                    "Tower North inventory: 50 studios, 100 one-bedrooms, 80 two-bedrooms, 20 three-bedrooms",
                    "Tower South units: 40 studios, 120 one-bedrooms, 140 two-bedrooms, 20 three-bedrooms",
                    "East Wing breakdown: 80 studios, 80 one-bedrooms, 40 two-bedrooms",
                ],
                "ground_truth": "Total 870 units distributed by type and building"
            },
            {
                "question": "What is the CAM charge breakdown?",
                "answer": "CAM charges: Insurance 35%, Maintenance 32%, Utilities 25%, Property Tax 8%. Average $185/unit/month.",
                "contexts": [
                    "CAM insurance component: 35% of total CAM charges",
                    "Maintenance services: 32% of CAM allocation",
                    "Utilities embedded in CAM: 25% of charges",
                    "Property tax: 8% of CAM. Average CAM charge: $185/unit/month",
                ],
                "ground_truth": "CAM breakdown percentages and average charge correct"
            },
            {
                "question": "Show lease renewal rates by building.",
                "answer": "Tower North: 84% renewal rate, Tower South: 77% renewal, East Wing: 69% renewal",
                "contexts": [
                    "Tower North maintains strong 84% lease renewal rate",
                    "Tower South lease renewal rate: 77%",
                    "East Wing has lower 69% renewal rate, suggesting retention challenges",
                ],
                "ground_truth": "Renewal rates: TN 84%, TS 77%, EW 69%"
            },
            {
                "question": "What events are scheduled in common areas for April?",
                "answer": "7 events: Fitness class (4/2, 4/9, 4/16, 4/23, 4/30), Tenant networking (4/5), Community cleanup (4/20)",
                "contexts": [
                    "April fitness classes scheduled: Tuesdays 6pm in Tower North gym",
                    "Tenant networking event April 5 in Tower North lobby",
                    "Community cleanup day scheduled April 20",
                ],
                "ground_truth": "7 community events scheduled for April"
            },
            {
                "question": "Which tenants have expiring parking permits?",
                "answer": "8 tenants with expiring permits: 3 in April, 3 in May, 2 in June. Renewal notices sent.",
                "contexts": [
                    "3 parking permits expire in April 2026",
                    "3 additional permits expire in May 2026",
                    "2 permits expire in June 2026. Renewal notices have been distributed.",
                ],
                "ground_truth": "8 total expiring permits across Q2 2026"
            },
            {
                "question": "Show environmental compliance status.",
                "answer": "All buildings compliant: Energy Star certified (Tower North, Tower South), Green Building standards (East Wing), no violations.",
                "contexts": [
                    "Tower North: Energy Star certified, compliant with all EPA standards",
                    "Tower South: Energy Star certified, no environmental violations",
                    "East Wing: Green Building standards certified, full compliance",
                ],
                "ground_truth": "All buildings meet or exceed environmental requirements"
            },
            {
                "question": "What is the average lease term by unit type?",
                "answer": "Studios: 10.2 months avg, 1BR: 11.5 months, 2BR: 12.1 months, 3BR: 12.8 months",
                "contexts": [
                    "Studio units average 10.2 month lease terms",
                    "1-bedroom units: 11.5 month average",
                    "2-bedroom units average 12.1 months",
                    "3-bedroom units: 12.8 month average lease term",
                ],
                "ground_truth": "Average lease terms increase with unit size"
            },
            {
                "question": "List tenants with pet policy violations.",
                "answer": "2 violations: Unit 207 (unauthorized pet), Unit 508 (exceeds weight limit). Both issued warnings.",
                "contexts": [
                    "Unit 207 has unauthorized pet - written warning issued",
                    "Unit 508 tenant has pet exceeding weight policy limits - warning sent",
                ],
                "ground_truth": "2 pet policy violations documented and addressed"
            },
            {
                "question": "What is the multi-family market comparison data?",
                "answer": "Market avg: $3,100/month, Portfolio avg: $2,980/month (-3.9%). Portfolio competitive advantage on pricing.",
                "contexts": [
                    "Regional multi-family market average: $3,100/month",
                    "Our portfolio average: $2,980/month",
                    "Pricing advantage: -3.9% below market, strong competitive position",
                ],
                "ground_truth": "Portfolio underpriced vs market by 3.9%"
            },
            {
                "question": "Show debt service coverage ratio by year.",
                "answer": "2023: 1.45x, 2024: 1.62x, 2025: 1.78x. DSCR improving with NOI growth.",
                "contexts": [
                    "2023 Debt Service Coverage Ratio: 1.45x",
                    "2024 DSCR: 1.62x, showing 11.7% improvement",
                    "2025 DSCR: 1.78x with continued improvement trajectory",
                ],
                "ground_truth": "DSCR trend shows healthy debt servicing capacity"
            },
        ]
    
    def create_eval_dataset(self) -> Dataset:
        """
        Convert test cases to HuggingFace Dataset format for RAGAS evaluation.
        
        Returns:
            Dataset object ready for evaluation
        """
        formatted_data = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": []
        }
        
        for test_case in self.test_cases:
            formatted_data["question"].append(test_case["question"])
            formatted_data["answer"].append(test_case["answer"])
            formatted_data["contexts"].append(test_case["contexts"])
            formatted_data["ground_truth"].append(test_case["ground_truth"])
        
        return Dataset.from_dict(formatted_data)
    
    def run_evaluation(self) -> Dict[str, Any]:
        """
        Run RAGAS evaluation metrics on the test dataset.
        
        Returns:
            Dictionary containing evaluation scores and assessment
        """
        dataset = self.create_eval_dataset()
        
        print("=" * 80)
        print("RAGAS EVALUATION FRAMEWORK - Portfolio Intelligence Hub")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Test Cases: {len(self.test_cases)}")
        print("=" * 80)
        
        try:
            # Run RAGAS evaluation with specified metrics
            results = evaluate(
                dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall,
                    context_entity_recall,
                ]
            )
            
            self.results = results
            return results
        except Exception as e:
            print(f"Error during evaluation: {e}")
            print("Note: Ensure ragas and datasets packages are installed")
            print("Install with: pip install ragas datasets")
            return {}
    
    def run_text_to_sql_accuracy(
        self, 
        generated_sql: str, 
        expected_sql: str
    ) -> Dict[str, Any]:
        """
        Compare generated SQL output against expected SQL for accuracy.
        
        Args:
            generated_sql: SQL generated by the text-to-SQL model
            expected_sql: Expected/ground truth SQL
            
        Returns:
            Dictionary with accuracy metrics
        """
        # Normalize SQL strings for comparison
        gen_normalized = ' '.join(generated_sql.split()).upper()
        exp_normalized = ' '.join(expected_sql.split()).upper()
        
        # Basic exact match
        exact_match = gen_normalized == exp_normalized
        
        # Extract key components for partial scoring
        gen_keywords = set(gen_normalized.split())
        exp_keywords = set(exp_normalized.split())
        
        # Calculate component overlap
        keyword_overlap = len(gen_keywords & exp_keywords) / len(exp_keywords) if exp_keywords else 0
        
        return {
            "exact_match": exact_match,
            "keyword_overlap": keyword_overlap,
            "accuracy_score": keyword_overlap if not exact_match else 1.0
        }
    
    def print_evaluation_report(self):
        """Print formatted evaluation report with metrics and recommendations."""
        if not self.results:
            print("\nNo evaluation results to display. Run evaluation first.")
            return
        
        print("\n" + "=" * 80)
        print("EVALUATION RESULTS SUMMARY")
        print("=" * 80)
        
        # Extract scores
        scores = {}
        for metric_name in ['faithfulness', 'answer_relevancy', 'context_precision', 
                           'context_recall', 'context_entity_recall']:
            if metric_name in self.results:
                scores[metric_name] = self.results[metric_name]
        
        # Print metrics with threshold comparison
        print("\nMetric Scores vs Thresholds:")
        print("-" * 80)
        print(f"{'Metric':<30} {'Score':<10} {'Threshold':<10} {'Status':<10}")
        print("-" * 80)
        
        threshold_map = {
            'faithfulness': self.thresholds.faithfulness_min,
            'answer_relevancy': self.thresholds.relevancy_min,
            'context_precision': self.thresholds.precision_min,
            'context_recall': self.thresholds.recall_min,
            'context_entity_recall': self.thresholds.entity_recall_min,
        }
        
        all_passing = True
        for metric, threshold in threshold_map.items():
            score = scores.get(metric, 0)
            status = "PASS" if score >= threshold else "FAIL"
            if status == "FAIL":
                all_passing = False
            print(f"{metric:<30} {score:<10.3f} {threshold:<10.3f} {status:<10}")
        
        print("-" * 80)
        print(f"Overall Status: {'PASS' if all_passing else 'FAIL'}")
        
        # Recommendations
        print("\nRecommendations:")
        print("-" * 80)
        for metric, threshold in threshold_map.items():
            score = scores.get(metric, 0)
            if score < threshold:
                gap = threshold - score
                print(f"• {metric}: Score {score:.3f} is {gap:.3f} below threshold")
                print(f"  Consider: Improving retrieval quality, refining context, tuning prompts")
        
        print("\n" + "=" * 80)


def main():
    """Main evaluation execution."""
    evaluator = RAGEvaluator()
    
    # Run evaluation
    print("\nInitializing RAGAS evaluation framework...")
    results = evaluator.run_evaluation()
    
    # Print comprehensive report
    evaluator.print_evaluation_report()
    
    # Example SQL evaluation
    print("\nText-to-SQL Evaluation Examples:")
    print("-" * 80)
    
    example_sql = [
        (
            "SELECT * FROM units WHERE rent < 3000",
            "SELECT unit_id, unit_number, rent FROM units WHERE rent < 3000"
        ),
        (
            "SELECT SUM(noi) FROM annual_metrics WHERE year >= 2023",
            "SELECT year, noi FROM annual_metrics WHERE year >= 2023"
        ),
    ]
    
    for generated, expected in example_sql:
        result = evaluator.run_text_to_sql_accuracy(generated, expected)
        print(f"Generated: {generated}")
        print(f"Expected: {expected}")
        print(f"Accuracy: {result['accuracy_score']:.2%}\n")
    
    print("=" * 80)
    print("Evaluation complete. Review results above.")
    print("=" * 80)


if __name__ == "__main__":
    main()
