# Human in the Loop (HITL) Module

## 概述

HITL（Human in the Loop）模块为FastMCP工具提供了交互式决策能力。通过这个模块，工具可以在执行过程中请求用户输入、确认或选择，实现关键决策的人工控制。

## 架构

HITL模块包含三个主要组件：

1. **HITL Server** - 处理工具请求和用户响应的中央服务器
2. **HITL Client** - 工具用来发送请求的客户端库
3. **HITL Shell** - 用户交互的命令行界面

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动HITL系统

运行集成的服务器和Shell：

```bash
python hitl_server.py
```

这会同时启动：
- HTTP服务器（监听端口8765）
- 交互式Shell界面

### 3. 运行FastMCP服务器

在另一个终端中运行：

```bash
python fastmcp_server.py
```

### 独立模式（高级用法）

如果需要分别运行服务器和Shell（例如远程部署），需要自行修改代码：

1. 修改 `server.py` 添加独立运行的入口
2. 创建独立的 shell 脚本使用 `HITLShell` 类

当前版本推荐使用集成模式，更简单可靠。

## 使用示例

### 在工具中集成HITL

```python
from utils.hitl import HITLClient

async def my_tool_function():
    hitl = HITLClient()
    
    # 请求文本输入
    user_input = await hitl.request_input(
        prompt="请输入项目名称：",
        tool_name="my_tool"
    )
    
    # 请求确认
    confirmed = await hitl.request_confirmation(
        message="是否继续执行？",
        tool_name="my_tool",
        details={"action": "删除文件"}
    )
    
    # 请求选择
    choice = await hitl.request_choice(
        prompt="选择操作模式：",
        choices=["快速", "标准", "详细"],
        tool_name="my_tool"
    )
```

## 请求类型

### 1. INPUT - 文本输入
请求用户输入文本信息。

### 2. CONFIRMATION - 确认
请求用户进行是/否确认。

### 3. CHOICE - 选择
请求用户从给定选项中选择。

### 4. REVIEW - 审查
请求用户审查内容并决定是否批准。

## 配置

通过环境变量配置HITL行为：

- `HITL_ENABLED` - 是否启用HITL（默认：true）
- `HITL_TIMEOUT` - 请求超时时间（默认：300秒）
- `HITL_SERVER_URL` - HITL服务器地址（默认：http://localhost:8765）

当`HITL_ENABLED=false`时，确认请求会自动返回true，其他请求返回None。

## 与架构审计工具的集成

架构审计工具已集成HITL功能：

### 1. 审计结果确认
在审计完成后，工具会请求用户确认是否将修改写入文件：
- 显示发现的错误和警告数量
- 显示修改内容的预览
- 等待用户确认
- 根据用户决定执行或取消操作

### 2. 审计修复批准（新功能）
使用 `request_audit_fix_approval` 工具请求用户批准具体的代码修复：

```python
# 示例：请求批准类型注解修复
response = await request_audit_fix_approval(
    old_string="def calc(x): return x * 2",
    new_string="def calculate(x: float) -> float: return x * 2",
    reason="函数名不够描述性，且缺少类型注解"
)

# response 可能是：
# "应用修复"
# "应用修复，但保留原函数名 calc"
# "修改为 def calc(x: Union[int, float]) -> Union[int, float]"
# "先检查这个函数在哪些地方被调用"
# 等等...
```

用户可以用自然语言描述任何操作指令，系统会返回这些指令供调用方处理。

## 故障排除

### 连接错误
- 确保HITL服务器正在运行
- 检查服务器地址和端口配置
- 确认防火墙设置允许连接

### 超时问题
- 增加`HITL_TIMEOUT`环境变量值
- 确保Shell正在运行并等待请求

### 请求未显示
- 检查Shell是否连接到正确的服务器
- 查看服务器日志确认请求是否收到

## 开发指南

### 添加新的请求类型

1. 在`models.py`的`RequestType`枚举中添加新类型
2. 在`shell.py`的`handle_request`方法中添加处理逻辑
3. 在`client.py`中添加便捷方法

### 自定义UI

Shell使用Rich库提供美观的命令行界面。可以通过修改`shell.py`中的显示逻辑来自定义外观。

## 安全考虑

1. HITL服务器默认监听所有接口（0.0.0.0）
2. 生产环境建议：
   - 使用localhost或内网地址
   - 添加认证机制
   - 使用HTTPS
   - 限制请求来源

## 未来改进

- [ ] WebSocket支持，实现实时通信
- [ ] Web界面作为Shell的替代方案
- [ ] 请求历史记录和审计日志
- [ ] 批量处理多个待处理请求
- [ ] 请求优先级和分类
- [ ] 自然语言指令解析器，自动理解和执行用户指令
- [ ] 上下文感知的智能建议
- [ ] 多语言支持