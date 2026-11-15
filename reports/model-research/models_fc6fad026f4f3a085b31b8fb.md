# granite-4.1-30b-base

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

固定 revision `9bb22a9` 的 README 对应目标 Base 变体。其定位是文本生成与专用模型训练的基座，支持摘要、分类、抽取、问答、长上下文生成和 FIM 代码补全。模型卡列出的十二种支持语言包含中文；架构为 decoder-only 稠密 Transformer，采用 GQA、RoPE、SwiGLU、RMSNorm 及共享输入输出嵌入。

依据：[src_e0446aed98fc0e3c3975](https://huggingface.co/ibm-granite/granite-4.1-30b-base/raw/9bb22a9/README.md)

### 评测条件与可比性

评测表按规模区分结果，本实体对应 30B Dense 列。已读内容包含知识、数学、代码和多语言任务，协议标注包括 MMLU 的 5-shot、GSM8K 的 8-shot，以及 HumanEval 的普通 pass@1 与采用 StarCoder Prompt 的 pass@1 两种设置；这些设置不能混用。多语言表另列各基准所含语言，不能将其覆盖范围等同于十二种模型支持语言。由于完整数据版本、评测工具、解码参数及运行条件未给出，本轮不形成完整协议成绩字段；HTML 注释中的候选结果也不作为正式成绩。

依据：[src_e0446aed98fc0e3c3975](https://huggingface.co/ibm-granite/granite-4.1-30b-base/raw/9bb22a9/README.md)

### 衍生关系

发布方称模型从头训练约 15 万亿 token，采用五阶段策略：前四阶段分别为 10、2、2、0.5 万亿 token，最后阶段进行长上下文扩展至 512K token。摘录未说明最后阶段的 token 数量，因此不自行补齐总量差额。模型卡将其列为专用模型训练的起点；当前材料未提供可核验的量化衍生仓库。

依据：[src_e0446aed98fc0e3c3975](https://huggingface.co/ibm-granite/granite-4.1-30b-base/raw/9bb22a9/README.md)

### 社区反馈与 Issue

原始 README 含一条关于 3B 基座与 Granite-4.0-3B-Micro 关系的待办注释，内容指向其他规模，不能据此推断本 30B 变体的权重继承关系。给定材料没有社区反馈或 Issue 正文，无法判断已报告故障及其修复状态。

依据：[src_e0446aed98fc0e3c3975](https://huggingface.co/ibm-granite/granite-4.1-30b-base/raw/9bb22a9/README.md)

### 冲突与待核实

证据为至多 18000 字符的截断 README，在架构表中途结束；后续架构信息及其他章节未读。尚未验证 512K 上下文的实际质量和资源需求、精确参数量、权重清单及精度、访问限制、独立许可文件、vLLM 支持、官方或第三方量化版本以及设备部署表现。链接指向的博客、GitHub 和外部文档未读；`researched` 仅覆盖本轮给定摘录的整理。

依据：[src_e0446aed98fc0e3c3975](https://huggingface.co/ibm-granite/granite-4.1-30b-base/raw/9bb22a9/README.md)

### 已读取的来源

- [src_e0446aed98fc0e3c3975](https://huggingface.co/ibm-granite/granite-4.1-30b-base/raw/9bb22a9/README.md) · source_statement · 2026-11-15T17:57:27+08:00
  阅读范围：至多18000字符；truncated=True
