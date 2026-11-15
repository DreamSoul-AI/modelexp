# Qwen3-VL-Embedding-8B

## 自动调研记录

业务日期：2026-11-14 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

给定来源路径、模型标题与revision 2c45655一致，元数据标注基础模型为Qwen/Qwen3-VL-8B-Instruct。该8B变体将文本、图像、截图、视频及混合输入编码到共享向量空间，用于多模态检索、匹配和聚类；模型卡标称支持30多种语言、32k上下文、自定义指令及64至4096维输出。配套Reranker承担相关性打分，不能与本实体的向量输出混同。

依据：[src_00d61e3624363b25c27f](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B/raw/2c45655/README.md)

### 评测条件与可比性

已提供部分包含MMEB-V2与MMTEB成绩表。MMEB-V2表覆盖78个数据集，分为图像36个、视频18个和视觉文档24个，并注明除IFM-TTE外均在更新的VisDoc OOD划分上重新评测；MMTEB表区分任务均值、类型均值与各任务类别。材料未完整给出指标计算、数据与代码版本、输出维度、视觉预处理、视频采样及评测指令等协议，因此不录入数值成绩，也不将其他Embedding或Reranker变体的结果归给本实体。

依据：[src_00d61e3624363b25c27f](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B/raw/2c45655/README.md)

### 衍生关系

模型卡支持与Qwen3-VL-8B-Instruct的基础模型关系，并声明支持MRL自定义输出维度及嵌入量化后处理。表下注释明确Quantization Support针对输出向量，不能推出已有GGUF、FP8、W8A8或其他权重量化版本；已提供部分没有这些制品的可核验记录。

依据：[src_00d61e3624363b25c27f](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B/raw/2c45655/README.md)

### 社区反馈与 Issue

Sentence Transformers示例默认通过系统提示使用“Represent the user's input.”指令，也展示了自定义检索提示。Transformers示例建议启用flash_attention_2以加速和节省内存，但没有给出硬件与资源实测。给定材料没有社区反馈、Issue讨论或独立复现记录，无法据此判断实际部署稳定性。

依据：[src_00d61e3624363b25c27f](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B/raw/2c45655/README.md)

### 冲突与待核实

本轮已阅读给定截取，但README在vLLM示例的main函数开头截断，后续内容未读；技术报告、博客、GitHub及外部排行榜也未提供或阅读。视频完整调用路径、vLLM完整配置、精确参数量、权重分片与体积、许可正文、访问门槛、权重量化及其视觉兼容性、显存、吞吐、完整评测协议和社区Issue均尚未验证。researched表示身份一致且已完成给定实质材料的整理，不表示全文或产品可用性已验证。

依据：[src_00d61e3624363b25c27f](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B/raw/2c45655/README.md)

### 已读取的来源

- [src_00d61e3624363b25c27f](https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B/raw/2c45655/README.md) · source_statement · 2026-11-14T16:26:53+08:00
  阅读范围：至多18000字符；truncated=True
