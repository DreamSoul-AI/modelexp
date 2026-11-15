# KV1-1.2B

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

本轮对象为仓库KV1-1.2B的6f9e1a0版本，卡面标题为KV1-1.2B-Instruct。它以LFM2.5-1.2B-Instruct为基座，针对低位宽KV缓存进行训练，适合研究长上下文缓存占用与生成质量之间的取舍。卡面标称1.17B参数、32,768 token上下文，权重保持BF16；“2-bit”指缓存量化码，计入缩放与偏置后实际为2.5 bits/value。

依据：[src_bbfaf40f1f9a0413d437](https://huggingface.co/klein-ml/KV1-1.2B/raw/6f9e1a0/README.md)

### 评测条件与可比性

发布方报告使用lm-eval并应用聊天模板：KV1的IFEval prompt-strict为77.63（541个提示），GSM8K 5-shot为44.80（250题），HumanEval pass@1为40.24（164题，卡面标注±3.8），MMLU-Pro 5-shot CoT为21.12（980题，每学科70题），GPQA-Diamond CoT为24.24（198题，卡面标注±3.1）。KV1使用自身训练后权重与BQ2_0缓存，对照组使用原始LFM2.5-1.2B-Instruct权重及不同精度缓存。材料未给出lm-eval版本、完整解码配置、题目抽样清单及误差区间的统计定义，无法完整复现；这些是发布方自报成绩。

另有发布方自建25任务测试集，涵盖指令、数学、执行单元测试的代码、原生工具调用与最长16K检索，KV1通过22/25，原模型FP16缓存通过24/25。卡面称所有工具调用及长上下文任务均通过，但未提供完整题目与判定代码。75.8%的“能力保留率”是六行测试相对FP16成绩比例的平均，包含自建测试集，并非统一通用能力指标；GPQA-Diamond的24.24接近25%的随机水平。

卡面给出每序列32K打包缓存60 MiB，对比FP16的384 MiB，约缩小6.4倍；该比较仅涉及KV缓存，BF16权重约2.3 GB不变。首版KV1.cpp会将缓存解包到复用的FP16临时缓冲区，32K时约64 MiB，因此实际峰值内存高于60 MiB。材料没有端到端吞吐、延迟或整机峰值内存实测。

依据：[src_bbfaf40f1f9a0413d437](https://huggingface.co/klein-ml/KV1-1.2B/raw/6f9e1a0/README.md)

### 衍生关系

训练以冻结的原模型及FP16缓存为教师，学生使用量化缓存；损失为逐位置完整下一token分布KL散度，加0.5倍归一化逐层隐藏状态MSE。方法包括直通估计器、Hadamard旋转和保留前4个token的FP16缓存。750M训练token的输入构成为聊天60%、代理及工具轨迹16%、代码12%、网页7%、数学5%；卡面报告使用一张RTX Pro 6000约17 GPU小时。

卡面链接同发布方GGUF仓库，声明有BF16、Q8_0、Q4_K_M权重量化版本；权重量化与BQ2_0缓存量化属于不同维度。2.6B仍在训练、其他规模处于计划中，不能据此认定它们已经发布。

依据：[src_bbfaf40f1f9a0413d437](https://huggingface.co/klein-ml/KV1-1.2B/raw/6f9e1a0/README.md)

### 社区反馈与 Issue

发布方明确指出知识密集型选择题恢复不足，拟通过短且按文档分隔的序列训练改进。运行方面，Transformers示例只模拟量化后的数值行为，缓存仍以BF16保存；实际缓存节省依赖KV1.cpp分支。给定材料没有社区讨论或Issue记录，不能把这些发布方说明当作社区验证。

依据：[src_bbfaf40f1f9a0413d437](https://huggingface.co/klein-ml/KV1-1.2B/raw/6f9e1a0/README.md)

### 冲突与待核实

已读完给定README，材料标记未截断；本轮researched仅表示该来源整理完成。未提供或未读取的内容包括LICENSE全文、权重及配置文件、GGUF文件清单与大小、KV1.cpp实现、演示页面、基座仓库、社区反馈及Issue。不能确认许可的具体商业条款、是否gated、精确参数总数、各量化制品可下载性或真实运行表现。卡面的训练、内存与评测声明均未独立复现。

依据：[src_bbfaf40f1f9a0413d437](https://huggingface.co/klein-ml/KV1-1.2B/raw/6f9e1a0/README.md)

### 已读取的来源

- [src_bbfaf40f1f9a0413d437](https://huggingface.co/klein-ml/KV1-1.2B/raw/6f9e1a0/README.md) · source_statement · 2026-11-15T17:46:51+08:00
  阅读范围：至多18000字符；truncated=False
