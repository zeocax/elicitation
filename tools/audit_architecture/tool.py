"""FastMCP tool for auditing architecture consistency"""

from typing import Optional
from pathlib import Path
import sys
import re

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.llm import LLMClient
from utils.hitl import HITLClient
from tools.file_status.manager import FileStatusManager
from .prompts import AUDIT_ARCHITECTURE_CONSISTENCY_PROMPT

# Global instances
llm_client = None
file_manager = None


def get_llm_client():
    """Get or create LLM client"""
    global llm_client
    if llm_client is None:
        llm_client = LLMClient()
    return llm_client


def get_file_manager():
    """Get or create file status manager"""
    global file_manager
    if file_manager is None:
        # Look for project_meta.json in parent directories
        current = Path.cwd()
        
        # Search up to 5 levels up for project_meta.json
        for _ in range(5):
            if (current / "project_meta.json").exists():
                file_manager = FileStatusManager(str(current))
                break
            parent = current.parent
            if parent == current:  # Reached root
                break
            current = parent
        
        # If not found, use current directory
        if file_manager is None:
            file_manager = FileStatusManager()
    
    return file_manager


async def audit_architecture_consistency(
    old_file: str,
    new_file: str,
    exemption_file: Optional[str] = None
) -> str:
    """
    Audit new architecture code for consistency with old architecture.
    
    This tool performs a strict audit of new architecture code by comparing it with
    the original architecture code. It marks all inconsistencies through comments
    and exceptions.
    
    Args:
        old_file: Path to the original architecture file (reference baseline)
        new_file: Path to the new architecture file (will be audited and modified)
        exemption_file: Optional path to exemption rules file
    
    Returns:
        Audit result message including counts of errors and warnings found.
    
    The tool will:
    1. Read both files and optional exemption rules
    2. Use AI to audit consistency
    3. Write the audited code back to new_file
    4. Update file audit status
    """
    try:
        # Read old file
        try:
            with open(old_file, 'r', encoding='utf-8') as f:
                old_code = f.read()
        except FileNotFoundError:
            return f"Error: Old file not found - {old_file}"
        except Exception as e:
            return f"Error reading old file: {str(e)}"
        
        # Read new file
        try:
            with open(new_file, 'r', encoding='utf-8') as f:
                new_code = f.read()
        except FileNotFoundError:
            return f"Error: New file not found - {new_file}"
        except Exception as e:
            return f"Error reading new file: {str(e)}"
        
        
        # Read exemption rules if provided
        exemption_rules = ""
        if exemption_file:
            try:
                exemption_path = Path(exemption_file)
                if exemption_path.exists():
                    with open(exemption_path, 'r', encoding='utf-8') as f:
                        exemption_rules = f.read().strip()
            except Exception as e:
                print(f"Warning: Failed to read exemption file: {e}")
        
        # If no exemption rules provided
        if not exemption_rules:
            exemption_rules = "无用户自定义豁免规则"
        
        # Format prompt
        prompt = AUDIT_ARCHITECTURE_CONSISTENCY_PROMPT.format(
            old_code=old_code,
            new_code=new_code,
            exemption_rules=exemption_rules
        )
        
        # Get LLM client and perform audit
        client = get_llm_client()
        
        # Use the prompt directly as user prompt, no system prompt needed
        response = await client.complete(prompt)
        
        # Extract code from response
        thinking_content = response["thinking_content"]
        audited_code = response["content"]
        
        # 输出thinking_content到hitl
        hitl = HITLClient()
        hitl.notify(message=thinking_content, tool_name="audit_architecture_consistency")
        
        # Count inconsistencies before asking for confirmation
        inconsistencies = audited_code.count("# INCONSISTENT:")
        not_implemented = audited_code.count("raise NotImplementedError")
        
        # Request user confirmation through HITL
        hitl = HITLClient()
        
        # Prepare preview (first 1000 characters)
        preview = audited_code[:1000]
        if len(audited_code) > 1000:
            preview += f"\n\n... ({len(audited_code) - 1000} more characters)"
        
        # Write the audited code back to new_file
        try:
            with open(new_file, 'w', encoding='utf-8') as f:
                f.write(audited_code)
        except Exception as e:
            return f"Error writing audited code: {str(e)}"
        
        # Update file status to audited after successful audit
        status_updated = False
        status_error = None
        try:
            fm = get_file_manager()
            status_updated = fm.update_file_status(new_file, audited=True)
        except Exception as e:
            status_error = str(e)
        
        result_msg = f"审计完成并已写入文件，共发现{inconsistencies}处不一致"
        
        if status_updated:
            result_msg += "\n✓ 文件审计状态已更新"
        elif status_error:
            result_msg += f"\n⚠️ 文件状态更新失败: {status_error}"
        else:
            result_msg += "\n⚠️ 文件状态更新失败"
            
        return result_msg
        
    except ValueError as e:
        return f"Configuration error: {str(e)}"
    except ImportError as e:
        return f"Missing dependency: {str(e)}"
    except Exception as e:
        return f"Error during architecture consistency audit: {str(e)}"