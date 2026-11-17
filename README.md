<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="xiaosang AI图集 — 22 个系列、3,666 张作品、1,488 个帖子汇于一处">
</p>

<p align="center">
  <a href="https://xiaosang.cc/xiaosang-gallery/">▶ 在线浏览 Browse Online</a>
  ·
  <a href="https://github.com/holynova/xiaosang-gallery">GitHub 仓库</a>
</p>

xiaosang AI图集把作品集里分散的图片项目汇到一个画廊：22 个系列、3,666 张图片、1,488 个帖子。按分组筛选、全屏滑览、本地点赞、单图下载，每个系列还附可复制的 Prompt 模板和生成 Skill。

xiaosang Gallery gathers the portfolio's scattered image projects into one gallery: 22 collections, 3,666 images, 1,488 posts. Filter by group, swipe through full-screen artwork, save local favorites, download individual files — each collection also ships a copyable prompt template and a generation skill.

## 截图 / Screenshots

<p align="center">
  <img src="./assets/readme/screenshot-mobile.png" width="300" alt="手机端瀑布流：纸上旅行、山河入版、农民画与印章、英雄联名概念等帖子">
</p>

## 功能 / Features

- **22 个系列**：按源站项目归类，系列标题下可筛选分组；系列总览见站内 `overview.html`。
- **帖子浏览**：成套作品按帖组织，每帖至多 20 张；打开帖子后上下切换帖子、左右切换组内图片（323 个多图帖）。
- **全屏滑览**：点开图片全屏查看，滑动切图。
- **本地点赞**：点赞按单张保存在本机。
- **单图下载**：点击下载后才读取原始或发布文件；1,532 张为已核实的原图，2,134 张保持源站发布文件字节。
- **Prompt 模板与 Skill**：每个系列一页生成说明（`skills/`，22 个 Skill 包），含可复制的 Prompt 模板。
- **按需加载**：首页先生成覆盖首屏的静态帖子，帖子索引、分系列列表、搜索、组内图片数据均分别按需加载。

## 系列 / Collections

| 系列 | 图片 | 帖子 | 系列 | 图片 | 帖子 |
| --- | ---: | ---: | --- | ---: | ---: |
| 山河入版（套色木刻） | 185 | 22 | 撕标签 · Wander | 137 | 8 |
| 纸上旅行（纸纹水粉） | 60 | 7 | 画风图谱 | 369 | 27 |
| 农民画与印章 | 321 | 44 | 上海穿墙图册 | 9 | 1 |
| 英雄联名概念 | 205 | 38 | 印刷图鉴 | 25 | 8 |
| 知识漫画 | 121 | 121 | 游戏画风转译 | 48 | 3 |
| 听见画面 | 60 | 60 | 课本插画 | 209 | 109 |
| 半透明玩具卫士 | 20 | 3 | 导演与机车 | 100 | 7 |
| 游戏真人化 | 67 | 6 | AI 图片画廊 | 951 | 951 |
| 创世纪变奏 | 40 | 6 | 文物数字图鉴 | 195 | 13 |
| 橡胶戳艺术 | 350 | 22 | 玉雕扑克牌 | 108 | 22 |
| 城市印记 | 40 | 4 | City Pop 城市画册 | 46 | 6 |

以源站作品数据为准；页面图标、截图、缩略图衍生件不重复入库。播客漫画不在此 22 个系列内。

## 本地运行 / Run Locally

直接打开 `index.html` 即可浏览；或起静态服务器：

```bash
python3 -m http.server 8780 --bind 127.0.0.1
# 打开 http://127.0.0.1:8780/
```

更新数据（需要 Pillow、curl；图片与迁移缓存目录由 Git 忽略）：

```bash
python3 scripts/migrate_full.py scripts/inventory.json
python3 scripts/build_site.py
python3 scripts/build_skills.py
npm run build     # 生成 dist/
npm run preview   # 预览 dist/
```

[迁移清单与本地素材要求](docs/catalog.md) · [加载基准与优化](PERFORMANCE.md)

## 技术 / Tech

- 零框架：原生 HTML/CSS/JavaScript + 瀑布流布局（`src/masonry.js`）。
- 数据分片：每系列的图片数据拆成多个 `data/<系列>-N.js`，按需加载；原始或发布图 5.64 GiB，AVIF/WebP 展示层 2.07 GiB。
- 图标使用 Lucide Static 1.73.0（见 `vendor/lucide.LICENSE`）。

```
index.html          画廊首页
overview.html       系列总览
gallery.js/css      画廊逻辑与样式
src/masonry.js      瀑布流布局
data/               分系列图片数据（按需加载）
scripts/            迁移、建站、Skill 生成、性能测量
skills/             22 个系列的生成 Skill 包
```

## English

**xiaosang Gallery** is a single gallery for the portfolio's image projects — 22 collections, 3,666 images, 1,488 posts, counted from the source sites (page icons, screenshots, and thumbnail derivatives are not double-counted; the podcast-comics series is excluded).

- **Browse**: collections group posts; open a post to swipe between posts vertically and images horizontally (323 multi-image posts, max 20 images each).
- **Favorites & downloads**: likes are saved per image locally; originals are fetched only when you click download (1,532 verified originals, 2,134 files kept byte-identical to the source release).
- **Reusable prompts**: each collection ships a generation skill (`skills/`, 22 packages) with a copyable prompt template.
- **Performance**: the homepage pre-renders static above-the-fold posts; indexes, lists, search, and image data load on demand. See [PERFORMANCE.md](PERFORMANCE.md) for benchmarks.
- **Run it**: open `index.html`, or `python3 -m http.server 8780`. Zero frameworks — vanilla HTML/CSS/JS with a masonry layout.
