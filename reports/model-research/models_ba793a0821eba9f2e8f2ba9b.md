# pearl-chat-85m-it

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

来源标题及下载路径与 pearl-chat-85m-it、revision `1c07979` 一致，模型卡明确将其定位为卢干达语多轮指令微调检查点。适用定位为卢干达语指令交互和多轮对话研究；临床健康语料的出现本身不构成医疗任务可靠性的证据。

依据：[src_b75b617919d70722c06e](https://huggingface.co/ai4ug/pearl-chat-85m-it/raw/1c07979/README.md)

### 评测条件与可比性

模型卡的 `v5 gates` 摘要覆盖乌干达事实与谚语通过率、四轮多轮连贯率、多轮问候塌缩率及 BLiMP-Luganda 最小对准确率。这些属于来源报告，未独立复测；材料没有样本量、测试集版本、提示模板、解码参数、评分实现或重复试验信息，因此本轮不将数值转成具有完整协议上下文的成绩候选，也不据此推断通用能力。

依据：[src_b75b617919d70722c06e](https://huggingface.co/ai4ug/pearl-chat-85m-it/raw/1c07979/README.md)

### 衍生关系

当前变体明确属于多轮指令微调检查点，模型卡列出 `ai4ug/luganda_pretrain_v5` 和 `ai4ug/luganda_sft_v5`。给定材料没有明确指向某个基座权重 revision，也未说明训练步数、优化器、数据配比或对齐算法；量化版本及转换制品同样没有来源支持。

依据：[src_b75b617919d70722c06e](https://huggingface.co/ai4ug/pearl-chat-85m-it/raw/1c07979/README.md)

### 社区反馈与 Issue

本轮没有社区讨论或 Issue 原文。模型卡中的问候塌缩率是评测项目，不能当作社区故障报告，也不能证明实际部署不存在该类问题。

依据：[src_b75b617919d70722c06e](https://huggingface.co/ai4ug/pearl-chat-85m-it/raw/1c07979/README.md)

### 冲突与待核实

已整理本轮提供的 README 内容，采集标记为未截断。尚未核验权重文件、精度、文件大小、下载权限、独立 LICENSE、聊天模板和实际推理支持；没有延迟、吞吐、内存或 CPU 可用性的实测依据。其他语言能力、量化质量、训练细节及社区反馈均待补充。仓库其他文件未提供，未视为已阅读或验证；researched 仅表示本轮来源整理完成。

依据：[src_b75b617919d70722c06e](https://huggingface.co/ai4ug/pearl-chat-85m-it/raw/1c07979/README.md)

### 已读取的来源

- [src_b75b617919d70722c06e](https://huggingface.co/ai4ug/pearl-chat-85m-it/raw/1c07979/README.md) · source_statement · 2026-11-15T17:51:31+08:00
  阅读范围：至多18000字符；truncated=False
