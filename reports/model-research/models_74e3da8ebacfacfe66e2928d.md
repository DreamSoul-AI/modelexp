# TimeLens2-8B

## 自动调研记录

业务日期：2026-11-15 · 状态：researched

以下结论基于所列来源的陈述与阅读范围，未进行本项目实际跑分。

### 结论与适用范围

来源标题、路径和基座说明与 TimeLens2-8B 变体一致，基座为 Qwen3-VL-8B-Instruct。模型面向视频时序定位：结合视频与文本查询返回相关时间区间；示例进一步要求返回全部相关区间，以秒为单位输出 JSON 数组。模型卡宣称覆盖短视频、长视频和第一人称视频定位，但给定材料不足以独立确认这些场景下的效果。页面未显示提交 SHA，因此指定 revision 尚未得到核验。

依据：[src_61bd517a15a06039bdc5](https://hf.co/MCG-NJU/TimeLens2-8B)

### 评测条件与可比性

卡片有七项时序定位基准的平均 mIoU 和领先性声明，但当前文本的 Benchmark Results 区段没有实际表格，也没有七项基准名称、测试划分、汇总权重、指标实现或评测配置。页尾还显示 OmniCompass VL 的排行榜条目，但缺少指标定义及协议。由于无法补全成绩上下文，本轮不将这些数字录为可比较成绩，也不确认领先性。卡片的 2 fps 推理示例不能直接当作上述成绩的评测条件。

依据：[src_61bd517a15a06039bdc5](https://hf.co/MCG-NJU/TimeLens2-8B)

### 衍生关系

模型树明确列出 Qwen/Qwen3-VL-8B-Instruct 为基座，并显示一个量化衍生模型。当前页面未提供本变体的完整训练配方，也未给出量化发布者、位宽、文件大小、转换流程或质量变化，无法据此确认原始字段中的第三方 GGUF 规格。

依据：[src_61bd517a15a06039bdc5](https://hf.co/MCG-NJU/TimeLens2-8B)

### 社区反馈与 Issue

页面显示 Community 入口及计数，并列出一个使用该模型的 Space，但没有讨论正文、Issue 内容或 Space 运行结果，无法归纳具体社区反馈或问题解决状态。卡片提供 Transformers 推理代码，未提供本轮实际加载、生成、显存占用或延迟测试结果。

依据：[src_61bd517a15a06039bdc5](https://hf.co/MCG-NJU/TimeLens2-8B)

### 冲突与待核实

指定 main@c9a368106adfabbe34d6f0c4066e97b7df79acac 未在页面材料中得到提交级核验，故未填写 revision 候选。论文、评测代码、完整基准表、文件清单、许可证文件、量化衍生页面、Space 和社区讨论未提供或未读。精确参数量、权重分片与体积、训练流程、上下文推理上限、硬件兼容性、显存和速度尚未核验；原始字段中的精确参数量、仓库创建日和 GGUF 大小未作为事实沿用。researched 仅表示给定页面整理完成。

依据：[src_61bd517a15a06039bdc5](https://hf.co/MCG-NJU/TimeLens2-8B)

### 已读取的来源

- [src_61bd517a15a06039bdc5](https://hf.co/MCG-NJU/TimeLens2-8B) · source_statement · 2026-11-15T18:33:41+08:00
  阅读范围：至多18000字符；truncated=False
