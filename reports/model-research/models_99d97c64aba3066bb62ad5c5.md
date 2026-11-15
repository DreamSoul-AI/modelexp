# multilingual-e5-large-instruct

## 自动调研记录

业务日期：2026-11-14 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

下载URL与model-index均明确对应 multilingual-e5-large-instruct，revision为274baa4，身份一致。可见材料提供分类、检索、聚类、重排序、语义文本相似度和双语文本挖掘评测记录，适合了解该准确变体的评测覆盖；标签包含sentence-transformers和transformers，但标签本身不足以证明具体运行环境兼容性。

依据：[src_837ff967cb7f10ab35df](https://huggingface.co/intfloat/multilingual-e5-large-instruct/raw/274baa4/README.md)

### 评测条件与可比性

多语言分类记录包含AmazonCounterfactual的en、de、en-ext、ja及AmazonReviews的en、de、es、fr、ja、zh；双语文本挖掘包括BUCC的四组语言对。BUCC条目使用test划分，数据revision为d51519689f32196a32af33b075a01d0e7c51e252；另有ArguAna、CQADupstack、ClimateFEVER、DBPedia、FEVER及FiQA2018等检索记录，其中多项revision为None。摘录未提供完整指令、编码、池化、软件版本或评测运行协议，本轮不提取数值成绩，也不据此给出与其他E5变体的受控性能比较。

依据：[src_837ff967cb7f10ab35df](https://huggingface.co/intfloat/multilingual-e5-large-instruct/raw/274baa4/README.md)

### 衍生关系

给定内容没有覆盖训练过程、权重清单或量化说明，无法核实原始字段所称F16权重、ONNX导出、第三方GGUF及其质量或兼容性；也无法确定该instruct变体的训练关系和查询指令模板。

依据：[src_837ff967cb7f10ab35df](https://huggingface.co/intfloat/multilingual-e5-large-instruct/raw/274baa4/README.md)

### 社区反馈与 Issue

本轮来源没有社区反馈或Issue正文，无法判断已知故障、用户体验或维护响应。可确认的资料限制是部分检索评测没有固定数据revision，且当前摘录未展示完整复现设置。

依据：[src_837ff967cb7f10ab35df](https://huggingface.co/intfloat/multilingual-e5-large-instruct/raw/274baa4/README.md)

### 冲突与待核实

来源标记truncated=True，在FiQA2018指标中途截断；后续评测和README正文未读。参数量、层数、向量维度、长度上限、完整语言范围、任务指令要求、许可证、发布方机构归属、模型创建日期、下载量、权重可用性与CPU运行性能均未由当前原始摘录证实，未将raw_fields中的说法写成已验证事实。researched仅表示本轮给定摘录已整理完成。

依据：[src_837ff967cb7f10ab35df](https://huggingface.co/intfloat/multilingual-e5-large-instruct/raw/274baa4/README.md)

### 已读取的来源

- [src_837ff967cb7f10ab35df](https://huggingface.co/intfloat/multilingual-e5-large-instruct/raw/274baa4/README.md) · source_statement · 2026-11-14T16:51:22+08:00
  阅读范围：至多18000字符；truncated=True
