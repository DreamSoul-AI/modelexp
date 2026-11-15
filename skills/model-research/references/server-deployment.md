# Linux 服务器部署与迁移

当前版本由 CSV 同步和只读表格校验两个独立服务组成；Markdown 交给 Grokbot，不安装或调用模型生成器，不接续旧研究队列。

## 环境和私有数据

使用 Python 3.11+、Node.js 和官方 lark-cli；普通专用用户运行，配置和 state 放仓外持久磁盘，目录700、配置600。建议目录为 /srv/model-research/repo、csv、validate、archives。不得把凭据、私有配置、SQLite 或原 CSV 提交 Git。

迁移包先核对 manifest 哈希，保留原包；复制 CSV 状态时保留映射、字段基线、历史原件、证据和人工修改。submitting/submitted/unknown 操作先对账，不能重建记录绕过。旧 AI state 离线归档，先 export-md 打包历史正文和索引，再停用并屏蔽旧服务。

## 官方授权

安装并核对官方 lark-cli 帮助，使用服务用户配置已有应用并完成 user 授权；不要把 App Secret、密码或令牌发到聊天或写进仓库。父目录必须归服务用户所有且可写，避免 keychain 存储失败。doctor 必须实际验证 user 身份和资源权限。

当前同步与校验都不需要 Codex 授权。历史独立 Codex 凭据可保留在私有目录，不由本次迁移擅自删除。

## 配置和安装

同步配置保留已授权映射、人工保护、选项追加和批量大小，allow_writes=true、agent.enabled=false。校验配置复制相同的字段规则，allow_writes=false，state_dir=./state，并设置 validation.baseline_state_dir 指向 CSV 的 state；两套状态目录必须分开。

```text
python3 skills/model-research/scripts/service.py --root /srv/model-research/csv install --config /srv/model-research/csv/project.json --mode apply --at 12:00 --retry-until 18:00 --continue-after-minutes 1
python3 skills/model-research/scripts/service.py --root /srv/model-research/validate install --config /srv/model-research/validate/project.json --mode validate --at 12:00 --retry-until 18:00 --continue-after-minutes 1
```

旧 research 服务模式、agent.command 已不受支持。不得复用旧 AI manage/deployment.json 来启动研究；旧固定版本仅保留为离线恢复依据。已有 CSV 服务升级前先安全停止，保留私有配置和 state，安装新固定版本后重新交给 systemd。

## systemd 与验收

安装 [systemd模板](../deploy/model-research@.service)，按真实专用用户和 CLI/Node 路径调整 PATH，enable --now model-research@csv.service model-research@validate.service。systemd 前台监督时不额外 manage start。旧 model-research@ai.service 保持 disable/mask。

验收包括：doctor、真实 CSV 读取、稳定观察、增量计划与回读、重复运行不重复新增；真实只读校验覆盖所有配置表，产出带具体记录/字段/CSV行号的报告，并证明无远端写入、无模型调用。不要为测试制造线上脏记录。问题项可以保留待人工处理，不擅自改评分和历史值。

检查 systemctl 状态、真实 PID/启动指纹、heartbeat、last-run、worker-results、state/validation/latest.json 和问题 CSV。partial 不算全表通过。校验和同步同时12:00启动时可能先看到未同步的新行，后续检查会反映最新一致性。

重启恢复与后续12:00自然触发分别验证；实际未观察的验收不得宣称已通过。当前尚无自动失败通知和授权到期提醒，不把存活进程当作完整业务保障。
