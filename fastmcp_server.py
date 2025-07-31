#!/usr/bin/env python3
"""FastMCP server for code analysis tools"""

from typing import Optional, Annotated
from fastmcp import FastMCP
from tools.file_status import list_file_status
from tools.audit_architecture import audit_architecture_consistency
from utils.hitl import HITLClient

# Create FastMCP server instance
mcp = FastMCP("Code Analyzer")

# Register the list_file_status tool
@mcp.tool
async def list_file_status_tool(
    directory: Annotated[str, "需要查看审计状态的文件夹或者文件的绝对路径。"] = None
) -> str:
    """
    列出文件审计状态（返回Markdown表格）
    
    显示项目中文件的审计状态，包括是否已审计、最后审计时间以及文件是否在审计后被修改。
    
    返回格式示例：
    | File | Status | Last Audited | Modified Since |
    |------|--------|--------------|----------------|
    | src/main.py | ✅ Audited | 2025-01-15 10:30 | No |
    | src/test.py | 🚫 Ignored | N/A | N/A |
    
    **Summary**: 1/1 files audited (1 file ignored)
    """
    return await list_file_status(directory)

# Register the audit_architecture_consistency tool
@mcp.tool
async def audit_architecture_consistency_tool(
    old_file: Annotated[str, "原框架代码文件的绝对路径（如PyTorch实现），作为审计的参考基准"],
    new_file: Annotated[str, "新框架代码文件的绝对路径（如Paddlepaddle实现），将被审计并修改以标记不一致之处"],
    exemption_file: Annotated[str, "审计豁免规则文件的绝对路径，包含应该被豁免的审计规则"]
) -> str:
    """
    深度学习框架迁移一致性审计工具
    
    专门用于深度学习模型在不同框架间迁移（如PyTorch到Paddlepaddle）的代码审计。
    精通PyTorch、TensorFlow、Paddlepaddle、MindSpore等主流框架，确保迁移后的代码功能完全一致。
    
    审计重点：
    1. 用户自定义的逻辑、变量名、超参数的一致性
    2. 计算流程的数学等价性
    3. 核心功能的完整性（激活函数、正则化项等）
    
    该工具会：
    1. 严格比对新旧框架代码的一致性
    2. 在不一致处添加注释：# INCONSISTENT: [原因]
    3. 注释掉不一致代码并抛出 NotImplementedError
    4. 自动更新文件的审计状态
    
    豁免情况：
    - 框架转换的必要修改（如tf.keras.Model vs torch.nn.Module）
    - 框架内置参数创建方式的差异
    - 已存在的NotImplementedError用于预留未实现部分
    - 新增的print或日志输出
    
    返回审计结果摘要，包含发现的不一致数量。
    """
    return await audit_architecture_consistency(old_file, new_file, exemption_file)

# Register the request_audit_fix_approval tool
@mcp.tool
async def request_audit_fix_approval(
    old_string: Annotated[str, "原始代码片段"],
    new_string: Annotated[str, "建议的修复代码"],
    reason: Annotated[str, "修复原因说明"]
) -> str:
    """
    请求用户批准审计修复建议并获取下一步指令
    
    展示代码修改的前后对比，并说明修复原因，让用户用自然语言描述下一步操作。
    
    返回:
    用户用自然语言描述的指令，例如：
    - "应用这个修复"
    - "跳过这个，继续下一个"
    - "修改变量名为 user_input 然后应用"
    - "暂停审计，我需要先查看相关文件"
    - "应用修复但添加详细注释"
    - 任何其他自然语言指令
    """
    hitl = HITLClient()
    
    # 创建格式化的展示内容
    content = f"""## 审计修复建议

**修复原因**: {reason}

### 原始代码:
```python
{old_string}
```

### 修复后代码:
```python
{new_string}
```
"""
    
    # 使用 request_feedback 请求用户反馈
    # 将内容包含在提示中
    full_prompt = f"""{content}

请审查此修复建议，并描述您希望执行的操作："""
    
    feedback = await hitl.request_feedback(
        prompt=full_prompt,
        tool_name="request_audit_fix_approval",
        context={"reason": reason}
    )
    
    return feedback

# Main entry point
if __name__ == "__main__":
    # Run the server with default stdio transport
    mcp.run()