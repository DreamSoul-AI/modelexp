# Sapiens2-0.4B 预训练骨干

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

来源明确对应facebook/sapiens2-pretrain-0.4b的预训练骨干。模型卡称其在10亿张人像图像上预训练，采用包含RoPE、GQA、SwiGLU、RMSNorm和QK-norm的Sapiens2 ViT，输出逐patch稠密特征。其用途是以人为中心的视觉研究、特征提取和任务头微调初始化；姿态、人体部位分割、表面法线和pointmap是列出的下游方向，本页未提供这些任务的直接预测示例。

依据：[src_c6df48165921ac8c0a3c](https://hf.co/facebook/sapiens2-pretrain-0.4b)

### 评测条件与可比性

模型卡报告0.398B参数、1.260T FLOPs、1024维嵌入、24层和16个注意力头；预训练分辨率为1024×768，patch大小为16。材料未说明FLOPs的完整统计口径，也未提供下游基准成绩、数据划分、任务头或微调协议，因此无法判断该变体相对其他规模的准确率收益。CUDA示例采用batch=1的RGB输入并建议ImageNet归一化，未报告延迟、吞吐量、显存或设备型号。

依据：[src_c6df48165921ac8c0a3c](https://hf.co/facebook/sapiens2-pretrain-0.4b)

### 衍生关系

页面模型树显示9个微调模型和1个量化模型，但未列出具体名称、训练关系细节、量化位宽、加载方式或精度评测。模型卡列出的官方检查点是sapiens2_0.4b_pretrain.safetensors，页面标注F32。现有材料不能确认原始字段提到的具体INT4-G128制品。

依据：[src_c6df48165921ac8c0a3c](https://hf.co/facebook/sapiens2-pretrain-0.4b)

### 社区反馈与 Issue

页面显示Community计数为4，但没有提供讨论正文或Issue记录，无法归纳社区反馈。页面同时给出Transformers自动加载片段及Sapiens2专用CUDA加载示例，实际兼容性未经本轮验证。页面采集时标示没有Inference Provider部署。

依据：[src_c6df48165921ac8c0a3c](https://hf.co/facebook/sapiens2-pretrain-0.4b)

### 冲突与待核实

页面未显示提交哈希，无法核验目标revision main@ce294175eb49429cb612bd91eb6a4a466fc2c358；因此未填revision字段，结论限于给定页面快照。模型卡的0.398B报告值不能用于确认原始字段中的395,450,384精确参数数目。论文、代码、许可证正文、文件列表、权重、衍生模型详情及社区讨论均未提供正文，未读且未验证。权重大小、重复文件关系、许可具体权限与禁令、CPU及手机支持、显存需求和量化效果仍待核实。本项researched仅表示本轮给定来源整理完成。

依据：[src_c6df48165921ac8c0a3c](https://hf.co/facebook/sapiens2-pretrain-0.4b)

### 已读取的来源

- [src_c6df48165921ac8c0a3c](https://hf.co/facebook/sapiens2-pretrain-0.4b) · source_statement · 2026-11-15T18:39:58+08:00
  阅读范围：至多18000字符；truncated=False
