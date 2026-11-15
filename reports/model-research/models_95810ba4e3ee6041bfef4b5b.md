# granite-4.1-3b-llmon-preview

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

本轮材料对应granite-4.1-3b-llmon-preview、revision 55a14ca，模型卡开发者为IBM Granite Team。该模型从Granite-4.1-3B-base微调，采用LLMON替代常规聊天表示，面向通用指令、RAG、代码、函数调用和多语言助手，卡片列出包括中文在内的12种语言。其适用重点是提示中同时包含可信指令和不可信文档或工具结果、需要显式表达执行边界的场景。

依据：[src_4e2c8b65ea29d06e6d7d](https://huggingface.co/ibm-granite/granite-4.1-3b-llmon-preview/raw/55a14ca/README.md)

### 评测条件与可比性

模型卡以Granite-4.1-3B常规指令模型为对照，目标是维持通用任务能力，已读表格包含知识、推理、数学、代码、指令遵循及BFCL v3工具调用项目。部分任务标注few-shot、CoT或pass@1，但所给片段未提供可复现所需的完整评测版本、数据划分、提示与解码条件，因此本轮不提取数值成绩为字段。卡片明确说明这些评测不衡量LLMON面对未绑定或对抗内容时保持指令/数据边界的效果。

依据：[src_4e2c8b65ea29d06e6d7d](https://huggingface.co/ibm-granite/granite-4.1-3b-llmon-preview/raw/55a14ca/README.md)

### 衍生关系

有证据的训练关系是从Granite-4.1-3B-base微调为3B-LLMON预览版；8B-LLMON仅被列为同系列其他规模，不能互用其成绩或制品信息。后训练配方及提示注入、红队和注意力实验被指向另一篇论文，本文材料不含论文正文。原始字段中第三方FP8、ONNX、GGUF及imatrix GGUF没有本轮证据支持。

依据：[src_4e2c8b65ea29d06e6d7d](https://huggingface.co/ibm-granite/granite-4.1-3b-llmon-preview/raw/55a14ca/README.md)

### 社区反馈与 Issue

卡片说明通常通过apply_chat_template自动生成LLMON，无需手写标记；接入方仍需正确区分instruction、data、requirement、documents与tools，并设置执行绑定。文档中的预期输出不能替代真实运行结果。当前材料不含社区反馈或Issue，无法形成关于实际稳定性、兼容故障或维护状态的结论。

依据：[src_4e2c8b65ea29d06e6d7d](https://huggingface.co/ibm-granite/granite-4.1-3b-llmon-preview/raw/55a14ca/README.md)

### 冲突与待核实

README至多读取18000字符且被截断，表格尾部与后续章节未读；外链论文、博客、仓库和演示未读。原始字段中的3,659,737,600精确参数、7.32 GB与BF16，以及同代基座参数差异，均不能由当前模型卡核实。权重下载、访问门槛、许可证文件、量化、vLLM和llama.cpp支持、显存、速度及安全效果均未验证。模型卡声明发布日期为2026-11-12，不能以无本轮证据的仓库创建时间替代发布日期。researched仅表示完成给定片段整理。

依据：[src_4e2c8b65ea29d06e6d7d](https://huggingface.co/ibm-granite/granite-4.1-3b-llmon-preview/raw/55a14ca/README.md)

### 已读取的来源

- [src_4e2c8b65ea29d06e6d7d](https://huggingface.co/ibm-granite/granite-4.1-3b-llmon-preview/raw/55a14ca/README.md) · source_statement · 2026-11-15T18:00:28+08:00
  阅读范围：至多18000字符；truncated=True
