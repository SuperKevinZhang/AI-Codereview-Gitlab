import json
import requests
import os
import re
import hashlib
import base64
import hmac
import time
import urllib.parse

from biz.utils.log import logger


class FeishuNotifier:
    def __init__(self, webhook_url=None, project_name=None):
        """
        初始化飞书通知器
        :param webhook_url: 飞书机器人webhook地址
        """
        self.enabled = os.environ.get('FEISHU_ENABLED', '0') == '1'

        #打印项目名称
        logger.info(f"项目名称:{project_name}")
        # 项目名称{'DMP'}是这个结构的，改为只要DMP这个内容
        # 判断是否为空或None
        if project_name and project_name != None:
            project_name = list(project_name)[0]  # 将集合转换为列表，并获取第一个元素
           
        logger.info(f"项目名称:{project_name}")
        logger.info(f'FEISHU_WEBHOOK_URL_{project_name}')
        logger.info(f"飞书webhook:{os.environ.get(f'FEISHU_WEBHOOK_URL_{project_name}', '')}")

        if project_name:
            self.webhook_url = webhook_url or os.environ.get(f'FEISHU_WEBHOOK_URL_{project_name}', '') or os.environ.get('FEISHU_WEBHOOK_URL', '')
        else:
            self.webhook_url = webhook_url or os.environ.get('FEISHU_WEBHOOK_URL', '')
        self.secret = os.environ.get(f'FEISHU_SECRET_{project_name}', '') or os.environ.get('FEISHU_SECRET', '')

    def gen_sign(self, timestamp, secret):
        # 拼接timestamp和secret
        logger.info(f"timestamp:{timestamp}, secret:{secret}")
        string_to_sign = '{}\n{}'.format(timestamp, secret)
        hmac_code = hmac.new(string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        # 对结果进行base64处理
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode('utf-8'))
        return sign
    
    def _get_post_url(self):
        if not self.secret:
            return self.webhook_url
        timestamp = str(round(time.time()))
        sign = self.gen_sign(timestamp, self.secret)
        return f"{self.webhook_url}?timestamp={timestamp}&sign={sign}"
    
    def send_message(self, content, msg_type='text', title=None, is_at_all=False):
        """
        发送飞书消息
        :param content: 消息内容
        :param msg_type: 消息类型，支持text和markdown
        :param title: 消息标题(markdown类型时使用)
        :param is_at_all: 是否@所有人
        """
        if not self.enabled:
            logger.info("飞书推送未启用")
            return

        if not self.webhook_url:
            logger.error("飞书Webhook URL未配置")
            return

        try:
            if msg_type == 'markdown':
                data = {
                    "msg_type": "interactive",
                    "card": {
                        "schema": "2.0",
                        "config": {
                            "update_multi": True,
                            "style": {
                                "text_size": {
                                    "normal_v2": {
                                        "default": "normal",
                                        "pc": "normal",
                                        "mobile": "heading"
                                    }
                                }
                            }
                        },
                        "body": {
                            "direction": "vertical",
                            "padding": "12px 12px 12px 12px",
                            "elements": [
                                {
                                    "tag": "markdown",
                                    "content": content,
                                    "text_align": "left",
                                    "text_size": "normal_v2",
                                    "margin": "0px 0px 0px 0px"
                                }
                            ]
                        },
                        "header": {
                            "title": {
                                "tag": "plain_text",
                                "content": title
                            },
                            "template": "blue",
                            "padding": "12px 12px 12px 12px"
                        }
                    }
                }
            else:
                data = {
                    "msg_type": "text",
                    "content": {
                        "text": content
                    },
                }

            logger.info(f"发送飞书Url: {self._get_post_url()}")
            response = requests.post(
                self._get_post_url(),
                json=data,
                headers={'Content-Type': 'application/json'}
            )

            if response.status_code != 200:
                logger.error(f"发送飞书消息失败: {response.text}")
                return

            result = response.json()
            if result.get('msg') != "success":
                logger.error(f"发送飞书消息失败: {result}")
            else:
                logger.info("飞书消息发送成功")

        except Exception as e:
            logger.error(f"发送飞书消息时发生错误: {str(e)}")
