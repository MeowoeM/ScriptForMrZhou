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