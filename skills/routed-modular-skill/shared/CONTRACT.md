# 模块调用契约 v2

每个模块在 catalog.json 中声明输入 Schema、输出 Schema、执行入口与生命周期 Hooks。

- 输入为 JSON 对象，执行前由 `pre` Hook 校验。
- 脚本从 stdin 读取输入，仅向 stdout 输出含 `result` 对象的 JSON。
- 输出在返回前由 `post` Hook 校验；校验失败不得交付结果。
- 失败向 stderr 写诊断并以非零状态退出，`on_error` Hook 记录错误阶段。
- 执行器返回 execution_id 与 trace；传入 `--state-dir` 时原子写入本地状态文件。
- 多个模块的结果不自动聚合，不隐含调用顺序或业务依赖。

当前运行时只实现项目使用的 JSON Schema 子集：`type`、`required`、`properties`、`additionalProperties` 与数组 `items`。这不是完整 JSON Schema 实现。
