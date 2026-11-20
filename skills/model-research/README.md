# Model 资料同步、校验与评分维护

本程序将 Grokbot 成品 CSV 同步飞书，独立校验填表一致性，并每日维护语言模型的代码、Agent、数学评测。Markdown 由 Grokbot 管理，不生成正文或每日摘要，不使用旧研究队列。

## 三个独立服务

| 服务 | 数据与行为 | 模型调用 |
| --- | --- | --- |
| csv | 模型、Benchmark、渠道、量化输入；计划、增量写回、回读与人工保护 | 无 |
| validate | 四表字段规则及 CSV/线上逐项核对；只输出问题，不修表 | 无 |
| scores | 文字输出的生成式语言模型；来源变化检查、三能力成绩及证据维护 | 官方 Codex CLI |

每天北京时间12:00开始、18:00前重试；评分只等待同业务日模型表稳定并同步完成。安装时可用 `--start-date YYYY-MM-DD` 设置首次自动业务日，服务提前启动只待机，历史回放仍须显式指定日期。三套配置、state 与锁分开。没有当日文件时明确等待，不能把旧成功记录当今天完成。

## Grokbot 输入

配置 `root_folder_token` 与 `subdirectory: ["model"]` 等具名子目录；不递归混入其他目录。模型、Benchmark、渠道使用各自 `*_daily_{date}.csv`，量化使用 `Quant Trail_daily_{date}.csv`，可设 `required:false`。source_links/backfill 不处理，`md/existing` 与 `md/backfill` 继续由 Grokbot 管理。

量化当前按线上真实类型映射27列。原模型名称不能直接写入关联列；效果证据长句不能直接写入单选列，故这两列保留原 CSV 待明确映射。未知数值留空，不填0、不臆造显存/速度。

## 使用

Python 3.11+ 标准库、官方 lark-cli；scores 另需官方 Codex CLI。凭据、实际配置、参考集合与状态置于仓外，先读取 [SKILL.md](SKILL.md)、[配置样例](assets/project.example.json)和[部署指南](references/server-deployment.md)。

```text
python3 skills/model-research/scripts/research.py doctor --config <配置>
python3 skills/model-research/scripts/research.py run --config <CSV配置> --date <业务日> --mode apply
python3 skills/model-research/scripts/research.py validate --config <只读配置> --date <业务日>
python3 skills/model-research/scripts/research.py scores --config <评分配置> --date <业务日> --mode apply
```

同步配置显式允许写入；校验必须 allow_writes=false。旧 agent.enabled/command 不可启用；评分使用独立 scores 配置。无 manifest 时至少两次一致内容且间隔60秒才允许同步。无基线的非空值保留，后续三方比较保护人工修改，未知提交先 verify/resume，不按 CSV 缺行删除历史记录。

每日 run 按表独立执行：缺文件、文件晚到、解析或表格访问失败只影响相应表，其他就绪表继续同步。每表单独记录稳定观察，晚到文件不会重置其他表的计时；缺可选量化文件标记 skipped。报告 roles 中逐表查看 completed、waiting_input、partial 等状态，总体 partial 仍可能包含已验证写回。每表完成即保存 `state/daily/<role>-latest.json`，评分只依赖当天模型表 completed 且 observed_stable/producer_confirmed；不等待其他表或整个 CSV worker 结束。校验也逐表执行，保留总报告，不因一份 CSV 损坏而跳过其他表比较。

## MD 资料总览

CSV 配置可启用 `md_overview: {"enabled": true, "folder_token": "<已确认的 md 文件夹 token>"}`。每次定时 CSV apply 任务结束后，即使输入缺失或部分失败，也独立扫描 md/ 全部子目录，更新唯一 README.md，列出全库正文数、类别数、日期分组、目录统计及真实飞书文件链接。排除总览和其他 README/INDEX/_index.md；按文件计数，不按模型名称去重，不推断正文调研状态。扫描不完整时标注异常并保留上次完整索引；检测到人工修改或未知提交则保存候选并停止覆盖，不重复新建。每天及内容有变化时才发布新版本，同日未变只核验。

使用 `research.py md-overview --config <CSV配置> --date <日期> --mode plan|apply` 可手动预览或更新。它只读取文件元信息、不调用模型、不修改正文，也不生成每日变更摘要。当前统计、候选、发布回执和旧版本保存在 CSV state/md-overview/，任务结果保存在服务 last-run.md_overview，校验与评分任务不执行该写入。

## 评分与冻结版本

只处理输出文字的生成式语言模型；专项和基座单列，多模态模型只取本配置明确的文字能力成绩。字段仅限代码、Agent、数学；科学、通用、指令遵循不参与维护。新 Benchmark 输出三能力内映射候选，不自动扩充能力或修改公式权重。

新冻结版本需用户授权，先 freeze-scores --version <新版本>，再 recalibrate 生成计划，核实后用 --calibration-plan <计划> 写回。参考文件一旦存在不可覆盖；通过新文件和新版本进行下一次迁移。v0.3 使用固定参考样本的中位秩经验百分位，后续成绩按同一分布计算。完整规则与原权重见[架构](<../../docs/records/架构设计 Architecture Design 模型调研自动化.md>)。重算前保留快照，写前核对原值，写后验证，重复执行不重写。

日常评分读取实际公开源，再提取逐字证据、Benchmark版本与配置，不让模型编造标化分。记录和来源均未变化时跳过模型。每次新模型调用前查询官方账户额度，任一额度窗口已用达到90%、额度未知或北京时间18:00时暂停；临近18:00缩短模型超时，给进程清理留出时间。默认不设每日调用次数上限，实际调用持续记账；max_calls_per_day 缺省或 null 表示无次数上限，正整数可另设限制。失败回执支持后续继续；已提交的写回仍须完成核验，不把失败标成完成。

## 问题处理与验证

校验问题保存在 state/validation/latest.json、逐次 JSON 和问题 CSV。评分状态在 state/scores/latest.json、receipts 与私有调用材料。CSV 同步会自动归一可确定的格式问题，再经写前保护、写回和回读；例如多选单元格“评测框架+评测套件”对应两个已有选项。未知枚举、缺少可查证的 revision 和人工冲突保留为具体问题，不猜值或覆盖。validate 保持只读；没有自动通知或每日摘要。partial 仍需阅读具体原因，数据一致性不能证明资料真实。

```text
python3 skills/model-research/tests/run_tests.py --output <新的仓外目录>
```

测试结果含逐用例记录。真实 CSV、模型调用、写后回读、重复运行、调度与重启分别验收。旧 Markdown 源码及快照已清理，历史成果在 Git 和仓外归档中保留；[Grokbot 写作提示词](assets/grokbot-md-prompt.txt)继续可用。

评分版本、公式与参考样本数见[冻结评分规则](references/scoring.md)。
