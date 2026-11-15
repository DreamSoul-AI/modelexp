# 三任务运行与恢复

CSV 同步、validate 只读校验、scores 评测维护分别使用独立配置、state、锁和固定版本。service.py install 支持 apply、validate、scores；北京时间12:00开启、18:00前重试，评分等待当天 CSV 稳定。systemd 前台 daemon 不另开后台 manage start。

process.json 和 heartbeat 只是证据之一；必须核对真实 PID、启动指纹、last-run 的业务日与实际结果。partial/error 或旧日成功不能当作今天完成。未知提交先对账，不盲目创建。评分额度不明或不足时不提交模型调用，保留失败回执和退避；不恢复旧 research/jobs 队列。

旧 AI 正文服务保持停用并屏蔽。历史正文、证据和人工修改离线保留，当前代码没有 Markdown 生成或导出兼容工具；Grokbot 接管文档。真实授权与资料置于仓外，不随仓库清理删除。
