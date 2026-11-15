# 同步与只读校验运行协议

当前运行包含 apply/plan 与 validate；research 模式和模型调用已移除。Markdown 正文由 Grokbot 交付，旧研究队列不再接续。

## 模式与调度

- apply 需要 allow_writes=true；plan 和 validate 需要 allow_writes=false。
- validate 只读取 CSV、schema、线上记录与可选同步基线，写本地快照和问题报告，不修改飞书或同步基线。
- 配置不得启用 agent.enabled 或 agent.command；旧配置明确报错，不静默执行历史模型命令。
- 每天 Asia/Shanghai 12:00 开始，当前部署至18:00；稳定观察一分钟接续，常规30分钟重查。进程存活不代表业务通过。
- CSV与校验分别使用 state_dir、锁、固定版本、last-run、heartbeat、runs 和 worker-results；不混用数据库。systemd 负责开机恢复，模板直接运行 daemon 前台入口。

## 报告

校验输出 state/validation/latest.json 和逐次 validation_*.json/.csv。保留业务日、实际检查时间、来源批次、读取快照、逐表覆盖、问题严重性与 CSV/线上值。部分失败、输入缺失、schema 变化或无法读取时不得报全批通过。模型次数为0，事实核实为false。

校验记录中 error/warning 产生 partial；已保护的人工差异为 info。历史记录没有当日 CSV 对照不视为错误。校验不是自动修复，也不核实公开来源真实性。

## 旧数据

保留 CSV 同步依赖的映射、基线、历史证据与内部 dossier 元信息；不清空人工笔记。export-md/finalize-md 只用于历史报告迁移。旧研究服务停用并屏蔽，旧 research/jobs 与 requests 留作离线审计，不进入当前调度。
