# Báo cáo kiểm thử BTProp — Phát hiện ảo giác trong câu hỏi trắc nghiệm

- **Backend LLM**: `gpt-4o-mini` (OpenAI API, confidence qua `logprobs`)
- **NLI**: `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` (CPU local)
- **Config test**: `MAX_LAYERS=1`, `FORCE_BOTH_STRATEGIES=False`, `PIVOT_TO_ENGLISH=True` (chế độ tiết kiệm token)
- **Công thức**: `score = 0.4·h_correct + 0.3·h_distractor + 0.3·h_explanation`
- **Ngưỡng**: `<0.3` THẤP | `0.3–0.6` TRUNG BÌNH | `>0.6` CAO

---

## Tổng quan kết quả

| # | Kịch bản | Score | Mức | Cờ cảnh báo | Kỳ vọng | Đánh giá |
|---|----------|-------|-----|-------------|---------|----------|
| T1 | Đáp án đánh dấu "đúng" là SAI (Berlin) | 0.918 | CAO | 3/3 flags | CAO | ✓ Đúng |
| T2 | Đáp án đúng, giải thích chứa 2 fact bịa | 0.277–0.301 | THẤP~TB | GIẢI THÍCH CHỨA FACT BỊA | TB | ⚠ Sát ngưỡng, flag bù |
| T3 | 4 đáp án, mọi thứ đúng (Sao Mộc) | 0.041 | THẤP | — | THẤP | ✓ Đúng |
| T4 | Distractor ẩn cũng đúng (Đức ∈ châu Âu) | 0.300 | THẤP | DISTRACTOR THỰC TẾ ĐÚNG | Flag phải bắt | ✓ Đúng |
| T5 | Điều kiện kép EU + euro (Pháp) | 0.051–0.068 | THẤP | — | THẤP | ✓ Đúng |
| T6 | Câu phủ định: đánh dấu Đức "KHÔNG thuộc EU" (sai) + giải thích bịa | 0.845–0.855 | CAO | 2–3 flags | CAO | ✓ Đúng |
| T7 | 4 option đều is_correct=true nhưng C bịa (VN dùng USD) | 0.714 | CAO | h_correct | CAO | ✓ Đúng |
| T8 | Câu suy luận có premise trong đề (syllogism mèo) | 0.196 | THẤP | — | THẤP | ✓ Đúng (sau 2 vá context) |
| T9 | Tái lập syllogism (đại bàng có cánh) | 0.000 | THẤP | — | THẤP | ✓ Đúng — toàn bộ symbolic |
| T10 | Premise đề bịa (Sao Kim có sự sống) + giải thích mâu thuẫn premise | 0.700 | VERY HIGH | h_max=1.00 + PREMISE ĐỀ BỊA + CRITICAL RISK | Override bắt đúng | ✓ Đúng |
| T16 | Option converse sai (mọi động vật có lông là chim cánh cụt) đánh dấu đúng | 0.700 | VERY HIGH | h_correct=1.00 | VERY HIGH | ✓ PASS (spec) |
| T17 | Premise bịa (mọi hành tinh có sự sống), A suy đúng modus ponens | 0.700 | VERY HIGH | h_correct + h_max + h_premise=0.90 | VERY HIGH | ✓ PASS (spec) |
| T18 | Câu KHÔNG thuộc EU: đánh dấu Đức sai, Thụy Sĩ làm distractor | 0.726 | VERY HIGH | h_correct=0.94 + distractor-thật | VERY HIGH | ✓ PASS (spec) |
| T19 | Mọi option factual-true, key gán sai (Paris↔Trái Đất) — phân biệt ANSWER_KEY_INCONSISTENCY vs HALLUCINATION | 0.049 | THẤP | ANSWER_KEY_INCONSISTENCY (A,B) | LOW ≤0.19 | ✓ PASS (sau 2 vá) |
| T20 | Cá voi: converse sai đánh true + premise "mọi thú đẻ con" sai thế giới + giải thích tự mâu thuẫn | 0.700 | VERY HIGH | h_correct + h_max + h_premise=0.90 | VERY HIGH | ✓ Đúng (1 vá FP) |
| T21 | JS `push()` — câu lập trình sạch, 4 claim giải thích đúng | 0.075 | THẤP | — | THẤP | ✓ Đúng, không FP |
| T22 | JS `x + y*3` = 11 nhưng key A=21 true; giải thích đúng (11) | 0.700 | VERY HIGH | h_correct=1.0 + ANSWER_KEY(A,B); h_premise=n/a, h_max=0 | VERY HIGH, chỉ flag key | ✓ PASS sau vá code-reasoning (trước vá: 2 FP) |
| T23 | HTML+JS `addEventListener`, `console.log(count)` = 0 nhưng key B=1 true; giải thích đúng (có claim điều kiện) | 0.700 | VERY HIGH | h_correct=1.0 + ANSWER_KEY(B,A); h_premise=n/a, h_max=0 | VERY HIGH, chỉ flag key | ✓ PASS lần đầu, không vá |
| T24 | `var`+`setTimeout` closure → `A,B,3,3,3` (B) nhưng key A true; giải thích VI đúng + claim phản thực `let` | 0.700 | VERY HIGH | h_correct=1.0 + ANSWER_KEY(A,B); h_max=0 | VERY HIGH, chỉ flag key | ✓ PASS sau vá 3 điểm yếu |

---

## Test 1 — Đáp án đánh dấu đúng là sai

### Input

```json
{
  "content": "Thủ đô của Pháp là thành phố nào?",
  "options": [
    {"key": "A", "text": "Berlin", "is_correct": "true"},
    {"key": "B", "text": "Paris", "is_correct": "false"}
  ],
  "explanation": "Berlin là thủ đô của Pháp từ năm 1800."
}
```

### Output

| Thành phần | prior | posterior | ảo giác |
|---|---|---|---|
| Đúng A (Berlin) | 0.000 | 0.138 | 0.862 |
| Sai B (Paris — thực tế đúng) | 1.000 | 1.000 | 1.000 |
| Giải thích "Berlin là thủ đô từ 1800" | 0.000 | 0.138 | 0.862 |

- `h_correct=0.90, h_distractor=1.00, h_explanation=0.86`
- Flags: `DAP AN DANH DAU DUNG BI SAI`, `CO DISTRACTOR THUC TE DUNG`, `GIAI THICH CHUA FACT BIA`
- **Score: 0.918 (CAO)**

### Phân tích

Câu hỏi vi phạm sự thật ở cả 3 vai trò: đáp án được chọn sai, đáp án bị loại (Paris) lại là đáp án thật — lỗi nghiêm trọng nhất của MCQ, và giải thích lặp lại khẳng định sai. Score ~0.9 phản ánh đúng mức độ "ảo giác toàn diện". Tái lập tốt: chạy lại cho 0.903↔0.918 (khác biệt nhỏ từ premise ngẫu nhiên).

---

## Test 2 — Đáp án đúng nhưng giải thích bịa fact

### Input

```json
{
  "content": "Nước sôi ở bao nhiêu độ C tại áp suất khí quyển tiêu chuẩn?",
  "options": [
    {"key": "A", "text": "90°C", "is_correct": "false"},
    {"key": "B", "text": "100°C", "is_correct": "true"},
    {"key": "C", "text": "110°C", "is_correct": "false"}
  ],
  "explanation": "Nước sôi ở 100°C vì phân tử nước có khối lượng nguyên tử là 50 và nhiệt độ sôi được Isaac Newton xác định lần đầu vào năm 1905."
}
```

### Output

| Thành phần | prior | posterior | ảo giác |
|---|---|---|---|
| Đúng B (100°C) | 1.000 | 0.81–0.86 | ~0.15 |
| Sai A (90°C) | 0.000 | 0.060 | 0.060 |
| Sai C (110°C) | 0.000 | 0.138 | 0.138 |
| Claim "boils at 100°C" | 0.997 | 0.947 | 0.053 |
| Claim "atomic mass of 50" | 0.000 | 0.025 | **0.975** |
| Claim "Newton determined 1905" | 0.000 | 0.204 | **0.796** |

- `h_explanation=0.60–0.61` → flag `GIAI THICH CHUA FACT BIA`
- **Score: 0.277–0.301 (THẤP↔TRUNG BÌNH, sát ngưỡng)**

### Phân tích

BTProp phát hiện chính xác 2 fact bịa ở mức claim (0.98 và 0.80) — đây là điểm mạnh cốt lõi: bóc tách giải thích thành claim nguyên tử rồi chấm riêng. Score tổng dao động quanh ngưỡng 0.3 do 2/3 thành phần sạch kéo trung bình xuống; **cờ cảnh báo thành phần đảm bảo lỗi không bị điểm tổng che giấu**.

Lưu ý lịch sử: trước khi vá `DECOMPOSE_PROMPT`, GPT đảo phủ định claim sai ("do **not** have atomic mass of 50") → mệnh đề đúng → ẩn hoàn toàn lỗi (score 0.153). Fix: rule "keep polarity exactly as asserted" + lớp verify NLI claim↔explanation.

---

## Test 3 — 4 đáp án, hoàn toàn đúng

### Input

```json
{
  "content": "Hành tinh nào lớn nhất trong Hệ Mặt Trời?",
  "options": [
    {"key": "A", "text": "Sao Thổ", "is_correct": "false"},
    {"key": "B", "text": "Sao Mộc", "is_correct": "true"},
    {"key": "C", "text": "Trái Đất", "is_correct": "false"},
    {"key": "D", "text": "Sao Hải Vương", "is_correct": "false"}
  ],
  "explanation": "Sao Mộc là hành tinh lớn nhất Hệ Mặt Trời, có khối lượng gấp khoảng 318 lần Trái Đất."
}
```

### Output

| Thành phần | prior | posterior | ảo giác |
|---|---|---|---|
| Đúng B (Sao Mộc) | 1.000 | 1.000 | 0.000 |
| Sai A (Sao Thổ) | 0.000 | 0.000 | 0.000 |
| Sai C (Trái Đất) | 0.000 | 0.138 | 0.138 |
| Sai D (Sao Hải Vương) | 0.000 | 0.060 | 0.060 |
| Giải thích (2 claims) | 1.000 | 1.000 | 0.000 |

- `h_correct=0.000, h_distractor=0.138, h_explanation=0.000`
- **Score: 0.041 (THẤP)** — tái lập chính xác qua nhiều lần chạy.

### Phân tích

Ca kiểm soát (control): hệ thống không báo động ảo với câu hỏi sạch. Chuyển đổi MCQ→statement giữ đúng nội dung option sai ("Saturn is the largest planet" không bị sửa thành Jupiter). `h_distractor=0.138` là sàn cơ học — posterior nhỏ khác 0 do nhánh contradict kéo xuống nhẹ theo transition Table 2.

---

## Test 4 — Distractor ẩn cũng là đáp án đúng

### Input

```json
{
  "content": "Nước nào sau đây nằm ở châu Âu?",
  "options": [
    {"key": "A", "text": "Pháp", "is_correct": "true"},
    {"key": "B", "text": "Đức", "is_correct": "false"},
    {"key": "C", "text": "Nhật Bản", "is_correct": "false"},
    {"key": "D", "text": "Brazil", "is_correct": "false"}
  ],
  "explanation": "Pháp là một quốc gia thuộc Tây Âu."
}
```

### Output

| Thành phần | prior | posterior | ảo giác |
|---|---|---|---|
| Đúng A (Pháp) | 1.000 | 1.000 | 0.000 |
| Sai B (Đức — thực tế đúng) | 1.000 | 1.000 | **1.000** |
| Sai C (Nhật Bản) | 0.000 | 0.102–0.209 | ~0.1–0.2 |
| Sai D (Brazil) | 0.000 | 0.102–0.209 | ~0.1–0.2 |
| Giải thích | 1.000 | 1.000 | 0.000 |

- `h_distractor=1.000` → flag `CO DISTRACTOR THUC TE DUNG - cau hoi nhap nhang`
- **Score: 0.300 (THẤP)**

### Phân tích

Đây là ca phát hiện được nhờ `h_distractor` lấy `max(posterior)`: model tin chắc "Đức" cũng là đáp án đúng → câu hỏi nhập nhằng (2 đáp án đúng). Điểm yếu được phơi bày: `h_distractor=1.0` chỉ nặng 30% nên tổng dừng 0.300 THẤP — **chính là lý do phải thêm cờ cảnh báo thành phần**; người đọc thấy flag "câu hỏi nhập nhằng" dù score thấp.

---

## Test 5 — Câu hỏi điều kiện kép (EU ∩ eurozone)

### Input

```json
{
  "content": "Trong một lớp học, giáo viên đưa ra câu hỏi: Quốc gia nào sau đây là thành viên của Liên minh châu Âu (EU) và đồng thời sử dụng đồng euro làm tiền tệ chính thức?",
  "options": [
    {"key": "A", "text": "Pháp", "is_correct": "true"},
    {"key": "B", "text": "Ba Lan", "is_correct": "false"},
    {"key": "C", "text": "Thụy Sĩ", "is_correct": "false"},
    {"key": "D", "text": "Đan Mạch", "is_correct": "false"}
  ],
  "explanation": "Đáp án đúng là Pháp vì Pháp là thành viên của EU và sử dụng đồng euro. Ba Lan cũng là thành viên EU nhưng hiện sử dụng đồng zloty. Thụy Sĩ không phải thành viên EU và sử dụng đồng franc Thụy Sĩ. Đan Mạch là thành viên EU nhưng đã duy trì đồng krone Đan Mạch và không sử dụng euro làm tiền tệ chính thức."
}
```

### Output

| Thành phần | prior | posterior | ảo giác |
|---|---|---|---|
| Đúng A (Pháp) | 1.000 | 1.000 | 0.000 |
| Sai B (Ba Lan) | 0.000 | 0.138 | 0.138 |
| Sai C (Thụy Sĩ) | 0.000 | 0.138 | 0.138 |
| Sai D (Đan Mạch) | 0.000 | 0.138 | 0.138 |
| Giải thích (4 claims) | 1.000 | 0.77–1.00 | 0.03–0.09 |

- `h_correct=0.000, h_distractor=0.138, h_explanation=0.031–0.089`
- **Score: 0.051–0.068 (THẤP)**

### Phân tích

Bài test khó nhất về ngữ nghĩa: điều kiện kép. Statement chuyển đổi giữ nguyên conjunction ("member of EU **and** uses euro"), nên hệ thống chấm Ba Lan/Đan Mạch sai vì thiếu euro, Thụy Sĩ sai vì thiếu EU — không false positive dù các nước "đúng một phần". Decompose giải thích đa câu thành claim theo từng nước, NLI verify không loại claim nào.

---

## Test 6 — Câu hỏi phủ định, đánh dấu sai + giải thích bịa

### Input

```json
{
  "content": "Quốc gia nào sau đây KHÔNG thuộc Liên minh châu Âu (EU)?",
  "options": [
    {"key": "A", "text": "Pháp", "is_correct": "false"},
    {"key": "B", "text": "Đức", "is_correct": "true"},
    {"key": "C", "text": "Thụy Sĩ", "is_correct": "false"},
    {"key": "D", "text": "Ý", "is_correct": "false"}
  ],
  "explanation": "Đáp án đúng là Đức vì Đức không thuộc EU. Pháp, Thụy Sĩ và Ý đều là thành viên EU."
}
```

Đáp án thật phải là **Thụy Sĩ** — Đức là thành viên sáng lập EU; giải thích bịa kép ("Đức không thuộc EU" + ngầm định "Thụy Sĩ là thành viên EU").

### Output

| Thành phần | prior | posterior | ảo giác |
|---|---|---|---|
| Đúng B (Đức — thực tế sai) | 0.000 | 0.000 | **1.000** |
| Sai A (Pháp) | 0.000 | 0.000 | 0.000 |
| Sai C (Thụy Sĩ — thực tế đúng) | 1.000 | 1.000 | **1.000** |
| Sai D (Ý) | 0.000 | 0.000 | 0.000 |
| Claim "Germany is not part of the EU" | 0.000 | 0.198 | **0.802** |
| Claim "Italy is a member of the EU" | 1.000 | 0.838 | 0.162 |

- `h_correct=1.000, h_distractor=1.000, h_explanation=0.482`
- Flags: `DAP AN DANH DAU DUNG BI SAI`, `CO DISTRACTOR THUC TE DUNG`
- **Score: 0.845 (CAO)** — 1.5 phút.

### Phân tích

- **Phủ định xử lý đúng**: statement chuyển đổi giữ nguyên "not part of the EU" — GPT đánh giá "Germany is not in EU" là sai tuyệt đối (posterior 0.000) và "Switzerland is not in EU" là đúng (1.000), tức hệ thống nhận ra đáp án đánh dấu lộn: đáp án thật (Thụy Sĩ) bị gán `is_correct=false`.
- Cây niềm tin cho claim giải thích "Đức không thuộc EU" bắt được fact bịa (ảo giác 0.80). `h_explanation=0.482` sát nhưng chưa qua ngưỡng 0.5 nên flag giải thích không bắn — lưu ý decompose chỉ tách được 2 claim, chưa test riêng claim "Thụy Sĩ là thành viên EU" (cũng là bịa); nếu có sẽ đẩy `h_explanation` cao hơn.
- Đây là mẫu thử thứ hai loại "đảo đáp án" (sau T1), và hệ thống lại trả CAO + flags đầy đủ → hành vi ổn định trên nhóm lỗi nghiêm trọng nhất.

---

## Test 7 — 4 option đều đánh dấu đúng nhưng C bịa fact

### Input

```json
{
  "content": "Phát biểu nào sau đây đúng về Việt Nam?",
  "options": [
    {"key": "A", "text": "Việt Nam nằm ở Đông Nam Á.", "is_correct": "true"},
    {"key": "B", "text": "Thủ đô của Việt Nam là Hà Nội.", "is_correct": "true"},
    {"key": "C", "text": "Việt Nam sử dụng đồng đô la Mỹ làm tiền tệ chính thức.", "is_correct": "true"},
    {"key": "D", "text": "Cả A, B và C đều đúng.", "is_correct": "true"}
  ],
  "explanation": "Việt Nam nằm ở Đông Nam Á và có thủ đô là Hà Nội. Việt Nam sử dụng đồng đô la Mỹ làm tiền tệ chính thức. Vì A, B và C đều đúng nên D cũng đúng."
}
```

A, B đúng; **C bịa** (Việt Nam dùng đồng VNĐ) → D sai theo logic; giải thích lặp lại claim USD.

### Output

| Thành phần | prior | posterior | ảo giác |
|---|---|---|---|
| Đúng A (Đông Nam Á) | 1.000 | 1.000 | 0.000 |
| Đúng B (Hà Nội) | 1.000 | 1.000 | 0.000 |
| Đúng C (USD — bịa) | 0.000 | 0.000 | **1.000** |
| Đúng D (cả A,B,C — sai theo) | 0.000 | 0.538 | 0.462 |
| Giải thích: claim USD | 0.000 | 0.000 | **1.000** |
| Giải thích: 2 claims đúng | 1.000 | 1.000 | 0.000 |

- `h_correct=1.000, h_distractor=n/a, h_explanation=0.333`
- Flag: `DAP AN DANH DAU DUNG BI SAI`
- **Score: 0.714 (CAO)** — 1.3 phút, file `btprop_result_03.json` + `run_gpt_03.log`.

### Phân tích

- **Edge case mới**: không có distractor nào (`is_correct=true` cả 4) → `h_distractor=n/a`, trọng số được chuẩn hóa lại trên 2 thành phần còn lại — công thức vẫn đúng, không crash.
- `h_correct` lấy `min` của các đáp án "đúng" → claim C bịa (posterior 0.000) kéo h_correct=1.000, flag bắn đúng. Claim USD trong giải thích cũng 0.000 — phát hiện chắc ở cả hai vai trò.
- **Lọc ngôn ngữ hoạt động nhưng là điểm cần lưu ý**: GPT sinh premise tiếng Việt cho claim USD → toàn bộ con bị loại ("bỏ, lệch ngôn ngữ") → posterior trơ = prior. Kết quả vẫn đúng vì GPT prior đã chắc sai, nhưng nếu claim mơ hồ hơn thì cây rỗng sẽ mất lợi ích propagation.
- `h_explanation=0.333` (<0.5, flag không bắn): trung bình 3 claim trong đó 1 bịa — cùng hạn chế "trung bình che lỗi" như T2; nếu giải thích nhiều claim đúng hơn thì lỗi càng bị loãng.

---

## Test 8 — Câu suy luận có premise trong đề (syllogism)

### Input

```json
{
  "content": "Tất cả mèo đều là động vật. Mimi là một con mèo. Kết luận nào sau đây chắc chắn đúng?",
  "options": [
    {"key": "A", "text": "Mimi là động vật.", "is_correct": "true"},
    {"key": "B", "text": "Mimi là chó.", "is_correct": "false"},
    {"key": "C", "text": "Tất cả động vật đều là mèo.", "is_correct": "false"},
    {"key": "D", "text": "Không thể biết Mimi có phải là động vật hay không.", "is_correct": "false"}
  ],
  "explanation": "Vì tất cả mèo đều là động vật và Mimi là mèo nên Mimi chắc chắn là động vật."
}
```

### Output (sau 2 vá context)

| Thành phần | prior | posterior | ảo giác |
|---|---|---|---|
| Đúng A ("Given all cats are animals... Mimi is an animal") | 1.000 | 0.773 | 0.227 |
| Sai B (Mimi is a dog) | 0.000 | 0.102 | 0.102 |
| Sai C (all animals are cats) | 0.000 | 0.175 | 0.175 |
| Sai D (không thể biết) | 0.000 | 0.261 | 0.261 |
| Giải thích (3 claims, chấm có context) | 0.99–1.00 | 0.895–0.945 | 0.055–0.105 |

- `h_correct=0.227, h_distractor=0.261, h_explanation=0.088, h_max=0.105`
- **Score: 0.196 (THẤP)**, không flag — đúng kỳ vọng. File `btprop_result_09.json` + `run_gpt_09.log`.

### Phân tích — vì sao cần 3 lần chạy

| Lần | Trạng thái | Score | Vấn đề |
|---|---|---|---|
| 1 | Trước vá context | 0.445 TB | Statement "Mimi is an animal" mất premise → GPT chấm 0.000 |
| 2 | Như trên (nhiễu) | 0.666 CAO | Biên độ nhiễu lớn khi judge thiếu context |
| 3 | Option có "Given..." | 0.289 THẤP | Option đúng; nhưng claim explanation vẫn chấm thế-giới → false flag h_expl=0.67 |
| 4 | + Explanation claim có context | **0.196 THẤP** | Đúng hoàn toàn, không flag |

- **Bài học**: câu hỏi suy luận cần premise của đề trong mọi statement — vá dạng `Given <premises>, <claim>` áp dụng cho cả option lẫn claim explanation (tái dùng prefix, không tốn thêm LLM call).
- Câu hỏi kiến thức thường (không premise) không bị ảnh hưởng: prefix chỉ trích khi statement bắt đầu bằng `Given`.

---

## Test 9 — Tái lập vá premise-context (syllogism đại bàng)

### Input

```json
{
  "content": "Tất cả chim đều có cánh. Đại bàng là một loài chim. Kết luận nào sau đây đúng?",
  "options": [
    {"key": "A", "text": "Đại bàng có cánh.", "is_correct": "true"},
    {"key": "B", "text": "Đại bàng là động vật có vú.", "is_correct": "false"},
    {"key": "C", "text": "Tất cả động vật có cánh đều là chim.", "is_correct": "false"},
    {"key": "D", "text": "Không thể biết đại bàng có cánh hay không.", "is_correct": "false"}
  ],
  "explanation": "Tất cả chim đều có cánh. Đại bàng là một loài chim. Vì vậy, đại bàng có cánh."
}
```

### Output

| Thành phần | prior | posterior | ảo giác |
|---|---|---|---|
| Đúng A (đại bàng có cánh, có "Given..." context) | 1.000 | 0.721 | 0.279 |
| Sai B (động vật có vú) | 0.000 | 0.102 | 0.102 |
| Sai C (mọi động vật có cánh là chim — đảo sai) | 0.000 | 0.102 | 0.102 |
| Sai D (không thể biết) | 0.000 | 0.198 | 0.198 |
| Giải thích 3 claims (chấm có context) | ~1.000 | 0.595–0.797 | 0.203–0.405 |

- `h_correct=0.279, h_distractor=0.198, h_explanation=0.278, h_max=0.405`
- **Score: 0.255 (THẤP)** (trước lớp symbolic), không flag. File `btprop_result_10.json` + `run_gpt_10.log`.

**Sau lớp symbolic reasoning (v2)** — mỗi claim có `reasoning_status` + `proof`, NLI/Belief Tree chỉ chấm claim UNKNOWN/EXTERNAL:

| Claim | reasoning_status | posterior |
|---|---|---|
| Đúng A (eagle has wings) | PROVEN_BY_LOGIC | 1.000 |
| Sai B (eagle is mammal) | DISPROVEN_BY_LOGIC | 0.000 |
| Sai C (all winged animals are birds — converse sai) | DISPROVEN_BY_LOGIC | 0.000 |
| Sai D (không thể biết) | DISPROVEN_BY_LOGIC | 0.000 |
| 3 claims giải thích | PROVEN_BY_LOGIC | 1.000 |

- `h_correct=0, h_distractor=0, h_explanation=0, h_max=0` → **Score: 0.000 (THẤP)**, 0.7 phút (BTProp bị skip hoàn toàn cho claim symbolic).
- Lưu ý triển khai: prover ban đầu dùng NLI bị **converse fallacy** (C bị entail nhầm → flag nhập nhằng giả) → chuyển `_logic_check` sang LLM judge (10 token/claim) — chính xác và vẫn nhanh.

### Phân tích

- Vá premise-context **tái lập đúng** trên syllogism thứ hai: statement tất cả option đều mang "Given that all birds have wings..." → đáp án đúng posterior 0.72 (cây entail đẩy lên từ prior 1.0), distractor giả đảo lập luận (C) và phủ định thông tin (D) đều bị cây contradict kéo về ~0.1–0.2.
- `h_explanation=0.278` cao hơn T8 chút vì premise ngẫu nhiên yếu hơn (conf 0.00–0.73 một vài con) — nhưng vẫn dưới ngưỡng flag và đúng bản chất giải thích sạch.
- Kết luận: vá context hoạt động ổn định trên nhóm câu hỏi suy luận, không phụ thuộc chủ đề cụ thể.

---

## Test 10 — Premise đề bịa + giải thích tự mâu thuẫn

### Input

```json
{
  "content": "Tất cả hành tinh trong Hệ Mặt Trời đều quay quanh Mặt Trời. Sao Kim là hành tinh duy nhất có sự sống trong Hệ Mặt Trời. Vì Sao Kim là một hành tinh nên Sao Kim quay quanh Mặt Trời. Chọn đáp án đúng.",
  "options": [
    {"key": "A", "text": "Sao Kim quay quanh Mặt Trời.", "is_correct": "true"},
    {"key": "B", "text": "Sao Kim là hành tinh duy nhất có sự sống trong Hệ Mặt Trời.", "is_correct": "true"},
    {"key": "C", "text": "Tất cả các hành tinh đều là Sao Kim.", "is_correct": "false"},
    {"key": "D", "text": "Không thể biết Sao Kim có quay quanh Mặt Trời hay không.", "is_correct": "false"}
  ],
  "explanation": "...Tuy nhiên, Sao Kim không phải là hành tinh duy nhất có sự sống trong Hệ Mặt Trời."
}
```

### Output

| Claim | reasoning_status | posterior |
|---|---|---|
| Đúng A (Sao Kim quay quanh Mặt Trời) | PROVEN_BY_LOGIC | 1.000 |
| Đúng B (Sao Kim có sự sống — đề nêu sẵn) | PROVEN_BY_LOGIC | 1.000 |
| Sai C, D | DISPROVEN_BY_LOGIC | 0.000 |
| Giải thích 3 claims nhất trí | PROVEN_BY_LOGIC | 1.000 |
| Giải thích "Sao Kim không phải duy nhất có sự sống" | DISPROVEN_BY_LOGIC | 0.000 |

- `h_correct=0, h_distractor=0, h_explanation=0.250, h_max=1.000` → flag `GIAI THICH CO CLAIM BIA NGHIEM TRONG` bắn.
- **Score: 0.075 (THẤP)**, 0.7 phút. File `btprop_result_13.json`.

### Phân tích — edge case "premise bịa"

- Symbolic layer chấm theo **premise-world**: B được "chứng minh" vì đề tự khẳng định — nhất quán logic nhưng bỏ qua sự thật thế giới (thật ra Trái Đất mới có sự sống).
- Giải thích phủ định premise đề → DISPROVEN + flag `h_max=1.0` bắt đúng claim mâu thuẫn, dù score tổng thấp (0.075) vì 3/4 claim nhất trí.
**Đã vá — premise world-check**: `_premise` trích ra được tách thành claim nguyên tử và chấm bằng BTProp theo thế giới thực (không dùng symbolic):

| Premise claim (world-check) | posterior | ảo giác |
|---|---|---|
| All planets revolve around the Sun | 0.906 | 0.094 |
| Venus is the only planet with life | 0.189 | **0.811** |

- Cây niềm tin của claim bịa tìm đúng phản chứng (Mars có dấu vết vi sinh, Enceladus có nước lỏng) → `h_premise=0.811` → flag `PREMISE DE BIA - de chua gia dinh sai the gioi thuc`.
- Score giữ 0.075 (flag-only, không đổi công thức) — giờ báo đủ cả 2 lỗi: giải thích tự mâu thuẫn premise + premise đề bịa so với thế giới thực. File `btprop_result_15.json` + `run_gpt_15.log`.

**Sau `critical_risk_override` (v3)**: `h_premise=0.898` + `h_max=1.000` ≥ 0.70 → `score=0.700`, `level=VERY HIGH` thay vì 0.075 THẤP loãng. Output in đủ `h_correct / h_distractor / h_explanation / h_explanation_max / h_premise / critical_risk / hallucination_score / level`. `h_distractor` không phải trigger — distractor sai thông thường không tính ảo giác. File `btprop_result_16.json` + `run_gpt_16.log`.

---

## Test 16–18 — Batch kiểm tra theo spec (3/3 PASS)

### T16 — Option converse sai được đánh dấu đúng

- A (penguins have feathers) `PROVEN_BY_LOGIC` 1.000; C (all birds have feathers) `PROVEN` 1.000; **B (all feathered animals are penguins — converse fallacy) `DISPROVEN_BY_LOGIC` 0.000 nhưng `is_correct=true`** → `h_correct=1.0`.
- `h_premise=0.256` (premise đề đúng thế giới); `score=0.700 VERY HIGH`. File `btprop_result_17.json`.
- LLM logic-judge bắt đúng converse fallacy — lỗi NLI trước đây đã hết.

### T17 — Premise bịa nhưng kết luận suy hợp lệ

- Premise "all planets have life" world-check → posterior 0.102 → `h_premise=0.898`, flag `PREMISE DE BIA`.
- A (Mars has life) `PROVEN_BY_LOGIC` 1.000 — symbolic ưu tiên, NLI không override.
- `score=0.700 VERY HIGH`, crit = h_correct + h_max + h_premise. File `btprop_result_18.json`.
- Lưu ý: B (lặp lại premise bịa, is_correct=true) bị `DISPROVEN` do conclusion-parse gộp chuỗi suy luận — trùng kết quả mong muốn (premise bịa đánh dấu đúng = lỗi đáp án) nhưng nhãn hơi lệch; claim giải thích "premise sai theo thực tế" bị DISPROVEN theo premise-world — biên premise-world vs world-truth đã biết.

### T18 — Câu phủ định + answer-key sai kép

- Không có premise suy luận → toàn bộ `EXTERNAL_CLAIM`, chấm BTProp.
- B (Đức, is_correct=true, thực tế sai với câu KHÔNG) → posterior 0.060 → `h_correct=0.940`.
- D (Thụy Sĩ, đáp án thật nhưng là distractor) → posterior 0.891 → `h_distractor=0.891` → flag distractor-thật ≡ `ANSWER_KEY_INCONSISTENCY`.
- `score=0.726 VERY HIGH`. File `btprop_result_19.json`.
- Lưu ý: A (Pháp KHÔNG thuộc EU — sai thực tế) bị cây đẩy 0.865 (nhiễu), C đúng 0.000.

---

## Test 19 — ANSWER_KEY_INCONSISTENCY ≠ HALLUCINATION

### Input (thiết kế)

Câu "Thủ đô của Pháp?" — mọi option là fact đúng: A Paris (đáp án thật, đánh false), B "Trái Đất quay quanh Mặt Trời" (đánh true dù không trả lời), C nước sôi 100°C, D Seine chảy qua Paris (đều false). Giải thích đúng, không premise.

### Kết quả

- `h_correct=0.123, h_distractor=0.000, h_explanation=0.000, h_max=0.000, h_premise=n/a`
- `answer_key_errors`: **B** (marked true, p_answer=0.000) + **A** (marked false, p_answer=1.000) — chính xác 2 option gán sai key.
- Flag duy nhất `ANSWER_KEY_INCONSISTENCY`; **0.049 THẤP** — không có hallucination flag nào.

### Vá cần thiết (2 vòng FAIL → fix)

| Lỗi | Nguyên nhân gốc | Vá |
|---|---|---|
| score 0.700 VERY HIGH | `option_to_statement` nhét claim đúng vào template → composite sai | Rule mới: option đã là câu factual → giữ nguyên làm claim |
| D bị liệt kê key-error sai | `p_answer` quá dễ (Seine→Paris gợi ý gián tiếp) | Prompt siết: "correctly and directly answers" |
| A bị `PROVEN_BY_LOGIC` vô nghĩa | LLM nhét câu hỏi vào `Given...` → pseudo-premise | Guard: bỏ premise chứa nghi vấn từ |

- Đồng thời tái định nghĩa `h_distractor`: chỉ đo distractor trả lời đúng câu hỏi chưa liệt kê key-error → factual-true distractor không bị phạt (đúng spec "distractor sai thường ≠ hallucination").
- File `btprop_result_23.json` + `run_gpt_23.log`.

---

## Test 20 — Cá voi: 3 lỗi chồng

### Input

Đề: "Tất cả thú đều đẻ con. Cá voi là thú. Vì vậy mọi động vật đẻ con đều là cá voi." — A/B/C `true`, D `false`. Giải thích kết thúc "Cá voi là loài cá nên không phải thú."

### Kết quả

| Claim | status | posterior |
|---|---|---|
| A whales are mammals | PROVEN_BY_LOGIC | 1.000 |
| B whales give birth | PROVEN_BY_LOGIC | 1.000 |
| **C all birth-giving animals are whales** (converse) | **DISPROVEN_BY_LOGIC**, is_correct=true | 0.000 |
| D whales are fish | DISPROVEN_BY_LOGIC | 0.000 |
| Premise "all mammals give birth" (world) | — | **0.102** (platypus/echidna đẻ trứng) |
| Giải thích "whales are fish" / "not mammals" | DISPROVEN_BY_LOGIC | 0.000 |

- `h_correct=1.0, h_explanation=0.40, h_max=1.0, h_premise=0.898` → crit ×3 → **0.700 VERY HIGH**.
- 3 lỗi đều bắt: đáp án converse sai, premise sai thế giới thực, giải thích tự mâu thuẫn.

### Vá: false positive answer-key

- Lần 1: `ANSWER_KEY_INCONSISTENCY (A,B,C)` báo sai — đề là chuỗi suy luận **không có câu hỏi**, nên `p_answer` ("trả lời đúng câu hỏi?") vô nghĩa → 0.000 cho mọi option.
- Fix: answer-key pass chỉ chạy khi `content` là câu hỏi thật (`?` hoặc từ hỏi EN/VI); report thêm `is_question`. T18/T19 (có câu hỏi) không đổi.
- File `btprop_result_25.json` + `run_gpt_25.log`.

---

## Test 21 — JS `push()` (domain code, câu sạch)

- 4 option `EXTERNAL_CLAIM` (không premise): A push() 0.891; B/C/D 0.138 (cây contradict kéo về đúng).
- 4 claim giải thích (push/pop/shift/unshift) posterior 0.88–0.91 — tách đủ, không trùng, không flip.
- `h_correct=0.109, h_distractor=0, h_explanation=0.106, h_max=0.118, h_premise=n/a`, không `answer_key_errors`.
- **0.075 THẤP**, 0 flag — pipeline sau các vá answer-key/premise-guard **không false-positive** trên câu kỹ thuật thông thường. File `btprop_result_26.json`.

---

## Test 22 — JS precedence, code block trong `content` (đánh giá thuần, không fix)

### Input

`content` chứa code đa dòng: `let x=5; let y=2; console.log(x + y*3);` — output thật **11** (B) nhưng key **A=21 true**; giải thích đúng và kết luận 11, mâu thuẫn key.

### Kết quả: **0.700 VERY HIGH** — kết luận đúng, nhưng 2/4 flag là false positive

| Thành phần | Giá trị | Đánh giá |
|---|---|---|
| A "result is 21" | posterior 0.000 → `h_correct=1.0` | **ĐÚNG** — bắt đáp án sai |
| `answer_key_errors` | A (marked true, p_answer=0.000) | **ĐÚNG**; thiếu B (p_answer không đủ 0.5 vì statement mất code) |
| B "output is 11" | posterior 0.364 | **Yếu** — đáp án thật chỉ 0.36 |
| `h_premise=1.0` | premise = `"the output of the following JavaScript code"` | **FP** — cụm danh từ, không phải mệnh đề |
| `h_max=0.78` | "y*3 is evaluated first" 0.219; "x+6 equals 11" 0.364; "output is 11" 0.502 | **FP** — claim đúng bị chấm thấp |
| "2*3 is 6" | `PROVEN_BY_LOGIC` proof = pseudo-premise | nhãn đúng, lý do sai |

### Nguyên nhân gốc (chưa vá)

1. **Mất code block**: `option_to_statement` sinh `"Given the output of the following JavaScript code, the result is 21"` — code `x + y*3` bị bỏ; mọi claim sau đó (option, giải thích) chấm **không có code** → GPT không tính được, posterior ở mức đoán (0.2–0.5).
2. **Pseudo-premise dạng cụm danh từ**: guard hiện tại chỉ chặn nghi vấn từ (`which/what/...`); `"the output of the following JavaScript code"` lọt → world-check 0.000 → `h_premise=1.0` + `PREMISE DE BIA` sai.
3. **Giải thích chấm trong context rỗng**: `Given <pseudo-premise>, ...` không mang code nên "x + 6 = 11" không biết x=5.

### Nhận xét (trước vá)

- Score tổng đúng (VERY HIGH) nhưng **vì lý do đúng một nửa**: `h_correct` + `ANSWER_KEY` là tín hiệu thật; `h_premise` và `h_max` là nhiễu. File `btprop_result_27.json`.

### Vá code-reasoning (cell 9) — kết quả sau vá: **PASS toàn bộ kỳ vọng**

| Thành phần | Trước | Sau |
|---|---|---|
| A "21" (marked true) | UNKNOWN 0.000 | **DISPROVEN_BY_LOGIC** proof `code exec -> output = 11` |
| B "11" | UNKNOWN 0.364 | **PROVEN_BY_LOGIC** 1.000 |
| C/D | UNKNOWN 0.000 | **DISPROVEN_BY_LOGIC** |
| "y*3 is evaluated first" | 0.219 (FP) | **PROVEN** 1.000 |
| 5 claim giải thích | 0.22–1.0 | tất cả PROVEN → `h_explanation=0, h_max=0` |
| `h_premise` | 1.0 (FP) | **n/a** |
| `answer_key_errors` | [A] | **[A, B]** (A marked true p=0.000; B marked false p=1.000) |
| flags | 4 (2 FP) | `DAP AN SAI` + `ANSWER_KEY_INCONSISTENCY (A, B)` + `CRITICAL RISK: h_correct` |
| score | 0.700 VERY HIGH | 0.700 VERY HIGH — **chỉ vì answer key sai** |

Cơ chế:

1. **Premise guard mở rộng**: ngoài nghi vấn từ, chặn cụm danh từ dẫn `the output/result/value/answer of ...` → không tạo `h_premise` cho câu dẫn.
2. **Code-reasoning pass**: `content` khớp ≥2 token code (`let/const/console.log/;/{}`...) → `_code_mode`; LLM trace thực thi (temp 0, nêu rõ precedence) → `output`. Code + trace + output trở thành **premise đã xác minh** cho `_logic_check` (option và giải thích), bỏ qua world fact-check (`report["code_execution"]`, in dòng `[Code exec ]`).
3. **Answer-key code mode**: option PROVEN/DISPROVEN theo thực thi → `p_answer = posterior` (1/0) thay vì hỏi LLM → bắt cả A (true→FALSE) lẫn B (false→TRUE).

Hồi quy: T19 → 0.038 THẤP, key A/B giữ nguyên (`btprop_result_30.json`); T20 → 0.700, `h_premise=0.898` giữ nguyên (`btprop_result_31.json`). File T22 sau vá: `btprop_result_28.json` / `_29.json`.

---

## Test 23 — DOM event listener (code mode, không vá)

### Input

`content` chứa HTML + `<script>`: `let count=0; btn.addEventListener('click', ()=>count++); console.log(count);` — hỏi output ngay khi script chạy, trước click. Output thật **0** (A) nhưng key **B=1 true**. Giải thích đúng, có claim điều kiện "if clicked once, count becomes 1".

### Kết quả: **0.700 VERY HIGH** — chỉ vì answer key sai

| Claim | status | posterior |
|---|---|---|
| B "1 printed" (marked true) | **DISPROVEN_BY_LOGIC** `code exec -> output = 0` | 0.000 |
| A "0 printed" (marked false) | **PROVEN_BY_LOGIC** | 1.000 |
| C undefined / D error | DISPROVEN_BY_LOGIC | 0.000 |
| "count initialized to 0" | PROVEN | 1.000 |
| "listener does not execute callback immediately" | PROVEN | 1.000 |
| "console.log prints 0 before click" | PROVEN | 1.000 |
| "if clicked once, count becomes 1" (điều kiện) | PROVEN | 1.000 |

- `h_correct=1.0, h_explanation=0, h_max=0, h_premise=n/a`; `answer_key_errors=[B, A]`.
- Flags: `DAP AN SAI` + `ANSWER_KEY_INCONSISTENCY (B, A)` + `CRITICAL RISK: h_correct` — **không** `GIAI THICH BIA`, **không** `PREMISE DE`.
- Code-reasoning pass tự xử lý đúng ngữ nghĩa async DOM (listener không chạy ngay) và claim điều kiện hậu-click không bị phạt. File `btprop_result_32.json` + `run_gpt_32.log`.

---

## Test 24 — `var` + `setTimeout` closure (code mode, VI, đánh giá thuần)

### Input

Code trong fenced block ```` ```javascript ````: `console.log("A"); for(var i=0;i<3;i++) setTimeout(()=>console.log(i),0); console.log("B");` — output thật **A, B, 3, 3, 3** (B) nhưng key **A=`A,B,0,1,2` true**. Giải thích tiếng Việt đúng, 8 câu, kết thúc bằng claim phản thực "dùng `let` thì mới ra 0,1,2".

### Kết quả: **0.700 VERY HIGH** — chỉ vì answer key sai (đúng)

| Claim | status | posterior |
|---|---|---|
| A `A,B,0,1,2` (marked true) | **DISPROVEN_BY_LOGIC** | 0.000 |
| B `A,B,3,3,3` (marked false) | **PROVEN_BY_LOGIC** | 1.000 |
| C `A,0,1,2,B` / D `A,B,2,2,2` | DISPROVEN_BY_LOGIC | 0.000 |
| 8/8 claim giải thích (event loop, `var` shared, i=3 sau loop, kết quả A,B,3,3,3) | PROVEN | 1.000 |

- `h_correct=1.0, h_explanation=0, h_max=0, h_premise=n/a`; `answer_key_errors=[A, B]`; không `GIAI THICH BIA`, không `PREMISE DE`.
- Code trace LLM **hoàn toàn đúng**: 3 lần schedule, i=3 sau loop, B trước, 3 callback in 3.

### 3 điểm yếu → đã vá (`_patch_gpt19`)

| # | Hiện tượng | Nguyên nhân | Vá | Kết quả sau vá |
|---|---|---|---|---|
| 1 | `[Code exec] output = A` (phải là `A, B, 3, 3, 3`) | Regex `Output:` bắt match **đầu** trong trace | Prompt đổi token `FINAL OUTPUT`; parse ưu tiên dòng bắt đầu `FINAL OUTPUT`/`Output` lấy **cuối**, fallback match cuối bất kỳ | `output = A B 3 3 3`, proof `code exec -> output = A B 3 3 3` |
| 2 | C, D gán `[logic] all-of-the-above` | Heuristic `\b[a-e]\b` khớp chữ cái trong output | Bỏ qua compound heuristic trong `_code_mode` (`for x in (_items if not _code_mode else [])`) | C/D `DISPROVEN` sạch, không còn tag `[logic]` |
| 3 | Claim "dùng `let` → 0,1,2" bị mất | `MAX_EXPLAIN_CLAIMS=8` cắt + có thể contradict-filter | MAX→12; bảo vệ claim điều kiện (`if/would/instead/nếu/giả sử/thay cho/had/were to...`) khỏi filter | Claim xuất hiện, **PROVEN_BY_LOGIC** 1.000 |

Sau vá: `h_correct=1.0, h_explanation=0, h_max=0, h_premise=n/a`; `answer_key_errors=[A,B]`; flags chỉ `DAP AN SAI` + `ANSWER_KEY_INCONSISTENCY (A,B)` + `CRITICAL RISK: h_correct`.

Hồi quy (test 35–37): T23 `output = 0`, key [B,A], 0.700 giữ nguyên; T19 0.038 THẤP; T20 0.700, `h_premise=0.898` — tất cả giữ nguyên.

File sau vá: `btprop_result_34.json` + `run_gpt_34.log`; trước vá: `btprop_result_33.json`.

---

## Đánh giá chung (sau 19 test, T1–T24)

### Kiến trúc hiện tại

`option→statement` → `to_english` → premise-extract + guard → **code-exec pass** (trace → verified premise) → **symbolic pass** (PROVEN/DISPROVEN_BY_LOGIC) → BTProp posterior (UNKNOWN/EXTERNAL) → **answer-key pass** (`p_answer`; code-mode dùng posterior) → compound-option → explanation decompose + contradict-filter (protect điều kiện) → `h_*` → weighted score + **critical-risk override ≥0.70** → flags.

### Điểm mạnh đã kiểm chứng

- **Phân tầng đúng chức năng**: premise-MCQ đi hoàn toàn đường symbolic không cần world-check (T9: 0.000); code-MCQ đi đường code-exec verified premise (T22–T24); câu thường đi BTProp (T1–T7).
- **Phân biệt lỗi answer-key vs hallucination**: cùng là "đáp án đánh dấu sai" nhưng T19 (claim đúng thực tế, chỉ sai key) → **0.038 THẤP** chỉ flag `ANSWER_KEY_INCONSISTENCY`; T18/T22–24 (đáp án đúng thực sự sai) → VERY HIGH qua `h_correct`. Không lẫn hai loại lỗi.
- **Bắt được cả hai chiều key-error**: marked-true→sai *và* marked-false→đúng (T18 D, T19 A, T22 B, T23 A, T24 B).
- **Critical-risk override** đảm bảo lỗi nghiêm trọng thành phần không bị điểm tổng che (T10, T16, T17, T20 — đều ≥0.70).
- **Premise fact-check** bắt premise bịa trong đề (T10, T17, T20 `h_premise≈0.8–0.9`) đồng thời vẫn cho option suy đúng theo premise là PROVEN.
- **Giải thích đa câu** tách claim độc lập, bắt claim bịa lẫn trong claim đúng (T2, T6, T20); claim điều kiện/phản thực không bị phạt (T23, T24).
- **Không false-positive trên câu sạch**: T3 0.041, T5 ~0.05, T21 0.075 — đều THẤP, 0 flag.
- Đa ngôn ngữ (VI→EN), câu phủ định, điều kiện kép, syllogism, converse fallacy (T16, T20).

### Điểm yếu còn lại

- **Phụ thuộc tri thức + suy luận của GPT**: toàn bộ phán quyết (statement-gen, trace code, logic-check, confidence, prior/posterior) đều qua cùng 1 LLM → **lỗi tương quan**: nếu GPT vừa trace sai code vừa chấp nhận kết quả sai làm premise verified, không tầng nào phát hiện. Code-exec chỉ 1 trace, không self-consistency.
- **Posterior gần nhị phân**: prior bão hòa 0/1, propagation chỉ kéo ~0.06–0.21 → khoảng giữa ít thông tin; borderline nhiễu (T2: 0.277–0.301).
- **Heuristic mỏng**:
  - `_is_question` / premise-guard chỉ là regex — câu hỏi không có `?`/từ hỏi ("Hãy cho biết...") có thể lọt mất answer-key pass; dạng câu dẫn khác có thể thành pseudo-premise.
  - Compound-option `\b[a-e]\b` vẫn rủi ro FP ở non-code mode (option chứa chữ cái trùng key); chỉ mới né trong code mode.
  - Conditional-protect để giữ claim điều kiện cũng có thể giữ lại claim decompose lật ngược nếu nó chứa "if/would".
- **Giải thích chỉ chấm từng claim riêng**: chưa kiểm tra *kết luận giải thích có khớp đáp án đánh dấu* — giải thích đúng từng câu nhưng dẫn đến option khác với key vẫn hợp lệ về điểm (T19/T22 bắt được nhờ answer-key pass, nhưng chỉ là lấn cận).
- **Không nguồn fact ngoài**: "ảo giác theo thế giới quan GPT" — bịa vượt tri thức GPT thì không bắt được.
- Config test `MAX_LAYERS=1` tiết kiệm nhưng nhiễu hơn production (L2 + both strategies).

### Đề xuất tiếp theo

1. **Code-exec self-consistency**: sinh 2–3 trace, majority-vote output; nếu không đồng thuận → hạ xuống UNKNOWN thay vì verified premise sai (rủi ro cao nhất hiện tại).
2. **Đối chiếu giải thích ↔ key**: thêm check "kết luận giải thích ủng hộ option nào" so với `is_correct` — phát hiện dạng lỗi "giải thích đúng nhưng chứng minh cho đáp án khác".
3. Thay `_is_question`/premise-guard regex bằng 1 call phân loại nhẹ hoặc rule phong phú hơn (đề imperative, câu dẫn danh từ bất kỳ).
4. Compound-option: chỉ kích hoạt khi có từ khoá tổng hợp ("tất cả/cả ... và/all of/both/neither"), không chỉ đếm ký tự key.
5. Hiệu chỉnh ngưỡng `p_answer`/crit/weights trên tập ~30–50 MCQ có nhãn (tối ưu F1) thay vì 0.5/0.70/0.4-0.3-0.3 cố định.
6. n-run aggregation cho case sát ngưỡng; config đầy đủ cho kết quả chính thức.
7. Dài hạn: interpreter thật cho code (node/deno) thay LLM trace; nguồn fact ngoài (retrieval) giảm phụ thuộc tri thức GPT.
