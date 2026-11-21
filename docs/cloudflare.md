# Cloudflare 独立站

Cloudflare Pages 连接本仓库的 main，输出目录为 dist。使用 Python 3.12，安装 requirements.txt 后执行 npm run build:pages；可将构建命令设为 `python3 -m pip install -r requirements.txt && npm run build:pages`。在 Pages 绑定 gallery.xiaosang.cc。

图像桶为 xiaosang-gallery-media，公开读取域名为 gallery-media.xiaosang.cc。将 R2_ENDPOINT、R2_ACCESS_KEY_ID、R2_SECRET_ACCESS_KEY 设在 Pages 的生产构建环境。后两项用加密变量，权限限于这个桶的对象读写。预览环境不给生产写凭据。

首次迁移从含 media/ 和 originals/ 的原线上版本 dist 运行 `python3 scripts/pages_media.py /path/to/dist`。脚本检查清单、按校验和复用已上传的对象，完成后写入校验记录。正式构建会通过公开域名检查这份记录。核对首页、缩略图、详情图、下载和旧链接后再切换主站。

日常将图片放入 additions/ 下已存在系列 ID 对应的文件夹后推送。网页构建生成缩略图、详情图和作品条目，并向 R2 补充新增对象。图片 URL 包含内容哈希。改首页样式直接推送 src/gallery.css。
