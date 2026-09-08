# 名片快查（card-contacts）

拍一张名片 → 多模态视觉模型识别 → 人工核对 → 一键写入金山文档表格（含正反面照片、导入人）。

技术栈：FastAPI + SQLAlchemy(SQLite/MySQL) + JWT ｜ Vue3 + TypeScript + Element Plus + Vite

## 功能模块

| 模块 | 说明 | 权限 |
| --- | --- | --- |
| 名片识别 | 单面/正反两面拍照或上传 → 视觉模型提取 → 表单核对 → 选择分类 → 写入金山文档；自动填「导入人」；同步失败可在「录入记录」重试 | 所有用户 |
| 名片分类（tab） | 每个分类对应金山表格的一个工作表；新建分类时自动在金山表格中新建同名工作表并写好表头 | 管理员 |
| 视觉模型配置 | 配置 OpenAI 兼容的多模态模型（OpenAI / 通义千问 / 智谱 / 豆包 / Kimi / OpenRouter / 自定义）。保存时会发一张测试图验证模型真的支持图片输入，**非视觉模型无法保存** | 管理员 |
| 用户体系 | 管理员发放账号、启用/停用、重置密码；普通用户只能识别与查看自己的记录 | 管理员 |
| 金山文档配置 | 填 file_id / script_id / AirScript-Token，测试连接、查看现有工作表 | 管理员 |

金山表格列结构（A~P）：

```
序 | 语种 | 大类 | 名字 | 性别 | 备注 | 职位 | 主营业务关键词 | 主营产品/服务类型 | 公司名 | 官网 | 邮箱 | 电话 | 正面照片 | 反面照片 | 导入人
```

## 一、本地启动

### 后端（Conda）

```powershell
# 在仓库根目录
conda env create -f environment.yml        # 创建环境 card-contacts（Python 3.11 + requirements）
conda activate card-contacts

copy backend\.env.example backend\.env    # Mac/Linux: cp backend/.env.example backend/.env，按需修改
python run.py                              # 在仓库根目录运行；http://localhost:8000  接口文档 /docs
```

以后更新依赖：`conda activate card-contacts && pip install -r backend/requirements.txt`。
不用 conda 也可以：`python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt`。

首次启动自动建表并创建管理员：`admin / admin123`（可在 `.env` 中改 `ADMIN_USERNAME` / `ADMIN_PASSWORD`，登录后请修改密码）。
同时会预置 6 个默认分类：1 餐饮 / 2 二奢 / 3 推广 / 4.综合 / 5 电商 / 6 旅游。

### 前端

```bash
cd frontend
npm install
npm run dev                                           # http://localhost:5173 （/api 已代理到 8000）
```

### 生产部署（单进程托管前端）

```bash
cd frontend && npm run build && rm -rf ../backend/static && cp -r dist ../backend/static
cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

也可以 `docker compose up -d --build`（见 `docker-compose.yml`），访问 `http://服务器IP:8000`。

> **重要**：`.env` 里的 `PUBLIC_BASE_URL` 必须填服务器**公网可访问**的地址（例如 `https://card.example.com`）。
> 金山文档是在金山服务器上通过这个地址拉取名片照片再插入表格的，`localhost` 只能本地测试文字写入，图片会插入失败。

## 二、金山文档（AirScript）配置教程

金山文档表格支持 AirScript 脚本，并且脚本可以发布成 HTTP 接口被外部调用。本项目后端就是调用这个接口把数据写进表格。

1. **准备表格**：在金山文档中打开你的名片表格。每个分类一个工作表（tab），第一行表头按上面 A~P 的顺序（P 列「导入人」若还没有，脚本第一次写入时会自动补上表头）。
2. **新建脚本**：菜单 **效率 → 脚本编辑器**（旧版叫 AirScript / 高级开发），点「新建脚本」，把仓库中
   [`kdocs/kdocs-airscript.js`](kdocs/kdocs-airscript.js) 的全部内容粘贴进去，保存（脚本名随意，如 `card-sync`）。
3. **发布为 API**：脚本编辑器右上角 **发布 → API 调用**（或「Webhook / 接口」），页面会给出：
   - 调用地址：`https://www.kdocs.cn/api/v3/ide/file/{file_id}/script/{script_id}/sync_task`
   - 请求头：`AirScript-Token: xxxxxxxx`
4. **填入系统**：用管理员登录系统 → 左侧「金山文档」→ 填 `file_id`、`script_id`、`AirScript-Token`（表格链接只是备注）→ 保存 → 「测试连接」。
   成功会显示脚本版本 `card-contacts-v1` 和当前所有工作表名。
5. **对应分类**：左侧「名片分类」里每个分类的「金山工作表名」必须与表格里 tab 名称完全一致（含空格），可点「在金山中创建/校验 tab」自动检查或创建。

### 脚本原理（kdocs/kdocs-airscript.js）

后端 `POST` 到 `sync_task`，body 为 `{"Context": {"argv": {...}}}`，脚本里用 `Context.argv` 取参数，`return` 的对象即接口返回的 `data.result`。支持的 `action`：

| action | 参数 | 作用 |
| --- | --- | --- |
| `health` | - | 返回版本与工作表列表，用于测试连接 |
| `list_sheets` | - | 列出所有工作表名 |
| `ensure_sheet` | `sheetName` | 工作表不存在则新建并写表头（新建分类时调用） |
| `add` | `sheetName, moduleLabel, card, importer, frontImageUrl, backImageUrl` | 写入一行；按 邮箱 / 电话 / 姓名+公司 查重，重复则只补照片和导入人；照片用 `Shapes.AddPicture(url)` 嵌入 N/O 列，导入人写 P 列 |

## 三、视觉模型配置

管理员 → 「视觉模型」→ 添加模型，选择服务商会自动填 Base URL 与推荐模型名，填 API Key，点「验证并保存」。

| 服务商 | Base URL | 推荐视觉模型 |
| --- | --- | --- |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` / `gpt-4o-mini` |
| 阿里通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-vl-max` / `qwen-vl-plus` |
| 智谱 | `https://open.bigmodel.cn/api/paas/v4` | `glm-4v-plus` |
| 火山引擎豆包 | `https://ark.cn-beijing.volces.com/api/v3` | `doubao-1.5-vision-pro-32k`（填接入点 ID 亦可） |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k-vision-preview` |
| 任意 OpenAI 兼容网关 | 自填 | 需支持 `image_url` 消息 |

验证方式：后端生成一张纯红色图片让模型回答颜色，答出「红/red」才算通过；纯文本模型会被拒绝保存。

## 四、环境变量（backend/.env）

| 变量 | 说明 |
| --- | --- |
| `SECRET_KEY` | JWT 签名密钥，务必改成随机串 |
| `DATABASE_URL` | 默认 `sqlite:///./data/app.db`；MySQL 示例 `mysql+pymysql://u:p@host:3306/db`（需 `pip install pymysql`） |
| `PUBLIC_BASE_URL` | 服务器对外地址，供金山文档拉取图片 |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 首次启动创建的管理员 |
| `CORS_ORIGINS` | 允许的前端地址，逗号分隔 |

## 目录结构

```
backend/
  app/main.py            FastAPI 入口、静态托管
  app/models.py          User / VisionModel / Category / KdocsConfig / CardRecord
  app/routers/           auth_users, vision_models, categories, kdocs_config, cards
  app/services/vision.py 多模态模型调用 + 视觉能力验证 + 名片字段提取
  app/services/kdocs.py  金山 AirScript 调用封装
frontend/src/views/      CardScan / Records / Categories / VisionModels / Kdocs / Users
kdocs/kdocs-airscript.js 粘贴到金山文档脚本编辑器
```

## 线上部署（Docker + 已有 nginx 反代）

以 `cards.moneymoon.jp` 为例，服务器上：

```bash
cd /opt && git clone https://github.com/yrssn/card-contacts.git && cd card-contacts
cp deploy/env.production.example backend/.env   # 改 SECRET_KEY / ADMIN_PASSWORD / PUBLIC_BASE_URL
docker compose up -d --build                     # 监听 127.0.0.1:9282
curl http://127.0.0.1:9282/api/health
```

反代：把 `deploy/nginx-cards.conf` 放进 shared-proxy 的 conf.d，证书用 certbot 申请后 `docker exec shared-proxy nginx -s reload`。
若 shared-proxy 无法解析 `host.docker.internal`，把 `proxy_pass` 改成 `http://<宿主机内网IP>:9282`，或把 `docker-compose.yml` 里 `networks.proxy.name` 改成 shared-proxy 所在网络名后直接 `proxy_pass http://card-contacts:8000`。

`PUBLIC_BASE_URL` 必须是这个 https 域名，金山文档才能拉到名片照片。
