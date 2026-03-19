# 打包 Windows .exe 说明

因为 PyInstaller **不能**在 Mac 上交叉编译出 Windows 程序，只能用 **GitHub Actions** 在云端 Windows 机器上构建。

## 操作步骤

### 1. 把项目推到 GitHub

```bash
cd /Users/ahs/cursor/social-manager

# 如果还没初始化
git init
git add .
git commit -m "Mayrichbe Manager"

# 在 GitHub 新建一个空仓库，然后
git remote add origin https://github.com/你的用户名/仓库名.git
git branch -M main
git push -u origin main
```

### 2. 触发构建

两种方式任选：

- **推送代码**：推送到 `main` 或 `master` 后自动开始构建
- **手动触发**：在 GitHub 仓库页面 → Actions → "Build Windows EXE" → Run workflow

### 3. 下载 .exe

构建约 5–10 分钟。完成后：

1. 打开 Actions → 选刚完成的 workflow
2. 在页面底部 Artifacts 中下载 **Mayrichbe-Manager-Windows**
3. 解压后得到：
   - `Mayrichbe Manager Setup 1.1.0.exe`：安装版，双击安装后使用
   - `Mayrichbe Manager 1.1.0.exe`：便携版，解压直接运行，无需安装

### 4. 发给朋友

把 **便携版** `Mayrichbe Manager 1.1.0.exe` 发给对方即可，双击即可运行。

---

**注意**：首次运行可能需要几分钟解压和初始化；杀毒软件可能误报，可先加白名单再运行。
