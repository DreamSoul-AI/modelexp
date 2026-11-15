# gte-multilingual-base

## 自动调研记录

业务日期：2026-11-14 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

来源为 gte-multilingual-base 的 9bbca17 revision，model-index 明确标注同名模型的 dense 变体，身份与目标一致。模型卡列出多种语言，并展示多语言嵌入任务结果，可作为多语言检索、文本相似度及跨语言文本匹配的候选；这些材料不能替代业务数据上的验证。researched 仅表示本轮给定片段的整理完成。

依据：[src_12091d9e7555b687424f](https://huggingface.co/Alibaba-NLP/gte-multilingual-base/raw/9bbca17/README.md)

### 评测条件与可比性

可见评测包括中文 AFQMC、ATEC、BQ 等相似度任务，多语言 AmazonReviews 分类，英语与波兰语检索、法语 Alloprof 任务，以及 BUCC 的德英、法英、俄英和中英双语文本挖掘。记录区分 test、validation 和 dev 划分，提供 config、指标及部分数据集 revision；也有 revision 为 None 的条目。所有这些结果属于卡面标注的 dense 变体，不能转用于稀疏或混合检索结论。由于编码维度、提示、归一化、软件版本等完整协议不可见，本轮不提取数值成绩或计算跨任务总分。

依据：[src_12091d9e7555b687424f](https://huggingface.co/Alibaba-NLP/gte-multilingual-base/raw/9bbca17/README.md)

### 衍生关系

给定片段未包含量化、训练衍生、第三方 ONNX 制品或训练方案说明。dense 评测标签本身不能证明模型提供稀疏输出、弹性维度或相应制品。

依据：[src_12091d9e7555b687424f](https://huggingface.co/Alibaba-NLP/gte-multilingual-base/raw/9bbca17/README.md)

### 社区反馈与 Issue

框架标签涉及 sentence-transformers、transformers 和 text-embeddings-inference，但片段未提供可复现运行步骤或社区 Issue。无法据此确认 CPU 镜像兼容性、特定版本故障、实际吞吐、内存占用及社区满意度。

依据：[src_12091d9e7555b687424f](https://huggingface.co/Alibaba-NLP/gte-multilingual-base/raw/9bbca17/README.md)

### 冲突与待核实

材料标注至多18000字符且 truncated=True，后续 README 内容未提供，不能视为已经验证。参数量、权重体积与精度、768维、8192上下文、弹性降维、稀疏向量、trust_remote_code 及最低依赖版本均缺少可见原文支持。语言列表和部分多语言评测不保证所有语言、领域或跨语言组合均有相同表现。完整许可文本、权重与衍生制品可用性、训练数据、发布日期、下载量及社区反馈也未在本轮确认。

依据：[src_12091d9e7555b687424f](https://huggingface.co/Alibaba-NLP/gte-multilingual-base/raw/9bbca17/README.md)

### 已读取的来源

- [src_12091d9e7555b687424f](https://huggingface.co/Alibaba-NLP/gte-multilingual-base/raw/9bbca17/README.md) · source_statement · 2026-11-14T16:55:03+08:00
  阅读范围：至多18000字符；truncated=True
