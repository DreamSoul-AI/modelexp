# 批次与工作流程

配置使用JSON，相对路径相对配置文件。输入文件名须唯一匹配指定业务日；渠道可使用明确文件名或唯一glob，出现多个候选时停止该输入，不按mtime自动猜最新。

独立渠道快照可配置 `latest_snapshot=true` 和 `channels_*.csv`：按文件名末尾的合法业务日期选不晚于本次业务日的最新版本。相同最新日期有多个候选仍阻断，未来日期不提前采用。日报保持精确当天文件名，不把昨天日报自动当今天交付。

ingest保留原件、生成实体和Markdown档案。无manifest时记录unconfirmed，默认禁止apply；只有项目明确接受该就绪限制，才配置allow_unconfirmed_input=true。确认manifest逐角色核对名称、哈希和业务日；允许零行须显式allow_empty。

CSV支持UTF-8/BOM、引号和多行；列名/别名必须唯一匹配。不合法行或重复身份报错；无法确定身份的行记录issues，其他独立行可继续，最终报告保持部分完成。来源替换产生新batch_id，同内容重复接收复用旧批次。

档案初始正文是未核验CSV信息，controlled_fields为空。为避免把AI工作伪装成完成，没有配置Agent且存在需要调研的AI字段时，run输出waiting_research及请求文件；可由当前Agent完成查证后生成候选文件继续。

新增衍生产物需先在项目配置中定义其role、表和字段，再由候选的discoveries提供identity_values和证据字段。未配置的角色不会自动建表。

## 当前CSV日常同步

用户已明确采用Grokbot成品CSV，当前流程跳过补充研究：accept_upstream=true、prefer_upstream=true、agent.enabled=false且不配置command。检查列映射、实时下拉选项及明确同义映射，再批量提交和回读。原件保留，人工编辑和评分保护继续生效；不因为需要研究MD而阻断表格更新。无manifest时采用至少60秒间隔的稳定内容观察。
