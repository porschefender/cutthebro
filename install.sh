#!/bin/bash

# ================================================
#  CutTheBro 一键安装脚本
#  github.com/porschefender/cutthebro
# ================================================

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${CYAN}ℹ  $1${NC}"; }
success() { echo -e "${GREEN}✅ $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠️  $1${NC}"; }
error()   { echo -e "${RED}❌ $1${NC}"; exit 1; }
ask()     { echo -e "${YELLOW}👉 $1${NC}"; }

echo ""
echo "================================================"
echo "🎬  CutTheBro 安装程序 v1.0"
echo "================================================"
echo ""

# ---- 检查系统 ----
if [[ "$OSTYPE" != "darwin"* ]]; then
  error "CutTheBro 目前只支持 macOS"
fi
success "macOS 系统确认"

# ---- Homebrew ----
if ! command -v brew &>/dev/null; then
  info "安装 Homebrew（可能需要输入系统密码）..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv)"
  echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
  success "Homebrew 安装完成"
else
  success "Homebrew 已安装"
fi

# ---- Python 3.11 ----
if ! brew list python@3.11 &>/dev/null; then
  info "安装 Python 3.11..."
  brew install python@3.11
  success "Python 3.11 安装完成"
else
  success "Python 3.11 已安装"
fi

# ---- ffmpeg ----
if ! command -v ffmpeg &>/dev/null; then
  info "安装 ffmpeg..."
  brew install ffmpeg
  success "ffmpeg 安装完成"
else
  success "ffmpeg 已安装"
fi

# ---- librsvg ----
if ! command -v rsvg-convert &>/dev/null; then
  info "安装图标工具..."
  brew install librsvg
  success "图标工具安装完成"
else
  success "图标工具已安装"
fi

# ---- Python 依赖 ----
info "安装 AI 依赖（这一步需要 5-10 分钟，请耐心等待）..."
pip3.11 install openai-whisper whisperx pyannote.audio flask anthropic --break-system-packages -q
success "AI 依赖安装完成"

# ---- 创建工作目录 ----
INSTALL_DIR="$HOME/CutTheBro"
mkdir -p "$INSTALL_DIR/outputs"
success "工作目录创建完成：$INSTALL_DIR"

# ---- 从 GitHub 下载程序文件 ----
info "下载程序文件..."
REPO="https://raw.githubusercontent.com/porschefender/cutthebro/main"

curl -fsSL "$REPO/app.py" -o "$INSTALL_DIR/app.py" || error "下载 app.py 失败，请检查网络"
curl -fsSL "$REPO/analyze.py" -o "$INSTALL_DIR/analyze.py" || error "下载 analyze.py 失败，请检查网络"
success "程序文件下载完成"

# ---- 收集 API Keys ----
echo ""
echo "================================================"
echo "🔑  配置 API Keys"
echo "================================================"
echo ""

# HuggingFace Token
echo "第 1 步：HuggingFace Token（免费）"
ask "请去 https://huggingface.co/settings/tokens 注册并获取 token"
open "https://huggingface.co/settings/tokens"
echo -n "请粘贴你的 HuggingFace Token（输入时不显示）: "
read -s HF_TOKEN
echo ""

if [[ -z "$HF_TOKEN" ]]; then
  warn "未输入 HuggingFace Token，说话人识别功能将无法使用"
else
  echo "export HUGGINGFACE_TOKEN=\"$HF_TOKEN\"" >> ~/.zprofile
  success "HuggingFace Token 已保存"
fi

# Claude API Key
echo ""
echo "第 2 步：Claude API Key（需充值 \$5）"
ask "请去 https://console.anthropic.com 获取 API Key"
open "https://console.anthropic.com"
echo -n "请粘贴你的 Claude API Key（输入时不显示）: "
read -s CLAUDE_KEY
echo ""

if [[ -z "$CLAUDE_KEY" ]]; then
  warn "未输入 Claude API Key，AI分析功能将无法使用"
else
  echo "export ANTHROPIC_API_KEY=\"$CLAUDE_KEY\"" >> ~/.zprofile
  success "Claude API Key 已保存"
fi

source ~/.zprofile 2>/dev/null

# ---- 同意 HuggingFace 模型协议 ----
echo ""
echo "================================================"
echo "📋  同意模型使用协议（必须）"
echo "================================================"
echo ""
info "请在浏览器中依次打开以下链接，登录后点击 Agree："
echo ""
echo "  1. https://huggingface.co/pyannote/speaker-diarization-3.1"
echo "  2. https://huggingface.co/pyannote/segmentation-3.0"
echo "  3. https://huggingface.co/pyannote/speaker-diarization-community-1"
echo ""
open "https://huggingface.co/pyannote/speaker-diarization-3.1"
sleep 1
open "https://huggingface.co/pyannote/segmentation-3.0"
sleep 1
open "https://huggingface.co/pyannote/speaker-diarization-community-1"
echo -n "三个页面都点击 Agree 后，按回车继续..."
read

# ---- 创建 Mac App ----
info "创建 CutTheBro App..."

APP_PATH="/Applications/CutTheBro.app"
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

cat > "$APP_PATH/Contents/MacOS/CutTheBro" << LAUNCHEOF
#!/bin/bash
source ~/.zprofile 2>/dev/null
source ~/.zshrc 2>/dev/null
cd "$INSTALL_DIR"

if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null 2>&1; then
  open http://localhost:5001
  exit 0
fi

python3.11 app.py &
sleep 2
open http://localhost:5001
wait
LAUNCHEOF
chmod +x "$APP_PATH/Contents/MacOS/CutTheBro"

cat > "$APP_PATH/Contents/Info.plist" << 'PLISTEOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>CutTheBro</string>
  <key>CFBundleExecutable</key><string>CutTheBro</string>
  <key>CFBundleIdentifier</key><string>com.cutthebro.app</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
</dict>
</plist>
PLISTEOF

# 生成图标
cat > /tmp/cutthebro_icon.svg << 'SVGEOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">
  <rect width="1024" height="1024" fill="#1A1612" rx="180"/>
  <rect x="212" y="392" width="600" height="450" fill="#F7F5F2" rx="18"/>
  <rect x="212" y="300" width="600" height="112" fill="#F7F5F2" rx="18"/>
  <clipPath id="c1"><rect x="212" y="300" width="600" height="112" rx="18"/></clipPath>
  <g clip-path="url(#c1)">
    <polygon points="212,300 285,300 212,412" fill="#1A1612"/>
    <polygon points="330,300 405,300 330,412 255,412" fill="#1A1612"/>
    <polygon points="450,300 525,300 450,412 375,412" fill="#1A1612"/>
    <polygon points="570,300 645,300 570,412 495,412" fill="#1A1612"/>
    <polygon points="690,300 765,300 690,412 615,412" fill="#1A1612"/>
    <polygon points="810,300 812,412 735,412" fill="#1A1612"/>
  </g>
  <rect x="232" y="282" width="42" height="36" fill="#8B4513" rx="6"/>
  <rect x="750" y="282" width="42" height="36" fill="#8B4513" rx="6"/>
  <g transform="rotate(-15 512 318)">
    <rect x="212" y="228" width="600" height="78" fill="#E2DDD8" rx="15"/>
    <clipPath id="c2"><rect x="212" y="228" width="600" height="78" rx="15"/></clipPath>
    <g clip-path="url(#c2)">
      <polygon points="212,228 285,228 212,306" fill="#1A1612"/>
      <polygon points="330,228 405,228 330,306 255,306" fill="#1A1612"/>
      <polygon points="450,228 525,228 450,306 375,306" fill="#1A1612"/>
      <polygon points="570,228 645,228 570,306 495,306" fill="#1A1612"/>
      <polygon points="690,228 765,228 690,306 615,306" fill="#1A1612"/>
      <polygon points="810,228 812,306 735,306" fill="#1A1612"/>
    </g>
  </g>
  <text x="512" y="560" text-anchor="middle" font-family="Helvetica Neue,Arial,sans-serif" font-size="78" font-weight="700" fill="#1A1612">Cut</text>
  <text x="512" y="668" text-anchor="middle" font-family="Helvetica Neue,Arial,sans-serif" font-size="78" font-weight="700" fill="#8B4513">The</text>
  <text x="512" y="776" text-anchor="middle" font-family="Helvetica Neue,Arial,sans-serif" font-size="78" font-weight="700" fill="#1A1612">Bro</text>
</svg>
SVGEOF

mkdir -p /tmp/AppIcon.iconset
for size in 16 32 64 128 256 512 1024; do
  rsvg-convert -w $size -h $size /tmp/cutthebro_icon.svg -o /tmp/AppIcon.iconset/icon_${size}x${size}.png 2>/dev/null
done
cp /tmp/AppIcon.iconset/icon_32x32.png    /tmp/AppIcon.iconset/icon_16x16@2x.png
cp /tmp/AppIcon.iconset/icon_64x64.png    /tmp/AppIcon.iconset/icon_32x32@2x.png
cp /tmp/AppIcon.iconset/icon_256x256.png  /tmp/AppIcon.iconset/icon_128x128@2x.png
cp /tmp/AppIcon.iconset/icon_512x512.png  /tmp/AppIcon.iconset/icon_256x256@2x.png
cp /tmp/AppIcon.iconset/icon_1024x1024.png /tmp/AppIcon.iconset/icon_512x512@2x.png
iconutil -c icns /tmp/AppIcon.iconset -o "$APP_PATH/Contents/Resources/AppIcon.icns" 2>/dev/null

touch "$APP_PATH"
killall Dock 2>/dev/null || true
success "CutTheBro App 创建完成"

# ---- 完成 ----
echo ""
echo "================================================"
echo "🎉  安装完成！"
echo "================================================"
echo ""
success "CutTheBro 已安装到 Applications 文件夹"
echo ""
echo "  使用方法："
echo "  1. 打开 Launchpad 找到 CutTheBro"
echo "  2. 双击启动"
echo "  3. 浏览器自动打开，开始使用！"
echo ""
echo "  如有问题请访问：https://github.com/porschefender/cutthebro"
echo ""
ask "按回车打开 Applications 文件夹..."
read
open /Applications
