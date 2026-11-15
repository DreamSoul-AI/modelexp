# granite-switch-4.1-8b-preview

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

身份与固定 revision 8a22410 的 8B Preview 模型卡一致。该模型基于 Granite 4.1 8B，将 12 个适配器组合进单一检查点，适合需要检索前查询处理、可回答性判断、生成后幻觉检查和引用生成，以及需求验证、安全审查的文本流程。Core 提供需求检查、上下文归因和不确定性估计；RAG 提供五类检索与生成辅助功能；Guardian 提供安全、事实性检测与纠正、策略合规检查。基座标称 8B、上下文 131,072 tokens；这些是基座规格，不能据此确定组合检查点总参数量。

依据：[src_e1907fa3664123ed481b](https://huggingface.co/ibm-granite/granite-switch-4.1-8b-preview/raw/8a22410/README.md)

### 评测条件与可比性

给定 README 没有提供该 revision 的基准成绩或可复现评测协议。可回答性与安全检测代码中的输出属于调用示例，不能视作实测结果。模型卡提出适配器可独立组合而不损失准确性，并描述不确定性输出的校准含义，但未在本材料内给出对应数据集、样本量、误差或对照实验，因此不生成成绩候选。

依据：[src_e1907fa3664123ed481b](https://huggingface.co/ibm-granite/granite-switch-4.1-8b-preview/raw/8a22410/README.md)

### 衍生关系

训练与组合关系由模型卡明确描述：独立训练的 activated LoRA 适配器来自 granitelib-core-r1.0、granitelib-rag-r1.0 和 granitelib-guardian-r1.0，通过控制 token 在连续 token 区间切换；KV cache normalization 使适配器读取基座表示，而不读取其他适配器的内部缓存状态。模型卡称适配器无需联合训练，组合后的检查点可用于 HF 和 vLLM；本材料未列出量化制品，不能据此判断量化版本是否存在。

依据：[src_e1907fa3664123ed481b](https://huggingface.co/ibm-granite/granite-switch-4.1-8b-preview/raw/8a22410/README.md)

### 社区反馈与 Issue

模型卡明确要求在实际用例中测试适配器、采用领域内容过滤并监控输出，说明 Guardian 能力不构成应用安全保证。给定材料没有社区讨论、用户反馈或 Issue 原文，无法形成社区稳定性、兼容性故障或缺陷修复结论。

依据：[src_e1907fa3664123ed481b](https://huggingface.co/ibm-granite/granite-switch-4.1-8b-preview/raw/8a22410/README.md)

### 冲突与待核实

本轮提供的 README 未截断，已完成阅读整理；其链接的 BUILD.md、基座模型卡、各适配器材料、教程、许可证正文及相关论文未提供，未读取或验证。实际权重分片、精度、总参数量、文件大小、访问门槛、签名有效性、量化衍生、硬件需求与性能均未核实；也无法从本材料确认该 Preview 是否已被其他版本取代。researched 仅表示本轮给定来源整理完成。

依据：[src_e1907fa3664123ed481b](https://huggingface.co/ibm-granite/granite-switch-4.1-8b-preview/raw/8a22410/README.md)

### 已读取的来源

- [src_e1907fa3664123ed481b](https://huggingface.co/ibm-granite/granite-switch-4.1-8b-preview/raw/8a22410/README.md) · source_statement · 2026-11-15T18:03:45+08:00
  阅读范围：至多18000字符；truncated=False
