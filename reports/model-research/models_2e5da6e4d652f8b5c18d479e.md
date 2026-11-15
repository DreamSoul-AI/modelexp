# Hark

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

已提供材料是 Hark 的权重模型卡，明确将其描述为支持英语和德语的零样本唤醒词引擎，通过输入短语指定唤醒词。模型卡提及 Home Assistant 应用和 Docker 镜像会自动获取、校验权重，适用方向是自定义唤醒短语与相关语音交互集成；本轮未验证集成运行效果。

依据：[src_2c950a51d4389f6f9b77](https://huggingface.co/Pioborgelt/hark/raw/main/README.md)

### 评测条件与可比性

模型卡将 benchmarks 链接到 GitHub，但给定正文没有测试集、误唤醒率、漏检率、检测阈值、噪声条件、延迟或硬件信息，不能形成有协议支持的成绩候选，也不能据此判断英语和德语在不同口音及噪声环境中的表现。

依据：[src_2c950a51d4389f6f9b77](https://huggingface.co/Pioborgelt/hark/raw/main/README.md)

### 衍生关系

给定材料仅确认这是权重仓库，未说明基础模型、训练数据、训练阶段、蒸馏关系、量化或 ONNX 导出情况。不能将原始字段中的检查点名称、数量及体积当作已核实制品信息。

依据：[src_2c950a51d4389f6f9b77](https://huggingface.co/Pioborgelt/hark/raw/main/README.md)

### 社区反馈与 Issue

权重的非商业许可与代码的 MIT 许可需要分别处理。模型卡提供 GitHub issues 入口，但本轮没有任何 Issue 正文、维护者回复或独立社区反馈，无法支持关于稳定性、兼容性或缺陷修复状态的结论。

依据：[src_2c950a51d4389f6f9b77](https://huggingface.co/Pioborgelt/hark/raw/main/README.md)

### 冲突与待核实

材料来自 raw/main，目标 revision「sha d3eb2fd3」未获得固定提交证据。已完整阅读所给短模型卡，但关联 GitHub 的安装、评测、Issue 和许可文件均未提供。精确参数量、权重文件格式与容量、CPU 支持、依赖版本、音频输入规格、评分输出形式及量化制品均待核实。researched 仅表示给定模型卡的整理完成。

依据：[src_2c950a51d4389f6f9b77](https://huggingface.co/Pioborgelt/hark/raw/main/README.md)

### 已读取的来源

- [src_2c950a51d4389f6f9b77](https://huggingface.co/Pioborgelt/hark/raw/main/README.md) · source_statement · 2026-11-15T19:01:22+08:00
  阅读范围：至多18000字符；truncated=False
