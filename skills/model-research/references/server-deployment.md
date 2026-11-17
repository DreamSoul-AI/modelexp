# Linux 服务器部署与迁移

当前部署由 CSV 同步、只读校验、评分维护三个独立服务组成。Markdown 由 Grokbot 管理，旧正文服务及队列保持停用。

## 环境与授权

Python 3.11+、Node.js、官方 lark-cli 与 Codex CLI。专用普通用户运行；配置、持久 state 和授权放仓外，私有目录700、文件600。迁移前核对哈希，保留原包、基线、原件、人工内容及未知提交回执。先处理旧未知提交，不能清空数据库绕过。

使用服务用户完成飞书应用配置及 user 授权；检查私有父目录归属和可写权限。Codex 使用官方浏览器登录流程及专用私有 CODEX_HOME，不要求设备代码或聊天传令牌。登录状态与真实调用分别测试。飞书显式 --as user，不切换身份绕过权限。

## 配置

CSV allow_writes=true；validate allow_writes=false，validation.baseline_state_dir 只读指向 CSV state。两者映射同一批字段。Grokbot 用根目录 token 与具名子目录，不递归混入 md 或 backfill。量化为可选的当日输入，明确27列映射和两列待处理边界。

scores 只配置 models，基础身份与模态只读，三个能力相关数值和维护元信息按 AI 策略；公式只读、allow_create=false。scores.enabled=true，设置官方模型、codex_command、codex_state_dir、reference_file、sync_root、批量大小与重查间隔。quota_stop_percent 默认90，每次新调用前查询官方额度，任一窗口已用达到阈值或额度未知即暂停；北京时间18:00停止，临近关闭时缩短模型超时。max_calls_per_day 缺省或 null 表示不按次数停止，可显式设正整数；升级不得清零实际调用计数。allow_unconfirmed_input=true 只用于已实际读取来源的评分证据批次，不复制给 CSV；评分仍先等待同日 CSV 稳定。

用户授权建立新版本后，freeze-scores 保存不可变参考与快照，recalibrate 生成计划，再 --calibration-plan 应用。不可覆盖参考文件或混用版本。日常更新依原固定分布标化，公式/原始权重不变。

## 安装与 systemd

服务根目录可用 /srv/model-research/csv、validate、scores。升级前安全停止对应服务并保存配置，保留 state；用新源码安装固定版本：

```text
python3 skills/model-research/scripts/service.py --root /srv/model-research/csv install --config /srv/model-research/csv/project.json --mode apply --at 12:00 --retry-until 18:00 --continue-after-minutes 1
python3 skills/model-research/scripts/service.py --root /srv/model-research/validate install --config /srv/model-research/validate/project.json --mode validate --at 12:00 --retry-until 18:00 --continue-after-minutes 1
python3 skills/model-research/scripts/service.py --root /srv/model-research/scores install --config /srv/model-research/scores/project.json --mode scores --at 12:00 --retry-until 18:00 --continue-after-minutes 1
```

调整[systemd模板](../deploy/model-research@.service)里的专用用户、真实目录与 CLI/Node PATH。enable --now 三个实例；旧 model-research@ai.service disable/mask，不复用旧部署启动 research。systemd 监督前台 daemon，不额外 manage start。

## 真实验收

CSV：doctor、当前文件、两次稳定观察、计划、写回、回读及重复运行无重复新增。校验：四表字段与 CSV 对照，报告具体记录/字段，证明无写表和模型调用，不能把 partial 当全通过。评分：实际来源及真实模型调用、三能力范围、冻结参考指纹、计划和回读、重复执行与额度/失败恢复。重算前后原始分及公式应保持。

检查 systemd PID、heartbeat、last-run、worker-results、validation/latest.json、scores/latest.json。重启恢复和下一次北京时间12:00自然触发必须实际观察后再报告，进程启动不是业务验收。当前无自动失败通知和每日变更摘要。

## 指定正式启用日期

清理和历史日报回放期间，先停止三个服务并备份表格、配置、状态与基线。安装时可用 `--start-date YYYY-MM-DD` 指定北京时间的首次自动业务日；服务可以提前启动待机，主机重启也不会提前运行。显式 `tick --date` 仍可用于已授权的历史回放。历史回放按日期顺序、先计划后写回，保留原始文件与哈希，逐日回读；不能复用已被回滚的旧操作回执跳过新写入。
