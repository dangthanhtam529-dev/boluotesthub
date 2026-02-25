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
        import os
        import logging
        
        # 记录当前工作目录和环境信息，便于排查定时任务环境问题
        logger = logging.getLogger("app.notification")
        logger.info(f"NotificationService 初始化 - 工作目录：{os.getcwd()}, 用户：{os.environ.get('USERNAME', 'N/A')}")
        
        # 配置同步 httpx 客户端，解决事件循环冲突
        self.http_client = httpx.Client(
            timeout=30.0,
            verify=True,  # 默认开启 SSL 验证
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    def close(self):
        """关闭 HTTP 客户端"""
        self.http_client.close()
    
    def send_to_channel(
        self,
        channel: NotificationChannel,
        title: str,
        content: str,
    ) -> tuple[bool, str]:
        """
        发送通知到指定渠道（同步版本，解决事件循环冲突）
        
        Returns:
            tuple[bool, str]: (是否成功，错误信息)
        """
        try:
            if channel.channel_type == ChannelType.DINGTALK:
                return self._send_dingtalk(channel.config, title, content)
            elif channel.channel_type == ChannelType.WEWORK:
                return self._send_wework(channel.config, title, content)
            elif channel.channel_type == ChannelType.EMAIL:
                return self._send_email(channel.config, title, content)
            else:
                return False, f"不支持的渠道类型：{channel.channel_type}"
        except Exception as e:
            return False, str(e)
    
    def _send_dingtalk(
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
        import os
        import logging
        
        logger = logging.getLogger("app.notification")
        
        try:
            logger.info(f"开始发送钉钉消息 - 工作目录：{os.getcwd()}")
            logger.info(f"Webhook 配置：{config_json[:50]}...")
            
            config = json.loads(config_json)
            webhook = config.get("webhook")
            secret = config.get("secret")
            
            if not webhook:
                logger.error("钉钉发送失败：缺少 webhook 配置")
                return False, "缺少 webhook 配置"
            
            url = webhook
            if secret:
                timestamp, sign = self._generate_dingtalk_sign(secret)
                url = f"{webhook}&timestamp={timestamp}&sign={sign}"
                logger.info(f"已生成加签 URL: ...timestamp={timestamp}...")
            
            message = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": content
                }
            }
            
            logger.info(f"正在发送请求到：{url[:80]}...")
            
            try:
                response = self.http_client.post(
                    url,
                    json=message,
                    headers={"Content-Type": "application/json"}
                )
            except httpx.SSLError as ssl_err:
                logger.error(f"钉钉 SSL 错误：{ssl_err}")
                logger.info("尝试禁用 SSL 验证重试...")
                # 定时任务环境下可能缺少 CA 证书，尝试禁用 SSL 验证
                with httpx.Client(timeout=30.0, verify=False) as client:
                    response = client.post(
                        url,
                        json=message,
                        headers={"Content-Type": "application/json"}
                    )
            except Exception as http_err:
                logger.error(f"钉钉 HTTP 请求异常：{http_err}")
                return False, f"网络请求失败：{str(http_err)}"
            
            logger.info(f"收到响应 - 状态码：{response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get("errcode") == 0:
                    logger.info("钉钉消息发送成功")
                    return True, ""
                else:
                    errcode = result.get("errcode")
                    errmsg = result.get("errmsg", "发送失败")
                    logger.error(f"钉钉 API 返回错误：errcode={errcode}, errmsg={errmsg}")
                    
                    # 特殊处理常见的权限错误
                    if errcode in [40008, 41002, 42003]:
                        logger.error(f"钉钉权限错误，请检查 webhook 配置：{errmsg}")
                        return False, f"权限错误 (errcode={errcode}): {errmsg}"
                    
                    return False, errmsg
            else:
                error_body = response.text[:500]
                logger.error(f"钉钉 HTTP 错误：{response.status_code}, body={error_body}")
                return False, f"HTTP 错误：{response.status_code}"
                
        except json.JSONDecodeError as json_err:
            logger.error(f"配置 JSON 解析失败：{json_err}")
            return False, "配置 JSON 格式错误"
        except Exception as e:
            logger.error(f"钉钉发送异常：{type(e).__name__}: {e}", exc_info=True)
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
    
    def _send_wework(
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
            
            response = self.http_client.post(
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
                return False, f"HTTP 错误：{response.status_code}"
                
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
