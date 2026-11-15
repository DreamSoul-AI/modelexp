# granite-switch-4.1-30b-preview

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

身份与固定 revision ff87bde 的 30B Preview 模型卡一致。模型以 Granite 4.1 30B 为基座，嵌入 12 个 Core、RAG、Guardian 适配器，面向文本生成流程中的查询改写与澄清、可回答性判断、幻觉检测、引用生成、需求验证、归因、不确定性估计和安全合规任务。模型卡将基座描述为 30B 稠密解码器 Transformer、131,072 tokens 上下文；没有给出含适配器后的总参数量。

依据：[src_7429305717229b1144ee](https://huggingface.co/ibm-granite/granite-switch-4.1-30b-preview/raw/ff87bde/README.md)

### 评测条件与可比性

本材料没有该 30B Preview revision 的定量跑分、硬件设置、评测数据版本或完整评测协议。文中可回答性和 Guardian 输出属于使用示例；组合无准确性损失、置信度校准等说法缺少本材料内的实验表格支持，不能据此建立成绩或与 8B 版本的性能比较。

依据：[src_7429305717229b1144ee](https://huggingface.co/ibm-granite/granite-switch-4.1-30b-preview/raw/ff87bde/README.md)

### 衍生关系

该模型是基座与独立训练 activated LoRA 适配器的组合制品。控制 token 触发粗粒度专家切换，同一适配器在连续 token 区间的所有层中生效；KV cache normalization 隔离不同适配器的内部缓存表示。模型卡说明无需联合训练，提供组合工具与同一检查点用于 HF/vLLM 的路径；本材料未列出量化版或其他训练衍生的具体制品。

依据：[src_7429305717229b1144ee](https://huggingface.co/ibm-granite/granite-switch-4.1-30b-preview/raw/ff87bde/README.md)

### 社区反馈与 Issue

明确的应用限制是安全适配器不能替代场景测试、内容过滤和持续输出监控。没有提供社区反馈或 Issue 内容，不能断言其运行稳定性、已知缺陷或修复状态；也不能仅凭基座规模判断某类消费级显卡能否运行。

依据：[src_7429305717229b1144ee](https://huggingface.co/ibm-granite/granite-switch-4.1-30b-preview/raw/ff87bde/README.md)

### 冲突与待核实

本轮给定 README 未截断，已完成阅读整理；BUILD.md、基座和适配器模型卡、许可证正文、论文及教程仅被链接，未读取。实际检查点参数量、分片数量、权重精度、文件大小、量化供应、访问门槛、显存需求、吞吐与签名有效性均未验证。材料也不足以确认 Preview 已被取代。researched 不表示这些制品和性能已通过验证。

依据：[src_7429305717229b1144ee](https://huggingface.co/ibm-granite/granite-switch-4.1-30b-preview/raw/ff87bde/README.md)

### 已读取的来源

- [src_7429305717229b1144ee](https://huggingface.co/ibm-granite/granite-switch-4.1-30b-preview/raw/ff87bde/README.md) · source_statement · 2026-11-15T18:03:45+08:00
  阅读范围：至多18000字符；truncated=False
