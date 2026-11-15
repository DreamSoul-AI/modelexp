# TimeLens2-4B-SFT

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

来源标题、仓库路径与 TimeLens2-4B-SFT 变体一致。模型卡将其定义为基于 Qwen3-VL-4B-Instruct 的视频时序定位 SFT 检查点：输入视频与文本查询，学习返回所有相关时间区间。适用于生成离策略 rollout、复现或扩展 SFT→GRPO 流程，以及研究强化学习前的长视频定位能力；最终发布版另指向 TimeLens2-4B。本轮已整理给定页面，但页面未显示提交 SHA，不能证明内容对应指定 revision。

依据：[src_d9146eb9304bb635513e](https://hf.co/MCG-NJU/TimeLens2-4B-SFT)

### 评测条件与可比性

给定页面没有该 SFT 变体的评测成绩和完整评测协议，也未提供可复核的测试集划分、指标实现或推理资源数据。因此不能把最终 GRPO 版本的表现归给本检查点，也不能从训练长度推定实际推理上限。

依据：[src_d9146eb9304bb635513e](https://hf.co/MCG-NJU/TimeLens2-4B-SFT)

### 衍生关系

训练关系明确为 Qwen3-VL-4B-Instruct→本 SFT 检查点→后续 rollout 与 GRPO 阶段。卡片称 SFT 使用 TimeLens2-93K、TimeLens-100K 和 Ego4D-NLQ-v2 官方训练划分，保留完整视频上下文，监督可变数量的时间区间，并采用多种指令与时间戳格式。配方为训练 1 个 epoch、打包序列最长 100K tokens、全局 batch size 256、学习率 5e-6，视觉编码器冻结；这些是发布方说明，未独立复现。模型树显示一个量化衍生项，但当前材料不足以确认发布者或具体规格。

依据：[src_d9146eb9304bb635513e](https://hf.co/MCG-NJU/TimeLens2-4B-SFT)

### 社区反馈与 Issue

加载说明存在需要核对的入口差异：正文要求通过 dataset 仓库下载后本地加载，页面通用组件则展示模型 ID 直接加载。材料未包含实际加载结果、社区讨论正文或 Issue 内容，不能据此判定加载失败，也无法归纳社区问题的严重性或解决状态。

依据：[src_d9146eb9304bb635513e](https://hf.co/MCG-NJU/TimeLens2-4B-SFT)

### 冲突与待核实

指定 main@f3349f640ff90ad6054d386a63ecbc9f8a599448 未在页面材料中得到提交级核验，故未填写 revision 候选。论文正文、官方代码、数据集说明、文件清单、许可证文件、量化衍生页面和社区讨论均未提供或未读；精确参数量、分片布局、权重体积、显存、依赖最低版本及实际可加载性尚未核验。原始字段中的精确参数量、文件大小和第三方 GGUF 规格未获本实体证据支持，未沿用。researched 仅表示给定页面整理完成。

依据：[src_d9146eb9304bb635513e](https://hf.co/MCG-NJU/TimeLens2-4B-SFT)

### 已读取的来源

- [src_d9146eb9304bb635513e](https://hf.co/MCG-NJU/TimeLens2-4B-SFT) · source_statement · 2026-11-15T18:33:40+08:00
  阅读范围：至多18000字符；truncated=False
