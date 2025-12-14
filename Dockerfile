# 使用官方 Python 3.13.7 作为基础镜像
FROM python:3.13.7-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
# --no-cache-dir: 减小镜像体积
# -i: 使用国内源加速（可选，部署时如果网络好可以去掉）
RUN pip install --no-cache-dir -r requirements.txt \
    && pip cache purge
# 复制项目代码到容器
COPY . .

# (重要) 确保容器内的应用能写入文件
# 假设你的数据库叫 db.sqlite3，或者你把它放在 data/ 文件夹里
RUN mkdir -p /app/data && chmod -R 777 /app/data


# 或者添加健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1
# 暴露端口 (请根据你的实际端口修改，比如 8000, 5000 等)
EXPOSE 8000

# 启动命令
CMD ["python", "main.py"]