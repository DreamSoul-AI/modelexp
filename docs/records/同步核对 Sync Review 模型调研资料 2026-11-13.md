# 飞书资料同步核对：2026-11-13

核验时间：2026-11-13T22:36:03+08:00。本轮渠道表创建、数据导入与本地设计同步已完成。

## 已核实的当前结构

| 表 | 表 ID | 目录报告记录数 | 字段数 | 修订 |
|---|---|---:|---:|---:|
| 模型评测表 | tbl91a5sM19a59aL | 385 | 74 | 184 |
| Benchmark收集表 | tblWnSCtqdffBr3W | 64 | 14 | 56 |
| 量化与后训练对比 | tblz5Aa0hpNK8Ubu | 612 | 29 | 35 |
| 渠道总表 | tbl6pXmb9qJHjtTA | 489 | 12 | 3 |

渠道表链接：https://dreamsoul.feishu.cn/base/L47LbtaVWabz1qs7pz8c6jYunbb?table=tbl6pXmb9qJHjtTA

## 来源与范围

用户澄清：线上此前尚未新增渠道表；新增资料在其提供的 model/benchmark 日报文件夹。已读取根目录和三个直接子目录，四个目录均 has_more=false；未递归扫描其他云空间。

输入渠道文件：channel/channels.csv，489 行、12 列，渠道ID无重复，渠道ID和渠道名称均无缺失。首次导入既有 Base 后将默认表名改为“渠道总表”。

channel/source_links_2026-11-13.csv 和 channel/source_links_backfill.csv 按用户明确要求跳过，未下载、未导入、未回填。

模型日报 131 行、Benchmark 日报 3 行已下载读取字段和样例。本轮没有将它们写入既有业务表；输入规模不是应新增的记录数。文件夹本轮没有返回 docx，不能宣称已同步额外在线文档正文。

## 导入核验

- 通过 drive +import --type bitable --target-token 导入 channels.csv，任务返回 ready=true、success。
- “备注”被导入器识别成多选并拆分；初始化中已修正为文本，按渠道ID对应 record_id 恢复 278 条非空备注原文。
- 全量回读 489 条，has_more=false；12 列合计 5,868 个单元格按日期、多选、链接和空值表示归一化后与源 CSV 全部一致。
- 原有模型、Benchmark、衍生产物表的记录数和修订号与写前一致。
- 导入保留上游状态：启用 233、未覆盖 1、访问异常 2、待覆盖 253。本次未逐站测试，不将“启用”描述为访问验证通过。

## 本地核查产物

- 原始 CSV、字段响应、导入结果、全量回读、比对结果保存在仓库外 `/workspace/scratch/model-research-sync-20261113/`。
- field-mapping.discovered.json 已加入渠道表字段映射，未来自动更新的字段归属仍待定义。
- channel-initial-baseline.json 保存这次核验成功的渠道初始值和 record_id；它不是其他三张表的完整同步基线。
- 设计稿已更新为四表结构、12列渠道格式、三目录输入和 source_links/backfill 延后规则。
- 本轮未启动定时采集、未发布环境、未推送 Git 分支。

## 后续更正：2026-11-14

本文件保留首次导入的历史证据。用户随后更正渠道数据，已使用 channels_2026-11-13.csv 清空重载；当前有效数据为 67 条，首次导入的 489 条及其 record_id 基线已被替代。详见 [渠道重拉记录](<同步核对 Sync Review 渠道重拉 2026-11-14.md>)。
