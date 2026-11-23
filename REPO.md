# modelexp 项目约定



## 用途与当前范围



原仓库是 RPipe 风格的图像分类实验流水线，源码位于 `src/`。用户在 `gyd` 分支开发 Model调研自动化，新增能力与现有训练流程分开组织。



当前已实现skills/model-research/统筹skill与标准库CLI；当前日常路径直接采用Grokbot成品CSV，统一列映射、选项及URL格式后按表批量同步并回读，不再重复调研。Codex公开来源阅读与MD正文使用独立research服务，和CSV进程、状态目录及锁分开运行。长期无人值守、主机重启恢复仍需验收。



## 项目规则



- 使用现有 checkout；用户要求的工作分支为 `gyd`。不为本任务额外创建 worktree，不擅自推送或发布。

- 保留 `src/`、`requirements.txt` 和既有实验行为。自动化代码独立放在 `skills/model-research/`，仅需 Python 3.11+ 标准库和可配置的官方 CLI。

- 当前飞书采用模型评测、Benchmark、量化与后训练、渠道四表结构。能力筛选通过模型主表视图组织。

- 渠道当前有效来源为按平台聚合的 14 条清单；历史 489 条和 67 条已被用户要求替换。渠道ID曾被上游重编，跨批匹配必须核对实体身份，旧 record_id 不可继承使用。

- `source_links` 与 `backfill` 文件按用户要求暂不处理；这不妨碍保存当前渠道入口及新调研结论的来源依据。

- 日常同步设计采用增量更新，不因源文件缺行而删除线上记录。清空重载仅作为用户明确提出的维护操作。

- 人工字段、评分参考集合、评分版本与公式列需明确规则；未配置归属的字段只生成候选，不自动覆盖。

- 业务日期与调度时区使用 `Asia/Shanghai`；业务日期、采集时间和实际同步时间分别记录。



## 资料与工作入口



- [文档导航](docs/README.md)：当前设计、计划、资料依据与历史核验。

- [架构设计](<docs/架构设计 Architecture Design 模型调研自动化.md>)：系统职责、数据、同步与运行设计。

- [代码结构设计](<docs/代码结构设计 Code Structure Design 模型调研自动化.md>)：当前已实现的模块、接口与状态边界。

- [开发计划](<docs/开发计划 Development Plan 模型调研自动化.md>)：后续实现顺序、依赖和验收。

- 模型与渠道资料、飞书原始响应、同步基线及凭据保存在仓库外；正式设计仅维护必要的结构、入口和证据范围。



## 环境、技能与验证



- 实验环境已准备 Python 3.11 和 PyTorch CPU 版；训练程序从 `src/` 运行。自动化设计不要求 GPU，不启动训练。

- `lark-cli` 当前验证版本为 1.0.100；实际可执行路径、配置目录和凭据目录通过本机配置提供，不能硬编码进共用程序。

- 本项目安装了 knowledge 的 10 个当前技能及飞书 25 个技能，目录为 `.agents/skills/`，来源和指纹见 `skills-lock.json`。这些是外部技能，与本项目已实现的 `skills/model-research/` 分开维护。

- 技能锁文件随项目维护，安装目录本地忽略。新环境恢复前先检查安装器帮助和版本，再按锁文件恢复；上游内容改变时应明确更新，不静默接受漂移。

- 已有 Cloud 技能与项目文件是否在新会话中被发现要分别核验；不通过修改聊天内的技能清单冒充安装。

- 当前程序已通过本地端到端及失败恢复测试；飞书用户身份、渠道 CSV 下载、14 行/12 列读取和只读计划已联调。新程序已完成三条模型新增、逐项回读和原385条/74列不变核对；跨任务凭据恢复、真实过期续期和长期运行仍需继续验证。

- 业务配置和 state_dir 放 checkout 外。Cloud 工作区文件不等于 GitHub 已推送或飞书已同步；配置样例不含私有目标和凭据。



## 文档适配与维护



沿用现有 `docs/` 和已确认的双语文件名，不复制公司部门目录。设计、代码结构、计划、工程依据、活动问题、开发记录和运行记录分别由文档导航定位；纯工程设计阶段不另造论文综述或科学实验计划。



历史 `同步核对 Sync Review` 文件保留名称和证据语义，通过当前入口说明其历史性质。正式记录逐步按 `开发记录 Development Record/` 与 `运行记录 Run Record/` 保存。本轮仅对受影响的入口和内容进行适配。



真实 `USER.md`、凭据与私有项目配置不提交。模板来源及采用范围见本次开发记录；模板更新不自动重建个人配置或启动历史定时任务。



## 当前自动写回规则



按用户明确要求，部署可用apply模式，不再固定停在只读。既有模型基础字段的非空人工值无基线时保留，允许在有来源依据时补空或新建；成功回读后程序维护字段保存基线，后续三方比较保护人工变化。渠道备注与已知访问问题保持人工维护，评分、公式和未映射列不写入。无生产方manifest时采用两次一致内容观察，不要求用户额外手工搬运或补MD。



用户于2026-11-14进一步明确：Grokbot已准备完整CSV，只需字段匹配、格式统一与直接同步，不重新调研。当前采用project.csv-sync.json，accept_upstream/prefer_upstream开启，Agent关闭，批量最多200条；发布者单选允许追加来自CSV的新标签，保留原选项及字段属性。其余表结构和评分不改。单链接字段只提交URL本体，完整原CSV保存在状态目录。



当前每日同步启动时间已按用户最新要求调整为北京时间12:00，18:00前保持原有重试规则；程序通用默认值仍为15:00，部署必须显式传--at 12:00，避免重装恢复旧时间。



## 云环境恢复时的运行核对



新实例恢复时，已保存的process.json和heartbeat.json不证明任务存活。先调用现有manage status并核对真实PID、启动指纹和业务日期；在用户已授权的自动同步范围内，验证后端连接后可用manage start恢复已有部署，不重新install、不回放历史字段修改、不发布环境。当天补跑结果必须回读，不能把旧日期的completed当作今天成功。若用户当前明确要求暂停执行，则只做读取核对。



2026-11-15已实际发生实例切换后进程缺失：当前环境启动说明仍为MNIST，无服务恢复步骤。恢复进程后当天91条模型和2条Benchmark新增回读通过，14条渠道已核对。启动说明也不能唤醒暂停实例，当前部署不具备暂停期间准点执行保障；详细边界见环境切换与定时恢复运行记录。



## 当前双任务运行



2026-11-15已恢复独立AI研究服务：CSV仍在/workspace/services/model-research，AI在/workspace/services/model-research-ai。AI使用research模式、独立state_dir、allow_writes=false，只写证据和MD，不调用表格plan/apply；CSV直接同步保持原设置。两项每日12:00启动，CSV重试至18:00，AI研究队列独立接续至23:59，旧正常日报的未完成项跨日期保留。研究正文以独立AI目录state/dossiers为准，CSV目录的输入MD不等于研究成果。



恢复实例时在现有授权范围分别核对两项manage status/start；不得把Agent关闭的CSV服务当成全部自动化。启动说明已保存到环境草稿，尚未发布；这不是平台级唤醒，暂停期间准点运行仍未解决。



## 定稿与服务器移交



版本0.6已提供finalize-md和export-md。Git研究报告位于reports/model-research，只含已生成正文和来源；原CSV、私有配置、SQLite、认证及人工笔记不发布。模板清理只能删除完全匹配的系统占位章节，必须保留人工扩写、代码围栏及生成段指纹。服务器部署及状态迁移依照skills/model-research/references/server-deployment.md；持久在线和新服务器验收仍待用户租用主机后完成。



## Workspace 采用记录



- 来源 [Workspace 098bd2e](https://github.com/DreamSoul-AI/workspace/tree/098bd2eccf23eb1e6d77a3eec6db51e6bc387daf)。采用范围为Learnings 命名与分发、文档规范配置、长作业检查点与恢复、调研、研究计划与研究结论归档、发布前分支对齐。项目专用流程见本文件。

- 单项更新：[Workspace 65657c5](https://github.com/DreamSoul-AI/workspace/tree/65657c50cf6d98ac1898ae0183cb9ca98498e0a9)。采用旧对话重读、新对话定位、文档主动补链接、浏览器收尾、飞书专节及 CLI 任务临时目录、共享资源主动检查；保留项目专有约定和原整版基线。共享 data/models 直接复用，仅 artifacts 按仓库隔离，接入示例见 [Workspace 教程](https://github.com/DreamSoul-AI/workspace/blob/main/templates/software-engineering/examples/shared-resources/README.md)。

- 单项更新：[Workspace f01fab8](https://github.com/DreamSoul-AI/workspace/tree/f01fab8598f570a45eca8320e546d636268b700a)。采用通用文档规范及飞书/GitHub 平台章节入口、首次接入默认值和已有选择保留、代码架构设计与代码结构设计并列命名；图表简洁要求随通用规范读取。保留本项目专有约定、既有文档路径及原整版基线。[规范分发副本](https://github.com/DreamSoul-AI/workspace/blob/f01fab8598f570a45eca8320e546d636268b700a/%E6%96%87%E6%A1%A3/%E8%A7%84%E8%8C%83/%E9%80%9A%E7%94%A8/%E9%80%9A%E7%94%A8%E6%96%87%E6%A1%A3%E8%A7%84%E8%8C%83.md)。
- 单项更新：[Workspace 823d496](https://github.com/DreamSoul-AI/workspace/tree/823d4965035899d66a2d57751f1d28fbf934f99a)。采用临时产物与共享入口分工、资料根定位、目录升级检查、双端文档先改本地及面向读者的汇报；源码、测试、项目 docs 与专有约定保留，原整版基线继续沿用。
- 单项更新：[Workspace ea16de5](https://github.com/DreamSoul-AI/workspace/tree/ea16de5eda676aadaeefc1897ce0b83c062de2b6)。采用常规问题直接处理、结合目标和进度主动建议下一步；Knowledge 能力更新沿 [Workspace 教程](https://github.com/DreamSoul-AI/workspace/blob/main/资料/教程和工具/使用教程.md#workspace-与-knowledge-更新) 默认接入，保留通用与个人来源、项目专有约定和原整版基线。
