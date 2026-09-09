# Routed Modular Skill

一种面向复杂 Agent Skill 的路由式模块化运行时：通过路由门禁选择模块，按当前场景加载文档，并使用 Schema、生命周期 Hooks、执行轨迹和可选状态持久化运行脚本。

本项目是架构约定与可运行参考模板，不是独立 Agent、正式行业标准或完整工作流引擎。名称简称 RMS。

## 为什么需要它

当一个 Skill 覆盖多种业务场景，把所有规则和示例放进 SKILL.md 会导致上下文膨胀。本架构将选择模块所需的信息与执行细节分开。门店奖励、报表生成和多平台部署均可采用这种组织方式。

## 目录

```text
README.md
skills/routed-modular-skill/
  SKILL.md                 # Agent 入口
  catalog.json             # 路由元数据、I/O Schema 与 Hooks
  scripts/rms.py           # list / route / load / run 参考运行时
  shared/CONTRACT.md       # 公共输入输出约定
  modules/
    text-length/
      GUIDE.md
      scripts/run.py
    text-uppercase/
      GUIDE.md
      scripts/run.py
tests/test_runtime.py
```

Skill 使用小写目录以匹配 frontmatter 名称。README 位于仓库层，不要求 Agent 在业务执行时读取。索引采用 JSON，使 Python 标准库即可运行；它与此前提出的 catalog.yaml 承担相同职责。

## 加载流程

1. 宿主发现并激活 SKILL.md。
2. Agent 根据 id 和 when 生成候选模块及分数；路由门禁拒绝低置信度或差距过小的选择。
3. load 仅返回命中模块的指南、Schema、Hooks 及公共契约路径。
4. pre Hook 校验输入，Executor 运行已注册脚本，post Hook 校验结果。
5. 运行时返回 execution_id 与 trace，并可选写入本地状态文件。
6. 将通过门禁的结构化结果交给业务层解释或汇总。

目录不会自动调度。自然语言意图识别由宿主 Agent 完成；本参考执行器只接受明确的模块 ID，不做关键词猜测。脚本直接执行，不需要把源码全部读入模型上下文。上下文已经加载的内容也不会由本项目自动卸载。

## 快速开始

需要 Python 3.10+，无第三方依赖。从仓库根目录运行：

```sh
python3 skills/routed-modular-skill/scripts/rms.py list
python3 skills/routed-modular-skill/scripts/rms.py route --candidates '[{"id":"text-length","score":0.92},{"id":"text-uppercase","score":0.20}]'
python3 skills/routed-modular-skill/scripts/rms.py load text-length
python3 skills/routed-modular-skill/scripts/rms.py run text-length --input '{"text":"你好 RMS"}'
python3 skills/routed-modular-skill/scripts/rms.py run text-uppercase --input '{"text":"hello"}'
python3 skills/routed-modular-skill/scripts/rms.py run text-length --input '{"text":"audit"}' --state-dir .rms-state
python3 -m unittest discover -s tests -v
```

第三条命令返回 result.length = 6；第四条返回 result.text = HELLO。示例用于验证加载机制，不包含真实门店奖励公式。

在支持文件读取和脚本执行的 Agent 中，将 `skills/routed-modular-skill/` 整个目录复制到该宿主认可的 Skill 目录，然后让 Agent 使用该 Skill 统计文本长度或转换大写。不同宿主的发现位置和授权机制需按其配置设置。

## 新增业务模块

1. 创建 modules/<id>/GUIDE.md，描述适用范围、输入、执行命令、输出和边界。
2. 创建 scripts/run.py，从 stdin 接收 JSON，向 stdout 写出含 result 的 JSON 对象；诊断写 stderr，失败返回非零退出码。
3. 在 catalog.json 添加唯一 id、简短 when、guide、entrypoint、输入/输出 Schema 和 Hooks，所有路径相对 Skill 根目录。
4. 增加业务结果与失败场景测试。只有真正共用的规则才进入 shared/，模块专属规则留在模块内。

资源或模板实际需要时再在模块下添加 resources/，在 GUIDE.md 中写明何时读取。不要预先枚举所有资源正文。需要多个模块时逐个显式选择；互斥、封顶、依赖顺序等组合规则由业务 Skill 定义，本模板不默认合并结果。

## 约定与边界

- SKILL.md 保存公共流程，catalog 只保存路由元数据，GUIDE 保存分支说明，脚本保存确定性实现。
- 以整个 Git 提交作为文档与脚本的发布单元，避免分别更新造成版本漂移。
- 未知模块、歧义路由、非法输入、非零退出、超时、无效输出均被门禁阻断。
- 路径必须限制在 Skill 根目录；只运行索引登记的脚本。
- 本地子进程不是安全沙箱，仅执行经过审查的可信模块；运行权限沿用宿主环境。
- JSON 输出结构检查不等同于业务结果正确，真实计算需另加已知答案测试。
- 路由分数由宿主 Agent 或上游分类器提供；阈值门禁不能证明语义分类本身正确。
- 当前 Schema 校验器仅实现仓库所需子集；生产环境可替换为完整 JSON Schema 实现。
- 未选择开源许可证；如需对外授权复用，应由维护者明确许可。

## 参考

- [Agent Skills 目录规范](https://agentskills.io/specification)
- [客户端按需加载指南](https://github.com/agentskills/agentskills/blob/main/docs/client-implementation/adding-skills-support.mdx)

modules/、GUIDE.md 与 catalog.json 是本项目的扩展约定，并非 Agent Skills 标准字段。
