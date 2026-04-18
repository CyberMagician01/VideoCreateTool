这是一个基于 Flask + 原生前端 + SQLite + 七牛云 AI 网关 的 AI 短剧/视频创作工作台，核心不是单点算法，而是把“故事生成、剧本打磨、分镜、封面、视频生成、成本统计、导出”串成了一套结构化创作流水线。
核心技术
1.	Flask 单体 Web 架构
后端入口很轻，主要负责创建 Flask 应用、注册页面/项目/AI/视频/导出几个 Blueprint，并初始化数据库。入口在 main.py (line 11)，Blueprint 注册在 main.py (line 14)。
整体分层比较清晰：
•	routes/：接口层，接收请求、返回 JSON
•	services/：业务层，处理 AI、视频、导出等核心逻辑
•	repositories/：数据访问层，封装 SQLite
•	utils/：状态标准化、默认状态、小工具
•	templates/ + static/：页面和原生 JS/CSS
2.	LLM 结构化创作流水线
程序的核心 AI 能力不是简单聊天，而是把创作拆成多个固定阶段：
•	故事引擎 story_engine
•	剧本评分 story_review
•	自动改稿 story_rewrite
•	标题包装 title_packaging
•	封面包装 cover_packaging
•	剧情工坊 workshop
•	分镜生成 storyboard
•	自然语言命令执行 command
•	全局意图路由 global_router
这些阶段集中在 agent_routes.py (line 345)，提示词模板集中在 prompt_service.py (line 26)。
它的关键点是：
让大模型输出严格 JSON，再通过 normalizer 统一清洗成稳定结构。
比如故事、评分、改稿、工坊、分镜、全局路由的标准化逻辑都在 normalizers.py (line 73) 开始。
3.	七牛云 / OpenAI-Compatible 模型网关接入
模型调用不是写死某个模型，而是通过配置层管理 provider、base_url、模型名、fallback、价格等。配置在 config.py (line 99)。
LLM 调用层支持：
•	OpenAI-compatible /chat/completions
•	JSON 结果提取和轻量修复
•	API Key / 七牛 AKSK 鉴权
•	超时重试
•	fallback 模型切换
•	token 成本估算
核心实现看 llm_service.py (line 56)、llm_service.py (line 196)。
4.	视频生成任务编排
视频能力是另一个核心模块。它支持：
•	文生视频
•	图生视频
•	首尾帧视频
•	长视频自动拆段
•	查询视频任务状态
•	根据上一段视频末帧继续生成下一段
•	BGM 上传和混音
•	网页搜索辅助
视频接口集中在 video_routes.py (line 47)。
实际视频服务层做了几件关键事：
•	根据 payload 判断走 text-to-video / image-to-video / start-end-to-video：video_service.py (line 256)
•	创建视频任务：video_service.py (line 392)
•	查询任务状态：video_service.py (line 480)
•	长视频拆段提示词续写：video_service.py (line 523)
•	抽取上一段末帧继续生成：video_service.py (line 207)
5.	媒体处理与对象存储
程序把本地上传的图片/音频上传到七牛 Kodo，让远程视频模型可以访问公网 URL。上传 token、对象 key、公网域名拼接等逻辑在 video_service.py (line 76)。
BGM 混音使用的是 moviepy，会下载视频和音频，本地合成后再尝试上传到七牛 Kodo。核心逻辑在 video_service.py (line 141)。
6.	项目状态持久化与快照机制
项目数据存在 SQLite 里，不是只靠浏览器本地状态。数据库表包括：
•	projects
•	project_states
•	project_snapshots
初始化在 project_repo.py (line 17)。
它支持项目创建、复制、软删除、状态保存、快照创建、快照恢复。项目接口在 project_routes.py (line 25)，状态保存接口在 project_routes.py (line 271)。
7.	原生前端状态机
前端没有用 React/Vue，而是用原生 JavaScript 管理整个创作台状态、接口调用、自动保存、长视频轮询、成本统计和页面渲染。
前端全局状态从 app.js (line 1) 开始定义，AI 阶段调用在 app.js (line 2776)，视频操作绑定在 app.js (line 4831)，成本记录在 app.js (line 5886)。
8.	导出能力
导出模块支持 Markdown、DOCX、PDF。
DOCX 使用 python-docx，PDF 使用 reportlab，并且考虑了中文字体注册。
核心逻辑在：
•	Markdown：export_service.py (line 190)
•	DOCX：export_service.py (line 327)
•	PDF：export_service.py (line 471)
最核心的技术亮点
你的程序最有价值的技术核心是：
•	用 结构化 Prompt + JSON Schema 思路 把大模型变成稳定的创作流程节点
•	用 Normalizer 层 抵抗模型输出不稳定的问题
•	用 Flask Blueprint + Service 分层 保持功能可扩展
•	用 SQLite 项目状态 + 快照 支撑持续创作
•	用 七牛云模型网关 + Kodo 对象存储 串起图片、视频、封面、搜索等外部 AI 能力
•	用 MoviePy 做本地视频后处理，比如 BGM 混音、末帧抽取
•	用 原生 JS 状态机 驱动多页面创作工作台
简单说：
这不是一个“视频生成接口壳子”，而是一个 AI 短剧生产流程编排系统。它的核心技术在于把不稳定的大模型能力，包装成可保存、可修改、可导出、可继续生成的创作流水线。

