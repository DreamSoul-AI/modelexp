# 360Zhinao3-7B

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

已阅读 qihoo360/360Zhinao3-7B 的 README@3f293b9 可见片段，下载表、Base 评测列和 Base 加载示例均对应目标模型。发布方将其定义为 7B 基座，在 360Zhinao2-7B 上以 700B 高质量 token 继续预训练，并称结构保持一致。卡片标注中英文，提供文本续写示例；适用范围可定位为基座能力研究及后续微调，不能把同页 Instruct 对话表现直接归给该 Base。

依据：[src_81c3309e3507c920f10b](https://huggingface.co/qihoo360/360Zhinao3-7B/raw/3f293b9/README.md)

### 评测条件与可比性

Base 评测明确使用 OpenCompass，覆盖考试、语言、知识、理解、推理、代码和数学；目标列报告 avg_zh 74.20、avg_all 74.83，部分单项为 C-Eval 84.7、MMLU 75.42、CMMLU 82.17、BBH 73.74、HumanEval 64.63、MBPP 67.80、MATH 37.60、GSM8K 78.77。这些均为发布方表格值；未披露 OpenCompass 版本、数据集版本及划分、few-shot 数、提示模板、采样参数、代码题执行与计分规则、聚合权重和硬件，不能作为完整协议下的可复现成绩。卡片的领先性描述也仅限发布方所列比较对象与设置。

依据：[src_81c3309e3507c920f10b](https://huggingface.co/qihoo360/360Zhinao3-7B/raw/3f293b9/README.md)

### 衍生关系

卡片列出 Base、Instruct、O1.5 三个独立模型入口，均在下载表中标为 BF16。O1.5 章节明确描述以 Instruct 为基础，采用 Light-R1 方法继续进行长思维链微调、RFT 和 GRPO；这些是系列衍生关系，不能据此断言 Base 本身经过相同后训练。微调章节提供从 multiturn_chat_0.8M 抽取 10,000 行的格式示例，脚本模型路径为 Instruct，因此该样例不能视为 Base 实际预训练数据或完整训练配方。所给材料没有量化制品证据。

依据：[src_81c3309e3507c920f10b](https://huggingface.co/qihoo360/360Zhinao3-7B/raw/3f293b9/README.md)

### 社区反馈与 Issue

部署章节推荐 vLLM 0.6.0，并要求复制架构实现及修改模型注册项，但启动命令实际指定 O1.5；本轮仅记录这项系列文档说明，不确认 Base 可直接按该命令运行。原始材料没有社区反馈、用户故障报告或 Issue 正文，无法判断实际兼容性问题及维护响应。

依据：[src_81c3309e3507c920f10b](https://huggingface.co/qihoo360/360Zhinao3-7B/raw/3f293b9/README.md)

### 冲突与待核实

README 片段在微调命令中途截断，后续参数、License 章节及可能存在的其他说明未读；链接指向的 GitHub、报告、代码、配置和权重文件也未提供正文。精确参数量、safetensors 分片与体积、完整 revision、实际显存及吞吐、最大上下文、量化与镜像、访问门槛、llama.cpp 兼容性和社区 Issue 均未核验。前代历史条目的 4K/32K/360K 上下文长度不能直接继承给本变体，微调样例 MAX_LEN=32768 也不能证明模型最大上下文。researched 仅表示给定片段的阅读整理完成。

依据：[src_81c3309e3507c920f10b](https://huggingface.co/qihoo360/360Zhinao3-7B/raw/3f293b9/README.md)

### 已读取的来源

- [src_81c3309e3507c920f10b](https://huggingface.co/qihoo360/360Zhinao3-7B/raw/3f293b9/README.md) · source_statement · 2026-11-15T18:19:03+08:00
  阅读范围：至多18000字符；truncated=True
