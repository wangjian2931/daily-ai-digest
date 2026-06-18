# daily-ai-digest

自动抓取国际物流 / 货代 / EPC 工程物流资讯，用 DeepSeek 生成中文日报，通过 Buttondown 发送邮件，并发布 GitHub Pages 落地页。

## 微信分享链接

https://wangjian2931.github.io/daily-ai-digest/

好友在微信里点开即可：
- 查看今日 AI 动态预览
- 在页面底部填写邮箱订阅（页面本身无需 VPN）
- 去邮箱点击确认后即可每天自动收信

---

## 首次配置 GitHub Pages（只需做一次）

1. 打开 https://github.com/wangjian2931/daily-ai-digest/settings/pages
2. **Build and deployment → Source** 选 **GitHub Actions**
3. 保存

---

## 推送代码并发布

```powershell
cd "C:\Wang Jian's files待转新机\cursor folder\daily-ai-digest"
git add .
git commit -m "add landing page for wechat sharing"
git push
```

然后：**Actions → Daily AI Digest → Run workflow**

成功后访问：https://wangjian2931.github.io/daily-ai-digest/

---

## GitHub Secrets

Settings → Secrets and variables → Actions：

- `DEEPSEEK_API_KEY`
- `BUTTONDOWN_API_KEY`

---

## 本地测试

```powershell
pip install -r requirements.txt
$env:DEEPSEEK_API_KEY = "你的key"
$env:BUTTONDOWN_API_KEY = "你的key"
$env:SEND_MODE = "draft"
python scripts/generate_digest.py
```

生成结果在 `docs/index.html` 和 `docs/previews/`。

---

## 自定义落地页

编辑 `config/site.yaml`：

- `title` / `tagline` / `description`：标题与微信卡片描述
- `buttondown_username`：你的 Buttondown 用户名
- `base_url`：GitHub Pages 地址
- `og_image`：微信卡片图片（建议 PNG，≥300×300）

替换 `docs/assets/og-cover.png` 可自定义微信分享缩略图。

---

## 修改信息源

编辑 `config/sources.yaml` 中的 RSS 列表。
