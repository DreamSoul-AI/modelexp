# Sapiens2-0.4B 人体部位分割

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

该来源确为 facebook/sapiens2-seg-0.4b 的实质模型卡，描述从 facebook/sapiens2-pretrain-0.4b 微调得到的29类人体部位分割模型，适用于以人为中心的图像与相关视觉研究。架构为 ViT 骨干加分割头，推理分辨率为1024×768（高×宽）。本轮完成所给页面的阅读整理；页面未显示提交哈希，无法确认其内容对应目标 revision main@449b3c5335e6722bb94990abdd1aa6e612432f22。

依据：[src_d177eb97e0d678b17fbf](https://hf.co/facebook/sapiens2-seg-0.4b)

### 评测条件与可比性

模型卡列出骨干参数0.398 B、骨干计算量1.260 T FLOPs、patch size 16。它们是模型规格，不是分割精度或实测速率；材料未提供评测数据集、划分、mIoU、硬件、精度模式、批量大小或计时协议，因此不能据此评价分割质量或部署速度。

依据：[src_d177eb97e0d678b17fbf](https://hf.co/facebook/sapiens2-seg-0.4b)

### 衍生关系

训练关系明确为从0.4B预训练骨干微调。页面模型树显示2个微调衍生模型、8个量化模型，但未提供这些衍生仓库的具体内容；不能确认其量化位宽、文件大小、加载要求或效果。

依据：[src_d177eb97e0d678b17fbf](https://hf.co/facebook/sapiens2-seg-0.4b)

### 社区反馈与 Issue

页面显示 Community 入口计数为4，并列出5个使用该模型的 Spaces，但未包含讨论或 Issue 正文，不能形成具体社区故障或成功运行结论。采集时页面提示没有 Inference Provider 部署；Spaces 列表也不足以证明这些应用可正常使用。

依据：[src_d177eb97e0d678b17fbf](https://hf.co/facebook/sapiens2-seg-0.4b)

### 冲突与待核实

未读取页面链接指向的论文、代码仓库、分割指南、许可全文、文件内容及社区讨论，固定 revision 也未核验。原记录中的406,601,709总参数、1.63 GB文件大小、重复权重判断、具体 MLX／INT4／TensorRT 衍生及许可用途条款均缺少本轮原始材料支持，不予沿用。当前页面提供 Transformers 示例，不能保留原记录中“不支持 Transformers 原生加载”的断言；实际兼容版本、CPU／移动端支持、显存需求及运行结果仍待核验。

依据：[src_d177eb97e0d678b17fbf](https://hf.co/facebook/sapiens2-seg-0.4b)

### 已读取的来源

- [src_d177eb97e0d678b17fbf](https://hf.co/facebook/sapiens2-seg-0.4b) · source_statement · 2026-11-15T18:45:53+08:00
  阅读范围：至多18000字符；truncated=False
