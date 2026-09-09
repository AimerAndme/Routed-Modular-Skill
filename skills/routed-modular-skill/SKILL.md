---
name: routed-modular-skill
description: 通过可信模块索引进行带门禁的路由，按需加载指南，并使用 Schema、生命周期 Hooks、执行轨迹和可选状态持久化运行已注册脚本。
---

# Routed Modular Skill

所有路径相对本文件所在目录；工具调用使用解析后的绝对路径。

1. 读取 [模块索引](catalog.json)，或运行 `python3 scripts/rms.py list`。
2. 根据任务产生候选模块与分数，并运行 `route`。结果为 `needs_clarification` 时必须澄清，不得绕过门禁。
3. 只对 `selected` 模块运行 `load <id>`；需要多个模块时分别路由和加载。
4. 按模块指南及 [公共契约](shared/CONTRACT.md) 准备输入。输入和输出由运行时 Schema Hook 校验。
5. 使用 `run <id>` 调用已注册执行器。常规执行不要读取脚本源码，也不要重写已有算法。
6. 检查状态、结果和 trace。失败不得当作成功；需要恢复或审计时传入独立的 `--state-dir`。

仅在指南明确要求时读取模块附属资料。不要递归读取全部 modules/。运行时只执行 catalog 登记的可信脚本；它不是安全沙箱。
