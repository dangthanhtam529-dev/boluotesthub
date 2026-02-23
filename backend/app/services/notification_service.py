"""
通知发送服务

支持：
- 钉钉机器人
- 企业微信机器人
- 邮件（预留）
"""

import json
import time
import hmac
import hashlib
import base64
import urllib.parse
import httpx
from datetime import datetime
from typing import Any

from app.models.notification import (
    NotificationChannel,
    NotificationLog,
    ChannelType,
)
from app.models.execution import TestExecution
from app.models.base import get_datetime_china


class NotificationService:
    """通知发送服务"""
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """关闭 HTTP 客户端"""
        await self.http_client.aclose()
    
    async def send_to_channel(
        self,
        channel: NotificationChannel,
        title: str,
        content: str,
    ) -> tuple[bool, str]:
        """
        发送通知到指定渠道
        
        Returns:
            tuple[bool, str]: (是否成功, 错误信息)
        """
        try:
            if channel.channel_type == ChannelType.DINGTALK:
                return await self._send_dingtalk(channel.config, title, content)
            elif channel.channel_type == ChannelType.WEWORK:
                return await self._send_wework(channel.config, title, content)
            elif channel.channel_type == ChannelType.EMAIL:
                return await self._send_email(channel.config, title, content)
            else:
                return False, f"不支持的渠道类型: {channel.channel_type}"
        except Exception as e:
            return False, str(e)
    
    async def _send_dingtalk(
        self,
        config_json: str,
        title: str,
        content: str,
    ) -> tuple[bool, str]:
        """
        发送钉钉消息
        
        配置格式:
        {
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
            "secret": "SECxxx"  // 可选，加签密钥
        }
        """
        try:
            config = json.loads(config_json)
            webhook = config.get("webhook")
            secret = config.get("secret")
            
            if not webhook:
                return False, "缺少 webhook 配置"
            
            url = webhook
            if secret:
                timestamp, sign = self._generate_dingtalk_sign(secret)
                url = f"{webhook}&timestamp={timestamp}&sign={sign}"
            
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": content
                }
            }
            
            response = await self.http_client.post(
                url,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    return True, ""
                else:
                    return False, result.get("errmsg", "发送失败")
            else:
                return False, f"HTTP 错误: {response.status_code}"
                
        except json.JSONDecodeError:
            return False, "配置 JSON 格式错误"
        except Exception as e:
            return False, str(e)
    
    def _generate_dingtalk_sign(self, secret: str) -> tuple[str, str]:
        """生成钉钉加签"""
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign
    
    async def _send_wework(
        self,
        config_json: str,
        title: str,
        content: str,
    ) -> tuple[bool, str]:
        """
        发送企业微信消息
        
        配置格式:
        {
            "webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
        }
        """
        try:
            config = json.loads(config_json)
            webhook = config.get("webhook")
            
            if not webhook:
                return False, "缺少 webhook 配置"
            
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "content": f"### {title}\n\n{content}"
                }
            }
            
            response = await self.http_client.post(
                webhook,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    return True, ""
                else:
                    return False, result.get("errmsg", "发送失败")
            else:
                return False, f"HTTP 错误: {response.status_code}"
                
        except json.JSONDecodeError:
            return False, "配置 JSON 格式错误"
        except Exception as e:
            return False, str(e)
    
    async def _send_email(
        self,
        config_json: str,
        title: str,
        content: str,
    ) -> tuple[bool, str]:
        """
        发送邮件（预留）
        
        配置格式:
        {
            "smtp_host": "smtp.example.com",
            "smtp_port": 465,
            "smtp_user": "user@example.com",
            "smtp_password": "password",
            "from_addr": "noreply@example.com",
            "to_addrs": ["user1@example.com", "user2@example.com"]
        }
        """
        return False, "邮件发送功能暂未实现"


class NotificationBuilder:
    """通知消息构建器"""
    
    @staticmethod
    def build_execution_notification(
        execution: TestExecution,
        project_name: str | None = None,
    ) -> tuple[str, str]:
        """
        构建执行完成通知消息
        
        Returns:
            tuple[str, str]: (标题, 内容)
        """
        status_emoji = "✅" if execution.status == "completed" else "❌"
        status_text = "通过" if execution.status == "completed" else "失败"
        
        title = f"🧪 测试执行{status_text}"
        
        lines = [
            f"### 🧪 测试执行{status_text}",
            "",
            f"**项目**: {project_name or execution.project_name or '未知项目'}",
            f"**执行状态**: {status_emoji} {status_text}",
            "",
            "---",
            "",
            "#### 📊 执行结果",
        ]
        
        if execution.total_cases:
            lines.append(f"- 用例总数: {execution.total_cases}")
            lines.append(f"- 通过: {execution.passed_cases or 0}")
            lines.append(f"- 失败: {execution.failed_cases or 0}")
            if execution.total_cases > 0:
                pass_rate = round((execution.passed_cases or 0) / execution.total_cases * 100, 1)
                lines.append(f"- 通过率: {pass_rate}%")
        
        if execution.duration:
            minutes = int(execution.duration // 60)
            seconds = int(execution.duration % 60)
            lines.append(f"- 耗时: {minutes}分{seconds}秒")
        
        lines.extend([
            "",
            "---",
            "",
            f"⏰ 执行时间: {execution.created_at.strftime('%Y-%m-%d %H:%M:%S') if execution.created_at else '未知'}",
        ])
        
        if execution.error_message:
            lines.extend([
                "",
                f"❌ 错误信息: {execution.error_message[:200]}",
            ])
        
        content = "\n".join(lines)
        return title, content
    
    @staticmethod
    def build_threshold_alert(
        execution: TestExecution,
        project_name: str | None = None,
        threshold: float = 80.0,
    ) -> tuple[str, str]:
        """
        构建阈值告警消息
        
        Returns:
            tuple[str, str]: (标题, 内容)
        """
        title = "🚨 测试通过率告警"
        
        pass_rate = 0
        if execution.total_cases and execution.total_cases > 0:
            pass_rate = round((execution.passed_cases or 0) / execution.total_cases * 100, 1)
        
        lines = [
            "### 🚨 测试通过率告警",
            "",
            f"**项目**: {project_name or execution.project_name or '未知项目'}",
            f"**当前通过率**: {pass_rate}%",
            f"**告警阈值**: {threshold}%",
            "",
            "---",
            "",
            "#### 📊 执行详情",
            f"- 用例总数: {execution.total_cases or 0}",
            f"- 通过: {execution.passed_cases or 0}",
            f"- 失败: {execution.failed_cases or 0}",
            "",
            f"⏰ 执行时间: {execution.created_at.strftime('%Y-%m-%d %H:%M:%S') if execution.created_at else '未知'}",
        ]
        
        content = "\n".join(lines)
        return title, content
    
    @staticmethod
    def build_test_message(channel_name: str) -> tuple[str, str]:
        """
        构建测试消息
        
        Returns:
            tuple[str, str]: (标题, 内容)
        """
        title = "🔔 通知测试"
        content = f"""### 🔔 通知测试

**渠道**: {channel_name}

这是一条测试消息，用于验证通知渠道配置是否正确。

⏰ 发送时间: {get_datetime_china().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return title, content
