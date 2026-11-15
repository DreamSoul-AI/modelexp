# TimeLens2-2B-SFT

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

页面标题与正文均明确指向 TimeLens2-2B-SFT，支持该变体身份。这是从 Qwen3-VL-2B-Instruct 初始化的监督微调检查点，输入视频和文本查询，学习返回包含目标视觉证据的全部时间区间；主要用于研究强化学习前的长上下文时序定位，以及后续 rollout 生成和 GRPO 训练。

依据：[src_6d1cbfb0b5a528b32892](https://hf.co/MCG-NJU/TimeLens2-2B-SFT)

### 评测条件与可比性

材料没有给出此 SFT 检查点的评测成绩或完整评测协议。正文明确区分它与论文报告的最终 GRPO 优化版本，因此不能把最终 TimeLens2-2B 的成绩归给本实体。

依据：[src_6d1cbfb0b5a528b32892](https://hf.co/MCG-NJU/TimeLens2-2B-SFT)

### 衍生关系

模型卡称 SFT 使用 TimeLens2-93K、TimeLens-100K 与 Ego4D-NLQ-v2 官方训练划分，保留完整视频上下文，监督可变数量的时间区间集合，并采用多样化指令和时间戳响应格式。2B 配方为训练一轮、打包序列最长 160K tokens、全局批量 128、学习率 1e-5，视觉编码器冻结；160K 是这里记载的训练序列长度，不能直接视为已验证的推理容量。该检查点是后续 GRPO 的起点；模型树另显示一个量化条目，但未展开其规格。

依据：[src_6d1cbfb0b5a528b32892](https://hf.co/MCG-NJU/TimeLens2-2B-SFT)

### 社区反馈与 Issue

页面提供模型仓库的自动加载提示，但正文另称检查点托管在 dataset 仓库，并要求以 repo_type=dataset 下载；实际托管位置与可执行加载路径仍需核实。材料没有具体社区反馈或 Issue 正文；采集时页面显示没有 Inference Provider 部署。

依据：[src_6d1cbfb0b5a528b32892](https://hf.co/MCG-NJU/TimeLens2-2B-SFT)

### 冲突与待核实

页面未出现提交哈希，无法核对 main@a559dcbdcc84ca95c3f8c3edffe4a0a63e7398b1，故不生成 revision 字段。本轮仅完成所给模型卡整理，未读取其链接指向的训练仓库、数据集、论文、评测代码或量化仓库，也未验证加载。原始字段所称语言／视觉／投影分拆文件、精确参数量、文件体积及仓库创建日期均缺少给定正文支持；显存、速度、硬件要求和 SFT 独立评测仍未知。

依据：[src_6d1cbfb0b5a528b32892](https://hf.co/MCG-NJU/TimeLens2-2B-SFT)

### 已读取的来源

- [src_6d1cbfb0b5a528b32892](https://hf.co/MCG-NJU/TimeLens2-2B-SFT) · source_statement · 2026-11-15T18:30:47+08:00
  阅读范围：至多18000字符；truncated=False
