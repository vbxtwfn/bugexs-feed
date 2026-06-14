# 不格小说网 JSON Feed

把 m.bugexs.com 的小说内容转成 JSON Feed，免费托管在 GitHub Pages 上。

## 订阅地址（部署后可用）

```
https://你的用户名.github.io/bugexs-feed/feeds/lastupdate.json
https://你的用户名.github.io/bugexs-feed/feeds/monthvote.json
https://你的用户名.github.io/bugexs-feed/feeds/home.json
https://你的用户名.github.io/bugexs-feed/feeds/dayvisit.json
```

## 快速部署（需要 GitHub 账号）

### 第一步：创建 GitHub 仓库

1. 打开 https://github.com/new
2. 仓库名称填：`bugexs-feed`（必须）
3. 选 **Private** 或 **Public** 都可以
4. ⚠️ **不要勾选** "Add a README file"
5. 点 "Create repository"

### 第二步：把代码推上去

在本地终端（Mac/Linux）运行：

```bash
# 克隆刚创建的空仓库（把 YOUR_USERNAME 换成你的 GitHub 用户名）
git clone https://github.com/YOUR_USERNAME/bugexs-feed.git
cd bugexs-feed

# 把本项目的所有文件复制进去（脚本所在目录）
# 如果你在本机操作，直接 cp -r 整个文件夹进来
# 如果在服务器上，可以用 scp 或者直接把文件内容粘贴过来

# 推送
git add .
git commit -m "init"
git push -u origin main
```

### 第三步：启用 GitHub Actions

1. 打开你的仓库页面：https://github.com/YOUR_USERNAME/bugexs-feed
2. 点 **Actions** 标签
3. 看到 "Generate JSON Feeds" 工作流后，点 **Enable workflow**

### 第四步：触发第一次生成

1. 在 Actions 页面点 **Generate JSON Feeds**
2. 点右边 **Run workflow** → 点绿色 **Run workflow** 按钮
3. 等 1-2 分钟完成后，点进去看结果

### 第五步：开启 GitHub Pages

1. 仓库 Settings → Pages
2. **Source** 选：**Deploy from a branch**
3. **Branch** 选：**gh-pages** → `/ (root)` → 点 **Save**
4. 等 2 分钟，访问：
   ```
   https://YOUR_USERNAME.github.io/bugexs-feed/feeds/lastupdate.json
   ```

> 💡 如果提示 404，多等几分钟让 GitHub 部署完成。

## Feed 说明

| 文件 | 说明 |
|------|------|
| `lastupdate.json` | 最近更新（50本） |
| `monthvote.json` | 月推荐榜 |
| `home.json` | 首页轮播 + 最近更新 |
| `dayvisit.json` | 日点击榜 |
| `weekvote.json` | 周推荐榜 |

## 自动更新

GitHub Actions 每 30 分钟自动抓取最新数据并更新页面。

## 阅读 App 支持

支持的工具：
- **静夜小组件**（iOS）- 添加自定义 RSS，填入上面的 URL
- **NetNewsWire**（Mac/iOS）- 免费开源 RSS 阅读器
- **Reeder**（Mac/iOS）- 支持 JSON Feed
- **Fluent Reader**（Windows）- 支持 JSON Feed
- **RSS 阅读器**（Android）- 大多数支持

## 本地运行

```bash
pip install requests beautifulsoup4 -q
python3 bugexs_feed.py                          # 最近更新
python3 bugexs_feed.py -t lastupdate -o feed.json
python3 bugexs_feed.py -t home                  # 首页
```
