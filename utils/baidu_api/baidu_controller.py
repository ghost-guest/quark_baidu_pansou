from utils.baidu_api.baidu_api import Network
import functools
import os
from utils.yml_utils.yml_operation import YmlOperation
import re
from typing import Any, Union, Tuple, Callable, List, Optional
import string
import random
from datetime import datetime
from utils.module import DatabaseManager


# 预编译正则表达式
SHARE_ID_REGEX = re.compile(r'"shareid":(\d+?),"')
USER_ID_REGEX = re.compile(r'"share_uk":"(\d+?)","')
FS_ID_REGEX = re.compile(r'"fs_id":(\d+?),"')
SERVER_FILENAME_REGEX = re.compile(r'"server_filename":"(.+?)","')
ISDIR_REGEX = re.compile(r'"isdir":(\d+?),"')
INVALID_CHARS = r'<>|*?\:'

def config_hot_reload(func):
    """配置热加载装饰器"""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, "_check_config_update"):
            self._check_config_update()
        return func(self, *args, **kwargs)

    return wrapper


class BaiduController:
    """
    百度相关操作类
    """

    def __init__(self):
        self.yml = YmlOperation()
        self.config = self.yml.load_config()
        self.config_path = self.yml.config_path
        self.config_mtime = os.path.getmtime(self.config_path)
        self.headers = self.config["BAIDU_HEADERS"]
        self.base_url = self.config["BAIDU_BASE_URL"]
        self.network = Network(self.headers, self.base_url)
        self.db_manager = DatabaseManager()
        self.conn = self.db_manager.get_connection()
        self.db_cursor = self.conn.cursor()
        bdstoken = self.network.get_bdstoken()
        self.network.bdstoken = bdstoken

    @config_hot_reload
    def extract_bdstoken_from_cookie(self, cookie: str) -> str:
        """
        从 Cookie 字符串中提取 bdstoken 值

        Args:
            cookie (str): Cookie 字符串

        Returns:
            str: 提取到的 bdstoken 值，如果未找到则返回空字符串
        """
        try:
            # 拆分 cookie 字符串
            cookies_dict = dict(map(lambda item: item.split('=', 1), filter(None, cookie.split(';'))))
            # 提取 bdstoken 值
            bdstoken = cookies_dict.get('bdstoken', '')
            return bdstoken
        except Exception as e:
            print(f"从 Cookie 提取 bdstoken 失败: {e}")
            return ""

    def _check_config_update(self):
        """检查配置文件是否更新"""
        current_mtime = os.path.getmtime(self.config_path)
        if current_mtime > self.config_mtime:
            self._reload_config()
            self.config_mtime = current_mtime

    def _reload_config(self):
        """重新加载配置文件"""
        self.yml = YmlOperation()
        self.config = self.yml.load_config()
        self.headers = self.config.get('BAIDU_HEADERS', "BAIDU_HEADERS")
        print("配置文件已重新加载")


    def normalize_link(self, url_code: str) -> str:
        """
            预处理链接至标准格式。

            :param url_code: 需要处理的的原始链接格式
            :return: 返回标准格式：链接+空格+提取码
            """
        # 升级旧链接格式
        normalized = url_code.replace("share/init?surl=", "s/1")
        # 替换掉 ?pwd= 或 &pwd= 为空格
        normalized = re.sub(r'[?&]pwd=', ' ', normalized)
        # 替换掉提取码字样为空格
        normalized = re.sub(r'提取码*[：:]', ' ', normalized)
        # 替换 http 为 https，顺便处理掉开头没用的文字
        normalized = re.sub(r'^.*?(https?://)', 'https://', normalized)
        # 替换连续的空格
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized

    @config_hot_reload
    def handle_create_dir(self, folder_name: str):
        """新建目录。如果目录已存在则不新建，否则会建立一个带时间戳的空目录"""
        result = self.network.get_dir_list(f'/{folder_name}')
        print(f"新建目录的为 {folder_name}")
        print(f"查询目录的结果 {result}")
        return_code = {"errno": 0}
        # 如果 result 为错误代码数字，代表目标目录不存在
        if folder_name and isinstance(result, int):
            return_code = self.network.create_dir(folder_name)
        if return_code["errno"] != 0:
            print(f"新建目录 {folder_name} 失败")
        else:
            print(f"新建目录 {folder_name} 成功")
        return return_code

    @config_hot_reload
    def update_cookie(self, bdclnd: str, cookie: str) -> str:
        """
        更新 cookie 字符串，以包含新的 BDCLND 值。

        :param bdclnd: 新的 BDCLND 值
        :param cookie: 当前的 cookie 字符串
        :return: 返回新 cookie 字符串
        """
        # 拆分 cookie 字符串到字典。先用 ; 分割成列表，再用 = 分割出键和值
        cookies_dict = dict(map(lambda item: item.split('=', 1), filter(None, cookie.split(';'))))
        # 在 cookie 字典中，更新或添加 BDCLND 的值
        cookies_dict['BDCLND'] = bdclnd
        # 从更新后的字典重新构建 cookie 字符串
        updated_cookie = ';'.join([f'{key}={value}' for key, value in cookies_dict.items()])

        return updated_cookie

    @config_hot_reload
    def verify_link(self, url: str, password: str):
        """验证链接有效性，验证通过返回转存所需参数列表"""
        # 对于有提取码的链接先验证提取码，试图获取更新 bdclnd
        if password:
            bdclnd = self.network.verify_pass_code(url, password)
            # 如果 bdclnd 是错误代码，直接返回
            print(f"verify_link验证提取码 {password} 的结果 {bdclnd}")
            if isinstance(bdclnd, int):
                return bdclnd

            # 更新 bdclnd 到 cookie
            self.network.headers['Cookie'] = self.update_cookie(bdclnd, self.network.headers['Cookie'])


        # 直接访问没有提取码的链接，或更新 bdclnd 后再次访问，获取转存必须的 3 个参数
        response = self.network.get_transfer_params(url)
        # print(f"打印访问的结果 {response}")
        # 这里不考虑网络异常了，假设请求一定会返回页面内容，对其进行解析
        return self.parse_response(response)

    @config_hot_reload
    def parse_response(self,response: str) -> Union[List[str], int]:
        """
        验证提取码通过后，再次访问网盘地址，此函数解析返回的页面源码并提取所需要参数。
        shareid_list 和 user_id_list 只有一个值，fs_id_list 需要完整返回

        :param response: 响应内容
        :return: 没有获取到足够参数时，返回错误代码 -1；否则返回三个参数的列表
        """
        shareid_list = SHARE_ID_REGEX.findall(response)
        user_id_list = USER_ID_REGEX.findall(response)
        fs_id_list = FS_ID_REGEX.findall(response)
        server_filename_list = SERVER_FILENAME_REGEX.findall(response)
        isdir_list = ISDIR_REGEX.findall(response)
        if not all([shareid_list, user_id_list, fs_id_list, server_filename_list, isdir_list]):
            return -1

        return [shareid_list[0], user_id_list[0], fs_id_list, list(dict.fromkeys(server_filename_list)), isdir_list]

    @config_hot_reload
    def creat_user_dir(self, folder_name: str):
        """建立用户指定目录，返回完整路径。目录名从原始输入取，函数为 custom_mode 专用"""

        # 建立自定义目录，如果没有指定则用行数代替
        custom_folder = self.generate_code(10)
        folder_name = f'{folder_name}/{custom_folder}'
        # 此处用替换处理目标目录名非法字符，不报错了
        folder_name = folder_name.translate(str.maketrans({char: '_' for char in INVALID_CHARS}))
        res = self.handle_create_dir(folder_name)

        return folder_name, res

    @config_hot_reload
    def save_and_share_file(self, task,save_path="百度分享资源"):
        """
        转存文件
        :param task:   需要包含 shareurl , share_type, share_password
        :return:
        """
        # cookie
        cookie = self.config.get("baidu_cookie")
        self.headers["Cookie"] = cookie
        # 从文本链接控件获取全部链接，清洗并标准化链接
        link = self.normalize_link(task["shareurl"])
        #获取 bdstoken 相关逻辑
        bdstoken = self.network.get_bdstoken()
        self.network.bdstoken = bdstoken

        # 创建转存目录，存在则不创建
        self.handle_create_dir(save_path)
        # 跳过非网盘链接
        if 'https://pan.baidu.com/' not in link:
            print(f'不支持的链接：{link}')
            return {"code": -1, "message": "不支持的链接"}
        else:
            # 转存逻辑 验证链接是否有效，返回的数字为错误代码，反之返回参数列表
            if not task.get("share_password"):
                task["share_password"] = task["shareurl"].split('pwd=')[-1]
            result = self.verify_link(task["shareurl"], task.get("share_password"))
            # 如果开启检查模式，插入检查结果，然后结束
            print(f"打印连接校验的结果 {result}")
            if isinstance(result, list):
                print(f"传递给 transfer_file 的参数: {result}")
                print(f"bdstoken 状态: {self.network.bdstoken}")
                print(f"当前 Cookie: {self.network.headers.get('Cookie')}")
                # 在获取一遍 bdstoken
                bdstoken = self.network.get_bdstoken()
                self.network.bdstoken = bdstoken
                # 创建转存目录，避免相同的而导致的转存失败
                folder_name, res_zc_dir = self.creat_user_dir(save_path)
                print(f"创建目录结果: {res_zc_dir}")
                print(f"传递给 transfer_file 的参数: {result}")
                print(f"目录名称: {folder_name}")
                print(f"bdstoken 状态: {self.network.bdstoken}")
                params_list = [result[0], result[1], result[2]]
                res_save = self.network.transfer_file(params_list, folder_name)
                print(f"转存成功result is {res_save}")
                if res_save["errno"] == 0:
                    print(f"转存成功")
                    baidu_record_time = int(datetime.now().timestamp())
                    # 插入文件记录并获取ID
                    try:
                        record_id = self.db_manager.insert_file_record(res_zc_dir["fs_id"],
                                                                       res_zc_dir["name"], task["share_type"],
                                                                       baidu_record_time)
                        print(f"插入的文件记录ID: {record_id}")
                    except Exception as e:
                        print(f"插入文件记录失败: {e}")
                    # 分享文件
                    res_share = self.share_file(res_zc_dir)
                    print(f"分享结果： {res_share}")
                    return {"code": 200, "msg": "转存成功", "data": res_share}
                else:
                    return {"code":500, "msg":"转存失败", "data": res_save}
            return {"code": -1, "message": "链接无效"}

    def generate_code(self, num = 4) -> str:
        """
        生成一个四位的随机提取码，包含大小写字母和数字。

        :return: 随机提取码
        """
        # 包含大小写字母和数字
        characters = string.ascii_letters + string.digits
        # 随机选择四个字符
        code = ''.join(random.choice(characters) for _ in range(num))

        return code

    @config_hot_reload
    def share_file(self, info):
        """执行分享操作并记录结果"""
        # 插入要分享的文件或文件夹到链接输入框，对文件夹加入 "/" 标记来区别
        is_dir = "/"
        filename = f"{info['name']}{is_dir}"
        msg = f'目录：{filename}' if is_dir else f'文件：{filename}'
        # 处理提取码
        password = self.generate_code()
        # 发送创建分享请求
        r = self.network.create_share(info['fs_id'], "0", password)
        print(f"创建分享结果： {r}")
        if isinstance(r, str):
            result = f'分享成功：{r}?pwd={password} {msg}'
        else:
            result = f'分享失败：错误代码（{r}） {msg}'
        print(f"分享的结果 result is {result}")
        return f"{r}?pwd={password}"

    @config_hot_reload
    def delete_file(self, fs_id_name):
        """删除转存的文件，节省空间"""
        cookie = self.config.get("baidu_cookie")
        self.headers["Cookie"] = cookie
        print(f"删除前的bdstoken的值： {self.network.bdstoken}")
        if not self.network.bdstoken or not isinstance(self.network.bdstoken, str):
            self.network.bdstoken = self.network.get_bdstoken()
        res = self.network.delete_file(fs_id_name)
        print(f"删除结果： {res}")
        if res["errno"] == 0:
            return True
        return False

    @config_hot_reload
    def check_resource_valid(self, share_url):
        """检查资源是否有效"""
        try:
            # 从百度链接上获取password
            password = share_url.split('pwd=')[-1]
            print(f"从百度链接上获取的密码为： {password}")
            cookie = self.config.get("baidu_cookie")
            self.headers["Cookie"] = cookie
            result = self.verify_link(share_url,password)
            # 如果开启检查模式，插入检查结果，然后结束
            print(f"资源有效性返回的结果： {result}")
            if isinstance(result, int):
                return False
            elif isinstance(result, list):
                return True
        except Exception as e:
            print(f"Error: {e}")
            return True
