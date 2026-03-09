# Evaluation Framework

This directory contains the evaluation framework for the AI Data Analyst.

## Files

- `test_dataset.json` - Test cases with expected behaviors
- `evaluate.py` - Evaluation script
- `results/` - Output directory for evaluation results

## Usage

Run evaluation against your data file:

```bash
python evaluation/evaluate.py --data-file "path/to/your/data.xlsx"
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--model` | Gemini model to evaluate | `gemini-2.5-flash` |
| `--test-file` | Path to test dataset | `evaluation/test_dataset.json` |
| `--data-file` | Path to data file (required) | - |
| `--output-dir` | Output directory | `evaluation/results` |

### Example

```bash
# Evaluate with student data
python evaluation/evaluate.py \
  --model gemini-3-flash-preview \
  --data-file "JEE - Prep Students - 2022.xlsx"
```

## Test Categories

| Category | Description |
|----------|-------------|
| `simple_lookup` | Basic SELECT queries |
| `filter_query` | WHERE clause queries |
| `aggregation` | COUNT, SUM, AVG queries |
| `unique_values` | DISTINCT queries |
| `pattern_match` | LIKE/pattern queries |
| `ordering` | ORDER BY queries |
| `complex_query` | Multi-condition queries |
| `unsupported` | Questions that should be rejected |

## Metrics Calculated

1. **Overall Accuracy** - % of tests passed
2. **Category Accuracy** - Accuracy per query type
3. **Difficulty Accuracy** - Accuracy by easy/medium/hard
4. **Response Time** - Average time per query
5. **Error Rate** - % of queries with errors

## Output

The evaluation generates:
- `results_YYYYMMDD_HHMMSS.json` - Detailed results
- `report_YYYYMMDD_HHMMSS.txt` - Human-readable report
