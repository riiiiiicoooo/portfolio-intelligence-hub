# AI Evaluation Framework - Portfolio Intelligence Hub

This directory contains comprehensive evaluation frameworks for the Portfolio Intelligence Hub's RAG-based analytics pipeline and Text-to-SQL generation system.

## Overview

The evaluation framework consists of two main components:

1. **RAGAS Framework** - Evaluates the Retrieval-Augmented Generation (RAG) pipeline
2. **Promptfoo** - Tests the Text-to-SQL generation prompts against adversarial inputs

## Directory Structure

```
evals/
├── ragas/
│   ├── eval_config.py          # RAGAS evaluation script
│   ├── test_cases.json         # 15 test cases with expected outputs
│   └── README.md
├── promptfoo/
│   ├── promptfooconfig.yaml    # Promptfoo test configuration
│   ├── prompts/
│   │   └── text_to_sql_prompt.txt  # System prompt for SQL generation
│   └── results.json            # Test results (generated)
└── README.md
```

## RAGAS Evaluation

### What is RAGAS?

RAGAS (Retrieval-Augmented Generation Assessment) is a framework for evaluating RAG systems using context-aware metrics without ground truth labels.

### Metrics Evaluated

1. **Faithfulness** (threshold: >= 0.85)
   - Measures how much the generated answer is grounded in retrieved context
   - Ensures responses don't hallucinate information

2. **Answer Relevancy** (threshold: >= 0.80)
   - Evaluates how relevant the generated answer is to the user's question
   - Prevents off-topic responses

3. **Context Precision** (threshold: >= 0.75)
   - Fraction of retrieved context that is relevant to the question
   - Indicates quality of retrieval

4. **Context Recall** (threshold: >= 0.70)
   - What fraction of ground truth facts are covered in retrieved context
   - Ensures completeness of information

5. **Context Entity Recall** (threshold: >= 0.75)
   - Percentage of relevant entities captured in context
   - Validates entity extraction quality

### Running RAGAS Evaluation

#### Installation

```bash
# Install required packages
pip install ragas datasets anthropic python-dotenv

# Set up environment
export ANTHROPIC_API_KEY="your_api_key_here"
```

#### Running the Evaluation

```bash
# Navigate to evals directory
cd evals/ragas

# Run evaluation
python eval_config.py
```

#### Expected Output

The script will:
1. Load 20 test cases from the real estate domain
2. Run RAGAS metrics on each test case
3. Print a comprehensive evaluation report with:
   - Score for each metric
   - Comparison against thresholds
   - Overall pass/fail status
   - Recommendations for improvement

#### Sample Report Output

```
================================================================================
RAGAS EVALUATION FRAMEWORK - Portfolio Intelligence Hub
Timestamp: 2026-03-04T14:30:00
Test Cases: 20
================================================================================

Metric Scores vs Thresholds:
--------------------------------------------------------------------------------
Metric                         Score      Threshold  Status    
--------------------------------------------------------------------------------
faithfulness                   0.872      0.850      PASS      
answer_relevancy               0.815      0.800      PASS      
context_precision              0.763      0.750      PASS      
context_recall                 0.681      0.700      FAIL      
context_entity_recall          0.778      0.750      PASS      
--------------------------------------------------------------------------------
Overall Status: FAIL
```

### Interpreting Results

- **PASS**: All metrics meet or exceed thresholds - RAG pipeline performing well
- **FAIL**: One or more metrics below threshold - indicates areas needing improvement

### Improvement Recommendations

If a metric fails:

- **Low Faithfulness**: Improve prompt to better ground responses in context, review retrieval results
- **Low Answer Relevancy**: Refine retrieval to get more relevant documents, improve prompt clarity
- **Low Context Precision**: Implement better filtering to exclude irrelevant results
- **Low Context Recall**: Improve retrieval algorithm, expand search scope, add more documents
- **Low Entity Recall**: Enhance named entity recognition, improve document indexing

## Promptfoo Evaluation

### What is Promptfoo?

Promptfoo is a framework for systematically testing LLM prompts, including adversarial/red-team testing.

### Test Categories

1. **Functional Tests** (Core functionality)
   - Occupancy rate queries
   - Price filtering
   - Financial trends (NOI, DSCR)
   - Maintenance/operations queries
   - Risk and compliance queries

2. **SQL Correctness Tests**
   - Proper SELECT syntax
   - Correct WHERE clause construction
   - Aggregation with GROUP BY
   - Date filtering and calculations
   - Percentage calculations

3. **Red Team Tests** (Security/robustness)
   - SQL Injection attempts
   - Unauthorized data access
   - PII extraction attempts
   - Out-of-scope queries
   - Ambiguous/tricky queries

### Running Promptfoo Evaluation

#### Installation

```bash
# Install Promptfoo via npm
npm install -g promptfoo

# Ensure API keys are set
export ANTHROPIC_API_KEY="your_key"
export OPENAI_API_KEY="your_key"
```

#### Running Tests

```bash
# Navigate to promptfoo directory
cd evals/promptfoo

# Run all tests
promptfoo eval

# View results in web UI (optional)
promptfoo view

# Export results to JSON
promptfoo eval --output results.json
```

#### Test Structure

Each test case includes:

```yaml
- description: Human-readable test name
  vars:
    user_query: Natural language question
    schema_context: Available tables and columns
  assert:
    - type: contains        # Check if output contains keyword
    - type: javascript      # Custom JS validation
    - type: llm-rubric      # LLM-based evaluation
```

### Assertion Types

1. **contains**: Checks if output includes specific text (e.g., "SELECT", "WHERE")
2. **javascript**: Custom validation logic (e.g., verify operators, check syntax)
3. **llm-rubric**: Uses Claude to evaluate quality based on criteria

### Interpreting Results

Test results are saved to `results.json`. Each test shows:

- **Test name** and description
- **Pass/Fail** status for each provider
- **Assertion details** showing what passed/failed
- **Output** showing the generated SQL

### Example Results Analysis

```json
{
  "description": "Query occupancy rate by building",
  "tests": [
    {
      "provider": "claude-sonnet",
      "pass": true,
      "assertions": [
        { "assertion": "contains 'SELECT'", "pass": true },
        { "assertion": "contains 'building_name'", "pass": true },
        { "assertion": "contains 'COUNT'", "pass": true }
      ]
    }
  ]
}
```

## Best Practices

### For RAGAS Evaluation

1. **Run regularly**: Evaluate after prompt changes or fine-tuning
2. **Track trends**: Monitor metric changes over time
3. **Prioritize metrics**: Focus on metrics most critical to your use case
4. **Test edge cases**: Ensure evaluation covers diverse query types
5. **Document baselines**: Record baseline scores for comparison

### For Promptfoo Testing

1. **Test multiple providers**: Compare Claude vs GPT-4 outputs
2. **Expand red team tests**: Add domain-specific adversarial queries
3. **Monitor regressions**: Ensure new prompts don't break previous functionality
4. **Review failures**: Analyze failed tests to understand model limitations
5. **Iterate on prompts**: Use failures to guide prompt refinement

## Integration with CI/CD

Add to your CI/CD pipeline:

```bash
#!/bin/bash
# run_evaluations.sh

# Install dependencies
pip install ragas datasets anthropic
npm install -g promptfoo

# Run RAGAS evaluation
python evals/ragas/eval_config.py > eval_results.txt
RAGAS_EXIT=$?

# Run Promptfoo evaluation
cd evals/promptfoo
promptfoo eval --output results.json
PROMPTFOO_EXIT=$?

# Fail pipeline if any evaluation fails threshold
if [ $RAGAS_EXIT -ne 0 ] || [ $PROMPTFOO_EXIT -ne 0 ]; then
    echo "Evaluations failed - check results"
    exit 1
fi

echo "All evaluations passed"
exit 0
```

## Test Cases Overview

### RAGAS Test Cases (20 total)

The `test_cases.json` file contains 20 comprehensive real-estate domain test cases:

- **Property Management**: Unit availability, occupancy rates, inventory
- **Financial**: NOI trends, utilities, CAM charges, DSCR
- **Leasing**: Lease expirations, renewals, average terms
- **Operations**: Work orders, parking permits, events
- **Compliance**: Environmental status, pet violations
- **Market Analysis**: Competitive positioning

Each test case includes:
- Unique test ID
- Associated persona (CFO, Property Manager, etc.)
- Natural language question
- Expected answer
- Expected SQL query
- Retrieved contexts
- Ground truth for validation

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'ragas'`
```bash
Solution: pip install ragas datasets
```

**Issue**: `ModuleNotFoundError: No module named 'anthropic'`
```bash
Solution: pip install anthropic
```

**Issue**: API key not found
```bash
Solution: export ANTHROPIC_API_KEY="sk-ant-..."
```

**Issue**: Promptfoo not found
```bash
Solution: npm install -g promptfoo
```

**Issue**: LLM evaluation (llm-rubric) not working
```bash
Solution: Ensure API keys are set and you have proper API access
```

## Contributing

To add new test cases:

1. Add entry to `test_cases.json` with unique test_id
2. Include representative query from real use case
3. Provide diverse contexts simulating RAG retrieval
4. Set realistic thresholds for evaluation
5. Document the test case purpose

## References

- [RAGAS Documentation](https://github.com/explodinggradients/ragas)
- [Promptfoo Documentation](https://www.promptfoo.dev/)
- [Real Estate Analytics Guide](../README.md)

## Support

For issues or questions about the evaluation framework:
1. Check the troubleshooting section above
2. Review RAGAS/Promptfoo official documentation
3. Analyze test case results for specific failures
4. Consult with the data science team for metric interpretation
