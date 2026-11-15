# granite-switch-4.1-30b

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

本档案对应仓库granite-switch-4.1-30b的eb20672提交，卡面实际版本为4.1.1，不能按仓库名称将其视作初始4.1。它在同一端点组合聊天、选项决策、安全检测与语音转写；decision返回选项标签概率，guardian-core以JSON封装yes/no判断。适合需要这些操作共享部署端点的应用。

依据：[src_bee1a0404906afed5ea5](https://huggingface.co/ibm-granite/granite-switch-4.1-30b/raw/eb20672/README.md)

### 评测条件与可比性

卡片报告了4.1.1 decision aLoRA在公开Jev Decision Index v0.3上的发布方评测。协议使用固定决策引擎系统提示，将State回合运行在冻结基座上，再以### DECISION回合提供问题和单令牌标签选项，读取首个助手令牌的选项logits并做softmax；Overall采用机会校正加权聚合，表中分数按×100展示。该结果适用对象是decision适配器，不能直接代表聊天、Guardian或语音能力。摘录未提供样本数、重复运行与误差估计；本轮未复现，也不将后文无系统提示的部署示例视为同一评测协议。

依据：[src_bee1a0404906afed5ea5](https://huggingface.co/ibm-granite/granite-switch-4.1-30b/raw/eb20672/README.md)

### 衍生关系

这是组合检查点：基座为ibm-granite/granite-4.1-30b，两个aLoRA分别来自Guardian与Core库，另嵌入470M语音编码器。卡片给出使用granite-switch 0.1.1重建组合的配方，并说明4.1.1保持两个适配器的配置类别、更新decision权重。其链接的8B与preview系列是其他变体，不能把它们的配置或能力归入本实体。

依据：[src_bee1a0404906afed5ea5](https://huggingface.co/ibm-granite/granite-switch-4.1-30b/raw/eb20672/README.md)

### 社区反馈与 Issue

文档明确的运行边界包括：语音仅以ASR级联方式接入，尚无联合训练和解码时引导；decision尚无Mellea intrinsic；vLLM一次最多请求128个标签token的logprob，更多选项需要多次请求。以上是文档限制，给定材料没有社区Issue或用户实测记录可用于判断实际故障频率。

依据：[src_bee1a0404906afed5ea5](https://huggingface.co/ibm-granite/granite-switch-4.1-30b/raw/eb20672/README.md)

### 冲突与待核实

README在How It Works部分被截断，后续内容未读；BUILD.md、AUDIO.md、依赖实现、权重、许可文件及链接中的评测榜单均未读取。精确总参数量、文件分片数和体积、GGUF及MLX量化制品、量化后的音频与适配器兼容性、显存占用、吞吐和延迟均未由本轮证据验证；卡片的ASR速度领先表述缺少日期与完整协议，不能作为已核验排名。未取得社区反馈或Issue材料。researched仅表示本轮所给摘录整理完成。

依据：[src_bee1a0404906afed5ea5](https://huggingface.co/ibm-granite/granite-switch-4.1-30b/raw/eb20672/README.md)

### 已读取的来源

- [src_bee1a0404906afed5ea5](https://huggingface.co/ibm-granite/granite-switch-4.1-30b/raw/eb20672/README.md) · source_statement · 2026-11-15T18:07:00+08:00
  阅读范围：至多18000字符；truncated=True
