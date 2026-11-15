# DWSLM-256M-Base-32K

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

本轮对象为DWSLM-256M-Base-32K的639dc81版本，不能与4K版的评测数值混用。它在DWSLM-256M-Base基础上，以至少16K token的文档额外训练953步、约500M token，对学习型旋转频率应用YaRN ×8，将上下文扩展至32,768 token；总训练量为24.11B token。它仍是未经指令微调及安全训练的基座模型，适用于续写、似然评分及长上下文训练研究。

模型采用20层混合架构，每组包含三层Kimi Delta Attention和一层全局注意力；卡面标称286M计算参数、369M查找参数，约655M存储参数。名称中的256M不等于交付权重总参数量，权重声明为FP32主权重。

依据：[src_f06cdc95339505e2efd8](https://huggingface.co/dwsllc/DWSLM-256M-Base-32K/raw/639dc81/README.md)

### 评测条件与可比性

发布方报告零样本cloze、按选项UTF-8字节归一化对数似然的长度归一化准确率，使用完整评测集、同一程序及BF16评分；提示遵循lm-evaluation-harness／OLMES，MMLU采用SmolLM cloze提示。元数据成绩为HellaSwag validation 0.3488、ARC-Easy test 0.4465、ARC-Challenge test 0.2509、PIQA validation 0.6148、WinoGrande validation（winogrande_xl）0.5075、MMLU test（all）0.2709；卡面六任务平均为0.407，标准误约±0.4个百分点。完整评测代码版本、提示与日志未随给定材料提供，未独立复现。

本变体在自有语料留出集、4K条件下的bits per byte为0.9957，扩展前为0.9963，发布方据此称短上下文质量保持。卡面另报告32K训练第95步至第953步的分位置bits per byte：0–4K从0.831降至0.822，4K–8K从0.804降至0.793，8K–16K从0.806降至0.795，16K–32K从0.791降至0.780。该位置评测的具体数据划分、样本量及统计误差未交代，只能视为发布方训练诊断，不能替代长上下文检索或推理验证。

依据：[src_f06cdc95339505e2efd8](https://huggingface.co/dwsllc/DWSLM-256M-Base-32K/raw/639dc81/README.md)

### 衍生关系

本变体的直接训练来源为DWSLM-256M-Base。共享预训练阶段为45,030步、23.61B token；32K阶段额外进行953步，每步524,288 token，学习率从基座最终下限1.85×10⁻⁴开始。共享预训练语料包括网页、代码、公版书籍、百科、科学、政府、新闻及数学，并加入289M合成改写token。卡面的32.8单GPU小时和约4.1×10¹⁹ FLOPs属于共享预训练描述，不能直接当作包含32K扩展的总成本。

卡面提供FP32权重及参考实现说明，没有列出本变体的量化或GGUF衍生，也没有提供这些制品不存在的证据。

依据：[src_f06cdc95339505e2efd8](https://huggingface.co/dwsllc/DWSLM-256M-Base-32K/raw/639dc81/README.md)

### 社区反馈与 Issue

参考实现不含KV缓存，每个生成token都重新运行前缀；32K输入条件下的生成速度及显存需求需要实际测量。默认推理路径依赖Ampere或更新NVIDIA GPU，训练使用的cuDNN路径则面向Hopper及Blackwell数据中心GPU。卡面提示模型经常出错、多语言质量不均且无安全训练；给定材料未包含社区反馈、Issue或修复记录。

依据：[src_f06cdc95339505e2efd8](https://huggingface.co/dwsllc/DWSLM-256M-Base-32K/raw/639dc81/README.md)

### 冲突与待核实

已读完本变体给定的未截断README；researched只表示给定来源阅读整理完成。未读取链接中的完整技术报告，也未检查权重、配置、实现、依赖及LICENSE文件，无法核实精确参数量、文件大小、下载及gated状态。量化制品、CPU及llama.cpp支持、32K峰值显存、吞吐、延迟、长文检索和推理能力均未验证；位置bits per byte的评测细节仍缺失。select字段未提供可核对的现有选项清单，因此未补写发布方或模态选项。

依据：[src_f06cdc95339505e2efd8](https://huggingface.co/dwsllc/DWSLM-256M-Base-32K/raw/639dc81/README.md)

### 已读取的来源

- [src_f06cdc95339505e2efd8](https://huggingface.co/dwsllc/DWSLM-256M-Base-32K/raw/639dc81/README.md) · source_statement · 2026-11-15T17:46:52+08:00
  阅读范围：至多18000字符；truncated=False
