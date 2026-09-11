# Legal Metrology Compliance Scanner — Benchmark Evaluation Report
**Evaluation Date:** 2026-09-07 20:05:00  
**Evaluation Standard:** Legal Metrology (Packaged Commodities) Rules, 2011  

---

## 1. Executive Performance Summary

| Metric | Score | Industry Benchmark | Compliance Status |
|:---|:---:|:---:|:---:|
| **Compliance Accuracy** | **100.0%** | > 90% |  **EXCEEDS** |
| **Precision (True Violations)** | **100.0%** | > 85% |  **EXCEEDS** |
| **Recall (Violations Caught)** | **100.0%** | > 85% |  **EXCEEDS** |
| **F1 Score** | **100.0%** | > 85% |  **OPTIMAL** |
| **Safety Deferral Rate** | **6.7%** | 5–15% |  **ZERO FABRICATION** |
| **Average Decision Latency** | **2.7 ms** | < 200 ms |  **REAL-TIME READY** |

---

## 2. Confusion Matrix

```
                      GROUND TRUTH (VIOLATION)    GROUND TRUTH (COMPLIANT)
PREDICTED VIOLATION          TP: 10                    FP: 0  
PREDICTED COMPLIANT          FN: 0                     TN: 5  
```

---

## 3. Statutory Rule Detection Coverage

| Rule Code | Statutory Clause | Ground Truth Violations | Correctly Detected | Sensitivity |
|:---|:---|:---:|:---:|:---:|
| **R001** | LM Rules 2011 | 1 | 1 | 100.0% |
| **R002** | LM Rules 2011 | 2 | 2 | 100.0% |
| **R003** | LM Rules 2011 | 1 | 1 | 100.0% |
| **R004** | LM Rules 2011 | 1 | 1 | 100.0% |
| **R005** | LM Rules 2011 | 1 | 1 | 100.0% |
| **R007** | LM Rules 2011 | 2 | 2 | 100.0% |
| **R008** | LM Rules 2011 | 1 | 1 | 100.0% |
| **R009** | LM Rules 2011 | 1 | 1 | 100.0% |

---

## 4. Individual Case Breakdown

| ID | Product | Category | Ground Truth | System Verdict | Match |
|:---|:---|:---|:---:|:---:|:---:|
| `CASE_001` | Herbal Essence Shampoo (400 ml | Personal Care | `PASS` | `PASS` | PASS |
| `CASE_002` | Premium Cashews (250 g Pouch)  | Food & Snacks | `FAIL` | `FAIL` | PASS |
| `CASE_003` | Sun Herbal Tea (100 gm Pack) — | Beverages | `FAIL` | `FAIL` | PASS |
| `CASE_004` | Glow Facial Serum — Deceptive  | Cosmetics | `FAIL` | `FAIL` | PASS |
| `CASE_005` | Farm Fresh Basmati Rice (1 kg) | Grains & Cereals | `FAIL` | `FAIL` | PASS |
| `CASE_006` | Mini Shampoo Sachet (6 ml) — S | Personal Care | `PASS` | `PASS` | PASS |
| `CASE_007` | Pocket Biscuit Pack (15 g) — S | Snacks | `PASS` | `PASS` | PASS |
| `CASE_008` | Almond Butter (200 g) — Missin | Spreads & Condiments | `FAIL` | `FAIL` | PASS |
| `CASE_009` | Handmade Bath Soap (125 g) — M | Personal Care | `FAIL` | `FAIL` | PASS |
| `CASE_010` | Spice Blend Garam Masala (100  | Spices | `FAIL` | `FAIL` | PASS |
| `CASE_011` | Sunflower Edible Oil (1 Litre  | Edible Oils | `FAIL` | `FAIL` | PASS |
| `CASE_012` | Premium Cold Beverage (750 ml  | Beverages | `FAIL` | `FAIL` | PASS |
| `CASE_013` | Cotton Hand Towels — Illegal N | Textiles | `FAIL` | `FAIL` | PASS |
| `CASE_014` | Cough Syrup Bottle — Uncalibra | Pharmaceuticals | `MANUAL_REVIEW` | `MANUAL_REVIEW` | PASS |
| `CASE_015` | Chakki Fresh Whole Wheat Atta  | Staples & Flour | `PASS` | `PASS` | PASS |
