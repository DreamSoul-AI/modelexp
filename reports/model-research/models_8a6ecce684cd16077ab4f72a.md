# TimeLens2-9B-SFT

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

已读页面明确对应 **TimeLens2-9B-SFT**，自述基于 Qwen/Qwen3.5-9B，并明确称为 SFT 版本。适用任务是根据文本查询预测视频中的相关时间区间。本轮给定页面的阅读整理已完成；页面没有将它定义为“非正式发布版”或“中间检查点”，不能沿用这类定位。

依据：[src_71abb1ce14741108cd7d](https://hf.co/ZhuYuhan/TimeLens2-9B-SFT)

### 评测条件与可比性

该 SFT 页面自报 mIoU（%）：Charades-STA 60.73、ActivityNet Captions 62.43、QVHighlights 71.85、VUE-TR 49.56、VUE-TR-v2 47.45、MomentSeeker 29.53、Ego4D-NLQ-v2 22.04，七项非加权平均 49.08。两个 VUE 基准使用可用视频子集。成绩未独立复现，也未绑定请求中的提交。来源未明确其余数据划分、视频子集清单、采帧与分辨率、提示词、解码配置、软件版本及硬件，完整评测协议尚缺。

依据：[src_71abb1ce14741108cd7d](https://hf.co/ZhuYuhan/TimeLens2-9B-SFT)

### 衍生关系

模型树将本模型列为 Qwen/Qwen3.5-9B 的微调后继，正文仅进一步说明它是 SFT 版本。材料未给出训练数据、训练超参数、后续训练阶段或与非 SFT 仓库之间的具体检查点继承关系；也未提供量化或转换制品详情，不能据此断言此类制品不存在。

依据：[src_71abb1ce14741108cd7d](https://hf.co/ZhuYuhan/TimeLens2-9B-SFT)

### 社区反馈与 Issue

给定正文没有 Community 讨论、Issue 内容或用户实测。页面加载示例只能支持文档层面的运行入口，不能证明实际加载成功、显存占用或长期稳定性。

依据：[src_71abb1ce14741108cd7d](https://hf.co/ZhuYuhan/TimeLens2-9B-SFT)

### 冲突与待核实

页面没有显示提交哈希，尚不能核对 `main@5d7c3e47e94a4c1529177053eea43932e6ee4e72`，因此不填写 revision 候选。论文、代码仓库、Collection、配置、文件列表及许可全文尚未读取；精确参数量、权重体积与分片、组织归属、Transformers 版本要求、显存需求、完整评测协议及基座许可均未验证。本轮 researched 仅表示给定实质页面已整理。

依据：[src_71abb1ce14741108cd7d](https://hf.co/ZhuYuhan/TimeLens2-9B-SFT)

### 已读取的来源

- [src_71abb1ce14741108cd7d](https://hf.co/ZhuYuhan/TimeLens2-9B-SFT) · source_statement · 2026-11-15T18:25:13+08:00
  阅读范围：至多18000字符；truncated=False
