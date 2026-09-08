# 文本长度

读取 ../../shared/CONTRACT.md。输入 text 必须为字符串。
在 Skill 根目录执行 `python3 scripts/rms.py run text-length --input '{"text":"你好 RMS"}'`。
输出 result.length = 6，计数包含空格。使用 Python len 的 Unicode 码点语义，组合字符和 emoji 可能包含多个码点，不是可视字形计数。空字符串结果为 0。
正常执行无需读取脚本源码或其他模块指南。
