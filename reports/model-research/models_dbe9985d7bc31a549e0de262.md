# Mistral-7B-Instruct-v0.2

## 自动调研记录

业务日期：2026-11-14 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

已整理与Mistral-7B-Instruct-v0.2、revision `63a8b08`一致的模型卡。该模型是Mistral-7B-v0.2的指令微调版本，面向文本指令和对话生成。模型卡将32K上下文、RoPE theta为1e6和取消滑动窗口注意力列为基础v0.2相对v0.1的变化；元数据另指向更新的Instruct-v0.3，不能将新版能力归入本实体。〔src_b2c2f09954c345470d20〕

依据：[src_b2c2f09954c345470d20](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2/raw/63a8b08/README.md)

### 评测条件与可比性

所提供模型卡没有基准成绩表或完整评测协议，无法生成跑分字段候选。推理示例分别展示确定性生成及采样生成，但属于使用演示，不构成质量、延迟或吞吐评测。〔src_b2c2f09954c345470d20〕

依据：[src_b2c2f09954c345470d20](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2/raw/63a8b08/README.md)

### 衍生关系

可确认的训练关系是由Mistral-7B-v0.2进行指令微调；模型卡未披露本版本的完整训练数据与配方。当前材料不支持确认TheBloke量化、MLC或llamafile等衍生产物，也未提供官方权重文件清单。〔src_b2c2f09954c345470d20〕

依据：[src_b2c2f09954c345470d20](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2/raw/63a8b08/README.md)

### 社区反馈与 Issue

模型卡要求使用`[INST]`与`[/INST]`包裹指令，首次指令带句首标记，助手输出由句末标记结束，并提供chat template接口。文档邀请改进Transformers分词器与mistral_common参考实现的一致性，另记录旧环境可能出现`KeyError: 'mistral'`及其版本相关处理建议；这些是文档提示，不能视为当前环境复现的Issue。模型卡还明确声明没有内容审核机制，因此面向需要审核输出的场景时，模型自身不提供该机制。〔src_b2c2f09954c345470d20〕

依据：[src_b2c2f09954c345470d20](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2/raw/63a8b08/README.md)

### 冲突与待核实

给定README已完整阅读；其中链接的论文、发布博客、Transformers文档及新版模型卡正文未提供，均未阅读核验。精确参数量、权重格式及大小、量化和端侧运行制品、硬件需求、性能成绩、训练数据以及社区反馈与Issue讨论仍缺证据。元数据中的`inference: false`和隐私说明不能单独证明权重不可用或仓库是否gated；本轮未核查访问条件、独立许可文件，也未运行推理。`researched`仅表示本轮给定来源的整理完成。〔src_b2c2f09954c345470d20〕

依据：[src_b2c2f09954c345470d20](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2/raw/63a8b08/README.md)

### 已读取的来源

- [src_b2c2f09954c345470d20](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2/raw/63a8b08/README.md) · source_statement · 2026-11-14T16:39:15+08:00
  阅读范围：至多18000字符；truncated=False
