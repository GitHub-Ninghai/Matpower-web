# MATPOWER Web 可视化平台 - 前端

Vue 3 + TypeScript + Vite 构建的电力系统仿真可视化大屏平台。

## 技术栈

- **Vue 3** - Composition API + `<script setup>`
- **TypeScript** - 类型安全
- **Vite** - 构建工具
- **Ant Design Vue** - UI 组件库
- **ECharts** - 数据可视化
- **Cytoscape.js** - 网络拓扑图
- **Pinia** - 状态管理
- **Vue Router** - 路由管理
- **Axios** - HTTP 客户端

## 项目结构

```
src/
├── api/                    # API 接口层
│   ├── index.ts           # Axios 实例配置
│   └── types.ts           # TypeScript 类型定义
├── components/            # 可复用组件
│   ├── TopologyGraph.vue      # 网络拓扑图
│   ├── VoltageChart.vue       # 电压监控图表
│   ├── PowerFlowChart.vue     # 潮流分布图表
│   ├── SystemSummary.vue      # 系统概要
│   ├── DataTable.vue          # 数据表格
│   ├── DisturbancePanel.vue   # 扰动注入面板
│   ├── AlarmPanel.vue         # 告警面板
│   ├── SimulationControls.vue # 仿真控制
│   └── CaseSelector.vue       # 用例选择器
├── stores/                # Pinia 状态管理
│   ├── simulation.ts      # 仿真状态
│   ├── cases.ts           # 用例管理
│   └── alarm.ts           # 告警管理
├── views/                 # 页面组件
│   └── Dashboard.vue      # 主大屏页面
├── router/                # 路由配置
│   └── index.ts
├── styles/                # 全局样式
│   └── global.css         # 深色主题样式
├── mock/                  # Mock 数据
│   └── data.ts            # IEEE 14 测试数据
├── App.vue                # 根组件
└── main.ts                # 应用入口
```

## 开发指南

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

默认运行在 `http://localhost:5173`

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 功能模块

### 1. 网络拓扑图 (TopologyGraph)
- 使用 Cytoscape.js 渲染电力网络
- 节点颜色表示电压状态
- 支持点击查看详情
- 力导向布局

### 2. 电压监控 (VoltageChart)
- ECharts 柱状图
- 实时显示各母线电压
- 越限告警

### 3. 潮流分布 (PowerFlowChart)
- 显示线路有功潮流
- 负载率可视化

### 4. 扰动控制 (DisturbancePanel)
- 线路断开
- 发电机跳闸
- 负荷变化
- 电压变化
- OPF 自动修正

### 5. 告警系统
- 电压越限告警
- 线路过载告警
- 发电机出力越限

## API 配置

在 `.env` 文件中配置后端 API 地址：

```
VITE_API_URL=http://localhost:8000
```

## 样式主题

项目使用深色 SCADA 风格主题：

- 主背景: `#0d1117`
- 次背景: `#161b22`
- 主题色: `#1890ff` (蓝色)
- 成功色: `#52c41a` (绿色)
- 警告色: `#faad14`
- 危险色: `#ff4d4f` (红色)
