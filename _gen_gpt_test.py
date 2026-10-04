import json, re

P = "BTProp_MCQ_GPT.ipynb"
nb = json.load(open(P, encoding="utf-8"))
cells = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]

# cells[0]=install(skip), [1]=config, [2]=prompts, [3]=LLM OpenAI, [4]=NLI,
# [5]=TreeGen, [6]=HMM, [7]=BTProp, [8]=MCQ, [9]=run
src = cells[1] + "\n\n" + "\n\n".join(cells[2:10])

# bỏ dòng ! / %
src = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith(("!", "%")))

# ---- Chế độ tiết kiệm token ----
src = src.replace("MAX_LAYERS = 2", "MAX_LAYERS = 1")
src = src.replace("FORCE_BOTH_STRATEGIES = True", "FORCE_BOTH_STRATEGIES = False")

# non-interactive: thay input() + chạy batch nhiều test case
src = re.sub(r'raw = input\(.*?\)\.strip\(\)', 'raw = ""', src)

TESTS_SRC = '''
TESTS = [
# T24: var + setTimeout closure — output thật "A, B, 3, 3, 3" (B) nhưng key A true; giải thích VI đúng, có claim phản thực (let -> 0,1,2)
r"""{"content": "Cho đoạn mã JavaScript sau:\\n\\n```javascript\\nconsole.log(\\"A\\");\\n\\nfor (var i = 0; i < 3; i++) {\\n  setTimeout(() => console.log(i), 0);\\n}\\n\\nconsole.log(\\"B\\");\\n```\\n\\nHỏi: Thứ tự các giá trị được in ra console là gì?",
  "options": [
    {"key": "A", "text": "A, B, 0, 1, 2", "is_correct": "true"},
    {"key": "B", "text": "A, B, 3, 3, 3", "is_correct": "false"},
    {"key": "C", "text": "A, 0, 1, 2, B", "is_correct": "false"},
    {"key": "D", "text": "A, B, 2, 2, 2", "is_correct": "false"}
  ],
  "explanation": "Lệnh console.log(\\"A\\") được thực thi đầu tiên. Vòng lặp tạo ra ba callback setTimeout nhưng các callback không được thực thi ngay lập tức. Vì sử dụng var nên biến i dùng chung cho cả ba callback. Sau khi vòng lặp kết thúc, i có giá trị 3. Tiếp theo console.log(\\"B\\") được thực thi. Khi event loop xử lý các callback, cả ba callback đều đọc giá trị hiện tại của i là 3. Vì vậy kết quả là A, B, 3, 3, 3. Việc sử dụng let thay cho var sẽ làm mỗi lần lặp có một binding i riêng, khi đó kết quả mới là A, B, 0, 1, 2."}""",
# hồi quy T23 (code mode, DOM listener) — expect B=1 true sai, A=0 false đúng
r"""{"content": "Consider the following HTML and JavaScript code:\\n\\n<button id=\\"btn\\">Click</button>\\n<script>\\nlet count = 0;\\ndocument.getElementById('btn').addEventListener('click', function() {\\n  count++;\\n});\\nconsole.log(count);\\n</script>\\n\\nWhat will be printed to the console immediately when the script runs, before the button is clicked?",
  "options": [
    {"key": "A", "text": "0", "is_correct": "false"},
    {"key": "B", "text": "1", "is_correct": "true"},
    {"key": "C", "text": "undefined", "is_correct": "false"},
    {"key": "D", "text": "An error occurs because addEventListener changes count.", "is_correct": "false"}
  ],
  "explanation": "The variable count is initialized to 0. Adding the click event listener does not execute the callback immediately. Therefore console.log(count) prints 0 before the user clicks the button. If the button is clicked once, count becomes 1."}""",
# hồi quy T19 (answer-key, không code)
r"""{"content": "Thủ đô của Pháp là thành phố nào?",
  "options": [
    {"key": "A", "text": "Paris", "is_correct": "false"},
    {"key": "B", "text": "Trái Đất quay quanh Mặt Trời.", "is_correct": "true"},
    {"key": "C", "text": "Nước sôi ở 100 độ C ở áp suất khí quyển chuẩn.", "is_correct": "false"},
    {"key": "D", "text": "Sông Seine chảy qua Paris.", "is_correct": "false"}
  ],
  "explanation": "Paris là thủ đô của Pháp."}""",
# hồi quy T20 (premise thật world-check)
r"""{"content": "Tất cả động vật có vú đều đẻ con. Cá voi là động vật có vú. Vì vậy, tất cả động vật đẻ con đều là cá voi.",
  "options": [
    {"key": "A", "text": "Cá voi là động vật có vú.", "is_correct": "true"},
    {"key": "B", "text": "Cá voi đẻ con.", "is_correct": "true"},
    {"key": "C", "text": "Tất cả động vật đẻ con đều là cá voi.", "is_correct": "true"},
    {"key": "D", "text": "Cá voi là loài cá và không phải động vật có vú.", "is_correct": "false"}
  ],
  "explanation": "Cá voi thực sự là động vật có vú và cá voi đẻ con. Từ việc tất cả động vật có vú đều đẻ con và cá voi là động vật có vú, có thể suy ra cá voi đẻ con. Tuy nhiên, không thể suy ngược rằng tất cả động vật đẻ con đều là cá voi. Cá voi là loài cá nên không phải động vật có vú."}""",
]
TESTS_OLD = [
# T16: đáp án "all feathered animals are penguins" (converse sai) bị đánh dấu đúng -> kỳ vọng VERY HIGH
r"""{"content": "Tất cả loài chim đều có lông vũ. Chim cánh cụt là loài chim. Vì vậy, mọi động vật có lông vũ đều là chim cánh cụt.",
  "options": [
    {"key": "A", "text": "Chim cánh cụt có lông vũ.", "is_correct": "true"},
    {"key": "B", "text": "Mọi động vật có lông vũ đều là chim cánh cụt.", "is_correct": "true"},
    {"key": "C", "text": "Tất cả chim đều có lông vũ.", "is_correct": "true"},
    {"key": "D", "text": "Chim cánh cụt không phải là chim.", "is_correct": "false"}
  ],
  "explanation": "Từ việc tất cả chim đều có lông vũ và chim cánh cụt là chim, có thể suy ra chim cánh cụt có lông vũ. Tuy nhiên, không thể suy ngược rằng mọi động vật có lông vũ đều là chim cánh cụt."}""",
# T17: premise đề bịa (mọi hành tinh có sự sống) nhưng A suy đúng -> PROVEN + h_premise>=0.7 -> VERY HIGH
r"""{"content": "Tất cả hành tinh trong Hệ Mặt Trời đều có sự sống. Sao Hỏa là một hành tinh trong Hệ Mặt Trời. Vì vậy, Sao Hỏa có sự sống.",
  "options": [
    {"key": "A", "text": "Sao Hỏa có sự sống.", "is_correct": "true"},
    {"key": "B", "text": "Tất cả hành tinh trong Hệ Mặt Trời đều có sự sống.", "is_correct": "true"},
    {"key": "C", "text": "Sao Hỏa không phải là hành tinh trong Hệ Mặt Trời.", "is_correct": "false"},
    {"key": "D", "text": "Sao Hỏa không có sự sống.", "is_correct": "false"}
  ],
  "explanation": "Nếu giả sử tất cả hành tinh trong Hệ Mặt Trời đều có sự sống và Sao Hỏa là một hành tinh trong Hệ Mặt Trời, thì theo modus ponens có thể suy ra Sao Hỏa có sự sống. Tuy nhiên, tiền đề rằng tất cả hành tinh đều có sự sống là sai theo kiến thức thực tế."}""",
# T18: câu phủ định KHÔNG thuộc EU, đánh dấu Đức sai + Thụy Sĩ (đáp án thật) là distractor -> ANSWER_KEY_INCONSISTENCY + VERY HIGH
r"""{"content": "Quốc gia nào sau đây KHÔNG thuộc Liên minh châu Âu (EU)?",
  "options": [
    {"key": "A", "text": "Pháp", "is_correct": "false"},
    {"key": "B", "text": "Đức", "is_correct": "true"},
    {"key": "C", "text": "Tây Ban Nha", "is_correct": "false"},
    {"key": "D", "text": "Thụy Sĩ", "is_correct": "false"}
  ],
  "explanation": "Pháp, Đức và Tây Ban Nha đều là thành viên của Liên minh châu Âu. Thụy Sĩ không phải là thành viên của Liên minh châu Âu. Vì câu hỏi hỏi quốc gia KHÔNG thuộc EU nên đáp án đúng là Thụy Sĩ."}""",
]
'''
src = src.replace('raw = ""', TESTS_SRC + '\nraw = ""')

# driver: mỗi test 1 cặp file STT riêng (run_gpt_NN.log + btprop_result_NN.json), không đè file cũ
NEW_DRIVER = (
    "import glob as _glob, io\n"
    "class _Tee(io.TextIOBase):\n"
    "    def __init__(self, a, b): self.a, self.b = a, b\n"
    "    def write(self, s):\n"
    "        self.a.write(s); self.b.write(s); return len(s)\n"
    "    def flush(self): self.a.flush(); self.b.flush()\n"
    "def _next_stt():\n"
    "    _pre = 'btprop_result_'\n"
    "    _ns = [int(_p[len(_pre):-5]) for _p in _glob.glob(_pre + '*.json')\n"
    "           if _p[len(_pre):-5].isdigit()]\n"
    "    return max(_ns) + 1 if _ns else 1\n"
    "for _ti, _tj in enumerate(TESTS, _next_stt()):\n"
    "    _log = open(f'run_gpt_{_ti:02d}.log', 'w', encoding='utf-8', errors='replace')\n"
    "    _o = sys.stdout; sys.stdout = _Tee(_o, _log)\n"
    "    try:\n"
    "        print()\n"
    "        print('#'*30 + f' TEST {_ti:02d} ' + '#'*30)\n"
    "        data = json.loads(_tj)\n"
    "        report = evaluate_mcq(data, btprop)\n"
    "        report['test_no'] = _ti\n"
    "        print_report(report)\n"
    "        with open(f'btprop_result_{_ti:02d}.json', 'w', encoding='utf-8') as _f:\n"
    "            json.dump(report, _f, ensure_ascii=False, indent=2)\n"
    "        print(f'>> btprop_result_{_ti:02d}.json + run_gpt_{_ti:02d}.log')\n"
    "    finally:\n"
    "        sys.stdout = _o; _log.close()"
)
src = re.sub(r"data = json\.loads\(raw or EXAMPLE_JSON\)[\s\S]*$",
             lambda m: NEW_DRIVER, src)
assert 'enumerate(TESTS' in src, 'driver replace failed'

src = ("import sys, time\n"
       "sys.stdout.reconfigure(encoding='utf-8', errors='replace')\n"
       "sys.stderr.reconfigure(encoding='utf-8', errors='replace')\n"
       "t0 = time.time()\n" + src +
       '\nprint(f"\\n=== Tổng thời gian: {(time.time()-t0)/60:.1f} phút ===")\n')

with open("btprop_gpt_test.py", "w", encoding="utf-8") as f:
    f.write(src)
compile(src, "btprop_gpt_test.py", "exec")
print("written,", len(src.splitlines()), "lines")
