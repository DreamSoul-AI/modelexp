# Pythia-160M

## 自动调研记录

业务日期：2026-11-14 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

已整理revision `50f5173`的Pythia-160M模型卡，名称及仓库对象一致。开发方为EleutherAI，定位是英文语言模型研究，尤其是可解释性与受控训练实验；不是开箱即用的聊天模型。本轮researched表示给定材料的阅读整理完成，不代表权重、性能或部署可用性已验证。

依据：[src_d1eedd9172f26f0c0be4](https://huggingface.co/EleutherAI/pythia-160m/raw/50f5173/README.md)

### 评测条件与可比性

模型卡称全部16个Pythia模型使用LM Evaluation Harness评测，结果按模型和训练步保存在项目的results/json目录；列出的任务包括LAMBADA、PIQA、WinoGrande、ARC-Easy及SciQ。给定材料只有图表引用，没有可核验的160M具体成绩及完整评测配置，因此不提取数值，也不将套件层面的性能宣传视为该revision的独立验证。

依据：[src_d1eedd9172f26f0c0be4](https://huggingface.co/EleutherAI/pythia-160m/raw/50f5173/README.md)

### 衍生关系

本对象使用未去重Pile，须与同尺寸deduped模型和早期Pythia v0区分。卡片称本轮为重训练后的当前发布版本，训练共143000步、299,892,736,000个token，采用统一的2,097,152 token批量，并提供154个检查点。卡片允许进一步微调，但未提供本对象量化或第三方训练衍生制品的可核验证据。

依据：[src_d1eedd9172f26f0c0be4](https://huggingface.co/EleutherAI/pythia-160m/raw/50f5173/README.md)

### 社区反馈与 Issue

模型卡明确提示事实准确性不足、训练数据中的偏见及冒犯性内容风险。规模字段采用卡片明确列出的162,322,944总参数；原始候选中的212,654,688计数没有对应权重统计证据，不能据此替换。材料提供Discord讨论入口，但没有实际社区反馈或Issue记录。

依据：[src_d1eedd9172f26f0c0be4](https://huggingface.co/EleutherAI/pythia-160m/raw/50f5173/README.md)

### 冲突与待核实

所给README未截断；其链接的论文、训练仓库、评测JSON、图表及社区讨论均未读取。尚不能核验权重格式与体积、实际张量计数、访问限制、第三方ONNX/GGUF/INT4制品、运行资源需求、具体跑分或实测行为。EleutherAI不在配置的publisher选项中，因此省略该select字段；卡片的开发方信息保留在正文。

依据：[src_d1eedd9172f26f0c0be4](https://huggingface.co/EleutherAI/pythia-160m/raw/50f5173/README.md)

### 已读取的来源

- [src_d1eedd9172f26f0c0be4](https://huggingface.co/EleutherAI/pythia-160m/raw/50f5173/README.md) · source_statement · 2026-11-14T16:47:14+08:00
  阅读范围：至多18000字符；truncated=False
