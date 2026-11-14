# Model 调研自动化

在 `gyd` 分支实现的首版 skill。接收指定业务日的 CSV，保留原件，建立稳定实体与 Markdown 档案，接收带证据的调研候选，生成并执行飞书字段增量计划。原有 `src/` 训练流程不受影响。

## 先跑本地演示

Python 3.11+，Linux/macOS，无新增 Python 依赖。从仓库根目录执行；示例目录必须为空且位于 checkout 外，可换成自己的绝对路径。

```bash
python skills/model-research/scripts/research.py demo --directory /tmp/model-research-demo --date 2026-11-13
python skills/model-research/scripts/research.py run --config /tmp/model-research-demo/project.json --date 2026-11-13 --mode apply
python skills/model-research/scripts/research.py run --config /tmp/model-research-demo/project.json --date 2026-11-13 --mode apply
```

演示只操作目录内的 JSON 后端：第一轮新增两个渠道，第二轮零操作。它用于验证流程，不进行真实调研，也不访问飞书。

## 接入实际项目

1. 将 [配置样例](assets/project.example.json) 复制到 checkout 外。配置、业务状态和凭据分别保管；配置与 state_dir 推荐都放持久磁盘。此云环境的 `/workspace` 是运行机文件系统，写文件不会自动进入 GitHub 或飞书。
2. 读取 [SKILL.md](SKILL.md)，使用已安装的飞书技能确认 CLI、用户登录和目标范围。实际 CLI 可执行路径通过 `backend.command` 的 argv 数组提供，不依赖固定机器路径。
3. 配置真实 base_token、table_id、field_id、CSV 列、类型与身份键。角色可配置 models、benchmarks、artifacts、channels 等；脚本不创建表，不推断未确认的映射。先用 `doctor` 和 `inspect --role <角色>` 检查。
4. 默认 `allow_writes=false`、字段 `policy=unassigned/manual`、`allow_create=false`。实际已授权的 AI 字段才设为 `ai`；新建还需满足身份和 required_on_create。类型、枚举和只读规则始终以实时 schema 核对。
5. 生产方完成声明参照 [manifest](assets/batch.example.json)。没有声明时默认禁止apply；可配置stable_observations，以至少60秒间隔的两次一致内容观察确认暂时稳定，变化或缺失会重新观察。allow_unconfirmed_input只供明确接受未确认输入的场景，不是本次自动部署采用的方式。

当前用户已确认Grokbot CSV是同步来源，日常流程直接导入。相应字段设置accept_upstream=true、prefer_upstream=true，agent.enabled=false且不配置agent.command；旧调研候选不盖过CSV，后续人工修改仍受三方比较保护。CSV来源归档不等于本程序独立验证其研究结论。

列名按column/column_aliases定位，value_aliases仅使用明确同义映射；多选兼容中文逗号，单选保留完整发布者名称。实时读取全部下拉选项，CLI截断时继续分页。明确配置allow_new_options的发布者单选可追加新标签，保留原选项、类型、说明和默认值。backend.batch_size=200按表批量提交，统一回读；提交结果不明时先核验，不重复新增。

## 一次完整处理

以下尖括号是待替换参数。命令均从仓库根目录运行。

```text
python skills/model-research/scripts/research.py doctor --config <项目配置>
python skills/model-research/scripts/research.py inspect --config <项目配置> --role <角色>
python skills/model-research/scripts/research.py ingest --config <项目配置> --date <业务日> [--manifest <完成声明>]
python skills/model-research/scripts/research.py import-candidates --config <项目配置> --batch <批次ID> --candidates <候选JSON>
python skills/model-research/scripts/research.py plan --config <项目配置> --batch <批次ID>
python skills/model-research/scripts/research.py apply --config <项目配置> --plan <计划文件>
```

`run --date <业务日> --mode plan|apply` 串起上述阶段，可传 `--candidates`。存在需要调研的字段而未配置 Agent 时，返回 waiting_research 和 request 文件，交由当前 Agent 依 [候选协议](references/evidence.md) 查证并生成候选。脚本不冒充已经搜索或读过来源。

若要无人值守执行，配置 `agent.command`：程序接收追加的 request JSON 路径，以 stdout 返回候选 JSON，诊断写 stderr，非零退出或超时视为失败。程序需自行提供检索、模型认证和工具；详见 [运行协议](references/runtime.md)。已提供真实Codex适配器；配置与自动调度见下文。

## 初始基线与失败恢复

已有线上值与候选不同且无基线时，先核对唯一实体及 record_id，再执行本地 `adopt`；该命令将线上值镜像为本地基线，保留 Markdown 正文，不写飞书。随后重新导入研究候选再 plan。

```text
python skills/model-research/scripts/research.py adopt --config <项目配置> --batch <批次ID> --entity <实体ID> --record-id <线上记录ID>
python skills/model-research/scripts/research.py verify --config <项目配置> --plan <原计划文件>
python skills/model-research/scripts/research.py resume --config <项目配置> --run <原运行ID>
```

`verify` 只查询并对账，绝不重发写请求；`resume` 回到原计划，先对账未知提交，再处理未提交项。同一实体有 unknown/submitting/submitted 时，新批次不能绕过该状态。查不到已提交结果时继续保留 unknown，不自动重建。

源编号重编由身份冲突阻断；人工核对之后，可用 `resolve-identity --role <角色> --source-id <来源编号> --entity <实体ID>` 修正本地别名。它不变更线上记录和历史批次。

## 产物与验证

配置的 state_dir 下保存 incoming 原件、batches、evidence、dossiers、requests、plans、runs 与 SQLite 映射/基线/操作日志。Markdown front matter 使用 JSON（合法 YAML）；生成段可由研究报告增量更新，人工笔记保留；生成段被人工修改时转为冲突。运行报告含结果和问题入口，证据 JSON 保留实际来源片段；脚本校验结构、引用和上下文，不替代阅读真伪判断。

```bash
python skills/model-research/tests/run_tests.py --output /tmp/model-research-test-results
```

输出目录应为新目录；保存 manifest.json、逐项 events.jsonl 和 report.md，支持按级别、标签、模块和用例筛选、超时、报告重建及排除已通过用例的接续。零用例不算通过。相关回归使用本地后端和测试用外部进程，覆盖身份重编、冲突、人工保护、分页、提交后回执丢失及恢复。

飞书实际只读联调与本地写入测试分别记录在 [实现运行记录](<../../docs/运行记录 Run Record/2026-11-14 自动化首版实现验证.md>)。该历史首版记录尚未写线上业务表；后续真实写回和Codex调研见下方增量记录；真实过期续期、主机重启和定时完整周期仍未验收。官方 CLI 无条件写入能力时，提交前检查与实际写入间仍存在竞争窗口；详见 [同步边界](references/sync.md)。

`source_links`、backfill、评分公式改写、清空表和云端 Markdown 交付均未启用。

## 部署到当前云环境试运行

用户明确要求部署时，Linux 环境可执行：

```text
python skills/model-research/scripts/service.py --root <仓外运行目录> install --config <私有项目JSON>
<仓外运行目录>/manage start
<仓外运行目录>/manage status
<仓外运行目录>/manage tick --date <明确业务日>
<仓外运行目录>/manage stop
```

运行目录保存 releases/current、私有 project.json（由部署方提供）、state、deployment.json、process.json、heartbeat.json、last-run.json、worker-results 和日志；源码副本与业务状态分开。默认plan部署保持只读；已授权的apply部署要求allow_writes=true并逐项回读。程序默认15:00开始；当前部署按用户要求在北京时间12:00开始、18:00前运行；当前有进展且有剩余时1分钟接续，空闲或退避时30分钟重查。渠道可用 latest_snapshot=true 复用最近已交付快照，模型与 Benchmark 仍严格取当天日报。

当前实例按用户要求使用apply直接同步Grokbot CSV；日常同步不调用Codex，不等待Markdown调研。环境停止后服务可能停止，需要status核查并在必要时start；没有安装系统级自启动或发布共享环境。后台Codex和MD调研代码保留为另行使用的可选能力，早期部署经过见 [部署记录](<../../docs/运行记录 Run Record/2026-11-14 云环境试运行部署.md>)。


## 正文调研与接续

配置agent.command为已部署版本的Python Codex适配器入口，并配置codex_state_dir及max_entities_per_run。外部Agent也可继续按原argv/JSON协议接入。run自动处理本轮可研究项，生成证据、正文和字段候选；随后生成计划，并按部署模式plan预览或apply写回。dossiers/README.md提供档案索引，research/jobs保存成功/失败回执。remaining>0不表示整批已完成；后续同日期调度继续处理未完成项，成功输入不重复调用模型。

自动整理严格限于已实际下载的来源和阅读范围。模型卡的系列宣传不等于具体变体实测，未读权重、量化制品和评测协议保留未知。详细结构见 [证据协议](references/evidence.md)。真实样例与服务状态见 [接入记录](<../../docs/运行记录 Run Record/2026-11-14 后台调研与正文接入.md>)。


## 自动更新多维表格

正式自动写回使用：

```text
python skills/model-research/scripts/service.py --root <运行目录> install --config <自动配置> --mode apply --continue-after-minutes 1
<运行目录>/manage start
```

同时配置allow_writes=true、具体AI字段与allow_create；不改变表结构或人工评分规则。无成功基线的既有非空值保留，空值可补，成功回读的程序字段后续用三方比较维护。上游没有完成manifest时可用间隔不少于60秒的两次相同内容观察；文件变化重新计时。未知提交先核验，不重复新增。

当前CSV直接同步按整份日报生成计划，再按表、每批最多200条提交并回读；不再按每轮3个实体重新调研。当前部署的工作窗口为北京时间12:00—18:00，空闲时30分钟重查；跨日期未完成项可显式指定日期接续。早期调研写回证据见 [自动写回记录](<../../docs/运行记录 Run Record/2026-11-14 多维表格自动写回.md>)。
