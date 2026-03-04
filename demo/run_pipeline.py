"""Demo script for Portfolio Intelligence Hub RAG pipeline.

This script demonstrates the text-to-SQL and semantic search capabilities
with sample data and queries for different user personas.
"""

import json
import argparse
import time
from typing import Any, Dict, List
from pathlib import Path
from dataclasses import dataclass


@dataclass
class QueryResult:
    """Represents a query execution result."""

    query: str
    classification: str
    sql_generated: str
    results: List[Dict[str, Any]]
    execution_time: float
    persona: str


class SampleDataLoader:
    """Loader for sample data."""

    def __init__(self, data_path: str):
        """Initialize loader.

        Args:
            data_path: Path to sample_data.json
        """
        self.data_path = data_path
        self.data = None

    def load(self) -> Dict[str, Any]:
        """Load sample data from JSON file.

        Returns:
            Dictionary containing all sample data
        """
        with open(self.data_path, "r") as f:
            self.data = json.load(f)
        return self.data

    def get_properties(self) -> List[Dict[str, Any]]:
        """Get properties data."""
        return self.data.get("properties", [])

    def get_work_orders(self) -> List[Dict[str, Any]]:
        """Get work orders data."""
        return self.data.get("work_orders", [])

    def get_leases(self) -> List[Dict[str, Any]]:
        """Get leases data."""
        return self.data.get("leases", [])

    def get_financial_data(self) -> List[Dict[str, Any]]:
        """Get financial data."""
        return self.data.get("financial_data", [])

    def get_documents(self) -> List[Dict[str, Any]]:
        """Get documents."""
        return self.data.get("documents", [])


class QueryGenerator:
    """Generator for demo queries by persona."""

    @staticmethod
    def generate_demo_queries() -> List[Dict[str, str]]:
        """Generate 20 realistic queries across all personas.

        Returns:
            List of query dictionaries with persona and query text
        """
        return [
            # Property Manager Queries (5)
            {
                "persona": "Property Manager",
                "query": "Which buildings have the most open work orders?",
            },
            {
                "persona": "Property Manager",
                "query": "Show me all units with pending maintenance in my assigned properties",
            },
            {
                "persona": "Property Manager",
                "query": "What is the current occupancy rate for Sunset Apartments?",
            },
            {
                "persona": "Property Manager",
                "query": "List all leases expiring in the next 90 days",
            },
            {
                "persona": "Property Manager",
                "query": "How many work orders are in progress for Harbor Bay?",
            },
            # Broker Queries (5)
            {
                "persona": "Broker",
                "query": "Show me all leases with renewal options",
            },
            {
                "persona": "Broker",
                "query": "Which units are currently vacant and ready for leasing?",
            },
            {
                "persona": "Broker",
                "query": "What are the average rents by unit type across all properties?",
            },
            {
                "persona": "Broker",
                "query": "List all active leases with their renewal deadlines",
            },
            {
                "persona": "Broker",
                "query": "How many 2-bedroom units do we have available for lease?",
            },
            # Finance Queries (5)
            {
                "persona": "Finance",
                "query": "What is the NOI trend for each property over the last quarter?",
            },
            {
                "persona": "Finance",
                "query": "Show me properties with budget variances exceeding 5%",
            },
            {
                "persona": "Finance",
                "query": "Calculate the portfolio-wide cap rate weighted average",
            },
            {
                "persona": "Finance",
                "query": "How much did we spend on maintenance across all properties last month?",
            },
            {
                "persona": "Finance",
                "query": "Show revenue and expense breakdown by property for March 2025",
            },
            # Executive Queries (5)
            {
                "persona": "Executive",
                "query": "What is the total portfolio valuation and average cap rate?",
            },
            {
                "persona": "Executive",
                "query": "Show portfolio occupancy trends over the last 3 months",
            },
            {
                "persona": "Executive",
                "query": "Which properties are underperforming against their cap rate targets?",
            },
            {
                "persona": "Executive",
                "query": "What is the overall portfolio health summary with key metrics?",
            },
            {
                "persona": "Executive",
                "query": "Show the top 3 properties by NOI and top 3 by occupancy rate",
            },
        ]


class TextToSQLSimulator:
    """Simulator for text-to-SQL pipeline."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize simulator.

        Args:
            data: Sample data dictionary
        """
        self.data = data

    def classify_query(self, query: str) -> str:
        """Classify query type.

        Args:
            query: Query string

        Returns:
            Classification (TEXT_TO_SQL or SEMANTIC_SEARCH)
        """
        semantic_keywords = ["lease renewal", "inspection", "condition", "summary"]
        if any(kw in query.lower() for kw in semantic_keywords):
            return "SEMANTIC_SEARCH"
        return "TEXT_TO_SQL"

    def generate_sql(self, query: str) -> str:
        """Generate SQL for query.

        Args:
            query: Query string

        Returns:
            Generated SQL statement
        """
        query_lower = query.lower()

        if "open work order" in query_lower:
            return """
            SELECT p.property_name, COUNT(*) as open_orders,
                   SUM(wo.cost) as total_cost
            FROM work_orders wo
            JOIN properties p ON wo.property_id = p.property_id
            WHERE wo.status = 'open'
            GROUP BY p.property_name
            ORDER BY open_orders DESC
            """

        elif "occupancy" in query_lower:
            return """
            SELECT p.property_name, o.snapshot_date,
                   ROUND(o.occupancy_rate * 100, 1) as occupancy_percentage
            FROM occupancy_data o
            JOIN properties p ON o.property_id = p.property_id
            ORDER BY p.property_name, o.snapshot_date DESC
            """

        elif "noi" in query_lower:
            return """
            SELECT p.property_name, f.month, f.noi, f.budget_variance
            FROM financial_data f
            JOIN properties p ON f.property_id = p.property_id
            ORDER BY p.property_name, f.month DESC
            """

        elif "lease" in query_lower and "renewal" in query_lower:
            return """
            SELECT l.lease_id, p.property_name, u.unit_number,
                   l.tenant_name, l.renewal_option, l.renewal_option_end
            FROM leases l
            JOIN properties p ON l.property_id = p.property_id
            JOIN units u ON l.unit_id = u.unit_id
            WHERE l.renewal_option = true
            ORDER BY l.renewal_option_end ASC
            """

        elif "vacant" in query_lower:
            return """
            SELECT p.property_name, u.unit_number, u.unit_type,
                   u.bedrooms, u.bathrooms, u.rent_monthly
            FROM units u
            JOIN properties p ON u.property_id = p.property_id
            WHERE u.status = 'vacant'
            ORDER BY p.property_name, u.unit_number
            """

        else:
            return "SELECT * FROM properties LIMIT 10"

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute query against sample data.

        Args:
            query: Query string

        Returns:
            Mock results
        """
        query_lower = query.lower()

        if "open work order" in query_lower:
            results = []
            wo_by_prop = {}
            for wo in self.data.get("work_orders", []):
                if wo["status"] == "open":
                    prop_id = wo["property_id"]
                    if prop_id not in wo_by_prop:
                        wo_by_prop[prop_id] = {"orders": 0, "cost": 0}
                    wo_by_prop[prop_id]["orders"] += 1
                    wo_by_prop[prop_id]["cost"] += wo.get("cost", 0)

            for prop in self.data.get("properties", []):
                prop_id = prop["property_id"]
                if prop_id in wo_by_prop:
                    results.append(
                        {
                            "property_name": prop["property_name"],
                            "open_orders": wo_by_prop[prop_id]["orders"],
                            "total_cost": wo_by_prop[prop_id]["cost"],
                        }
                    )
            return sorted(results, key=lambda x: x["open_orders"], reverse=True)

        elif "occupancy" in query_lower:
            return self.data.get("occupancy_data", [])[:5]

        elif "noi" in query_lower:
            return self.data.get("financial_data", [])[:5]

        else:
            return self.data.get("properties", [])[:3]


class SemanticSearchSimulator:
    """Simulator for semantic search pipeline."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize simulator.

        Args:
            data: Sample data dictionary
        """
        self.data = data

    def search(self, query: str) -> Dict[str, Any]:
        """Perform semantic search.

        Args:
            query: Search query

        Returns:
            Search results with answer
        """
        documents = self.data.get("documents", [])
        matching_docs = []

        query_terms = set(query.lower().split())
        for doc in documents:
            doc_terms = set(
                (doc.get("title", "") + " " + doc.get("content", "")).lower().split()
            )
            overlap = len(query_terms & doc_terms)
            if overlap > 0:
                matching_docs.append(
                    {
                        "doc_id": doc["doc_id"],
                        "title": doc["title"],
                        "score": overlap / len(query_terms),
                        "content": doc["content"][:200] + "...",
                    }
                )

        matching_docs = sorted(
            matching_docs, key=lambda x: x["score"], reverse=True
        )[:3]

        answer = f"Based on {len(matching_docs)} relevant documents found, the search results show multiple properties with related information."

        return {
            "query": query,
            "retrieved_chunks": matching_docs,
            "synthesized_answer": answer,
            "confidence": min(1.0, len(matching_docs) * 0.3),
        }


class DemoRunner:
    """Main demo runner."""

    def __init__(self, data_path: str, verbose: bool = False):
        """Initialize demo runner.

        Args:
            data_path: Path to sample_data.json
            verbose: Enable verbose output
        """
        self.data_path = data_path
        self.verbose = verbose
        self.loader = SampleDataLoader(data_path)
        self.data = self.loader.load()
        self.text_to_sql = TextToSQLSimulator(self.data)
        self.semantic_search = SemanticSearchSimulator(self.data)

    def format_sql(self, sql: str) -> str:
        """Format SQL for display.

        Args:
            sql: SQL statement

        Returns:
            Formatted SQL
        """
        return " ".join(sql.split())

    def print_result(self, query_num: int, result: QueryResult) -> None:
        """Print formatted result.

        Args:
            query_num: Query number
            result: Query result
        """
        print(f"\n{'='*80}")
        print(f"Query {query_num}: [{result.persona}]")
        print(f"{'='*80}")
        print(f"\nQuestion: {result.query}")
        print(f"\nClassification: {result.classification}")
        print(f"Execution Time: {result.execution_time:.3f}s")

        if result.classification == "TEXT_TO_SQL":
            print(f"\nGenerated SQL:")
            print("-" * 40)
            print(self.format_sql(result.sql_generated))
            print("-" * 40)

        print(f"\nResults ({len(result.results)} rows):")
        if result.results:
            # Print as markdown table
            headers = list(result.results[0].keys())
            print("| " + " | ".join(headers) + " |")
            print("|" + "|".join(["---"] * len(headers)) + "|")
            for row in result.results[:5]:  # Show first 5 rows
                values = [str(row.get(h, "")) for h in headers]
                print("| " + " | ".join(values) + " |")
            if len(result.results) > 5:
                print(f"... and {len(result.results) - 5} more rows")

    def run_demo(
        self,
        persona_filter: str = None,
        query_filter: str = None,
    ) -> None:
        """Run complete demo.

        Args:
            persona_filter: Filter by persona (optional)
            query_filter: Filter by query keyword (optional)
        """
        print("\n" + "=" * 80)
        print("Portfolio Intelligence Hub - Demo Pipeline")
        print("=" * 80)
        print(f"\nLoaded data:")
        print(f"  - {len(self.data.get('properties', []))} properties")
        print(f"  - {len(self.data.get('units', []))} units")
        print(f"  - {len(self.data.get('leases', []))} leases")
        print(f"  - {len(self.data.get('work_orders', []))} work orders")
        print(f"  - {len(self.data.get('documents', []))} documents")

        queries = QueryGenerator.generate_demo_queries()

        # Filter queries
        if persona_filter:
            queries = [q for q in queries if q["persona"].lower() == persona_filter.lower()]
        if query_filter:
            queries = [q for q in queries if query_filter.lower() in q["query"].lower()]

        print(f"\nRunning {len(queries)} queries...")

        results = []
        for i, query_spec in enumerate(queries, 1):
            query = query_spec["query"]
            persona = query_spec["persona"]

            start_time = time.time()

            # Classify
            classification = self.text_to_sql.classify_query(query)

            # Generate and execute
            if classification == "TEXT_TO_SQL":
                sql = self.text_to_sql.generate_sql(query)
                query_results = self.text_to_sql.execute_query(query)
            else:
                sql = ""
                search_results = self.semantic_search.search(query)
                query_results = [search_results]

            execution_time = time.time() - start_time

            result = QueryResult(
                query=query,
                classification=classification,
                sql_generated=sql,
                results=query_results,
                execution_time=execution_time,
                persona=persona,
            )

            results.append(result)
            self.print_result(i, result)

        # Summary
        print(f"\n{'='*80}")
        print("Summary")
        print(f"{'='*80}")
        print(f"Total queries executed: {len(results)}")
        print(
            f"Average execution time: {sum(r.execution_time for r in results) / len(results):.3f}s"
        )

        text_to_sql_count = sum(
            1 for r in results if r.classification == "TEXT_TO_SQL"
        )
        semantic_count = sum(
            1 for r in results if r.classification == "SEMANTIC_SEARCH"
        )

        print(f"Text-to-SQL queries: {text_to_sql_count}")
        print(f"Semantic search queries: {semantic_count}")

        personas = set(r.persona for r in results)
        print(f"\nQueries by persona:")
        for persona in sorted(personas):
            count = sum(1 for r in results if r.persona == persona)
            print(f"  - {persona}: {count}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Portfolio Intelligence Hub Demo Pipeline"
    )
    parser.add_argument(
        "--data",
        type=str,
        default="sample_data.json",
        help="Path to sample_data.json",
    )
    parser.add_argument(
        "--persona",
        type=str,
        help="Filter by persona (Property Manager, Broker, Finance, Executive)",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Filter by query keyword",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    # Check if data file exists
    if not Path(args.data).exists():
        print(f"Error: Data file not found: {args.data}")
        return

    runner = DemoRunner(args.data, verbose=args.verbose)
    runner.run_demo(persona_filter=args.persona, query_filter=args.query)


if __name__ == "__main__":
    main()
