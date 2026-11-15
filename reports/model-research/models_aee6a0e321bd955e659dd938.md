# RzenEmbed-v2-7B

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

所给qihoo360/RzenEmbed仓库在ea95c33的README标题为RzenEmbed-v2-7B，与目标名称一致。模型面向多模态嵌入和检索，提供文本检索图像、图像检索文本、文档图像检索及文本检索视频的示例；使用不同任务指令生成嵌入，再计算向量相似度。评测表标称规模为8.29B，不能仅凭名称中的7B推定精确参数量。

依据：[src_973a7c495a09186c4c68](https://huggingface.co/qihoo360/RzenEmbed/raw/ea95c33/README.md)

### 评测条件与可比性

README包含MMEB-V2总体及图像、视频、视觉文档分组表，并将MMEB-V2、MMEB-Visdoc和MMEB-Video领先声明限定在2025-09-29。表中没有完整说明数据集版本、指标定义、聚合权重、预处理、检索候选池、提示词和评测代码revision，因此本轮不生成成绩字段，也不将历史发布方声明延伸为当前榜单状态。视频使用示例中的8帧抽样不构成评测设置证据。

依据：[src_973a7c495a09186c4c68](https://huggingface.co/qihoo360/RzenEmbed/raw/ea95c33/README.md)

### 衍生关系

README链接论文《RzenEmbed: Towards Comprehensive Multimodal Retrieval》和360CVGroup/RzenEmbed代码仓库，但当前正文未披露基座、训练阶段、损失函数或量化衍生关系。不能根据对照表中其他Qwen2-VL模型的名称，反推本模型的架构或训练来源。

依据：[src_973a7c495a09186c4c68](https://huggingface.co/qihoo360/RzenEmbed/raw/ea95c33/README.md)

### 社区反馈与 Issue

视频示例调用`Image.fromarray`，但该代码块没有导入`Image`；独立运行前需要补齐相应导入，这是静态阅读发现，未实际执行。所给材料没有社区反馈或Issue线程，无法判断真实部署稳定性及问题处理状态。

依据：[src_973a7c495a09186c4c68](https://huggingface.co/qihoo360/RzenEmbed/raw/ea95c33/README.md)

### 冲突与待核实

所给README未截断，已完成阅读；所链接论文、GitHub代码、榜单和实际推理模块尚未读取。README没有许可条款，不能据此认定整个权重仓库无许可或允许商用。权重格式、精确参数量、BF16状态、模型架构、显存需求、量化与端侧制品、镜像哈希及实际性能均未核验；不采用上游记录中的硬件估算。本轮researched只表示给定来源的整理已完成。

依据：[src_973a7c495a09186c4c68](https://huggingface.co/qihoo360/RzenEmbed/raw/ea95c33/README.md)

### 已读取的来源

- [src_973a7c495a09186c4c68](https://huggingface.co/qihoo360/RzenEmbed/raw/ea95c33/README.md) · source_statement · 2026-11-15T18:22:16+08:00
  阅读范围：至多18000字符；truncated=False
