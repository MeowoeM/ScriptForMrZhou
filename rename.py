import zipfile
import os
from pathlib import Path
import re

path = Path('\\\\Meow\\Share\\New_folder\\python学习材料')
fns = os.listdir(path)

for fn in fns:
    if not fn.endswith('.zip'):
        continue
        
    if '(1)' in fn:
        continue
        
    print(path / fn)
    zip = zipfile.ZipFile(path / fn, 'r')
    password = re.search('\d+', fn).group()
    zip.setpassword(str.encode(password))

    for name in zip.namelist():
        if not name.endswith(('/', '\\')):
            with open(path / os.path.basename(name), 'wb') as f:
                f.write(zip.read(name))
                
            exe = path / name
            pdf = exe.with_suffix('.pdf')
            
            if not os.path.exists(pdf):
                exe.rename(pdf)

    zip.close()