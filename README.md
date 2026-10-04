# BTProp-MCQ — Phát hiện ảo giác trong câu hỏi trắc nghiệm

Pipeline phát hiện **hallucination** trong câu hỏi trắc nghiệm (MCQ) do LLM sinh ra,
dựa trên phương pháp **BTProp (Belief Tree Propagation)** của bài báo
[NAACL 2025 — *A Probabilistic Framework for LLM Hallucination Detection via Belief Tree Propagation*](https://aclanthology.org/2025.naacl-long.158/)
(`2025.naacl-long.158.pdf`), mở rộng thêm các tầng kiểm tra chuyên cho miền MCQ.

## Ý tưởng cốt lõi

BTProp không tin tưởng confidence của LLM một cách trực tiếp. Với mỗi khẳng định:

1. Xây **belief tree** — đệ quy sinh các mệnh đề con liên quan logic tới mệnh đề cha,
   bằng 3 chiến lược: *statement decomposition*, *supportive/contradictory premises*,
   *statement correction*.
2. Gán quan hệ logic cha–con bằng mô hình **NLI** (entailment/contradiction/neutral, 2 chiều).
3. Suy luận posterior `p(Z₀ = T | {Sᵤ})` bằng **hidden Markov tree** (belief propagation),
   dùng emission ước lượng từ Table 1 + transition từ Table 2 của paper.

## Kiến trúc pipeline (vượt paper)

```
MCQ JSON (content/options/explanation)
  → option→statement  →  EN pivot  →  premise-extract + guard
  → code-exec pass (trace → verified premise, không fact-check thế giới)
  → symbolic pass (PROVEN/DISPROVEN_BY_LOGIC)
  → BTProp posterior (claim còn lại, kiểm chứng với thế giới)
  → answer-key pass (p_answer; code-mode dùng posterior)
  → compound-option pass ("tất cả các đáp án trên")
  → explanation decompose + NLI contradict-filter (bảo vệ claim điều kiện)
  → h_* → weighted score + critical-risk override (≥0.70) → flags
```

### Điểm thành phần

| Score | Ý nghĩa |
|---|---|
| `h_correct` | Đáp án đánh dấu đúng bị sai (hallucination / key error) |
| `h_distractor` | Distractor thực sự đúng (ẩn đáp án đúng trong lựa chọn sai) |
| `h_explanation`, `h_explanation_max` | Claim trong giải thích bịa — trung bình / max |
| `h_premise` | Premise trong đề mâu thuẫn thế giới thực |
| `hallucination_score` | `0.4·h_correct + 0.3·h_distractor + 0.3·h_explanation` + override |
| `answer_key_errors` | Các option gán `is_correct` sai so với khả năng trả lời câu hỏi |
| `critical_risk` | Signal ≥0.70 → ép score ≥0.70, mức `VERY HIGH` |

### Phân biệt hallucination vs answer-key error

Cùng là "đáp án đánh dấu sai" nhưng hệ phân biệt được: claim **đúng thực tế** chỉ gán sai key
→ score THẤP + flag `ANSWER_KEY_INCONSISTENCY`; claim **sai thực tế** → `h_correct` cao →
VERY HIGH qua critical-risk override.

## Stack

- **LLM**: `gpt-4o-mini` (OpenAI API, confidence qua `logprobs` — cách đọc confidence
  giống repo gốc của paper).
- **NLI**: `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` (chạy CPU ~700MB).
- Đa ngôn ngữ (VI → pivot EN), hỗ trợ câu suy luận (premise-context), câu có code snippet
  (JS event loop, closure, precedence...).

## Cài đặt & chạy

```bash
pip install -U openai "transformers>=4.44" sentencepiece protobuf torch
export OPENAI_API_KEY=sk-...   # hoặc nhập khi chạy cell 2
```

- **Notebook**: `BTProp_MCQ_GPT.ipynb` — chạy tuần tự các cell; cell 9 chứa `evaluate_mcq`, cell 10 chạy test.
- **Test batch**: `python _gen_gpt_test.py` sinh `btprop_gpt_test.py` (ghép các cell + inject TESTS), rồi `python btprop_gpt_test.py`.
- **Config test**: `MAX_LAYERS=1`, `PIVOT_TO_ENGLISH=True` (tiết kiệm token); production nên `MAX_LAYERS=2` + `FORCE_BOTH_STRATEGIES=True`.

## File chính

| File | Vai trò |
|---|---|
| `BTProp_MCQ_GPT.ipynb` | Pipeline đầy đủ (cells 1–10) |
| `BTProp_MCQ_Hallucination.ipynb` | Bản gốc tham khảo (HF model backbone) |
| `_gen_gpt_test.py` | Sinh script test từ notebook + bộ test JSON |
| `TEST_REPORT.md` | Báo cáo 19 test case (T1–T24) + đánh giá chung |
| `2025.naacl-long.158.pdf` | Paper BTProp gốc |

## Kết quả kiểm thử (19 case)

- Câu sạch không false-positive: T3 0.041, T5 ~0.05, T21 0.075 → THẤP.
- Answer-key error phát hiện cả 2 chiều (marked-true→sai, marked-false→đúng): T18, T19, T22–T24.
- Premise bịa bắt đúng (`h_premise` 0.80–0.90) nhưng vẫn tôn trọng suy luận đúng theo premise.
- Code snippet: `console.log`, `setTimeout`+`var` closure, DOM `addEventListener` →
  trace đúng output, PROVEN/DISPROVEN_BY_LOGIC.

Chi tiết: `TEST_REPORT.md` — bao gồm cả điểm yếu còn lại (lỗi tương quan 1-LLM,
posterior gần nhị phân, heuristic mỏng) và roadmap cải thiện.

## Bảo mật

- Không commit API key — `OPENAI_API_KEY` đọc từ biến môi trường hoặc nhập lúc chạy.
- File sinh (`btprop_gpt_test.py`), kết quả (`btprop_result_*.json`), log (`run_gpt*.log`) bị gitignore.
