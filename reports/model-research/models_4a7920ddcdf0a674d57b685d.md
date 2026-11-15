# Light-IF-8B

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

指定来源的README标题、仓库链接和加载路径均指向Light-IF-8B，来源revision为dc9920b，身份一致。模型卡将其定位于复杂指令遵循，强调生成前预览约束、生成中推理及输出自检；适合据此考察受格式、行数、字数等多条件约束的文本生成能力，实际可靠性仍需任务验证。

依据：[src_37f7398a74ae924edc74](https://huggingface.co/qihoo360/Light-IF-8B/raw/dc9920b/README.md)

### 评测条件与可比性

发布方评测表列有Light-IF-8B在SuperClue、IFEval、CFBench、IFBench上的结果，并列出多个对照模型。给定README未说明评测集版本、切分、样本量、指标聚合口径、提示模板、采样参数、生成预算及评测脚本版本，因此本轮不形成数值成绩字段，也不能据此认定独立复现或通用性能优势。Quickstart的enable_thinking=True和max_new_tokens=32768只是使用示例设置，不能补作评测条件。

依据：[src_37f7398a74ae924edc74](https://huggingface.co/qihoo360/Light-IF-8B/raw/dc9920b/README.md)

### 衍生关系

元数据明确基座为Qwen/Qwen3-8B。模型卡介绍的训练流程包括生成复杂约束指令、过滤过易或过难样本、以拒绝采样构造适配数据，再进行保熵监督微调Entropy-SFT和逐token熵自适应强化学习TEA-RL，奖励采用规则式多维度设计；这些属于发布方方法描述，材料未提供可核验的训练数据清单、训练配置或量化衍生制品。

依据：[src_37f7398a74ae924edc74](https://huggingface.co/qihoo360/Light-IF-8B/raw/dc9920b/README.md)

### 社区反馈与 Issue

README包含加载示例和展示输出，但没有提供独立用户反馈、Issue讨论或修复记录，不能从展示案例推断实际部署稳定性。头图alt文本写作Light-IF-32B，与本卡名称不同；标题、仓库链接和加载路径仍一致指向8B，不能把图片替代文本当作32B身份依据。

依据：[src_37f7398a74ae924edc74](https://huggingface.co/qihoo360/Light-IF-8B/raw/dc9920b/README.md)

### 冲突与待核实

给定README文本已完成阅读，材料标记truncated=False；其链接的论文、GitHub、博客及外部图片内容未读取。精确参数量、BF16与分片信息、权重体积、官方或第三方量化、镜像逐文件一致性、创建日期、完整提交哈希、是否gated、独立LICENSE文件及硬件性能均未由本实体给定证据核验。researched仅表示本轮给定来源整理完成。

依据：[src_37f7398a74ae924edc74](https://huggingface.co/qihoo360/Light-IF-8B/raw/dc9920b/README.md)

### 已读取的来源

- [src_37f7398a74ae924edc74](https://huggingface.co/qihoo360/Light-IF-8B/raw/dc9920b/README.md) · source_statement · 2026-11-15T18:10:16+08:00
  阅读范围：至多18000字符；truncated=False
