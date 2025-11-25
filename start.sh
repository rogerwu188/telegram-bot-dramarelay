#!/bin/bash

# 启动 Bot 在后台
python3 bot.py &

# 启动 API 服务器在前台
python3 api_server.py
