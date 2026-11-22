# Cloudflare Pages 免费托管

gallery.xiaosang.cc 连接本仓库 main，使用 Python 3.12，构建命令为 `python3 -m pip install -r requirements.txt && npm run build:pages`，发布 dist。改网页或在 additions/ 的系列目录中加入图片后推送即可。新图的原图、缩略图、详情图与页面进入同一版本，构建不需要 Cloudflare 密钥。

gallery-media.xiaosang.cc 指向 xiaosang-gallery-media Pages 项目，保存迁移时已有的 media/ 和 originals/。灾难恢复时从历史正式 dist 复制这两个目录，保留下载响应头，用 Wrangler Pages Direct Upload 发布到这个媒体项目。可和 catalog/legacy-media.json 核对文件数及排序后以换行连接的相对路径 SHA-256。日常发布只构建网页仓库。

免费版每个 Pages 站点最多 20,000 个文件，每个文件最多 25 MiB。构建在超出此范围时停止。旧的 /xiaosang-gallery/ 入口由作品集转向新站。
