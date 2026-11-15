# granite-4.1-3b-base

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

给定README标题、示例仓库名与来源URL均对应granite-4.1-3b-base，revision为dacb9cb。该模型由IBM Granite Team开发，定位是通用文本生成及专用模型训练的基座，覆盖摘要、分类、抽取、问答、FIM代码补全和长文本任务；模型卡列出12种支持语言，并声明上下文扩展至512K tokens。上述能力是发布方描述，本轮未实测。

依据：[src_9dfbfc3ed6e5631c41dc](https://huggingface.co/ibm-granite/granite-4.1-3b-base/raw/dacb9cb/README.md)

### 评测条件与可比性

已读评测表包含通用知识、数学、代码和多语言任务；本实体应读取3B Dense列。表中区分MMLU的5-shot、MMLU-Pro的5-shot加CoT、BBH的3-shot加CoT、GSM8K的8-shot，以及HumanEval的普通pass@1与StarCoder Prompt版本。多语言评测分别覆盖MMMLU的11种、INCLUDE的14种及MGSM的5种语言，不能将这些集合直接等同于模型声明支持的12种语言。可见材料未提供完整评测框架版本、数据版本、提示模板及采样参数，因此不提取数值为可复现成绩，也不将表格视为独立验证。

依据：[src_9dfbfc3ed6e5631c41dc](https://huggingface.co/ibm-granite/granite-4.1-3b-base/raw/dacb9cb/README.md)

### 衍生关系

模型卡明确称本模型与Granite 4.0 3B Micro共享底层架构及权重，并描述约15万亿tokens的训练：四阶段分别为10万亿、2万亿、2万亿、0.5万亿，另有上下文扩展阶段。架构描述为仅解码器稠密Transformer，包含GQA、RoPE、SwiGLU、RMSNorm和输入输出共享嵌入；可见表格列出嵌入维度2560及40层。这些是训练与结构声明，未通过配置或权重核验。

依据：[src_9dfbfc3ed6e5631c41dc](https://huggingface.co/ibm-granite/granite-4.1-3b-base/raw/dacb9cb/README.md)

### 冲突与待核实

README在架构表中途被截断，后续内容未读；链接指向的技术博客、GitHub、完整配置和权重均未提供。给定原始摘录不足以核验raw_fields中的精确参数量、BF16体积、分片数、第三方GGUF、vLLM支持、未gated状态或已被4.2取代等说法，故不形成对应字段候选。未提供社区讨论或Issue正文，无法总结实际用户反馈、已知故障及修复状态。模型卡发布日期为2026-04-29，raw_fields所记4月6日创建时间缺少本轮原始API证据，不能替代发布日期。researched仅表示给定可见材料整理完成。

依据：[src_9dfbfc3ed6e5631c41dc](https://huggingface.co/ibm-granite/granite-4.1-3b-base/raw/dacb9cb/README.md)

### 已读取的来源

- [src_9dfbfc3ed6e5631c41dc](https://huggingface.co/ibm-granite/granite-4.1-3b-base/raw/dacb9cb/README.md) · source_statement · 2026-11-15T17:54:30+08:00
  阅读范围：至多18000字符；truncated=True
