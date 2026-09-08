# 文本大写转换

读取 ../../shared/CONTRACT.md。输入 text 必须为字符串。
在 Skill 根目录执行 `python3 scripts/rms.py run text-uppercase --input '{"text":"hello"}'`。
输出 result.text = HELLO。采用 Python str.upper 的 Unicode 语义，转换后长度可能变化（如 ß 变为 SS）；空字符串保持为空。
正常执行无需读取脚本源码或其他模块指南。
