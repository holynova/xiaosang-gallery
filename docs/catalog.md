# xiaosang AI图集

汇总作品集里的公开图片类项目，共 22 个系列、3,666 张图片、1,488 个帖子。排除播客漫画。以源站作品数据为准；页面图标、截图、缩略图衍生件不重复入库。

## 本地入口

在项目目录运行 `python3 -m http.server 8780 --bind 127.0.0.1`，打开 http://127.0.0.1:8780/。也可直接打开 index.html。系列总览位于 overview.html。

按源站项目归为系列。系列标题下可筛选分组。成套作品每帖至多二十张，超出时按源站顺序拆帖。独立知识漫画、乐队摄影和无原生图组的作品各自成帖。打开帖子后上下切帖子，左右切组内图。

## 数据与性能

- 323 个多图帖。下载文件中 1,532 张为已核实的原图，2,134 张保持源站发布文件字节。点赞按单张保存在本机。
- 原始或发布图占 5.64 GiB，AVIF/WebP 展示层占 2.07 GiB。图片与迁移缓存目录由 Git 忽略。
- 首页先生成覆盖首屏的静态帖子。首页帖子索引、分系列列表、索引搜索、组内图片数据均分别按需加载。点击下载后才读取原始或发布文件。
- 更新数据时运行 `python3 scripts/migrate_full.py scripts/inventory.json`，再运行 `python3 scripts/build_site.py` 和 `python3 scripts/build_skills.py`。脚本依赖 Pillow、curl。联名图集中现有原图引自本机源项目；其余使用来源清单。
- 图标使用 Lucide Static 1.73.0，许可证见 vendor/lucide.LICENSE。

同条件的 [加载基准与优化结果](../PERFORMANCE.md) 含首屏、高清详情和样式方案对照。

## 迁移清单

| 作品集系列 | 图片 | 帖子 |
| --- | ---: | ---: |
| [山河入版](https://shanhe-gallery.xiaosang.cc/) | 185 | 22 |
| [纸上旅行](https://world-landmarks.xiaosang.cc/) | 60 | 7 |
| [农民画与印章](https://folk-gallery.xiaosang.cc/) | 321 | 44 |
| [英雄联名概念](https://crossover-folk-gallery.xiaosang.cc/) | 205 | 38 |
| [知识漫画](https://xiaosang.cc/concept-atlas/) | 121 | 121 |
| [听见画面](https://xiaosang.cc/rock-in-pictures/) | 60 | 60 |
| [半透明玩具卫士](https://translucent-toy-guard.xiaosang.cc/) | 20 | 3 |
| [游戏真人化](https://elden-ring-liveaction.xiaosang.cc/) | 67 | 6 |
| [创世纪变奏](https://the-creation-variants.xiaosang.cc/) | 40 | 6 |
| [橡胶戳艺术](https://rubber-stamp-world-cities.xiaosang.cc/) | 350 | 22 |
| [城市印记](https://city-stamp.xiaosang.cc/) | 40 | 4 |
| [City Pop 城市画册](https://citypop-shanghai-exploration.xiaosang.cc/) | 46 | 6 |
| [撕标签 · Wander](https://daily-necessities-library.xiaosang.cc/) | 137 | 8 |
| [画风图谱](https://art-style-showcase.xiaosang.cc/) | 369 | 27 |
| [上海穿墙图册](https://shanghai-through-walls.xiaosang.cc/) | 9 | 1 |
| [印刷图鉴](https://print-atlas.xiaosang.cc/) | 25 | 8 |
| [游戏画风转译](https://game-style-transfer-atlas.xiaosang.cc/) | 48 | 3 |
| [课本插画](https://text-book-pics.xiaosang.cc/) | 209 | 109 |
| [导演与机车](https://director-motorcycle-cinema.xiaosang.cc/) | 100 | 7 |
| [AI 图片画廊](https://ai-gallery.xiaosang.cc/) | 951 | 951 |
| [文物数字图鉴](https://wenwu-checkin.xiaosang.cc/) | 195 | 13 |
| [玉雕扑克牌](https://xiaosang.cc/jade-cards-lab/) | 108 | 22 |
