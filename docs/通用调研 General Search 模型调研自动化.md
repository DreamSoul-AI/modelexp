# 模型调研自动化工程依据

日期：2026-11-14。范围：现有流程、数据同步机制和可借鉴的开源方案，服务本项目设计 v0.1。阅读深度为本地代码/技能说明、CLI实际调用、仓库元数据与 README；未部署下列开源项目。

## 已有机制与取舍

| 依据 | 已观察到的行为 | 对本设计的影响 |
|---|---|---|
| lark-cli 的用户登录与 Linux 存储实现 | 默认用户目录写入曾失败，使用官方配置/数据目录覆盖后保存成功；刷新凭据已取得 | 明确持久目录与运行账号；需要单独验证真实续期与重启 |
| Base 渠道导入及回读 | CSV 的“备注”被自动推断为多选并拆开，修正文本后恢复原文 | 导入后核对字段类型与所有受影响值，不能只看行数 |
| 渠道源连续替换 | 同名 CSV/业务日下，来源从489条变67条再变14条，渠道ID也被重编 | 文件名和上游编号不够；版本固定、内部实体身份与旧基线失效是必要环节 |
| 官方记录导出 | NDJSON命令输出manifest，而非普通ok信封 | 适配器按命令类型解析，保留退出码与实际产物检查 |
| document-sync 0.2.0 正文 | 明确清单、上传/下载/both方向、逐文档回执；状态脚本只判定、不传输 | 复用在线档案交付；多维表格字段同步仍由本项目实现 |

上述 CLI 操作已发生，不代表本设计中的同步引擎或定时服务已完成。当前3项核心选择是：一个统筹 skill、SQLite 与文件存储、复用官方 CLI。理由是先把已有 CSV→飞书流程跑稳，减少首版的服务和凭据维护面。

## 同类开源方案初筛

本次读取各官方 README 及 GitHub 仓库元数据。以下是机制参考，不是安装建议或性能比较。

| 项目 | 资料中可借鉴的部分 | 本项目取舍 |
|---|---|---|
| [Open Deep Research](https://github.com/langchain-ai/open_deep_research) | 研究任务编排、模型/搜索配置、评估入口；README还介绍历史plan-and-execute实现 | 借鉴分阶段研究及证据压缩，不直接接成飞书同步服务。当前仓库元数据显示 archived=true，首版不选为运行底座 |
| [RAGFlow](https://github.com/infiniflow/ragflow) | README说明异构内容处理、知识组织、检索与可追溯引用，也提供服务部署方案 | 档案规模扩大后评估检索层；首版按实体和变更定位证据，不先部署整套RAG服务 |
| [Lighteval](https://github.com/huggingface/lighteval) | README提供LLM评测任务、后端和执行入口 | 借鉴任务/指标/配置分离；未来实际跑分阶段再评估接入。资料收集和评测执行保持独立 |

尚未核验这些项目的源码执行、当前 API 兼容、许可证适用细节、资源需求及其与项目表结构的集成。下一阶段围绕“来源更新、引用、版本和失败接续”定向读源码/测试，只有发现能替代现有职责的组件才引入依赖。

## 资料与阅读条目

- [knowledge](https://github.com/DreamSoul-AI/knowledge.git)：安装当前10个技能，实际阅读 document-sync 的输入、逐项清单、指纹、冲突与回执规则。价值是直接复用文档交付，限制是它没有实现业务表格字段合并。
- [lark-cli](https://github.com/larksuite/cli)：实际阅读安装包说明、配置/身份与Base/Drive技能，调用官方命令；Linux keychain源码用于确认受支持的存储目录变量。限制是跨任务和真实过期刷新未测试。
- [Open Deep Research README](https://github.com/langchain-ai/open_deep_research/blob/main/README.md)：阅读配置、评估、部署和历史实现介绍，理解研究编排分工；未验证实际执行。
- [RAGFlow README](https://github.com/infiniflow/ragflow/blob/main/README.md)：阅读用途、关键功能与部署章节，了解检索及引用职责；未检验实际检索质量。
- [Lighteval README](https://github.com/huggingface/lighteval/blob/main/README.md)：阅读任务分类、安装和quickstart，了解评测执行的职责范围；未运行评测。
- [工作环境模板](https://dreamsoul.feishu.cn/drive/folder/LidJfLEoRln9tXdXJVlcO6RHnLg?from=from_copylink)：已读取研发版、教程和REPO模板，按仓库实际布局适配。没有将ZIP中全部规范当作已读取或最新云端正文。
- [通用调研规范](https://dreamsoul.feishu.cn/docx/YcWIdE4INoLqoLxR5O8cbl7hnTf)：相关章节用于范围、直接依据、取舍与未验证项的组织；不是本项目功能来源。

原始来源响应、README及元数据快照保存在本次仓库外运行资料中，入口见 [运行记录](<运行记录 Run Record/2026-11-14 技能安装与模板接入.md>)。动态默认分支内容可能后续变化，本文件只代表本次阅读范围。
