# Evaluation results

| Experiment | k | n | Recall@k | Hit-all@k | MRR | Exec acc | Easy | Medium | Hard | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline-retrieval | 4 | 40 | 0.962 | 0.900 | 0.988 | - | - | - | - | dense only, n_chunks=10 |
| baseline | 4 | 40 | 0.962 | 0.900 | 0.988 | 97.5% | 100.0% | 100.0% | 90.0% | dense k=4, schema-only prompt, explain off |
