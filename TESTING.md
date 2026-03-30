# MATPOWER Web 前后端集成测试指南

## 环境准备

### 1. 安装依赖

**后端依赖：**
```bash
cd E:\matpower-web\backend
pip install -r requirements.txt
```

**前端依赖：**
```bash
cd E:\matpower-web\frontend
npm install
```

### 2. 启动服务

**方式一：使用启动脚本**
- Windows: 双击 `E:\matpower-web\start.bat`
- Linux/Mac: 运行 `bash E:/matpower-web/start.sh`

**方式二：手动启动**

后端：
```bash
cd E:\matpower-web\backend
python run.py
```

前端：
```bash
cd E:\matpower-web\frontend
npm run dev
```

### 3. 验证服务状态

- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- 前端界面: http://localhost:5173

## 测试流程

### 测试一：后端健康检查

```bash
curl http://localhost:8000/health
```

预期响应：
```json
{
  "status": "healthy",
  "octave_initialized": true,
  "matpower_path": "E:/matpower"
}
```

### 测试二：获取测试用例列表

```bash
curl http://localhost:8000/api/cases
```

预期响应包含至少 case9, case14 等测试用例。

### 测试三：完整 IEEE 14 测试流程

#### 3.1 加载测试用例

前端操作：
1. 打开 http://localhost:5173
2. 在下拉框中选择 "IEEE 14 Bus System"
3. 观察拓扑图是否正确显示

#### 3.2 运行 AC 潮流计算

前端操作：
1. 选择仿真模式为 "AC 潮流"
2. 点击 "运行" 按钮
3. 观察进度条和日志
4. 检查结果：
   - 电压图表是否更新
   - 潮流图表是否更新
   - 系统概要数据是否正确
   - 数据表格是否显示结果

#### 3.3 修改参数并重新仿真

前端操作：
1. 在数据表格中找到母线 1
2. 修改其有功负荷 (pd) 从默认值改为 200 MW
3. 点击 "运行" 按钮
4. 检查仿真结果是否反映参数变化

#### 3.4 查看仿真历史

前端操作：
1. 查看底部日志面板
2. 应该显示多条仿真记录
3. 每条记录包含时间戳和结果摘要

### 测试四：扰动注入流程

#### 4.1 正常运行

1. 确保系统在正常状态（无告警）
2. 所有母线电压在 0.95-1.05 p.u. 范围内

#### 4.2 注入线路停运扰动

前端操作：
1. 在扰动面板中选择扰动类型 "线路停运"
2. 选择线路（如母线 1 → 母线 2）
3. 点击 "应用扰动" 按钮
4. 观察结果：
   - 拓扑图中该线路应该变色或隐藏
   - 重新计算潮流
   - 检查是否有电压越限或线路过载告警

#### 4.3 OPF 修正

前端操作：
1. 在有告警的状态下
2. 点击 "OPF 修正" 按钮
3. 观察结果：
   - 发电机出力重新分配
   - 告警是否消除
   - 总发电成本变化

### 测试五：数据导出

#### 5.1 导出仿真结果

前端操作：
1. 完成一次仿真后
2. 点击 "导出" 按钮
3. 选择导出格式（JSON/CSV）
4. 验证下载的文件内容

### 测试六：WebSocket 实时通信

#### 6.1 验证 WebSocket 连接

浏览器控制台：
```javascript
// 打开浏览器控制台，检查 WebSocket 连接
// 应该看到 "[WS] Connected to ws://localhost:8000/ws/simulation/dashboard-client"
```

#### 6.2 观察实时进度更新

前端操作：
1. 打开浏览器网络面板
2. 筛选 WebSocket 连接
3. 运行一次仿真
4. 观察 WS 消息：
   - `{"type": "progress", "progress": 0, "status": "running", ...}`
   - `{"type": "progress", "progress": 50, "status": "running", ...}`
   - `{"type": "progress", "progress": 100, "status": "completed", ...}`

### 测试七：多测试用例验证

对以下测试用例重复测试三和测试四：
- case9 (9 母线系统)
- case14 (14 母线系统)
- case30 (30 母线系统)
- case57 (57 母线系统)

### 测试八：并发性能测试

使用集成测试脚本：

```bash
node E:/matpower-web/test-integration.js
```

该脚本会自动运行所有 API 端点的测试。

## 验收标准

### 基础功能

- [ ] 后端服务能正常启动
- [ ] 前端界面能正常加载
- [ ] WebSocket 连接成功
- [ ] 能获取测试用例列表
- [ ] 能加载单个测试用例详细数据

### 仿真功能

- [ ] AC 潮流计算正常
- [ ] DC 潮流计算正常
- [ ] OPF 计算正常
- [ ] 仿真结果数据完整
- [ ] 系统概要统计正确

### 扰动功能

- [ ] 线路停运扰动能正确应用
- [ ] 发电机停运扰动能正确应用
- [ ] 负荷变化扰动能正确应用
- [ ] OPF 修正能解决约束违规

### 界面交互

- [ ] 拓扑图正确显示母线和线路
- [ ] 电压图表正确更新
- [ ] 潮流图表正确更新
- [ ] 告警面板正确显示违规
- [ ] 日志面板记录操作历史
- [ ] 数据表格显示仿真结果

### 性能指标

- [ ] 单次 AC 潮流计算时间 < 5 秒
- [ ] WebSocket 消息延迟 < 100ms
- [ ] 界面响应时间 < 500ms
- [ ] 大型测试用例 (case118) 能正常加载

## 常见问题

### 问题 1: 后端启动失败

**症状**: `ModuleNotFoundError: No module named 'octave2py'`

**解决**:
```bash
pip install octave2py
```

### 问题 2: Octave 未初始化

**症状**: 后端日志显示 "Octave engine not initialized"

**解决**:
1. 确保 GNU Octave 已安装并添加到 PATH
2. 确保 MATPOWER 已正确安装
3. 检查 `app/core/config.py` 中的路径配置

### 问题 3: 前端连接后端失败

**症状**: 浏览器控制台显示 CORS 错误

**解决**:
1. 检查后端 CORS 配置
2. 确保前端代理配置正确
3. 检查防火墙设置

### 问题 4: WebSocket 连接失败

**症状**: `[WS] Connection failed` 错误

**解决**:
1. 确保后端服务正常运行
2. 检查 WebSocket 端点是否正确
3. 检查浏览器控制台详细错误信息

## 测试报告模板

```markdown
# MATPOWER Web 集成测试报告

**测试日期**: YYYY-MM-DD
**测试人员**: [姓名]
**环境**: Windows 11 / Node.js vXX / Python vXX

## 测试结果

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 后端健康检查 | ✅ / ❌ | |
| 获取测试用例列表 | ✅ / ❌ | |
| 加载 case14 数据 | ✅ / ❌ | |
| AC 潮流计算 | ✅ / ❌ | |
| DC 潮流计算 | ✅ / ❌ | |
| OPF 计算 | ✅ / ❌ | |
| 线路停运扰动 | ✅ / ❌ | |
| 发电机停运扰动 | ✅ / ❌ | |
| OPF 修正 | ✅ / ❌ | |
| WebSocket 通信 | ✅ / ❌ | |
| 数据导出 | ✅ / ❌ | |

## 发现的问题

1. [问题描述]
   - 重现步骤:
   - 预期行为:
   - 实际行为:
   - 严重程度: 高/中/低

## 改进建议

1. [建议内容]

## 总体评价

- [ ] 通过验收，可以部署
- [ ] 需要修复问题后重新测试
```
