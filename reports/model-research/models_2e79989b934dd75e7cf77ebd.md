# Sapiens2-1B 人体部位分割

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

该来源确为 facebook/sapiens2-seg-1b 的实质模型卡，描述从 facebook/sapiens2-pretrain-1b 微调得到的29类人体部位分割模型。当前对象是标准1B变体，模型卡另列的1B-4K是不同变体，不能混用其规格。标准1B采用 ViT 骨干加分割头，推理分辨率为1024×768（高×宽），面向以人为中心的图像及视觉研究。本轮完成所给页面的阅读整理；页面未显示提交哈希，无法确认其内容对应目标 revision main@60cf0b3584d68dccca9adb3b59677b72a5611378。

依据：[src_2fbbbabfbbbe04de5b7b](https://hf.co/facebook/sapiens2-seg-1b)

### 评测条件与可比性

标准1B模型卡列出骨干参数1.462 B、骨干计算量4.715 T FLOPs、patch size 16。材料没有测试集、数据划分、分割精度、硬件、批量大小、精度模式或计时协议，不能据此判断它相对于较小变体的精度收益和实际性能；这些规格也不代表整模型实测资源消耗。

依据：[src_2fbbbabfbbbe04de5b7b](https://hf.co/facebook/sapiens2-seg-1b)

### 衍生关系

训练关系明确为从1B预训练骨干微调。页面模型树显示1个微调衍生模型及1个量化模型，但没有给出相应仓库内容；无法确认具体 INT4-G128、MLX bf16 制品、文件大小或效果。

依据：[src_2fbbbabfbbbe04de5b7b](https://hf.co/facebook/sapiens2-seg-1b)

### 社区反馈与 Issue

页面显示 Community 入口计数为4，并列出5个使用该模型的 Spaces，但未提供讨论或 Issue 正文，无法提炼具体社区经验或已知故障。采集时页面提示没有 Inference Provider 部署；页面中的加载示例及 Spaces 列表均不构成本轮运行验证。

依据：[src_2fbbbabfbbbe04de5b7b](https://hf.co/facebook/sapiens2-seg-1b)

### 冲突与待核实

未读取论文、代码仓库、分割指南、许可全文、权重文件及社区讨论，固定 revision 未核验。原记录中的1,470,819,821总参数、5.88 GB文件大小、重复文件判断、量化文件大小及详细许可条款缺少本轮原始材料支持。页面提供 Transformers 加载示例，因此不沿用原记录“不支持 Transformers 原生加载”的说法；实际兼容版本、显存、CPU／移动端可用性、推理效果和量化损失均未验证。

依据：[src_2fbbbabfbbbe04de5b7b](https://hf.co/facebook/sapiens2-seg-1b)

### 已读取的来源

- [src_2fbbbabfbbbe04de5b7b](https://hf.co/facebook/sapiens2-seg-1b) · source_statement · 2026-11-15T18:45:54+08:00
  阅读范围：至多18000字符；truncated=False
