# 当前代码结构

`skills/model-research/scripts/` 使用标准库，职责如下：

| 模块 | 职责 |
| --- | --- |
| common / identity / state | 配置、类型与实体身份、SQLite 基线、锁和操作回执 |
| ingest | 按业务日与根目录/具名子目录接收 CSV、不可变原件与稳定观察 |
| daily | 逐表接收、观察、同步与校验；隔离单表失败，发布独立完成回执和总报告 |
| md_overview | 全量扫描 MD 文件元信息、生成全库总览、保护人工修改、回读与未知提交对账 |
| lark_adapter | 官方 user CLI、字段投影与分页、批量记录写回和本地测试后端 |
| evidence / dossiers | 内部字段证据元信息与索引，保留人工内容，不生成研究正文 |
| sync | 三方比较、计划证明、提交前检查、回读、未知提交恢复 |
| validation | 字段与 CSV/线上一致性只读校验 |
| score_policy / score_sources | 文字输出与三能力白名单、有限量实际来源读取及引用检查 |
| score_agent / score_quota | 官方 Codex 结构化提取、无模型 turn 的额度读取 |
| score_calibration | 不可变冻结参考、百分位计算、可恢复且保护并发修改的重算 |
| scores | 来源变化检查、模型预算、逐记录回执和证据候选写回 |
| research / service | 命令入口、固定版本、每日调度与前台 daemon |

每次读取最多50个字段，超出时按 record_id 合并投影；分页和跨投影必须版本一致。评分任务与 CSV、校验不共享可写状态。配置、运行资料和授权不放源码目录。测试使用独立临时本地后端，按用例持久保存结果。
