# Evaluation results

| Experiment | k | n | Recall@k | Hit-all@k | MRR | Exec acc | Easy | Medium | Hard | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline-retrieval | 4 | 40 | 0.962 | 0.900 | 0.988 | - | - | - | - | dense only, n_chunks=10 |
| baseline | 4 | 40 | 0.962 | 0.900 | 0.988 | 97.5% | 100.0% | 100.0% | 90.0% | dense k=4, schema-only prompt, explain off |
| ret-dense-k1 | 1 | 40 | 0.650 | 0.425 | 0.975 | - | - | - | - | dense, n_chunks=10 |
| ret-dense-k2 | 2 | 40 | 0.834 | 0.675 | 0.988 | - | - | - | - | dense, n_chunks=10 |
| ret-dense-k3 | 3 | 40 | 0.929 | 0.825 | 0.988 | - | - | - | - | dense, n_chunks=10 |
| ret-dense-k5 | 5 | 40 | 0.980 | 0.925 | 0.988 | - | - | - | - | dense, n_chunks=10 |
| ret-dense-k6 | 6 | 40 | 0.990 | 0.975 | 0.988 | - | - | - | - | dense, n_chunks=10 |
| ret-dense-k4-n28 | 4 | 40 | 0.962 | 0.900 | 0.988 | - | - | - | - | dense, n_chunks=28 |
| ret-bm25-k4 | 4 | 40 | 0.884 | 0.750 | 0.821 | - | - | - | - | bm25, n_chunks=10 |
| ret-hybrid-k4 | 4 | 40 | 0.967 | 0.900 | 0.963 | - | - | - | - | hybrid, n_chunks=10 |
| ret-hybrid-k4-n28 | 4 | 40 | 0.962 | 0.900 | 0.963 | - | - | - | - | hybrid, n_chunks=28 |
| ret-dense-k4-fk0.8 | 4 | 40 | 0.962 | 0.900 | 0.988 | - | - | - | - | dense, n_chunks=10, fk-expand boost=0.8 |
| ret-hybrid-k4-n28-fk0.95 | 4 | 40 | 0.970 | 0.925 | 0.963 | - | - | - | - | hybrid, n_chunks=28, fk-expand boost=0.95 |
| gen-strict-k4 | 4 | 40 | 0.962 | 0.900 | 0.988 | 90.0% | 100.0% | 93.3% | 70.0% | dense, n_chunks=10, strict tables, ~1800 prompt chars |
| gen-noschema | 4 | 40 | - | - | - | 55.0% | 20.0% | 86.7% | 60.0% | dense, n_chunks=10, NO schema, ~470 prompt chars |
| gen-nofk-k4 | 4 | 40 | 0.962 | 0.900 | 0.988 | 87.5% | 100.0% | 86.7% | 70.0% | dense, n_chunks=10, no FK hints, ~1660 prompt chars |
| gen-k2 | 2 | 40 | 0.834 | 0.675 | 0.988 | 82.5% | 100.0% | 86.7% | 50.0% | dense, n_chunks=10, ~1217 prompt chars |
| gen-strict-k2 | 2 | 40 | 0.834 | 0.675 | 0.988 | 65.0% | 100.0% | 53.3% | 30.0% | dense, n_chunks=10, strict tables, ~1217 prompt chars |
| gen-strict-nofk-k4 | 4 | 40 | 0.962 | 0.900 | 0.988 | 87.5% | 100.0% | 86.7% | 70.0% | dense, n_chunks=10, no FK hints, strict tables, ~1660 prompt chars |
| gen-retry1 | 4 | 40 | 0.962 | 0.900 | 0.988 | 87.5% | 100.0% | 86.7% | 70.0% | dense, n_chunks=10, no FK hints, strict tables, retries=1, ~1660 prompt chars, 2 retry calls |
| gen-coldesc | 4 | 40 | 0.962 | 0.900 | 0.988 | 87.5% | 100.0% | 86.7% | 70.0% | dense, n_chunks=10, no FK hints, strict tables, col descriptions, ~2465 prompt chars |
| gen-examples | 4 | 40 | 0.962 | 0.900 | 0.988 | 87.5% | 100.0% | 86.7% | 70.0% | dense, n_chunks=10, no FK hints, strict tables, example values, ~2721 prompt chars |
| gen-fewshot | 4 | 40 | 0.962 | 0.900 | 0.988 | 87.5% | 100.0% | 86.7% | 70.0% | dense, n_chunks=10, no FK hints, strict tables, few-shot, ~2336 prompt chars |
| gen-retry1 | 4 | 40 | 0.962 | 0.900 | 0.988 | 87.5% | 100.0% | 86.7% | 70.0% | dense, n_chunks=10, no FK hints, strict tables, retries=1, ~1660 prompt chars, 2 retry calls |
| gen-coldesc | 4 | 40 | 0.962 | 0.900 | 0.988 | 87.5% | 100.0% | 86.7% | 70.0% | dense, n_chunks=10, no FK hints, strict tables, col descriptions, ~2465 prompt chars |
| gen-examples | 4 | 40 | 0.962 | 0.900 | 0.988 | 87.5% | 100.0% | 86.7% | 70.0% | dense, n_chunks=10, no FK hints, strict tables, example values, ~2721 prompt chars |
| gen-fewshot | 4 | 40 | 0.962 | 0.900 | 0.988 | 87.5% | 100.0% | 86.7% | 70.0% | dense, n_chunks=10, no FK hints, strict tables, few-shot, ~2336 prompt chars |
