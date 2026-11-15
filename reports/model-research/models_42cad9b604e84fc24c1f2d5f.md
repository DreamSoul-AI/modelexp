# Sapiens2-1B 预训练骨干

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

给定页面与 facebook/sapiens2-pretrain-1b 变体一致，内容为预训练视觉骨干。模型卡称其在10亿张人像图像上预训练，输出逐 patch 稠密特征，适合以人为中心的特征提取与下游任务头微调。架构包含 RoPE、GQA、SwiGLU、RMSNorm 和 QK-norm；预训练分辨率为1024×768，patch size 为16。

依据：[src_c2cf55c84c892059bb16](https://hf.co/facebook/sapiens2-pretrain-1b)

### 评测条件与可比性

材料未提供该骨干的下游基准成绩、数据划分、评价指标或可复现实验协议，无法据此评价姿态、分割、法线或 pointmap 的实际精度。Quick Start 仅展示批大小为1、RGB 输入、CUDA 前向与特征输出，未报告设备型号、耗时、峰值显存或端侧测试。

依据：[src_c2cf55c84c892059bb16](https://hf.co/facebook/sapiens2-pretrain-1b)

### 衍生关系

页面模型树显示13个微调模型和1个量化模型，并链接包含下游任务检查点的 Sapiens2 集合。这仅支持存在相关条目的页面声明；材料未展开衍生模型身份、基座 revision、量化位宽、格式、加载方式或质量评测，不能确认原始字段中的 Reza2kn INT4-G128 描述。

依据：[src_c2cf55c84c892059bb16](https://hf.co/facebook/sapiens2-pretrain-1b)

### 社区反馈与 Issue

页面显示4条 Community 条目，但未提供讨论正文，无法归纳具体社区反馈或 Issue。页面自动生成了 Transformers 加载片段，模型卡则给出 Sapiens2 原生加载示例；两者均未在本轮执行，不能据此断言 Transformers 原生兼容性，也不能断言其不支持。采集时页面注明没有 Inference Provider 部署。

依据：[src_c2cf55c84c892059bb16](https://hf.co/facebook/sapiens2-pretrain-1b)

### 冲突与待核实

给定下载内容未显示提交哈希，尚不能将页面内容绑定到目标 revision main@267ee98834051d5a25ccef32bddbe9748f701c28，故不提交 revision 字段候选。论文、代码仓库、许可全文、文件列表及社区讨论正文未提供，未核对权重大小、重复文件关系、精确参数计数、训练细节和用途限制；原始字段中的1,455,474,192参数及5.82 GB未获本轮材料支持。CPU、手机端、显存需求和实际加载可用性仍未验证。researched 仅表示本轮给定页面的阅读整理完成。

依据：[src_c2cf55c84c892059bb16](https://hf.co/facebook/sapiens2-pretrain-1b)

### 已读取的来源

- [src_c2cf55c84c892059bb16](https://hf.co/facebook/sapiens2-pretrain-1b) · source_statement · 2026-11-15T18:42:55+08:00
  阅读范围：至多18000字符；truncated=False
