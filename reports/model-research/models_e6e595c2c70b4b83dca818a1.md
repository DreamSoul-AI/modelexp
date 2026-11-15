# Sapiens2-5B 表面法线估计

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

来源明确对应 facebook/sapiens2-normal-5b，即 5B 表面法线任务检查点。它由 Sapiens2-5B 预训练骨干微调，采用 ViT 骨干与法线估计头，针对人体中心图像输出相机坐标系下的三通道单位法线；模型卡标注推理分辨率为 1024×768（高×宽）。

依据：[src_f33f7ed6cbfbd622dff0](https://hf.co/facebook/sapiens2-normal-5b)

### 评测条件与可比性

模型卡列出骨干参数量 5.071B、骨干 FLOPs 15.722T、2432 维嵌入、56 层、32 个注意力头及 patch size 16。给定页面没有法线任务的评测数据集、指标成绩或完整测试协议，不能由模型规模推断其精度优于其他变体，也不能由 FLOPs 推算实测吞吐和延迟。

依据：[src_f33f7ed6cbfbd622dff0](https://hf.co/facebook/sapiens2-normal-5b)

### 衍生关系

基础模型为 facebook/sapiens2-pretrain-5b；官方列出 safetensors 文件 sapiens2_5b_normal.safetensors，页面标注 F32。模型树显示一个量化条目，但未给出发布者、位宽、分组方式、加载要求或性能比较，尚不能确认原始待核字段中的具体 INT4 制品。

依据：[src_f33f7ed6cbfbd622dff0](https://hf.co/facebook/sapiens2-normal-5b)

### 社区反馈与 Issue

页面展示 Community 计数 4，以及 facebook/sapiens2-normal 和 Joedwoo/sapiens2-normal 两个 Space 入口；没有讨论正文、复现记录或 Issue 内容，无法归纳社区质量反馈。页面提供 Transformers 专用类示例，原始待核字段中“不是 transformers 原生支持”的判断缺乏当前来源支持；加载成功与否尚未实测。

依据：[src_f33f7ed6cbfbd622dff0](https://hf.co/facebook/sapiens2-normal-5b)

### 冲突与待核实

已读完所给页面摘录，模型身份一致；页面未展示提交哈希，目标 revision main@898f7c3a0273d3132028789d242257a0aa87314e 尚未核实，故不填 revision 候选。论文、代码、任务指南、许可全文、文件清单和社区讨论正文未提供，未作阅读验证。精确总参数量、21.3GB 文件大小、文件去重关系、量化效果、许可具体授权及禁令、显存峰值、24GB 显卡余量、CPU 和手机运行能力均未获本轮证据支持。researched 仅表示给定来源整理完成。

依据：[src_f33f7ed6cbfbd622dff0](https://hf.co/facebook/sapiens2-normal-5b)

### 已读取的来源

- [src_f33f7ed6cbfbd622dff0](https://hf.co/facebook/sapiens2-normal-5b) · source_statement · 2026-11-15T18:51:42+08:00
  阅读范围：至多18000字符；truncated=False
