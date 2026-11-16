# xiaosang AI图集

把作品集分散的图片汇到一个画廊，共 22 个系列、3,666 张图片和 1,488 个帖子。支持按分组筛选、全屏滑览、本地点赞、单图下载，以及可复制的 Prompt 模板和生成 Skill。

A gallery of 3,666 images across 22 collections. Browse grouped posts, swipe through full-screen artwork, save local favorites, download individual files, and explore reusable prompts and generation skills.

![xiaosang AI图集手机预览](assets/screenshot.png)

## 在线体验 / Live demo

- [Cloudflare Demo](https://xiaosang.cc/xiaosang-gallery/)
- [GitHub Repo](https://github.com/holynova/xiaosang-gallery)

<img src="assets/qr.png" width="160" alt="扫描二维码打开 xiaosang AI图集">

## 本地运行 / Run locally

```sh
python3 -m pip install Pillow
python3 scripts/migrate_full.py scripts/inventory.json
python3 scripts/build_skills.py
npm run build
npm run preview
```

[迁移清单与本地素材要求](docs/catalog.md) · [加载基准与优化](PERFORMANCE.md)

## 发布 / Deploy

```sh
npm run build
node /path/to/holynova.github.io/scripts/stage-cloudflare.mjs "$PWD/dist"
cd /path/to/holynova.github.io
npx --yes wrangler@4.128.0 deploy --config wrangler.jsonc
```

图库从 `main` 构建，纳入作品集的 `xiaosang-portfolio` Worker。图片与打包产物由 Git 忽略。
