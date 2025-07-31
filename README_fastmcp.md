# FastMCP Code Analyzer

使用 FastMCP 框架重构的代码分析工具，包含文件审计状态跟踪和架构一致性审计功能。

## 项目结构

```
.
├── fastmcp_server.py         # FastMCP 主服务器
├── tools/                    # 工具模块
│   ├── file_status/         # 文件状态跟踪工具
│   │   ├── tool.py         # 工具实现
│   │   └── manager.py      # 状态管理逻辑
│   └── audit_architecture/  # 架构审计工具
│       ├── tool.py         # 工具实现
│       └── prompts.py      # 审计提示词
├── utils/                   # 通用工具
│   └── llm/                # LLM 连接管理
│       ├── client.py       # 统一客户端接口
│       ├── config.py       # 配置管理
│       └── providers.py    # 不同 LLM 提供商实现
└── requirements.txt        # 项目依赖
```

## 安装

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置 LLM（创建 `.env` 文件）：
```env
AI_PROVIDER=openai
OPENAI_API_KEY=your-api-key
AI_MODEL=gpt-4
```

## 运行

```bash
# 直接运行
python fastmcp_server.py

# 或使用 fastmcp CLI
fastmcp run fastmcp_server.py
```

## 可用工具

### 1. mcp_list_file_status
列出文件审计状态，返回 Markdown 表格格式。

**参数：**
- `directory` (可选): 目录路径，不提供则列出所有已跟踪文件

### 2. mcp_audit_architecture_consistency  
深度学习框架迁移一致性审计工具。

专门用于深度学习模型在不同框架间迁移（如TensorFlow到PyTorch）的代码审计。

**参数：**
- `old_file`: 原框架代码文件路径（如TensorFlow实现）
- `new_file`: 新框架代码文件路径（如PyTorch实现）  
- `exemption_file` (可选): 豁免规则文件路径

**审计重点：**
- 用户自定义的逻辑、变量名、超参数的一致性
- 计算流程的数学等价性
- 核心功能的完整性（激活函数、正则化项等）

### 3. mcp_request_audit_fix_approval
请求用户批准审计修复建议并获取下一步指令。

**参数：**
- `old_string`: 原始代码片段
- `new_string`: 建议的修复代码
- `reason`: 修复原因说明

**返回：**
用户用自然语言描述的指令，例如：
- "应用这个修复"
- "跳过这个，继续下一个"
- "修改变量名为 user_input 然后应用"
- "暂停审计，我需要先查看相关文件"
- 任何其他自然语言指令

## 与 Claude Desktop 集成

在 Claude Desktop 配置文件中添加：

```json
{
  "mcpServers": {
    "code-analyzer-fastmcp": {
      "command": "python",
      "args": ["/path/to/fastmcp_server.py"]
    }
  }
}
```

## 特性

- ✅ 使用 FastMCP 装饰器简化工具定义
- ✅ 模块化设计，每个工具独立管理
- ✅ 统一的 LLM 客户端接口
- ✅ 支持 OpenAI 和 Anthropic
- ✅ 文件状态自动跟踪
- ✅ 架构一致性审计
- ✅ 支持 `.auditignore` 文件来忽略特定文件
- ✅ Human in the Loop (HITL) 支持交互式决策

## 使用 .auditignore

在项目根目录创建 `.auditignore` 文件，使用类似 `.gitignore` 的语法来指定要忽略的文件：

```
# 忽略测试文件
**/test_*.py
**/tests/*.py

# 忽略特定文件
tools/example.py

# 忽略临时目录
temp/**/*.py
```

被忽略的文件在状态列表中会显示为 "🚫 Ignored"。

## Human in the Loop (HITL)

HITL 模块允许工具在执行过程中请求用户输入和确认。

### 使用方法

1. 启动HITL系统（服务器和Shell集成）：
```bash
python hitl_server.py
```

2. 在另一个终端运行FastMCP服务器：
```bash
python fastmcp_server.py
```

### 功能特点

- 🚀 集成式设计：一个命令同时启动服务器和Shell
- 🔒 架构审计工具在写入文件前会请求用户确认
- 📊 显示错误和警告统计
- 👀 提供修改预览
- ❌ 支持取消操作
- 🌐 基于HTTP通信，支持远程部署

### 配置选项

- `HITL_ENABLED=false` - 禁用HITL功能
- `HITL_SERVER_URL=http://localhost:8765` - HITL服务器地址
- `HITL_TIMEOUT=300` - 请求超时时间（秒）

详细使用说明请参考 [HITL_README.md](./HITL_README.md)。