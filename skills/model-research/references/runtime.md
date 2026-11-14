# 运行与授权

Python 3.11+，Linux/macOS，无新增Python依赖。CLIcommand是argv数组，可配置本机包装器；不改HOME，不读取或输出密钥，认证由官方CLI管理。

agent.command也是argv数组。执行器追加一个request JSON的绝对路径；程序读取请求，完成已授权调研，将候选JSON写stdout，诊断写stderr，成功退出0。超时或不合法结果报错。外部程序必须自己具备模型认证、网络和检索能力；脚本不会自动取得当前聊天的能力。不要配置一个不能访问来源的回声程序并声称已完成调研。

未配置Agent时可用SKILL指导当前Agent消费request，再以--candidates继续。Agent请求禁止云端写入，生成字段候选后由确定性同步器检查。配置的任意外部程序仍具有运行账号权限，部署时需选择受信任执行器并使用合适的隔离/权限。

入口每次只执行一轮，不安装cron、不启用已有定时任务、不发消息。当前部署按用户要求在12:00（Asia/Shanghai）调用run；需要先验证持久存储、可更新刷新凭据、Agent认证和完整周期，未通过前保持人工触发。

## 当前云环境试运行

Linux 可用 `scripts/service.py --root <仓外目录> install --config <私有配置>` 安装固定版本副本，随后执行该目录 `manage start|status|stop|tick`。`tick --date YYYY-MM-DD` 显式试跑历史业务日，默认取当天上海日期。默认mode=plan且allow_writes=false；明确的apply部署要求allow_writes=true，两者不一致时拒绝执行。

程序默认15:00开始；当前部署通过--at 12:00设置为每日北京时间12:00起、18:00前检查输入；retry_minutes控制空闲轮询，continue_after_minutes控制有进展且有剩余时的接续。当前CSV同步按整份日报规划、每批最多200条提交，不逐条研究，空闲30分钟重查。daemon 在本实例运行，30 秒更新一次心跳，保存 worker 结果、last-run、调度状态和进程启动指纹；重复 start 复用既有进程，stop 校验进程身份后停止自己的进程组。此服务没有主机重启集成，环境暂停、销毁或用户登出后是否存活均不作保证；需要时明确执行 manage start 恢复。

安装时按内容指纹将 skill 复制到 releases/<版本>/skills/model-research，再通过 current 引用；修改仓库后需停止并重新 install/start，不自动运行尚未审查的新代码。私有配置、状态与飞书凭据分别保存，安装过程不复制授权文件。

仅研究流程在未配置研究Agent时记录waiting_research和request路径；当前CSV同步配置agent.enabled=false、无command且字段accept_upstream，research_runtime=not_required，不产生研究阻塞。缺当天日报时保持 waiting_input，独立输入可先研究并建档。配置Codex适配器后，每次最多处理max_entities_per_run个实体；真实材料读取、结构化候选和正文写入经过同一验证链路。早期401与默认目录授权丢失的历史见部署记录，当前授权应通过后台私有目录的实际模型调用单独检查。

本地file后端提供可重复演示，验证持久化与同步行为；不能代替飞书平台写入/授权续期或真实Agent调研验证。云端档案交付另复用document-sync并明确方向和目标，本首版只生成本地Markdown。


## Codex适配与持久状态

将agent.command配置为Python解释器及本版本scripts/codex_agent.py的argv，配置独立的codex_state_dir、model和超时。该目录位于checkout外、仅账号可读；只在后台子进程使用CLI官方CODEX_HOME设置，不替换聊天进程的默认目录，不复制聊天凭据。用该专用目录执行官方浏览器登录，授权只保存在其auth.json，私有目录不得提交、上传或发布共享快照。目录位置本身不保证云磁盘跨任务持久化，仍需恢复验证。

适配器先读取固定修订的HF模型卡或GitHub README，限制公开HTTPS、单来源一MiB、最多18000字符，保存原始响应指纹和实际片段，再调用Codex的只读模式及结构化输出。没有读到来源时写unavailable和失败原因，不调用模型凭空补结论。当前仅依据已下载材料整理；未自动遍历所有链接、全部社区Issue、完整论文或权重，也不运行模型实测。

state_dir/research/jobs按实体、输入内容与workflow_version保存工作ID。成功结果可跨批复用，正文已落盘但作业回执未落盘可对账；失败30分钟后可重试，needs_review/unavailable六小时后再查，不反复立即计费。当前运行按指定业务日分批，旧业务日可显式tick --date继续，不会擅自启用backfill文件。remaining不是零时保持partial，来源完成声明缺失依旧阻断线上应用。

超时和停止会终止整个子作业进程组，模型、适配器与调度worker的预算分别配置。当前私有试运行配置每轮3个实体，旧工作流回执保留；修改workflow_version才强制重新研究同输入，不通过删状态绕过回执。


## 自动写回部署

用户明确要求的自动维护可执行service.py install --config <私有配置> --mode apply --continue-after-minutes 1，再start。计划模式仍默认不写；apply配置和部署模式必须一致，不能只改一个开关绕过计划、字段和输入校验。当前服务使用project.csv-sync.json，所有目标表、字段和权限由该私有配置指定。

没有上游manifest时可启用input_readiness.strategy=stable_observations、min_interval_seconds=60。读取内容完整且两次哈希一致、观察间隔足够后为observed_stable；替换或缺失输入会重新观察。状态与批次版本绑定，不把“文件暂时稳定”记成“生产方声明完整”。

旧模型的人工非空基础信息无基线时保留，空字段可bootstrap_empty补齐；程序成功写入并回读的字段保存基线，以后按三方比较维护。score/公式/人工备注等未在自动映射内的字段不会提交。渠道仅恢复用户此前明确重拉、已回读验证的初始基线，备注与访问问题保留人工维护。

创建时完整身份匹配之外，可配置creation_guard_keys核对名称别名与来源；相关身份不清则暂缓该实体，不因其他无关历史行缺字段就阻断全表。字段更新按同一记录合并，请求前再查、请求后回读；未知提交下一轮先对账，不盲重发。命令超时、来源缺失、人工冲突分别保留，不用“允许写入”绕过这些真实问题。

## CSV直接同步

当前用户要求直接采用Grokbot已经整理的CSV：下载并固定原件、按field_id匹配列、统一明确别名/下拉/URL格式、生成增量计划、按表批量写入和回读。prefer_upstream使原CSV优先于早期调研候选；人工镜像在CSV未变时仍保留。日常同步不调用Codex、不等待MD正文。研究协议保留为另行需要时使用。

backend.batch_size范围1—200，默认1；批量方式在提交前重新读取目标、校验每条记录的旧值及候选指纹。整组标记submitting后提交，回读按完整身份和服务返回ID确认，绝不假定返回ID顺序。回执丢失或读回不匹配时标记unknown，下次仅对账。
