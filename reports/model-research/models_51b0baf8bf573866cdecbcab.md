# Sapiens2-1B 表面法线估计

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

该来源明确对应 facebook/sapiens2-normal-1b，即普通 1B 表面法线变体；家族表中的 1B-4K 是另一变体。模型由 Sapiens2-1B 预训练骨干微调，采用 ViT 骨干与法线估计头，输出相机坐标系下的三通道单位法线，适用范围为人体中心图像与相关视觉研究。模型卡给出的推理分辨率为 1024×768（高×宽）。

依据：[src_604a49e4d4f75ad4ade4](https://hf.co/facebook/sapiens2-normal-1b)

### 评测条件与可比性

模型卡列出骨干参数量 1.462B、骨干 FLOPs 4.715T，以及 1536 维嵌入、40 层、24 个注意力头和 patch size 16。这些是结构与计算量标注，不能作为法线预测精度或实测速度。给定页面没有测试集、误差指标、硬件、推理精度及计时协议，因此本轮不填写成绩或推导性能排名。

依据：[src_604a49e4d4f75ad4ade4](https://hf.co/facebook/sapiens2-normal-1b)

### 衍生关系

训练关系明确指向 facebook/sapiens2-pretrain-1b。官方模型卡列出 sapiens2_1b_normal.safetensors，页面标注 F32；模型树显示一个微调条目和一个量化条目，但摘录没有其名称、量化方案或质量验证，无法据此确认具体第三方制品。

依据：[src_604a49e4d4f75ad4ade4](https://hf.co/facebook/sapiens2-normal-1b)

### 社区反馈与 Issue

页面展示 Community 计数 4，并列出官方及社区 Spaces，但未提供讨论正文或 Issue 内容，无法归纳用户反馈和故障。页面还展示 Transformers 专用类加载示例，因此原始待核字段中“不是 transformers 原生支持”的说法不宜继续采用；示例对应的版本与实际可运行性仍需核验。

依据：[src_604a49e4d4f75ad4ade4](https://hf.co/facebook/sapiens2-normal-1b)

### 冲突与待核实

已读完本轮所给页面摘录，模型身份一致；但摘录没有提交哈希，尚不能核实目标 revision main@3480505c6690732dfdc91e7078213dba14844ab3，故不填 revision 候选。论文、官方代码、法线指南、许可全文、文件清单和社区讨论正文均未提供，未作阅读验证。总参数精确值、文件大小、两个权重文件是否重复、Reza2kn INT4-G128 与 MLX 制品、商用及用途限制、显存需求和 CPU／手机可用性均未获本轮原始证据支持。researched 仅表示给定来源整理完成。

依据：[src_604a49e4d4f75ad4ade4](https://hf.co/facebook/sapiens2-normal-1b)

### 已读取的来源

- [src_604a49e4d4f75ad4ade4](https://hf.co/facebook/sapiens2-normal-1b) · source_statement · 2026-11-15T18:51:42+08:00
  阅读范围：至多18000字符；truncated=False
