# Qwen3-4B-Instruct-2507

## 自动调研记录

业务日期：2026-11-14 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

已读README与Qwen3-4B-Instruct-2507、revision cdbee75一致。这是Qwen3-4B非思考模式更新版，经过预训练与后训练，标称4.0B参数、原生262,144 token上下文，适用于文本对话、指令生成和工具调用。卡片明确仅支持非思考模式，不生成<think></think>块，无需再指定enable_thinking=False；不能将其当作可切换思考模式的原版Qwen3-4B。

依据：[src_a84c334652c2c43ffb43](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/raw/cdbee75/README.md)

### 评测条件与可比性

README提供发布方评测表，覆盖知识、推理、代码、对齐、Agent和多语言任务，并与GPT-4.1-nano-2025-04-14及两个Qwen3非思考变体对照。部分测试注明版本或时间窗口，例如LiveBench 20241125、LiveCodeBench v6（25.02—25.05）；Arena-Hard v2注明以GPT-4.1评判胜率。但表格未给出各项完整提示、采样、样本聚合、评测框架版本及硬件协议，因此本轮不将表中数值作为具有完整协议的成绩候选。

卡片另给出使用建议：Temperature=0.7、TopP=0.8、TopK=20、MinP=0，多数查询建议输出长度16,384 token；数学题建议逐步推理并用盒装格式给最终答案，选择题建议用JSON的answer字段规范输出。这些是最佳实践建议，材料没有确认评测表的每一项均采用这些设置，不能用它们补齐缺失的成绩协议。

依据：[src_a84c334652c2c43ffb43](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/raw/cdbee75/README.md)

### 衍生关系

模型卡确认该变体是Qwen3-4B非思考模式的更新，并列出预训练与后训练阶段，但没有提供具体训练数据或配方。给定README没有列出FP8、GGUF、MLX 4bit或RK182X转换制品，输入记录中的相关制品和大小不能在本轮据此确认为事实。

依据：[src_a84c334652c2c43ffb43](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/raw/cdbee75/README.md)

### 社区反馈与 Issue

文档提示transformers低于4.51.0会出现KeyError: 'qwen3'；部署长上下文发生OOM时可缩短上下文，例如降至32,768 token。卡片还提示较高presence_penalty可能造成语言混杂和性能轻微下降。这些属于发布方提示，材料未提供社区Issue、用户复现、修复提交或独立反馈。

依据：[src_a84c334652c2c43ffb43](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/raw/cdbee75/README.md)

### 冲突与待核实

本轮已读完提供的未截断README；链接的博客、GitHub、硬件及推理性能文档、Qwen-Agent源码、技术报告、LICENSE正文和外链图片内容未提供、未读。尚未核验权重清单、精度与体积、精确参数量、访问限制、量化衍生、各运行时对此revision的兼容性、长上下文显存需求及完整跑分协议。未执行部署、推理或独立评测；researched仅表示本轮给定来源的阅读整理完成。

依据：[src_a84c334652c2c43ffb43](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/raw/cdbee75/README.md)

### 已读取的来源

- [src_a84c334652c2c43ffb43](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507/raw/cdbee75/README.md) · source_statement · 2026-11-14T16:14:57+08:00
  阅读范围：至多18000字符；truncated=False
