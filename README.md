# daily-ai-digest

自动抓取 AI 相关 RSS，用 DeepSeek 生成中文日报，并通过 Buttondown 发送 Newsletter。

## 本地测试

```powershell
cd daily-ai-digest
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

$env:DEEPSEEK_API_KEY = "你的key"
$env:BUTTONDOWN_API_KEY = "你的key"
$env:SEND_MODE = "draft"   # draft=只创建草稿，send=真正发送

python scripts/generate_digest.py
```

## GitHub Secrets

在仓库 Settings → Secrets and variables → Actions 中添加：

- `DEEPSEEK_API_KEY`
- `BUTTONDOWN_API_KEY`

## 修改信息源

编辑 `config/sources.yaml` 中的 RSS 列表即可。
