"""Build the Skill pages and self-contained packages from sampled series."""
from pathlib import Path
from PIL import Image
import html
import json

root=Path(__file__).resolve().parent.parent
catalog=json.loads((root/'.migration/complete.json').read_text())
skills=root/'skills'
skills.mkdir(exist_ok=True)

def document(content):
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>xiaosang AI图集 · Skills</title><link rel="icon" href="../favicon.svg"><link rel="stylesheet" href="../gallery.css"><link rel="stylesheet" href="skills.css"><script defer src="../vendor/lucide.js"></script><script defer src="skills.js"></script></head>
<body><svg id="icons" class="symbol-bank" aria-hidden="true"></svg><main class="page-width skill-page"><a class="back" href="../index.html"><svg class="icon" aria-hidden="true"><use href="#lucide-arrow-left"></use></svg>xiaosang AI图集</a><h1>xiaosang AI图集 · Skills</h1>{content}</main></body></html>'''

def anchor(url,title,css=''):
    return f'<a class="{css}" href="{html.escape(url)}">{html.escape(title)}</a>'
cards=[]
links=[]
labels=['主体','视角与场景','配色与材质']
for series in catalog:
    ident=series['id']
    title=series['title']
    slug='gallery-'+ident
    package=skills/'packages'/slug
    samples=series['works'][:2]
    (package/'assets').mkdir(parents=True,exist_ok=True)
    for work in samples:
        with Image.open(root/work['variants']['detail'][0]) as image:
            image.thumbnail((660,660),Image.Resampling.LANCZOS)
            image.save(package/'assets'/f'{work["id"]}.webp',quality=83)
    template=series['template']
    filled=template
    for label,value in zip(labels,[samples[0]['title'],samples[0]['category'] or '合适的场景',series['style']]):
        filled=filled.replace(f'【{label}】',value)
    references='\n'.join(f'- [{w["title"]}](assets/{w["id"]}.webp)' for w in samples)
    (package/'SKILL.md').write_text(f'''---
name: {slug}
description: 为{title}系列编写{series['style']}提示词，或生成符合该系列技法的图像。适用于明确要求这一系列或该视觉技法的任务。
---

# {title}

## 准备

先确认主体、视角和配色。查看下面的参考图，提取构图、光色和材质特征。将用户提供的事实、题材照片或原文作为内容依据，单独标明用途。

{references}

## 模板

{template}

## 填写示例

{filled}

## 输出

仅要求提示词时返回填好的文本。要求成图时，使用可用的图像生成工具，记录实际输入的提示词。检查主体辨识度、构图和材质，针对实际偏差修改。涉及文物、建筑和知识内容时，校对可验证的事实以及示意或推断标记。

[作品来源]({series['url']})
''')
    links.append(anchor('#'+ident,title,'series-link'))
    pics=''.join(f'<figure><img src="packages/{slug}/assets/{w["id"]}.webp" alt="{html.escape(w["title"])}" loading="lazy"><figcaption>{html.escape(w["title"])}</figcaption></figure>' for w in samples)
    cards.append(f'<section class="skill-card" id="{ident}"><header><div><p>{html.escape(series["style"])}</p><h2>{html.escape(title)}</h2></div>{anchor("packages/"+slug+"/SKILL.md","打开 SKILL.md","skill-file")}</header><div class="skill-body"><p>{html.escape(template)}</p><div class="skill-images">{pics}</div></div></section>')
(skills/'index.html').write_text(document('<nav aria-label="系列">'+''.join(links)+'</nav>'+''.join(cards)))
