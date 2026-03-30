/**
 * MATPOWER Web 前后端集成测试脚本
 *
 * 运行方式：
 * node E:/matpower-web/test-integration.js
 *
 * 前提条件：
 * 1. 后端服务已启动 (http://localhost:8000)
 * 2. 前端服务已启动 (http://localhost:5173)
 */

const http = require('http');

const API_BASE = 'http://localhost:8000';

// 颜色输出
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logSection(title) {
  console.log('\n' + '='.repeat(60));
  log(title, 'blue');
  console.log('='.repeat(60));
}

// HTTP 请求封装
function request(method, path, data = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, API_BASE);
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json'
      }
    };

    const req = http.request(url, options, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        try {
          const json = body ? JSON.parse(body) : null;
          resolve({ status: res.statusCode, data: json });
        } catch (e) {
          resolve({ status: res.statusCode, data: body });
        }
      });
    });

    req.on('error', reject);

    if (data) {
      req.write(JSON.stringify(data));
    }

    req.end();
  });
}

// 测试套件
async function runTests() {
  logSection('MATPOWER Web 集成测试');

  let passedTests = 0;
  let failedTests = 0;

  // 测试 1: 健康检查
  logSection('测试 1: 后端健康检查');
  try {
    const result = await request('GET', '/health');
    if (result.status === 200 && result.data.status === 'healthy') {
      log('✓ 后端服务正常', 'green');
      passedTests++;
    } else {
      log('✗ 后端服务异常', 'red');
      failedTests++;
    }
  } catch (e) {
    log(`✗ 健康检查失败: ${e.message}`, 'red');
    failedTests++;
  }

  // 测试 2: 获取测试用例列表
  logSection('测试 2: 获取测试用例列表');
  try {
    const result = await request('GET', '/api/cases');
    if (result.status === 200 && Array.isArray(result.data)) {
      log(`✓ 获取到 ${result.data.length} 个测试用例`, 'green');
      result.data.forEach(c => log(`  - ${c.name}: ${c.buses} buses, ${c.generators} gens`));
      passedTests++;
    } else {
      log('✗ 测试用例格式错误', 'red');
      failedTests++;
    }
  } catch (e) {
    log(`✗ 获取测试用例失败: ${e.message}`, 'red');
    failedTests++;
  }

  // 测试 3: 获取 case14 详细数据
  logSection('测试 3: 获取 case14 详细数据');
  try {
    const result = await request('GET', '/api/cases/case14');
    if (result.status === 200 && result.data.base_mva) {
      log(`✓ case14 数据加载成功`, 'green');
      log(`  - Base MVA: ${result.data.base_mva}`);
      log(`  - Buses: ${result.data.bus?.length || 0}`);
      log(`  - Generators: ${result.data.gen?.length || 0}`);
      log(`  - Branches: ${result.data.branch?.length || 0}`);
      passedTests++;
    } else {
      log('✗ case14 数据格式错误', 'red');
      failedTests++;
    }
  } catch (e) {
    log(`✗ 获取 case14 失败: ${e.message}`, 'red');
    failedTests++;
  }

  // 测试 4: 运行 AC 潮流计算
  logSection('测试 4: 运行 AC 潮流计算');
  try {
    const result = await request('POST', '/api/simulation/pf', {
      case_name: 'case14',
      sim_type: 'PF',
      algorithm: 'NR'
    });
    if (result.status === 200 && result.data.success) {
      log(`✓ AC 潮流计算成功`, 'green');
      log(`  - Converged: ${result.data.converged}`);
      log(`  - Iterations: ${result.data.iterations}`);
      log(`  - Time: ${(result.data.et * 1000).toFixed(0)}ms`);
      if (result.data.system_summary) {
        const s = result.data.system_summary;
        log(`  - Total Gen: ${s.total_generation?.toFixed(2)} MW`);
        log(`  - Total Load: ${s.total_load?.toFixed(2)} MW`);
      }
      passedTests++;
    } else {
      log('✗ AC 潮流计算失败', 'red');
      log(`  Error: ${result.data.message || 'Unknown'}`, 'yellow');
      failedTests++;
    }
  } catch (e) {
    log(`✗ AC 潮流计算请求失败: ${e.message}`, 'red');
    failedTests++;
  }

  // 测试 5: 运行 OPF
  logSection('测试 5: 运行最优潮流 (OPF)');
  try {
    const result = await request('POST', '/api/simulation/opf', {
      case_name: 'case14',
      sim_type: 'OPF'
    });
    if (result.status === 200 && result.data.success) {
      log(`✓ OPF 计算成功`, 'green');
      log(`  - Total Cost: $${result.data.total_cost?.toFixed(2)}/hr`);
      passedTests++;
    } else {
      log('✗ OPF 计算失败', 'red');
      log(`  Error: ${result.data.message || 'Unknown'}`, 'yellow');
      failedTests++;
    }
  } catch (e) {
    log(`✗ OPF 计算请求失败: ${e.message}`, 'red');
    failedTests++;
  }

  // 测试 6: 应用扰动 (线路停运)
  logSection('测试 6: 应用线路停运扰动');
  try {
    const result = await request('POST', '/api/simulation/disturbance', {
      case_name: 'case14',
      disturbance: {
        disturbance_type: 'line_outage',
        target_id: { f_bus: 1, t_bus: 2 }
      }
    });
    if (result.status === 200 && result.data.success) {
      log(`✓ 扰动应用成功`, 'green');
      passedTests++;
    } else {
      log('✗ 扰动应用失败', 'red');
      failedTests++;
    }
  } catch (e) {
    log(`✗ 扰动请求失败: ${e.message}`, 'red');
    failedTests++;
  }

  // 测试 7: 获取仿真历史
  logSection('测试 7: 获取仿真历史');
  try {
    const result = await request('GET', '/api/simulation/history?limit=5');
    if (result.status === 200 && Array.isArray(result.data)) {
      log(`✓ 获取到 ${result.data.length} 条历史记录`, 'green');
      passedTests++;
    } else {
      log('✗ 历史记录格式错误', 'red');
      failedTests++;
    }
  } catch (e) {
    log(`✗ 获取历史失败: ${e.message}`, 'red');
    failedTests++;
  }

  // 测试 8: 获取系统统计
  logSection('测试 8: 获取系统统计');
  try {
    const result = await request('GET', '/api/data/stats');
    if (result.status === 200) {
      log(`✓ 系统统计获取成功`, 'green');
      log(`  - Total Records: ${result.data.total_records || 0}`);
      passedTests++;
    } else {
      log('✗ 系统统计获取失败', 'red');
      failedTests++;
    }
  } catch (e) {
    log(`✗ 系统统计请求失败: ${e.message}`, 'red');
    failedTests++;
  }

  // 总结
  logSection('测试总结');
  const totalTests = passedTests + failedTests;
  log(`总测试数: ${totalTests}`, 'blue');
  log(`通过: ${passedTests}`, 'green');
  log(`失败: ${failedTests}`, failedTests > 0 ? 'red' : 'green');

  if (failedTests === 0) {
    log('\n🎉 所有测试通过！前后端集成正常。', 'green');
  } else {
    log(`\n⚠️  有 ${failedTests} 个测试失败，请检查。`, 'yellow');
  }

  process.exit(failedTests > 0 ? 1 : 0);
}

// 运行测试
runTests().catch(err => {
  log(`\n✗ 测试运行失败: ${err.message}`, 'red');
  process.exit(1);
});
