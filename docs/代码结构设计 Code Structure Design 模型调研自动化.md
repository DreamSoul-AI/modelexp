# 模型调研自动化代码结构设计

> 2026-11-16范围更新：正文交给Grokbot，原Codex生成器、研究服务和队列已移除。当前实现为CSV同步与不调用模型的只读字段/一致性校验，详见[当前改造记录](<开发记录 Development Record/2026-11-16 正文外移与表格校验.md>)和[运行指南](../skills/model-research/README.md)。本文下方涉及自动研究、正文及队列的内容仅保留为历史设计。


版本：v0.6 · 状态：以下为首版已实现结构，真实自动写回已联调，长期无人值守仍待验收。依据 [架构设计](<架构设计 Architecture Design 模型调研自动化.md>) 划分职责，不改现有 `src/` 训练代码。

## 实现目录与职责

```text
skills/model-research/
├── SKILL.md
├── README.md
├── references/
│   ├── workflow.md
│   ├── entities-and-fields.md
│   ├── evidence.md
│   ├── sync.md
│   └── runtime.md
├── assets/
│   ├── project.example.json
│   ├── batch.example.json
│   └── dossier.template.md
├── scripts/
│   ├── common.py
│   ├── service.py
│   ├── research.py
│   ├── ingest.py
│   ├── identity.py
│   ├── evidence.py
│   ├── dossiers.py
│   ├── sources.py
│   ├── codex_agent.py
│   ├── sync.py
│   ├── lark_adapter.py
│   ├── state.py
│   └── agent_runner.py
└── tests/
    ├── run_tests.py
    └── scripts/test_*.py
```

目录内脚本、references、assets 及测试均已写入；使用入口见 [README](../skills/model-research/README.md)。外部已安装技能保存在 `.agents/skills/`，由锁文件恢复，不复制到本项目新 skill 的源码目录。

| 模块 | 主要职责 | 不承担的事情 |
|---|---|---|
| `research.py` | 参数校验、阶段调度、结果和退出状态 | 不内置 API 密钥或私有表 ID |
| `ingest.py` | 目录分页、批次发现、下载、版本固定、CSV 校验 | 不将缺文件解释成零条交付 |
| `identity.py` | 内部实体ID、来源别名、record_id 映射和歧义检测 | 不以名称或渠道ID单独匹配 |
| `evidence.py` | 来源版本、阅读范围、档案元信息与候选契约 | 不把 CSV 值当已核验结论 |
| `sync.py` | 三方比较、计划、前提检查、应用、回读和接续 | 不控制用户授权页面 |
| `lark_adapter.py` | 子进程 argv 调用、输出解析、分页及错误分类 | 不用 shell 拼接、不重实现 OAuth |
| `state.py` | SQLite 事务、锁、操作日志和已验证字段基线 | 不保存秘密凭据 |
| `agent_runner.py` | 调用配置的 Agent、限制任务范围、验证候选输出 | 不假定继承当前聊天的工具或登录 |

`SKILL.md` 说明触发范围、必读配置、阶段操作、失败恢复与验收。references 承载业务规则，assets 提供无凭据样例，详细 CLI 用法从已安装的版本匹配技能读取。

## 当前命令入口

以下命令已实现；前缀为 `python skills/model-research/scripts/`。入口脚本运行目录为仓库根目录，配置文件中的相对路径统一相对配置本身解析。

```text
research.py doctor --config <配置>
research.py inspect --role <角色> --config <配置>
research.py ingest --date <业务日> --config <配置> [--manifest <完成声明>]
research.py import-candidates --batch <批次ID> --candidates <JSON> --config <配置>
research.py plan --batch <批次ID> --config <配置>
research.py apply --plan <计划文件> --config <配置>
research.py verify --plan <计划文件> --config <配置>
research.py resume --run <运行ID> --config <配置>
research.py run --date <业务日> --mode <plan|apply> --config <配置>
research.py adopt --batch <批次ID> --entity <实体ID> --record-id <记录ID> --config <配置>
research.py resolve-identity --role <角色> --source-id <来源编号> --entity <实体ID> --config <配置>
research.py demo --directory <仓外空目录> --date <业务日>
```

`doctor` 初始化本地状态并检查配置后端/用户身份（不证明全部资源权限），`inspect` 读取选定角色的真实 schema 与完整记录；不自动登录、新建应用或改表。`plan` 不写云端。`apply` 校验计划、输入哈希、规则版本与授权范围，过期前提不能直接应用。`resume` 先处理 unknown/pending_verification，再推进其他操作。

首版不开放日常运行的 delete 或 reset 子命令。用户明确清空重导时走单独维护流程，固定来源、备份、确认范围和全量回读。

## 数据契约

- `batch.json`：schema_version、batch_id、business_date、输入角色/token/hash、生产方状态、接收范围。
- `candidates.json`：entity_id、字段候选值、evidence_ids、判断类别、适用版本与限制。只接受白名单字段，不接受命令、目标URL或任意文件路径作为执行指令。
- `plan.json`：plan_id、输入和规则版本、目标/字段ID、expected_old_value、new_value、证据、授权策略和操作ID。
- `report.json` / `report.md`：新增、更新、无变化、跳过、冲突、未知、失败和未执行的数量及入口。部分成功不计为整批成功。

`operation_id` 从操作类型、实体、身份、字段、新旧值、schema 和候选证明计算；目标首次新增时先建立实体级操作ID，再关联实际 record_id。序列化顺序和归一化规则要有版本，避免排序变化引发重复写入。

## 状态与文件

| 状态表 | 当前保存内容 |
|---|---|
| batches / runs | 不可变批次 JSON、每次尝试与结果 |
| entities / aliases | 内部实体、来源身份与当前别名 |
| mappings | 稳定实体与实际 record_id 配对 |
| baselines | 成功核验的字段值，按实体与字段独立保存 |
| operations | 计划、实体、提交状态、回执和待核验结果 |

schema/配置指纹与候选证据绑定在计划和档案，冲突保存在 plan/report 的 issues 中；首版没有另建 conflicts/channel_checks 空表。别名变更另有 identity-resolutions 审计文件。

SQLite 短事务配合 state_dir 级进程锁，不在网络请求中持有数据库事务。业务文件保存在仓外 incoming、batches、evidence、dossiers、requests、plans、runs、snapshots 和临时 cli/downloads 目录。原件按内容哈希保存；提交前先持久化 submitting，回读不确定不自动重发。单次运行报告边执行边保存。

## 依赖和适配

首版使用 Python 3.11+ 标准库（含 SQLite、fcntl、zoneinfo）和可配置的官方 CLI，无新增 Python 依赖，不向训练依赖中塞入整套爬虫/RAG框架。秘密信息与业务目标配置在仓库外。

调用 CLI 以退出码、业务信封和命令类型判断结果：普通 API 成功通常为 `ok=true`；NDJSON 导出返回 manifest，按其格式、records_count、has_more、产物路径和实际文件判断。不能把无 `ok` 的成功 manifest 判为失败。stdout 与 stderr 分开解析；错误只输出分类，不回显可能含秘密的原始 stderr。

字段/记录格式优先遵循已核实的 lark-base 规范；首次本地 CSV 转成 Base 使用 drive 导入链路，既有表的日常增量更新使用 record 操作。导入器可能推断类型，不能省略字段与内容核验。

## 验证入口

```bash
python skills/model-research/tests/run_tests.py --output /tmp/model-research-results
```

测试覆盖输入版本、身份重编号、证据协议、人工正文、三方冲突、字段保护、分页、未知提交、接续、进程锁和完整 CLI 本地旅程，结果逐项持久化。测试目录与 scripts 模块对应，不运行原训练测试。

飞书只读联调已完成渠道云盘下载、14 行/12 列快照和计划生成；新程序已完成真实新增与回读、重复计划零操作和原数据保护核对。当前云环境已部署apply自动写回，独立Codex已实际读取模型卡并写入研究正文；刷新凭据过期续期、主机重启和完整定时周期尚未验收。具体命令、结果与证据见 [运行记录](<运行记录 Run Record/2026-11-14 自动化首版实现验证.md>)。

## 当前CSV直接路径

research.run → ingest → CSV字段映射/格式统一 → sync.plan → submit_batches → lark批量记录接口 → 全部目标回读。allow_new_options只对配置允许的单选标签追加，实时选项分页补齐；模型链接列只写入规范URL。后台研究及MD保留为可选模块，日常CSV处理不调用agent_runner。

## 独立研究入口

research.py research → research_pipeline.workset → agent_runner → 有证据的MD正文。状态目录、SQLite及进程与CSV分开，不调用sync.plan/apply，也不维护下拉选项。工作集合合并同配置下保留的正常日报，按实体保留最新输入并优先当天，复用成功研究回执。service mode增加research，其配置必须禁用远端写入。

## 阅读交付

markdown_delivery.finalize清理完全匹配的旧占位章节并备份，保留生成段指纹、原输入和人工扩写；export导出经过指纹检查的AI正文，拒绝覆盖人工修改过的快照。reports/model-research存储本次阅读快照，私有运行数据及认证不进入Git。deploy/model-research@.service和服务器指南定义目标目录及开机恢复方式，新服务器行为须另验收。
