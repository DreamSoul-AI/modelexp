# 渠道表清空重拉：2026-11-14

当前有效版本：第二次重拉的 14 条、12 列。下文保留首轮 67 条的过程，第二轮结果见文末。

核验时间：2026-11-14T01:15:19+08:00。

用户明确要求清空渠道总表并重新拉取最新来源。已重新读取指定 channel 文件夹，发现源文件改为 channels_2026-11-13.csv，67 行、12 列；source_links 与 backfill 继续跳过。

## 执行与结果

- 目标：渠道总表 tbl6pXmb9qJHjtTA，保留表、字段和表入口。
- 写前完整备份原有 489 条记录及字段定义。
- 输入字段、ID唯一性、选项和日期通过校验后预览删除与写入请求。
- 分批删除原有 489 条，回读确认记录数为 0。
- 按现有 text/select/datetime 类型写入 67 条，不使用导入器自动推断字段。
- 全量回读 67 条，has_more=false；804 个单元格按链接、日期、多选与空值表示归一化后，与 CSV 全部一致。
- 原来其他三张表的记录数和修订号未变化。

旧记录已删除，因此 record_id 全部更新。后续使用渠道ID重新匹配，本轮 verified-baseline.json 替代首次导入基线；不要使用旧 record_id 更新渠道。

## 取证位置

仓库外目录：`/workspace/scratch/channel-reload-20261114/`。

包括新版 CSV、写前字段与记录、删除/写入预览、每批结果、清空确认、最终回读、verification.json 和 verified-baseline.json。未对渠道站点逐一做访问验证，保留 CSV 中的状态声明。

## 第二次重拉：当前有效版本

核验时间：2026-11-14T01:37:38+08:00。用户再次要求清空重拉。重新列取指定目录，确认 channels_2026-11-13.csv 已替换，源 token 为 IV72bFdKtoMdpQx6XsBcuimin9b。新版按平台聚合为 14 行、12 列。

已备份旧 67 条及 schema，确认目标仍为同一渠道表；完成删除和空表回读，再将采集对象配置为多选，写入 14 条。全部 168 个单元格按日期、链接、多选和空值归一化后与 CSV 一致。其他三张表记录数及修订号未变化；source_links 和 backfill 继续跳过。

证据目录：`/workspace/scratch/channel-reload-20261114-r2/`，包含输入、备份、预览、写入结果、回读、verification.json 与当前 verified-baseline.json。第一轮基线和其 record_id 不再有效。上游渠道ID跨批可能重编，后续不能仅凭相同渠道ID继承旧实体关系。
