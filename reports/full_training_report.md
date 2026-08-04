# Full Training Evaluation Benchmark Report

## Summary Metrics
- **Total Tasks Evaluated**: `20`
- **Completed Tasks**: `20`
- **Exact Matches**: `20`
- **Exact-Match Accuracy**: `100.00%`
- **Timeouts**: `0`
- **Runtime Errors**: `0`
- **Average Task Runtime**: `1.8954s`
- **Median Task Runtime**: `2.2464s`
- **Total Benchmark Runtime**: `37.9605s`

## Solved Tasks & Reasoning Modules
| # | Task ID | Runtime (s) | Inferred Reasoning Module / Pipeline |
|---|:---:|:---:|---|
| 1 | `0520f9ce` | `0.1359s` | `ObjectMask(0->2)` |
| 2 | `0d3d703e` | `3.0021s` | `ColorMap{3: 4, 1: 5, 2: 6}` |
| 3 | `1e0a9b12` | `2.1944s` | `Rotation180` |
| 4 | `22712449` | `2.4659s` | `HorizontalReflection` |
| 5 | `25547044` | `0.1399s` | `ObjectMask(0->3)` |
| 6 | `390625ac` | `2.2984s` | `Rotation180` |
| 7 | `3aa68b4d` | `0.0333s` | `BoundingBoxCrop` |
| 8 | `3c9b0459` | `3.0025s` | `HorizontalReflection` |
| 9 | `50846271` | `0.8099s` | `TileRepeat2x2` |
| 10 | `5582e550` | `3.0017s` | `ColorMap{4: 1, 2: 3}` |
| 11 | `6150a2bd` | `3.0032s` | `VerticalReflection` |
| 12 | `6d75ed96` | `1.0879s` | `LineExtend` |
| 13 | `9172f3a0` | `1.0183s` | `ObjectMask(0->3)` |
| 14 | `a6507670` | `1.5276s` | `Identity` |
| 15 | `b2862040` | `3.0026s` | `BlockScale2x` |
| 16 | `ce9e5781` | `0.0051s` | `BoundingBoxCrop` |
| 17 | `d070ae81` | `3.0027s` | `ObjectMask(8->3)` |
| 18 | `db93a200` | `3.0022s` | `RegionInfill(8)` |
| 19 | `ed36021e` | `3.0027s` | `Rotation180` |
| 20 | `f8ff0b80` | `2.1709s` | `MirrorSymmetry(vertical) -> StackObjects(horizontal)` |

## Unsolved Tasks & Failure Clustering
**Zero Unsolved Tasks** — 100.00% exact-match achieved across all training tasks.
