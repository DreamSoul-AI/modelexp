# granite-switch-4.1-8b

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

固定提交 fb4aa78 对应仓库 granite-switch-4.1-8b，但已读模型卡明确标识为产品修订 4.1.1，应与原始 4.1 及 8B Preview 区分。该修订只有 decision、guardian-core 两个 aLoRA 适配器，聊天能力来自基座；另内嵌 470M TurboCTC 语音编码器。适用任务包括自然语言回复、带标签选项的决策、安全检测，以及英语、法语、德语、西班牙语、葡萄牙语、意大利语和日语的转写后对话。音频路径为 ASR 转写再交给 LLM，不能据此认定具备对原始音频的端到端理解或音频输出能力。

依据：[src_95b73cbeda6038831596](https://huggingface.co/ibm-granite/granite-switch-4.1-8b/raw/fb4aa78/README.md)

### 评测条件与可比性

模型卡报告的是 4.1.1 的 decision aLoRA 在公开 Jev Decision Index v0.3 上的成绩：Overall 46.72、Knowledge 28.7、Language 53.1、Retrieval 60.4、Tools 63.4、Arts 19.0；均为分数乘以 100，Overall 为机会校正后的加权聚合。已披露协议采用固定 decision-engine 系统提示，先在冻结基座上处理 State: 回合，再以 ### DECISION 回合给出问题和单 token 标签选项，读取首个 assistant token 的选项标签 logits 并作 softmax。这是模型卡自报结果，未提供硬件、推理后端版本、样本量及完整评测脚本，未独立复现；后文为缓存复用展示的无系统提示调用示例不同于上述评测提示协议，不能直接替代它。关于 ASR“最快”的表述未附比较日期及完整协议，不作为经验证排名。

依据：[src_95b73cbeda6038831596](https://huggingface.co/ibm-granite/granite-switch-4.1-8b/raw/fb4aa78/README.md)

### 衍生关系

4.1.1 保留 4.1 的两个适配器，更新 decision 权重而保持调用格式和读出方式，并将语音输入由英语扩展为七语种，转写带标点和大小写。模型卡提供 granite-switch==0.1.1 的组合路径：基座 granite-4.1-8b，筛选 Core 与 Guardian 库中的 decision、guardian-core aLoRA，并启用音频编码器；具体秩与目标层需读取 BUILD.md。模型卡列出 4.1.1 标签 granite-switch-4.1.1-8b 和旧版标签 granite-switch-4.1-8b，但未提供量化制品证据。

依据：[src_95b73cbeda6038831596](https://huggingface.co/ibm-granite/granite-switch-4.1-8b/raw/fb4aa78/README.md)

### 社区反馈与 Issue

已读文档说明 decision 尚无 Mellea intrinsic，应使用低层接口；guardian-core 可通过 Mellea 调用。decision 的选项概率读取依赖单 token 标签与 logprob_token_ids，文档指出每请求超过 128 个 ID 会触发 HTTP 400，并给出相同提示下分块取回、统一 softmax 的处理方式；这是文档限制及方案，未经本轮实测。材料未包含社区反馈或 Issue 原文，不能据此判断实际用户故障频率或修复状态。

依据：[src_95b73cbeda6038831596](https://huggingface.co/ibm-granite/granite-switch-4.1-8b/raw/fb4aa78/README.md)

### 冲突与待核实

给定 README 明确被截断，末尾停在 How It Works 架构示意中，后续内容未读；BUILD.md、AUDIO.md、决策适配器卡、Jev 数据与评测实现、发布博客、许可证正文和外链教程也未提供。权重实际文件、总参数量、精度、大小、GGUF/MLX 或其他量化版、量化后音频与适配器兼容性、显存与吞吐、下载门槛均未核实。原始字段中关于 Chat 适配器、精确参数量及量化制品的描述不作为事实候选；已读模型卡明确只列两个适配器。researched 仅表示现有实质来源足以形成该固定提交的档案，不表示截断部分、跑分或运行可用性已验证。

依据：[src_95b73cbeda6038831596](https://huggingface.co/ibm-granite/granite-switch-4.1-8b/raw/fb4aa78/README.md)

### 已读取的来源

- [src_95b73cbeda6038831596](https://huggingface.co/ibm-granite/granite-switch-4.1-8b/raw/fb4aa78/README.md) · source_statement · 2026-11-15T18:03:46+08:00
  阅读范围：至多18000字符；truncated=True
