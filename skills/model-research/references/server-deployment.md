# Linux服务器迁移与运行

交付目标：将CSV直接同步、AI调研与MD两个独立服务迁到持续在线的Linux服务器。代码在GitHub的gyd分支；研究阅读快照在reports/model-research。私有配置、同步基线、证据和队列通过私有迁移包转移，不能从Git仓库重建这些运行数据。

## 服务器准备

建议使用Ubuntu 24.04 LTS、Python 3.11以上、Node.js LTS。入门可选2核/2GB内存、20GB以上持久磁盘，无GPU需求；这是部署建议，尚未在新租服务器上实测。保持服务器在线、系统时间同步，并允许访问GitHub、飞书、OpenAI及资料来源站点。

运行身份统一为普通用户modelresearch。管理员准备目录：

```bash
sudo useradd --create-home --shell /bin/bash modelresearch
sudo install -d -o modelresearch -g modelresearch -m 700 /srv/model-research
```

已有该用户时跳过创建。后续安装、授权和手动预检均用这个用户；避免授权给root、服务却用另一用户运行。

建议目录：

```text
/srv/model-research/
├── repo/               # gyd代码
├── csv/
│   ├── project.json    # 私有CSV配置
│   ├── state/          # CSV原件、SQLite基线、映射及提交回执
│   └── current/        # service install生成的固定版本
└── ai/
    ├── project.json    # 私有AI配置
    ├── state/          # AI证据、MD、工作回执及历史批次
    └── current/        # 独立固定版本
```

## 获取代码与私有运行数据

```bash
git clone --branch gyd https://github.com/DreamSoul-AI/modelexp.git /srv/model-research/repo
```

私有迁移包另行下载或通过SSH传输，权限设为600，不提交GitHub。当前交付的包包含csv/与ai/的project.json和state/、文件哈希清单、保留业务日期；不含CLI登录凭据、安装依赖、旧进程或可直接复用的current部署链接。

先在私有目录解包，核对migration-manifest.json中的文件哈希，再把csv与ai目录复制到上述目标位置。所有权交给modelresearch，配置和状态只允许该用户读写。保留原包，不覆盖唯一备份。

运行状态迁移的重要约束：

- CSV和AI的state目录必须分开，不能混合SQLite或覆盖彼此档案。
- CSV中若有submitting/submitted/unknown操作，应先在原环境verify对账，不能在新服务器重建记录绕过。
- 配置里的CLI路径、AI脚本路径和Codex专用目录必须改为新服务器路径；不要直接运行旧deployment.json或旧manage。
- 修改运行路径会改变配置指纹。新主机应重新接收迁移清单列出的正常日报日期，尤其AI的旧日期；不删除原队列和成功回执。这样旧未完成项进入新配置的研究集合，相同实体/原始输入/workflow_version的成功MD继续复用。
- 历史原件、请求和回执中仍可能保留原机器的绝对路径，仅用于审计；审阅时在迁移后的对应state目录定位。原云环境销毁前，要验证历史来源文件与队列可接续。

## 安装CLI并重新授权

安装飞书官方lark-cli和官方Codex CLI，分别验证版本及帮助，再授权。飞书已实测版本1.0.100；Codex已实测0.167.0-alpha.4。新主机必须先确认实际版本支持当前适配器使用的exec、输出schema及相关选项，不因安装成功就启用AI服务。

```bash
npx @larksuite/cli@latest install
lark-cli --version
lark-cli config init
npm install -g @openai/codex
codex --version
codex exec --help
```

使用已有飞书应用时按官方引导配置并以user身份授权。应用配置和授权信息只在服务器官方私有目录保存，不写入仓库或聊天。

Codex使用独立私有状态目录。可以用下面的Python进程局部环境执行官方登录，不修改整个聊天或机器的默认状态目录：

```python
import os
import subprocess
from pathlib import Path

private = Path.home() / ".local/share/model-research-codex"
private.mkdir(parents=True, exist_ok=True, mode=0o700)
subprocess.run(["codex", "login"], env={**os.environ, "CODEX_HOME": str(private)}, check=True)
```

浏览器OAuth若使用127.0.0.1:1455回调，可先用SSH本地端口转发连接服务器，再按官方引导登录。不要将回调、密码或令牌提交Git。登录状态检查后还须实际完成一轮有来源的研究，不能只看auth.json存在。

## 调整私有配置并安装固定版本

将两份project.json中的state_dir保持为./state，backend.command改为新主机真实lark-cli路径。

CSV配置：allow_writes=true，Agent关闭，保留既有字段映射、人工保护、批量大小和上游优先规则。AI配置：allow_writes=false，Agent启用，command为Python及/srv/model-research/ai/current/skills/model-research/scripts/codex_agent.py，codex_state_dir为上述新授权目录。保留agent.roles、include_previous_batches及workflow_version；不要为迁移随意提升工作流版本或清空成功回执。

```bash
cd /srv/model-research/repo
python3 skills/model-research/scripts/service.py --root /srv/model-research/csv install --config /srv/model-research/csv/project.json --mode apply --at 12:00 --retry-until 18:00 --continue-after-minutes 1
python3 skills/model-research/scripts/service.py --root /srv/model-research/ai install --config /srv/model-research/ai/project.json --mode research --at 12:00 --retry-until 23:59 --continue-after-minutes 1
```

先不要运行manage start，完成手动验收后交给systemd前台监督。已有服务更新版本时先停止它，保留配置与state，再install新版本。

## 迁移验收

1. 分别用research.py doctor检查两份配置的后端连接。
2. 对CSV运行ingest与plan，确认身份、字段映射、保护和未知回执。内容稳定观察至少两次、间隔60秒，不能伪造生产方manifest。
3. 对AI按迁移清单中的保留日期执行ingest，使旧普通日报加入新配置的研究队列。本次私有包保留2026-11-14与2026-11-15；未来以实际清单为准，不读取source_links/backfill文件。
4. 用CSV manage tick --date YYYY-MM-DD完成一轮，检查回读、重复规划和零重复新增；如第一次为observing，至少60秒后再检查。
5. 用AI manage tick --date YYYY-MM-DD完成一轮，确认真实模型调用、带来源正文、剩余队列及成功缓存复用。
6. 检查两条任务的state路径不同、生成段人工保护及私有权限，再启动常驻服务。

当前已有云实例的129项独立流程回归及后续Markdown交付回归、真实CSV写入、AI正文和并行验证记录；这些不替代新服务器的上述验收。

## 开机恢复与常驻运行

仓库提供[systemd模板](../deploy/model-research@.service)。systemd负责开机启动和异常重启，程序内部负责北京时间12:00的调度与各自续跑窗口。

```bash
sudo cp /srv/model-research/repo/skills/model-research/deploy/model-research@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now model-research@csv.service model-research@ai.service
sudo systemctl status model-research@csv.service model-research@ai.service
```

模板直接运行daemon前台入口，不使用会自行fork退出的manage start。正常由systemd管理时，不再额外手动启动另一个daemon。

检查业务结果：

```bash
/srv/model-research/csv/manage status
/srv/model-research/ai/manage status
journalctl -u model-research@csv.service -u model-research@ai.service --since today
```

还要检查各自last-run.json、heartbeat.json、runs、worker-results和AI档案索引。pending/partial不算整批完成，PID存在也不等于今天已执行成功。

## 已知边界与最终验收

- 当前没有自动失败通知或授权到期提醒；需要监控last-run及授权状态，后续再接通知渠道。
- 启动发生在当天窗口内时会接续；超过18:00才启动CSV服务会等次日。需要补当天或离线多天时，显式manage tick --date，遵守稳定观察及回读规则，不能宣称已有任意日期的自动补跑。
- 研究处理窗口到23:59，剩余项跨日接续；来源不可读、身份不清或正文被人工修改时保留待核实/冲突。
- 仅有读取材料的研究，没有完整论文/Issue遍历、模型实测或完整量化制品自动发现链路。
- 服务器首次部署、CLI授权续期、真实重启恢复及连续多天准点执行尚须新主机验证。本仓库提供可迁移实现和模板，不将尚未租用的服务器标记为部署完成。

正式验收至少包括一次真实同步、一次真实AI正文、一轮重复运行无重复新增，以及服务器重启后两服务恢复并在后续12:00自然触发成功。
