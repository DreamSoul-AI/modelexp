# NVIDIA-Nemotron-3-Nano-4B-BF16

## 自动调研记录

业务日期：2026-11-14 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

本档案对应 `nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16@dfaf35d`，模型卡内部版本为v1.0。作者描述其由9B-v2父模型压缩而来，采用Mamba2-Transformer混合架构，面向英文和代码任务，可通过聊天模板控制推理开关。边缘Agent、游戏NPC、本地语音助手和IoT自动化是目标场景；已列出的模型原生输入输出均为文本，语音场景不构成原生音频能力证据。

依据：[src_2d7a36e0f6020df2b88f](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16/raw/dfaf35d/README.md)

### 评测条件与可比性

模型卡分别提供Reasoning-off与Reasoning-on成绩表，使用NeMo-Skills和Orak；Orak注明仅评估Super Mario、Darkest Dungeon和StarDew Valley三款游戏。两种模式覆盖的任务集合不完全相同，不能将结果混合。正文缺少完整评测版本、提示、采样次数、输出预算和计分设置，因此本轮不提取数值成绩，也不把部署示例或推荐采样参数当成评测协议。

依据：[src_2d7a36e0f6020df2b88f](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16/raw/dfaf35d/README.md)

### 衍生关系

来源明确列出父模型 `nvidia/NVIDIA-Nemotron-Nano-9B-v2` 及Nemotron Elastic压缩关系。后训练说明包含多语言文本，并称使用DeepSeek、Qwen和Nemotron等模型生成的合成推理数据；这不等于支持语言承诺扩展到全部训练语言。当前材料只支持BF16变体身份，没有官方量化版或第三方GGUF、ONNX的核验材料。

依据：[src_2d7a36e0f6020df2b88f](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16/raw/dfaf35d/README.md)

### 社区反馈与 Issue

README一处称模型由NVIDIA从头训练，另一处明确称由9B-v2压缩，需进一步厘清各阶段的训练关系。Transformers示例加载 `nvidia/NVIDIA-Nemotron-3-Nano-4B`，而当前仓库及vLLM、TRT-LLM示例使用带 `-BF16` 后缀的名称，不能据前者确认当前变体已在该Transformers版本通过测试。材料提供Discord入口，但没有社区反馈或Issue正文，无法判断用户问题及修复情况。

依据：[src_2d7a36e0f6020df2b88f](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16/raw/dfaf35d/README.md)

### 冲突与待核实

本轮README在公共数据集表中截断，截断后的全部内容未读；链接中的技术报告、完整许可、运行容器和评测代码亦未读。未检查权重、配置、解析器、量化制品、实际可下载性或任何运行性能。卡面预训练截止日期与后文数据收集日期属于不同口径，其关系尚未厘清；超过10T tokens的训练数据声明也未进一步核对到压缩和后训练各阶段。现有标题和来源可支持实体身份，故标记为researched，仅表示本轮给定片段整理完成。

依据：[src_2d7a36e0f6020df2b88f](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16/raw/dfaf35d/README.md)

### 已读取的来源

- [src_2d7a36e0f6020df2b88f](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16/raw/dfaf35d/README.md) · source_statement · 2026-11-14T16:43:12+08:00
  阅读范围：至多18000字符；truncated=True
