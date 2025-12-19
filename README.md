# Speech Project

## 项目概述
`Speech Project` 是一个基于 Flask 的英语口语学习平台，集成了语音生成、语音评估和语音分析功能。项目采用模块化设计，结合 Celery 实现异步任务处理，并集成了百度翻译和讯飞语音等第三方服务。

## 系统架构

### 主要组件
- **Flask 应用**：提供 RESTful API 接口，处理用户请求。
- **Celery 任务队列**：用于异步处理耗时任务，如语音生成和评估。
- **数据库**：存储用户数据、语音记录和评估结果。
- **第三方服务集成**：包括百度翻译、讯飞语音等。

### 模块划分
- **app 模块**：核心业务逻辑，包括用户认证、语音评估、问题管理等。
- **celery_app 模块**：异步任务处理，如语音生成和评估任务。
- **tools 模块**：辅助工具和脚本，如数据导入和测试脚本。
- **utils 模块**：提供通用工具类，如邮件发送、ID 生成、翻译服务等。
- **views 模块**：定义了多个视图，包括用户认证、问题管理、会话管理等。

## 技术栈
- **后端**：Python, Flask, Celery
- **数据库**：SQLite（开发环境）, PostgreSQL（生产环境）
- **第三方服务**：百度翻译 API, 讯飞语音 API
- **任务队列**：Redis（作为 Celery 的消息代理）

## 数据库结构
数据库包含以下主要表：
- **用户表**：存储用户信息，包括用户名、密码哈希等。
- **语音记录表**：存储用户上传的语音文件及其相关元数据。
- **评估结果表**：存储语音评估的分数和详细结果。
- **会话表**：记录用户的会话信息，包括会话名称、最后活跃时间等。

## 安装与启动

### 环境准备
1. 确保已安装 Python 3.8 或更高版本。
2. 安装 Redis 并确保服务已启动。

### 安装依赖
运行以下命令安装项目依赖：
```bash
pip install -r requirements.txt
```

### 启动开发服务器
运行以下命令启动 Flask 开发服务器：
```bash
python run.py
```
服务器默认运行在 `http://127.0.0.1:5000`。

### 启动 Celery 任务队列
运行以下命令启动 Celery worker：
```bash
celery -A celery_app.tasks worker --loglevel=info
```

## 视图接口
- **`/`**: 返回项目简介。
- **`/auth`**: 用户认证相关接口。
- **`/questions`**: 问题管理接口。
- **`/session`**: 会话管理接口。
- **`/statistics`**: 统计功能接口。

## 测试
运行以下命令执行测试脚本：
```bash
pytest
```

## 常见问题
- **如何切换数据库？**
  修改 `app/config.py` 中的数据库配置，切换到 PostgreSQL 或其他数据库。
- **如何添加新任务？**
  在 `celery_app/tasks.py` 中定义新任务，并确保在 Flask 应用中调用。

## 贡献
欢迎提交 Issue 或 Pull Request 来改进项目。

## 联系方式
- **作者**: Speech Project 团队
- **邮箱**: support@speechproject.com
- **GitHub**: [项目地址](https://github.com/codemade188/speech_project)
