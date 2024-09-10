"""
lanzou云api有变，lanzou_api这个库没来得及更新，会导致需要密码的分享报错，不需要密码的正常下载，下面是临时patch

site_packages/lanzou/api/core.py中的get_file_info_by_url替换为

    def get_file_info_by_url(self, share_url, pwd='') -> FileDetail:
        if not is_file_url(share_url):  # 非文件链接返回错误
            return FileDetail(LanZouCloud.URL_INVALID, pwd=pwd, url=share_url)

        first_page = self._get(share_url)  # 文件分享页面(第一页)
        if not first_page:
            return FileDetail(LanZouCloud.NETWORK_ERROR, pwd=pwd, url=share_url)

        if "acw_sc__v2" in first_page.text:
            # 在页面被过多访问或其他情况下，有时候会先返回一个加密的页面，其执行计算出一个acw_sc__v2后放入页面后再重新访问页面才能获得正常页面
            # 若该页面进行了js加密，则进行解密，计算acw_sc__v2，并加入cookie
            acw_sc__v2 = calc_acw_sc__v2(first_page.text)
            self._session.cookies.set("acw_sc__v2", acw_sc__v2)
            logger.debug(f"Set Cookie: acw_sc__v2={acw_sc__v2}")
            first_page = self._get(share_url)  # 文件分享页面(第一页)
            if not first_page:
                return FileDetail(LanZouCloud.NETWORK_ERROR, pwd=pwd, url=share_url)

        first_page = remove_notes(first_page.text)  # 去除网页里的注释
        if '文件取消' in first_page or '文件不存在' in first_page:
            return FileDetail(LanZouCloud.FILE_CANCELLED, pwd=pwd, url=share_url)

        # 这里获取下载直链 304 重定向前的链接
        try:
            if 'id="pwdload"' in first_page or 'id="passwddiv"' in first_page:  # 文件设置了提取码时
                if len(pwd) == 0:
                    return FileDetail(LanZouCloud.LACK_PASSWORD, pwd=pwd, url=share_url)  # 没给提取码直接退出
                # data : 'action=downprocess&sign=AGZRbwEwU2IEDQU6BDRUaFc8DzxfMlRjCjTPlVkWzFSYFY7ATpWYw_c_c&p='+pwd,
                sign = re.search(r"skdklds = '(\w+?)'", first_page).group(1)
                kd = re.search(r"kdns =(\d+?);", first_page).group(1)
                file_id = re.search(r"file=(\d+?)'", first_page).group(1)
                post_data = {'action': 'downprocess', 'sign': sign, 'p': pwd, 'kd': kd}
                link_info = self._post(self._host_url + f'/ajaxm.php?file={file_id}', post_data)  # 保存了重定向前的链接信息和文件名
                second_page = self._get(share_url)  # 再次请求文件分享页面，可以看见文件名，时间，大小等信息(第二页)
                if not link_info or not second_page.text:
                    return FileDetail(LanZouCloud.NETWORK_ERROR, pwd=pwd, url=share_url)
                link_info = link_info.json()
                second_page = remove_notes(second_page.text)
                # 提取文件信息
                f_name = link_info['inf'].replace("*", "_")
                f_size = re.search(r'大小.+?(\d[\d.,]+\s?[BKM]?)<', second_page)
                f_size = f_size.group(1).replace(",", "") if f_size else '0 M'
                f_time = re.search(r'class="n_file_infos">(.+?)</span>', second_page)
                f_time = time_format(f_time.group(1)) if f_time else time_format('0 小时前')
                f_desc = re.search(r'class="n_box_des">(.*?)</div>', second_page)
                f_desc = f_desc.group(1) if f_desc else ''
            else:  # 文件没有设置提取码时,文件信息都暴露在分享页面上
                para = re.search(r'<iframe.*?src="(.+?)"', first_page).group(1)  # 提取下载页面 URL 的参数
                # 文件名位置变化很多
                f_name = re.search(r"<title>(.+?) - 蓝奏云</title>", first_page) or \
                         re.search(r'<div class="filethetext".+?>([^<>]+?)</div>', first_page) or \
                         re.search(r'<div style="font-size.+?>([^<>].+?)</div>', first_page) or \
                         re.search(r"var filename = '(.+?)';", first_page) or \
                         re.search(r'id="filenajax">(.+?)</div>', first_page) or \
                         re.search(r'<div class="b"><span>([^<>]+?)</span></div>', first_page)
                f_name = f_name.group(1).replace("*", "_") if f_name else "未匹配到文件名"
                # 匹配文件时间，文件没有时间信息就视为今天，统一表示为 2020-01-01 格式
                f_time = re.search(r'>(\d+\s?[秒天分小][钟时]?前|[昨前]天\s?[\d:]+?|\d+\s?天前|\d{4}-\d\d-\d\d)<', first_page)
                f_time = time_format(f_time.group(1)) if f_time else time_format('0 小时前')
                # 匹配文件大小
                f_size = re.search(r'大小.+?(\d[\d.,]+\s?[BKM]?)<', first_page)
                f_size = f_size.group(1).replace(",", "") if f_size else '0 M'
                f_desc = re.search(r'文件描述.+?<br>\n?\s*(.*?)\s*</td>', first_page)
                f_desc = f_desc.group(1) if f_desc else ''
                first_page = self._get(self._host_url + para)
                if not first_page:
                    return FileDetail(LanZouCloud.NETWORK_ERROR, name=f_name, time=f_time, size=f_size, desc=f_desc,
                                      pwd=pwd, url=share_url)
                first_page = remove_notes(first_page.text)
                # 一般情况 sign 的值就在 data 里，有时放在变量后面
                file_id = re.search(r"file=(\d+?)'", first_page).group(1)
                sign = re.search(r"'sign':(.+?),", first_page).group(1)
                ajaxdata = re.search(r"var ajaxdata\s*=\s*'(.*)';", first_page).group(1)
                ciucjdsdc = re.search(r"var ciucjdsdc\s*=\s*'(.*)';", first_page).group(1)
                aihidcms = re.search(r"var aihidcms\s*=\s*'(.*)';", first_page).group(1)
                kd = 1
                if len(sign) < 20:  # 此时 sign 保存在变量里面, 变量名是 sign 匹配的字符
                    sign = re.search(rf"var {sign}\s*=\s*'(.+?)';", first_page).group(1)
                post_data = {
                    'action': 'downprocess', 
                    'signs': ajaxdata, 
                    'sign': sign, 
                    'websign': ciucjdsdc, 
                    'websignkey': aihidcms,
                    'ves': 1,
                    'kd': 1,
                }
                # 某些特殊情况 share_url 会出现 webpage 参数, post_data 需要更多参数
                # https://github.com/zaxtyson/LanZouCloud-API/issues/74
                # https://github.com/zaxtyson/LanZouCloud-API/issues/81
                if "?webpage=" in share_url:
                    ajax_data = re.search(r"var ajaxdata\s*=\s*'(.+?)';", first_page).group(1)
                    web_sign = re.search(r"var a?websigna?\s*=\s*'(.+?)';", first_page).group(1)
                    web_sign_key = re.search(r"var c?websignkeyc?\s*=\s*'(.+?)';", first_page).group(1)
                    post_data = {'action': 'downprocess', 'signs': ajax_data, 'sign': sign, 'ves': 1,
                                 'websign': web_sign, 'websignkey': web_sign_key}
                link_info = self._post(self._host_url + f'/ajaxm.php?file={file_id}', post_data)
                if not link_info:
                    return FileDetail(LanZouCloud.NETWORK_ERROR, name=f_name, time=f_time, size=f_size, desc=f_desc,
                                      pwd=pwd, url=share_url)
                link_info = link_info.json()
        except AttributeError as e:  # 正则匹配失败
            logger.error(e)
            return FileDetail(LanZouCloud.FAILED)

        # 这里开始获取文件直链
        if link_info['zt'] != 1:  # 返回信息异常，无法获取直链
            return FileDetail(LanZouCloud.FAILED, name=f_name, time=f_time, size=f_size, desc=f_desc, pwd=pwd,
                              url=share_url)

        fake_url = link_info['dom'] + '/file/' + link_info['url']  # 假直连，存在流量异常检测
        download_page = self._get(fake_url, allow_redirects=False)
        if not download_page:
            return FileDetail(LanZouCloud.NETWORK_ERROR, name=f_name, time=f_time, size=f_size, desc=f_desc,
                              pwd=pwd, url=share_url)
        download_page.encoding = 'utf-8'
        download_page_html = remove_notes(download_page.text)
        if '网络异常' not in download_page_html:  # 没有遇到验证码
            direct_url = download_page.headers['Location']  # 重定向后的真直链
        else:  # 遇到验证码，验证后才能获取下载直链
            try:
                file_token = re.findall("'file':'(.+?)'", download_page_html)[0]
                file_sign = re.findall("'sign':'(.+?)'", download_page_html)[0]
                check_api = 'https://vip.d0.baidupan.com/file/ajax.php'
                post_data = {'file': file_token, 'el': 2, 'sign': file_sign}
                sleep(2)  # 这里必需等待2s, 否则直链返回 ?SignError
                resp = self._post(check_api, post_data)
                direct_url = resp.json()['url']
                if not direct_url:
                    return FileDetail(LanZouCloud.CAPTCHA_ERROR, name=f_name, time=f_time, size=f_size, desc=f_desc,
                                      pwd=pwd, url=share_url)
            except IndexError as e:
                logger.error(e)
                return FileDetail(LanZouCloud.FAILED)

        f_type = f_name.split('.')[-1]
        return FileDetail(LanZouCloud.SUCCESS,
                          name=f_name, size=f_size, type=f_type, time=f_time,
                          desc=f_desc, pwd=pwd, url=share_url, durl=direct_url)

"""

import os
import time
from lanzou.api import LanZouCloud
from typing import Dict, List


def isUrl(token: str) -> bool:
    return (len(token) >= 11) and (token.encode().isalnum())


def parseLine(
    line: str,
    separator: str=' ：;；:',
) -> List[Dict[str, str]]:
    line = line.strip('\n')
    if len(line) == 0:
        return []
    
    for s in separator:
        line = line.replace(s, '|')
        
    tokens = line.split('|') 
    date = tokens[0][:-2]
    
    buffer = list()
    idx_url = list()
    items = list()
    i = 0
    
    for token in tokens:
        if len(token) == 0:
            continue
        
        if isUrl(token):
            idx_url.append(i)
            
        buffer.append(token)
        i += 1
        
    for i in idx_url:
        item = dict()
        item['date'] = date
        item['title'] = buffer[i-1]
        item['url'] = buffer[i]
        
        if (i != len(buffer) - 1) and (buffer[i+1] == '密码'):
            item['pwd'] = buffer[i+2]
            
        items.append(item)
        
    return items


def callback(file_name):
    print(f'Downloaded to {file_name}')
    
    
def downloadItem(lzy: LanZouCloud, item: Dict, path: str) -> int:
    if 'pwd' in item:
        pwd = item['pwd']
    else:
        pwd = ''
        
    return lzy.down_file_by_url(
        f'https://lanzoui.com/{item["url"]}',
        pwd=pwd,
        save_path=path,
        downloaded_handler=callback,
    )


def downloadItems(
    items: List[Dict],
    paths: Dict={
        'python': '\\\\Meow\\Share\\New_folder\\python学习材料',
        'wp': '\\\\Meow\\Share\\New_folder\\python学习材料',
        'jm': '\\\\Meow\\Share\\New_folder\\JM内学习资料',
    },
    misc_path: str='\\\\Meow\\Share\\New_folder\\gauss学习资料',
    interval: float=5,
):
    lzy = LanZouCloud()
    failed_items = list()
    
    for item in items:
        is_misc = True
        time.sleep(interval)
        
        for category, path in paths.items():
            if item['title'].lower()[:len(category)] == category:
                status = downloadItem(lzy, item, path)
                is_misc = False
                break
            
        if is_misc:
            status = downloadItem(lzy, item, misc_path)
            
        if status == LanZouCloud.FAILED:
            failed_items.append(item)
            print('failed: ', item)
            
    return failed_items

        
config_fn = '\\\\Meow\\Share\\New_folder\\特殊秘籍20240405.txt'
items = list()

with open(config_fn, 'r', encoding='utf-8') as f:
    for line in f.readlines()[16:]:
        items += parseLine(line)
        
# failed_items = downloadItems(items)
# failed_items
