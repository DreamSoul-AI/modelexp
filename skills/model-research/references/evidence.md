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
