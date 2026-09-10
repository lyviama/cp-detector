# CP 鑑定器 · CP Detector 🔮

> 真假CP一卦便知 —— 六爻合盤 Web App（小红书 Vibecoding 大赛参赛作品）

**CP Detector** answers the question every shipper has: *"Is this pairing real?"* — using classical Liu Yao (六爻) divination with relationship-aware casting.

## ✨ Features

- 💕 **磕CP占卜**：按关系类型（恋人/暧昧/友情）自动取用神，合盘解卦
- 🎴 **三数起卦**：输入三个数字即可起卦，零学习成本
- 📊 **完整卦理引擎**：纳甲、六亲、世应、六兽，纯前端 JavaScript 实现
- 📱 **移动优先**：小红书轻应用场景设计

## 🚀 Run

纯前端项目，直接打开 `dist/index.html` 或部署到任意静态托管：

```bash
# 本地预览
python3 -m http.server -d dist 8080
```

- `dist/` — 可直接部署的成品
- `src/` — 源码
- `ref/` — 六爻算法参考实现（Python）

## 🧠 How it works

用户输入三个数字 → 起卦 → 按问卜关系自动配六亲取用神 → 世应生克 + 六兽 → 生成「八九不离十」式的解卦结论。

## 📄 License

MIT
