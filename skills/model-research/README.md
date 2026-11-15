# Model 资料同步与表格校验

当前版本将 Grokbot 成品 CSV 增量同步到飞书，并独立校验字段规则与 CSV/线上记录的一致性。Markdown 正文交由 Grokbot；本程序不调用模型、不建立研究队列、不生成调研正文。既有 `src/` 训练流程不变。

## 使用入口

Python 3.11+ 标准库，Linux/macOS；飞书通过官方 lark-cli，以 `--as user` 操作。私有配置和状态放 checkout 外。先读取 [SKILL.md](SKILL.md)、[配置样例](assets/project.example.json) 和[服务器部署指南](references/server-deployment.md)。

```text
python3 skills/model-research/scripts/research.py doctor --config <配置>
python3 skills/model-research/scripts/research.py inspect --config <配置> --role models
python3 skills/model-research/scripts/research.py run --config <同步配置> --date <业务日> --mode apply
python3 skills/model-research/scripts/research.py validate --config <只读校验配置> --date <业务日>
```

同步配置 `allow_writes=true`，受控字段明确 `accept_upstream=true`、`prefer_upstream=true`。Agent 必须关闭；旧模型命令或 `agent.enabled=true` 会明确报错。无生产方完成声明时，至少两次相同内容、间隔不少于60秒的稳定观察后才写入。字段映射、格式规范、批量提交与人工保护沿用原规则；未知提交先对账，不重复新建。

校验配置 `allow_writes=false`，使用独立 state_dir；复制同步配置的字段归属与列映射，不把所有字段改为 unassigned。配置 `validation.baseline_state_dir` 指向同步 state，以只读方式识别已保护的人工修改。校验不会推进同步基线。

## 校验范围

- 读取所有配置表的实时 schema 和记录，检查映射字段类型、枚举值、日期格式、完整实体身份、重复身份与重复 record_id。
- 逐项比较当前业务日 CSV 与唯一匹配的线上记录，报告漏同步、字段差异、映射改变、输入错误与双方冲突。
- 人工维护、公式、只读、未归属字段不按 CSV 强制一致；已保护的人工修订单列为信息，不自动覆盖。
- 历史记录不因当天 CSV 缺行而被删除或判为漏项。量化与后训练表没有当前 CSV 时仍检查其映射字段和身份，但不冒充做过 CSV 对照。
- 输出私有 `state/validation/latest.json`、逐次 JSON 和 UTF-8 BOM 问题 CSV。字段包含严重性、原因、表角色、实体、record_id、CSV 行号、字段、期望值与实际值；保留读取快照。

这是结构与一致性校验，不验证许可、模型规模、量化效果、跑分等事实的真实性，不调用模型或自动访问研究来源。校验结果有错误或警告时返回 `partial`（CLI退出码3）；严重性 info 的人工差异不阻断通过。输入不稳定、缺失或后端不可读不能报通过。

## 两项定时服务

```text
python3 skills/model-research/scripts/service.py --root <csv目录> install --config <同步配置> --mode apply --at 12:00 --retry-until 18:00 --continue-after-minutes 1
python3 skills/model-research/scripts/service.py --root <validate目录> install --config <只读校验配置> --mode validate --at 12:00 --retry-until 18:00 --continue-after-minutes 1
```

两服务使用独立 state、锁和运行记录。systemd 以前台 daemon 管理开机恢复；内部调度使用 Asia/Shanghai，稳定观察阶段一分钟接续，常规检查间隔30分钟。校验可在同步之前发现临时差异，下次只读检查会更新报告，不会争抢同步写锁。

## 恢复与历史数据

`ingest`、`plan`、`apply`、`verify`、`resume`、`adopt`、`resolve-identity` 保留原有保护与对账规则，参见[同步与恢复](references/sync.md)。保留 SQLite 映射、字段基线、原 CSV、证据及历史人工修改。CSV 内部 dossier 是既有同步元信息存储，不是新生成的研究正文。

旧 `research` 服务模式、Codex 正文适配器和研究队列已移除。旧研究服务应停用并屏蔽，私有历史 state 可离线归档。保留 `export-md`、`finalize-md` 仅供历史文档迁移；候选导入不再接受 dossiers 正文。历史报告位于 [reports/model-research](../../reports/model-research/README.md)，不代表自动更新。

## Grokbot Markdown 交接

完整可复制的[写作提示词](assets/grokbot-md-prompt.txt)规定实体、版本、来源、评测条件、量化/训练关系、未知项与人工保护。Grokbot 生成文档和索引后打包交付，不由本程序自动发布或推送。

## 验证

```text
python3 skills/model-research/tests/run_tests.py --output <新的仓外结果目录>
```

测试使用本地文件后端，覆盖只读校验、字段冲突、人工修订、历史记录、重复运行、提交回执丢失和恢复；真实飞书校验另行记录。未运行或失败项不计通过。
