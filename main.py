import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
from contextlib import asynccontextmanager
from utils.quark_api.quark_controller import QuarkController
from utils.module import DatabaseManager
from utils.scheduler import FileCleanupScheduler
from utils.baidu_api.baidu_controller import BaiduController
from utils.plugin.plugin_zijianfuwuqi import ZjFuwuQi
from utils.yml_utils.yml_operation import YmlOperation

# 全局变量
db_manager = None
quark_client = None
cleanup_scheduler = None
baidu_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器
    """
    global db_manager, quark_client, cleanup_scheduler, baidu_client

    # 启动时执行的初始化操作
    print("应用启动中...")

    # 初始化数据库管理器
    db_manager = DatabaseManager('app.db')

    # 初始化Quark客户端
    quark_client = QuarkController()
    # 初始化百度客户端
    baidu_client = BaiduController()
    # 创建并启动定时清理任务
    cleanup_scheduler = FileCleanupScheduler(
        db_manager=db_manager,
        client=[quark_client, baidu_client],
        interval=60
    )

    # 启动定时任务
    cleanup_scheduler.start()
    print("定时清理任务已启动")

    yield  # 应用运行期间

    # 关闭时执行的清理操作
    if cleanup_scheduler:
        cleanup_scheduler.stop()
        print("定时清理任务已停止")

    print("应用已关闭")


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# @app.post("/")
# async def quark_save(request: Request):
#     print("收到POST请求")
#     try:
#         # 获取请求参数
#         request_body = await request.body()
#         # json解析
#         request_parse_body = json.loads(request_body.decode("utf-8"))
#         # quark save
#         quark_operator = QuarkController()
#         url_share = request_parse_body.get("kw")
#         task_name = request_parse_body.get("task_name")
#         dict_p = {
#             "shareurl": url_share,
#             "savepath": "夸克分享资源",
#             "taskname": task_name,
#             "share_type":"quark"
#         }
#         res = quark_operator.save_file_and_get_share_url(dict_p)
#         return {"message": res}
#     except Exception as e:
#         print(f"Error: {e}")
#         return {"message": "Error: " + str(e)}
#
#     print(f'request_body: {request_parse_body}')
#     return {"message": "Hello World"}
#
#
# @app.post("/baidu")
# async def baidu_save(request: Request):
#     print("收到POST请求")
#     try:
#         # 获取请求参数
#         request_body = await request.body()
#         # json解析
#         request_parse_body = json.loads(request_body.decode("utf-8"))
#         # baidu save
#         baidu_operator = BaiduController()
#         url_share = request_parse_body.get("kw")
#         task_name = request_parse_body.get("task_name")
#         share_password = request_parse_body.get("share_password")
#         dict_p = {
#             "shareurl": url_share,
#             "savepath": "百度分享资源",
#             "taskname": task_name,
#             "share_password":share_password,
#             "share_type":"baidu"
#         }
#         res = baidu_operator.save_and_share_file(dict_p)
#         return {"message": res}
#     except Exception as e:
#         print(f"Error: {e}")
#         return {"message": "Error: " + str(e)}


@app.get("/")
async def read_index():
    """
    返回主页
    :return:
    """
    return FileResponse("static/index.html")


@app.get("/admin")
async def read_admin():
    """
    返回主页
    :return:
    """
    return FileResponse("static/admin.html")


@app.post("/get_resource")
async def get_resource(request: Request):
    # 从自己搭建的docker的服务器上获取资源
    """request_parse_body:
    {
  "kw": "心动的信号",
  "cloud_types": [
    "baidu"
  ]
}
    :param request:
    :return:
    """
    print("收到POST请求")
    request_body = await request.body()
    request_parse_body = json.loads(request_body.decode("utf-8"))
    print(f'request_body: {request_parse_body}')

    async with ZjFuwuQi() as client:
        result = await client.post_data(data=request_parse_body)
        print(f"result is {result}")
        # 增加一个有效性的检测

        return result


@app.post("/get_share")
async def get_share(request: Request):
    # 获取分享链接的方法
    share_url = "资源已失效，请换一个"
    try:
        request_body = await request.body()
        request_parse_body = json.loads(request_body.decode("utf-8"))
        print(f"request_parse_body is {request_parse_body}")
        # 获取类型
        share_type = request_parse_body.get("share_type")
        share_name = request_parse_body.get("share_name")
        share_url = request_parse_body.get("share_url")
        # share_passsword = request_parse_body.get("share_password", "")
        if share_type == "baidu":
            baidu_operator = BaiduController()
            dict_p = {
                "shareurl": share_url,
                "savepath": "百度分享资源",
                "taskname": share_name,
                "share_type": "baidu"
                # "share_password":share_passsword,
            }
            res = baidu_operator.save_and_share_file(dict_p)
            print(f"百度，分享的结果为 {res}")
            if res["code"] == 200:
                return {"message": res["data"]}
            else:
                return {"message": share_url}
        if share_type == "quark":
            quark_operator = QuarkController()
            dict_p = {
                "shareurl": share_url,
                "savepath": "夸克分享资源",
                "taskname": share_name,
                "share_type": "quark"
            }
            res = quark_operator.save_file_and_get_share_url(dict_p)
            if res["code"] == 200:
                return {"message": res["data"]}
            else:
                return {"message": share_url}
    except Exception as e:
        print(f"Error: {e}")
        return {"message": share_url}


@app.post("/update_config")
async def update_config(request: Request):
    try:
        request_body = await request.body()
        request_parse_body = json.loads(request_body.decode("utf-8"))

        config_type = request_parse_body.get("config_type")
        cookie_value = request_parse_body.get("cookie_value")

        # 这里需要实现配置文件更新逻辑
        # 可以调用 YmlOperation 类的 update_config 方法
        # 示例伪代码：
        yml_op = YmlOperation()
        yml_op.update_config({config_type: cookie_value})

        return {"code": 200, "message": "配置更新成功"}
    except Exception as e:
        print(f"更新配置出错: {e}")
        return {"code": 500, "message": "配置更新失败"}


@app.post("/check_valid")
async def check_valid(request: Request):
    try:
        request_body = await request.body()
        request_parse_body = json.loads(request_body.decode("utf-8"))
        print(f"request_parse_body is {request_parse_body}")
        if request_parse_body.get("url") is None:
            return True
        else:
            share_url = request_parse_body.get("url")
            print(f"share_url is {share_url}")
            share_type = request_parse_body.get("share_type")
            print(f"share_type is {share_type}")
            baidu_operator = BaiduController()
            quark_operator = QuarkController()
            if share_type == "quark":
                res = quark_operator.check_resource_valid(share_url)
                return res
            if share_type == "baidu":
                res = baidu_operator.check_resource_valid(share_url)
                print(f"百度，分享的结果为 {res}")
                return res
    except Exception as e:
        print(f"Error: {e}")
        return True


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
