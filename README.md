## 小Z搜索

百度夸克网盘资源搜索，转存分享


### 推荐使用docker-compose 安装
```
# 先下载到本地
git clone https://github.com/ghost-guest/quark_baidu_pansou.git
# 切换到目录下
cd quark_baidu_pansou
# 运行
docker-compose up -d

```

### git clone 北京地区超时的办法
关闭 HTTP/2（最推荐，通常能解决）
Git 默认使用 HTTP/2 协议进行通信，有时该协议的帧层（Framing Layer）会因为网络中间设备（如路由器、防火墙）的干扰而报错。强制 Git 使用旧版 HTTP/1.1 协议通常能解决问题。
```aiignore
git config --global http.version HTTP/1.1
```