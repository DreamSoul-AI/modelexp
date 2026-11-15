# Sapiens2-5B 预训练骨干

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

给定页面与 facebook/sapiens2-pretrain-5b 变体一致，内容为5B档预训练视觉骨干。模型卡称其在10亿张人像图像上预训练，输出逐 patch 稠密特征，适合以人为中心的特征提取和下游任务头微调。架构包含 RoPE、GQA、SwiGLU、RMSNorm 和 QK-norm；预训练分辨率为1024×768，patch size 为16。

依据：[src_2a946f643a05495978d1](https://hf.co/facebook/sapiens2-pretrain-5b)

### 评测条件与可比性

材料没有该变体的下游精度成绩、数据划分、评价指标或比较协议，不能推断其相对1B等变体的精度收益。Quick Start 展示批大小为1的 CUDA 前向流程，未报告设备型号、推理耗时和峰值显存，不能据此判断24 GB显卡是否足以运行。

依据：[src_2a946f643a05495978d1](https://hf.co/facebook/sapiens2-pretrain-5b)

### 衍生关系

页面模型树显示9个微调模型和1个量化模型，并链接包含下游任务检查点的 Sapiens2 集合。材料未展开这些条目的名称、基座 revision、训练协议、量化位宽或精度变化，不能据此确认 Reza2kn INT4-G128 制品及其兼容性。

依据：[src_2a946f643a05495978d1](https://hf.co/facebook/sapiens2-pretrain-5b)

### 社区反馈与 Issue

页面显示4条 Community 条目，但正文未提供，无法判断是否存在加载故障、性能问题或其他具体 Issue。页面包含自动生成的 Transformers 片段和模型卡中的 Sapiens2 加载示例，均未实测，原始字段中“不是 transformers 原生支持”的断言证据不足。采集时页面注明没有 Inference Provider 部署。

依据：[src_2a946f643a05495978d1](https://hf.co/facebook/sapiens2-pretrain-5b)

### 冲突与待核实

下载内容未显示提交哈希，尚不能绑定到目标 revision main@407b02b9225640bed662296a7f03739bee03633b，故不提交 revision 字段候选。论文、代码、许可全文、文件列表及社区讨论正文未提供；权重大小、重复文件关系、精确参数计数和许可用途限制未核对。原始字段中的5,066,902,995参数、20.3 GB及24 GB显卡余量估算不作为本轮已验证事实。CPU、手机端和实际运行资源需求仍未知。researched 仅表示本轮给定页面的阅读整理完成。

依据：[src_2a946f643a05495978d1](https://hf.co/facebook/sapiens2-pretrain-5b)

### 已读取的来源

- [src_2a946f643a05495978d1](https://hf.co/facebook/sapiens2-pretrain-5b) · source_statement · 2026-11-15T18:42:55+08:00
  阅读范围：至多18000字符；truncated=False
