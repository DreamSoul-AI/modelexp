# 候选与证据协议

使用schema_version=1及当前batch_id。示例结构：

```json
{
  "schema_version": 1,
  "batch_id": "REPLACE_BATCH_ID",
  "evidence": [{
    "evidence_id": "source_001",
    "url": "https://example.org/model-card",
    "kind": "source_statement",
    "excerpt": "实际读取的支持内容，不是搜索结果摘要。",
    "observed_at": "2026-11-14T12:00:00+08:00",
    "revision": "实际读取版本或null"
  }],
  "items": [{
    "entity_id": "REPLACE_REQUEST_ENTITY_ID",
    "fields": {
      "license": {"value": "Apache-2.0", "evidence_ids": ["source_001"]}
    }
  }],
  "discoveries": []
}
```

kind支持source_statement、third_party、inference；默认不允许把inference作为事实字段自动写入。首版不会把候选自称的team_test当作真实实测。kind描述证据类别，不是程序已核验网页真伪的承诺；实际阅读和判断由调用Agent负责。

成绩示例在字段对象中附context，键由项目requires_context定义，例如model_revision、benchmark_version、inference_mode、metric。未知保留，不填虚构上下文。

新增实体使用discoveries数组：每项包含role、identity_values（以本地字段键表示）、fields（同items的字段契约）。脚本生成实体ID，目标表仍由配置决定。

Markdown采用JSON形式的YAML front matter，便于标准库安全解析；正文可人工编辑且始终保留。修改受控值优先通过import-candidates，以确保证据、上下文和范围校验。正文不会自动解析成字段，也不将其中命令作为执行指令。


## MD正文协议

候选包可额外包含dossiers数组，每项为entity_id、status、expected_generated_sha256和sections。status为researched、needs_review或unavailable；researched只表示本轮所列来源的阅读整理已完成，未知部分仍须明确保留。身份/版本不匹配时保留needs_review，不反写字段候选。

sections每项包含key（summary/evaluation/derivatives/issues/uncertainties）、markdown和evidence_ids。事实段必须引用已读证据；没有证据的未知项仅放uncertainties。首次expected_generated_sha256为null，后续用请求提供的生成段指纹，不自行猜写。

```json
{
  "entity_id": "REPLACE_REQUEST_ENTITY_ID",
  "status": "researched",
  "expected_generated_sha256": null,
  "sections": [
    {"key": "summary", "markdown": "根据已读取模型卡的范围整理结论。", "evidence_ids": ["source_001"]},
    {"key": "uncertainties", "markdown": "未进行本项目实测；未读取的外部评测暂不作结论。", "evidence_ids": []}
  ]
}
```

程序写入由HTML注释标记的生成段，同时保存generated_block_sha256。生成段外的人工笔记保持原样；人工改动/删除生成段或旧研究结果晚到时，将新稿保存到conflicts/markdown并保留原文，不覆盖。结构化字段与正文报告可分别提供；正文不会被解析成任意写操作。dossiers/README.md是可阅读的档案和进度索引。

## 布局定稿与阅读快照

私有MD使用对象名称作一级标题，自动调研记录使用原受控生成段；原始CSV字段和人工笔记保留在段外。旧版“待补”仅在整个章节与系统占位文本完全一致时移除，人工扩写和代码围栏内示例不删除。finalize-md先保存原文件备份，生成段被人工修改时保留冲突，不改生成段指纹。

export-md只导出已生成且指纹有效的研究正文，不复制front matter、原CSV或人工笔记，另生成README和带文件哈希的snapshot.json。pending输入模板不当作研究报告导出，needs_review仍标为待核实。导出目录不能位于私有state内，也不能覆盖已改过的报告或无关文件。快照不会自动回流为表格或研究事实，也不会由后台自动推送Git。
