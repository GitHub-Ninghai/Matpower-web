# MATPOWER Web - 电力系统仿真平台

基于 [MATPOWER](https://matpower.org/) 的 Web 可视化电力系统仿真平台，提供潮流计算、最优潮流（OPF）、扰动分析等功能的交互式图形界面。

![Dashboard](docs/dashboard.png)

---

## 功能特性

### 网络拓扑可视化

基于 Cytoscape.js 的交互式电力网络拓扑图，支持缩放、平移和节点点击查看详情。母线按类型着色，支路显示潮流方向和负载率。

![Topology](docs/topology.png)

### 电压监测

ECharts 柱状图实时展示各母线电压幅值，绿/黄/红三色标识正常、越限和严重状态，直观显示电压安全问题。

![Voltage Chart](docs/voltage-chart.png)

### 潮流分布

展示各支路有功功率及线路负载率，高负载线路自动标红告警。

![Power Flow Chart](docs/powerflow-chart.png)

### 数据表格与编辑

提供母线、发电机、支路数据的表格视图，支持在线编辑参数（负荷、电压、线路容量等），编辑后自动重新计算。

![Data Panel](docs/data-panel.png)

### 告警面板

自动检测电压越限、线路过载、发电机出力异常等问题，按严重等级分类展示，支持一键跳转定位。

![Alarm Panel](docs/alarm-panel.png)

### 系统概要与扰动控制

底部面板展示系统总发电/负荷/损耗等关键指标，以及扰动注入控制台和仿真日志。

![Bottom Panel](docs/bottom-panel.png)

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3 + TypeScript + Vite + Ant Design Vue 4 + ECharts 6 + Cytoscape.js |
| **后端** | Python 3.12 + FastAPI + Uvicorn |
| **仿真引擎** | GNU Octave + MATPOWER（子进程调用） |
| **数据库** | SQLite（SQLAlchemy + aiosqlite） |
| **通信** | REST API + WebSocket |

---

## 快速开始

### 环境要求

- **Node.js** >= 18
- **Python** >= 3.10
- **GNU Octave** >= 6.2（需加入系统 PATH）
- **MATPOWER** 8.0+（已挂载到项目路径）

### 1. 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd ../frontend
npm install
```

### 2. 启动服务

```bash
# 后端（默认端口 8000）
cd backend
python run.py

# 前端（默认端口 5173）
cd frontend
npm run dev
```

或使用一键启动脚本：

```bash
# Windows
start-all.bat

# Linux/macOS
./start-all.sh
```

### 3. 访问应用

- **前端界面**: http://localhost:5173
- **后端 API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

---

## Docker 部署

```bash
docker-compose up -d
```

生产环境（含 Nginx 反向代理）：

```bash
docker-compose --profile production up -d
```

---

## 支持的仿真类型

| 类型 | 说明 | 算法 |
|------|------|------|
| **AC 潮流** | 交流潮流计算 | Newton-Raphson, Fast Decoupled (XB/BX), Gauss-Seidel |
| **DC 潮流** | 直流潮流计算 | 线性化近似 |
| **最优潮流 (OPF)** | 经济调度优化 | MIPS 等内点法 |

## 测试用例

内置 78 个 MATPOWER 标准测试用例，包括：

| 用例 | 母线数 | 说明 |
|------|--------|------|
| case9 | 9 | IEEE 9 母线系统 |
| case14 | 14 | IEEE 14 母线系统 |
| case30 | 30 | IEEE 30 母线系统 |
| case39 | 39 | IEEE 39 母线系统 |
| case57 | 57 | IEEE 57 母线系统 |
| case118 | 118 | IEEE 118 母线系统 |
| case300 | 300 | IEEE 300 母线系统 |
| ... | ... | 更多用例 |

---

## 扰动分析

支持四种扰动类型的实时注入：

- **线路开断** — 移除指定传输线路
- **发电机开断** — 关停指定发电机
- **负荷变化** — 调整母线负荷（MW/MVAr）
- **电压调整** — 修改电压设定值

支持 N-1 故障分析、蒙特卡洛模拟、灵敏度分析等高级功能。

---

## 项目结构

```
matpower-web/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/routes/       # API 路由（cases, simulation, disturbance, data）
│   │   ├── api/ws.py         # WebSocket 端点
│   │   ├── core/             # 核心逻辑（Octave 引擎）
│   │   ├── db/               # 数据库模型与连接
│   │   ├── models/           # Pydantic 数据模型
│   │   ├── services/         # 业务逻辑层
│   │   └── main.py           # 应用入口
│   └── run.py                # 启动脚本
├── frontend/                 # Vue 3 前端
│   ├── src/
│   │   ├── components/       # UI 组件
│   │   ├── views/            # 页面视图
│   │   ├── stores/           # Pinia 状态管理
│   │   ├── api/              # HTTP/WebSocket API 客户端
│   │   └── router/           # Vue Router 配置
│   └── package.json
├── docs/                     # 文档与截图
├── docker-compose.yml        # Docker 编排
├── start-all.bat / .sh       # 一键启动脚本
└── README.md
```

---

## API 概览

| 模块 | 端点 | 说明 |
|------|------|------|
| **用例管理** | `GET /api/cases` | 列出所有测试用例 |
| | `GET /api/cases/{name}` | 获取用例数据 |
| | `PUT /api/cases/{name}/params` | 修改用例参数 |
| **仿真** | `POST /api/simulation/run` | 异步运行仿真 |
| | `POST /api/simulation/pf` | 潮流计算 |
| | `POST /api/simulation/opf` | 最优潮流 |
| | `POST /api/simulation/n1-analysis` | N-1 分析 |
| **扰动** | `POST /api/disturbance/apply` | 注入扰动 |
| | `POST /api/disturbance/auto-correct` | OPF 自动校正 |
| **数据** | `GET /api/data/simulations` | 仿真记录查询 |
| | `POST /api/data/export/json` | 导出 JSON |
| | `POST /api/data/export/csv` | 导出 CSV |
| **WebSocket** | `/ws/simulation/{client_id}` | 仿真进度推送 |
| | `/ws/events` | 事件广播 |

完整 API 文档请访问 http://localhost:8000/docs。

---

## License

BSD-3-Clause
