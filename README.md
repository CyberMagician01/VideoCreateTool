# VideoCreateTool

一个基于 **Flask** 的 AI 视频/短剧创作工具。  
目前项目主要支持：

- 项目管理
- 故事生成（story engine）
- 爆款故事模板
- 剧本评分 / 自动改稿
- 剧情工坊（workshop）
- 分镜生成（storyboard）
- 标题包装建议
- 视频脚本生成
- 视频任务创建 / 查询
- DOCX / PDF 导出
- 网页搜索辅助

## 最近更新（2026-04-11）

- 创作工坊新增统一“预览窗口”：故事引擎、剧本工坊、分镜工厂均支持一键弹窗预览当前生成结果。
- 视频实验室新增“题材/风格”下拉选择，降低输入门槛并提升风格控制一致性。
- 清理视频实验室中面对用户的中间过程字段，隐藏“首尾帧模式”输入框，只保留必要入口。
- 长视频拆段升级为“自动续段链路”：
  - 创建拆段任务时优先创建第 1 段。
  - 第 N 段成功后，自动截取该段视频最后一帧并上传到对象存储。
  - 第 N+1 段自动使用上一段末帧作为图生首帧继续生成，实现更强镜头连贯性。
- 新增后端接口：`POST /api/video/create-next-segment-from-video`，用于“上一段视频 -> 末帧抽取 -> 下一段任务创建”。
- 新增后端能力：根据视频 URL 自动抽取末帧并上传公网图，供后续视频任务直接使用。

## 最近更新（2026-04-10）

- 故事引擎新增爆款模板能力：支持在前端选择故事模板，并自动把模板的钩子、冲突升级和结尾悬念策略注入生成流程。
- 新增剧本评分器：可对故事卡、剧情工坊、分镜结果进行结构化评分，输出问题摘要、低分维度和优先修改动作。
- 新增自动改稿流程：评分后可生成多个改写候选版本，并支持一键应用到当前项目状态。
- 新增标题包装能力：支持评估当前标题、生成多个备选标题、推荐理由和平台话题标签。
- 导出中心已接入标题包装结果，Markdown / DOCX / PDF 导出时会一并带出标题建议内容。

- 视频实验室新增图生视频本地上传能力：支持拖拽/点击上传、上传进度条、已选图片删除按钮。
- 图生参考图上传后自动填充 `image_url`，并在创建任务时自动判定 `text / image / start_end` 模式。
- 新增后端图片上传接口：`POST /api/video/upload-image`。
- 新增七牛对象存储配置（`QINIU_KODO_BUCKET`、`QINIU_KODO_PUBLIC_DOMAIN`、`QINIU_KODO_UPLOAD_HOST`），上传图片后返回公网 URL 供模型读取。
- 针对七牛 Kodo 上传机房不匹配问题，增加按错误提示自动重试对应区域上传域名。
- 修复图生参考图在页面切换后丢失问题：`video_lab` 状态新增并持久化 `image_url/start_image_url/end_image_url`。

---

# 1. 快速说明
已完成第一阶段架构重构，采用分层设计：
- `main.py`：仅作为项目启动入口
- `routes/`：存放接口路由
- `services/`：存放核心业务逻辑
- `repositories/`：存放数据库操作
- `utils/`：存放工具函数与数据清洗
- `config.py` + `.env`：统一管理配置

开发时请勿将业务逻辑写回 `main.py`。

---

# 2. 项目结构

```text
VideoCreateTool-main/
├─ app/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ repositories/
│  │  ├─ __init__.py
│  │  └─ project_repo.py
│  ├─ routes/
│  │  ├─ __init__.py
│  │  ├─ agent_routes.py
│  │  ├─ export_routes.py
│  │  ├─ page_routes.py
│  │  ├─ project_routes.py
│  │  └─ video_routes.py
│  ├─ services/
│  │  ├─ __init__.py
│  │  ├─ export_service.py
│  │  ├─ llm_service.py
│  │  ├─ prompt_service.py
│  │  ├─ story_template_service.py
│  │  └─ video_service.py
│  └─ utils/
│     ├─ __init__.py
│     ├─ helpers.py
│     └─ normalizers.py
├─ data/
│  └─ projects.db
├─ static/
│  ├─ app.js
│  └─ style.css
├─ templates/
│  ├─ export_center.html
│  ├─ index.html
│  ├─ studio.html
│  ├─ video_lab.html
│  └─ visual.html
├─ .env
├─ main.py
├─ README.md
└─ requirements.txt
```

---

# 3. 每个目录是干什么的

## main.py

项目启动入口。

只负责：
- 创建 Flask app
- 注册 blueprint
- 初始化数据库
- 启动服务

## app/config.py

放项目配置，例如：
- 数据库路径
- 七牛云 AK/SK
- 文本模型参数
- 视频模型参数
- 默认 provider
- 各类接口 path

以后新增环境变量，优先改这里。

## app/routes/

放接口。

### page_routes.py
页面渲染路由，例如：
- `/`
- `/studio`
- `/visual`
- `/export-center`
- `/video-lab`

### project_routes.py
项目管理接口，例如：
- 获取项目列表
- 创建项目
- 获取项目详情
- 更新项目
- 删除项目
- 保存 / 读取项目状态

### agent_routes.py
AI 创作流程接口，例如：
- 获取故事模板列表
- 获取模型 provider 列表
- 多模型比较
- story engine
- story review
- story rewrite
- title packaging
- workshop
- storyboard
- command
- export markdown

### video_routes.py
视频相关接口，例如：
- 生成视频脚本
- 创建视频任务
- 创建长视频任务
- 创建下一段续段任务（基于上一段视频末帧）
- 查询视频任务状态
- 网页搜索

### export_routes.py
导出接口，例如：
- 导出 DOCX
- 导出 PDF

## app/services/

放业务逻辑。

### llm_service.py
负责：
- 调用大模型
- provider 分发
- JSON / 文本结果解析
- 网关请求封装

### prompt_service.py
负责所有提示词拼接，例如：
- 故事生成提示词
- 故事评分提示词
- 自动改稿提示词
- 标题包装提示词
- workshop 提示词
- 分镜提示词
- command 提示词
- 视频脚本提示词

### story_template_service.py
负责：
- 管理内置爆款故事模板
- 提供模板列表查询
- 根据 `template_id` 返回模板约束
- 给故事引擎提供钩子、冲突升级、结尾悬念等模板信息

### video_service.py
负责：
- 创建视频任务
- 查询视频任务
- 长视频拆段
- 视频末帧抽取与上传
- 长视频自动续段（上一段末帧驱动下一段）
- 搜索接口封装
- 视频状态标准化

### export_service.py
负责：
- 导出内容标准化
- 标题包装结果整理
- Markdown 生成
- DOCX 生成
- PDF 生成

## app/repositories/

放数据库读写逻辑。

### project_repo.py
负责：
- 初始化 SQLite
- 创建项目
- 查询项目
- 查询项目状态
- 默认项目处理

原则：路由里尽量不要直接写 SQL。

## app/utils/

放工具函数和数据清洗逻辑。

### helpers.py
放通用小工具，例如：
- 时间处理
- 文本处理
- 默认状态管理
- 安全类型转换

### normalizers.py
放数据结构标准化逻辑，例如：
- story card 规范化
- workshop 规范化
- storyboard 规范化
- video state 规范化
- project state 规范化

如果模型返回结构不稳定，优先在这里做兼容。

---

# 4. 本地运行方法

## 4.1 创建虚拟环境
```bash
python -m venv .venv
```

Windows 激活命令：
```bash
.venv\Scripts\activate
```

Mac/Linux 激活命令：
```bash
source .venv/bin/activate
```

## 4.2 安装依赖
```bash
pip install -r requirements.txt
```

如果网络不好，可以加清华镜像源：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 4.3 配置 .env
在项目根目录创建 `.env` 文件，填写你自己的配置。

示例配置：
```env
QINIU_AK=your_ak
QINIU_SK=your_sk
QINIU_TEXT_API_KEY=your_text_api_key
QINIU_VIDEO_API_KEY=your_video_api_key

QINIU_LLM_MODEL=qwen-plus
QINIU_LLM_BASE_URL=your_llm_base_url

QINIU_VIDEO_MODEL=wan2.6-t2v
QINIU_VIDEO_BASE_URL=your_video_base_url

# 图生视频图片公网化（必填，否则本地上传图无法被云端模型读取）
QINIU_KODO_BUCKET=your_bucket_name
QINIU_KODO_PUBLIC_DOMAIN=your-public-domain.com
# 可选，默认 https://up.qiniup.com
QINIU_KODO_UPLOAD_HOST=https://up.qiniup.com
```

注意：
- `.env` 不要随便提交到仓库
- 密钥不要写死在代码里

## 4.4 启动项目
```bash
python main.py
```

默认访问地址：`http://127.0.0.1:5000`

---

# 5. 开发时修改意见


| 修改的内容                 | 对应修改的文件/目录                                                                |
| -------------------------- | ---------------------------------------------------------------------------------- |
| 页面布局                   | `templates/*.html`                                                                 |
| 前端交互逻辑               | `static/app.js`                                                                    |
| 页面样式                   | `static/style.css`                                                                 |
| 新增一个接口               | `app/routes/对应模块.py`（项目管理放project_routes.py，视频相关放video_routes.py） |
| 模型调用逻辑               | `app/services/llm_service.py`                                                      |
| 提示词内容                 | `app/services/prompt_service.py`                                                   |
| 视频任务逻辑               | `app/services/video_service.py`                                                    |
| 导出功能逻辑               | `app/services/export_service.py`                                                   |
| 数据库表结构/读写逻辑      | `app/repositories/project_repo.py`                                                 |
| 兼容模型返回格式不稳定问题 | `app/utils/normalizers.py`                                                         |

---

# 6. 开发规则

**规则 1**：不要把业务逻辑重新写回 main.py

**规则 2**：不要在多个地方重复写相同逻辑
> 例如：模型调用逻辑统一放 llm_service.py，导出逻辑统一放 export_service.py

**规则 3**：新增功能时先想清楚属于哪一层
> 大致分层：请求入口 → routes；真正处理逻辑 → services；数据库存取 → repositories；通用小工具 → utils

**规则 4**：接口尽量返回统一结构
推荐成功格式：
```json
{
  "ok": true,
  "result": {}
}
```
推荐失败格式：
```json
{
  "ok": false,
  "error": "错误提示信息"
}
```

**规则 5**：配置不要硬编码，统一写到 `.env` 和 `config.py`

**规则 6**：新文件名尽量保持英文、语义清晰
> 例如：video_routes.py、export_service.py、project_repo.py

---

# 7. 常见协作流程

## 场景 1：想加一个“新的 AI 功能”
建议流程：
1. 在 `routes/` 里新增对应接口
2. 在 `services/` 里实现核心业务逻辑
3. 如果需要新 prompt，写入 `prompt_service.py`
4. 如果模型返回结构复杂，补充 `normalizers.py` 兼容逻辑

## 场景 2：想加一个“新的导出格式”
建议流程：
1. 在 `export_service.py` 里实现生成逻辑
2. 在 `export_routes.py` 里新增对应接口
3. 前端页面补充对应操作按钮

## 场景 3：想加项目字段
建议流程：
1. 修改数据库表结构
2. 更新 `project_repo.py` 读写逻辑
3. 更新前端读取和展示逻辑
4. 如果状态结构变更，同步修改 `normalizers.py`

---

# 8. 当前已知问题 / 后续优化方向

目前架构已经比最开始清晰很多，但还可以继续优化：

1. 可以把 `create_app()` 挪到 `app/__init__.py`，让 Flask 结构更标准
2. 可以加统一日志：接口日志、模型调用日志、视频任务日志、错误日志
3. 可以加统一异常处理（现在很多地方还是 try/except 分散写的）
4. 可以加单元测试：route 测试、service 测试、repository 测试
5. 可以继续细分 service：如果后面功能越来越多，可以进一步拆分为 `story_service.py`、`search_service.py`、`provider_service.py` 等

---

# 9. 新队友第一次接手建议

如果你第一次看这个项目，推荐按这个顺序理解，最容易搞清楚整个请求流：
1. 先看 `main.py`
2. 再看 `routes/` 目录
3. 再看 `services/` 目录
4. 再看 `repositories/` 目录
5. 最后看 `utils/normalizers.py`

---


## 补充：常见报错说明
1. 镜像源报错 `download result from oss storage err`：可更换清华镜像源 `https://pypi.tuna.tsinghua.edu.cn/simple` 重试
2. 访问报错 `URL拼写可能存在错误，请检查`：请确认项目已正常启动，访问地址为 `http://127.0.0.1:5000`，检查URL拼写是否正确
