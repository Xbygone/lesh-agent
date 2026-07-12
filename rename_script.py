import os

files = ['updater.py', 'release.py', 'README.md', 'README_tr.md']
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    content = content.replace('yerel-agent', 'lesh-agent')
    content = content.replace('Xbygone/lesh-agent', 'Xbygone/lesh-agent') # Safety
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)

logo_html = '<p align="center">\n  <img src="assets/logo.jpg" width="250" alt="Lesh Logo">\n</p>\n\n'

for f in ['README.md', 'README_tr.md']:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if '<p align="center">' not in content:
        with open(f, 'w', encoding='utf-8') as file:
            file.write(logo_html + content)

print('Updated files successfully!')
