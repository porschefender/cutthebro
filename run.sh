#!/bin/bash

# 🎬 CutTheBro 批量处理脚本
# 支持视频：.mov .mp4
# 支持音频：.mp3 .m4a .wav .aac .flac

cd ~/CutTheBro

process_file() {
  local FILE="$1"
  local BASENAME=$(basename "$FILE")
  local NAME="${BASENAME%.*}"
  local PROJECT_DIR="$2"
  local REPORT="$PROJECT_DIR/${NAME}_分析报告.txt"

  if [ -f "$REPORT" ]; then
    echo "⏭️  已有分析报告，跳过：$BASENAME"
    return
  fi

  echo "🎬 处理：$BASENAME"
  echo "📝 转录中..."

  python3.11 -m whisperx "$FILE" \
    --language en \
    --diarize \
    --output_dir "$PROJECT_DIR"

  local TXT="$PROJECT_DIR/${NAME}.txt"
  if [ ! -f "$TXT" ]; then
    echo "❌ 转录失败：$BASENAME"
    return
  fi

  echo "✅ 转录完成"
  echo "🤖 AI分析中..."
  python3.11 ~/CutTheBro/analyze.py "$TXT" "$PROJECT_DIR"
  echo "✅ 完成：${NAME}_分析报告.txt"
}

if [ -z "$1" ]; then
  echo "用法："
  echo "  单个文件：./run.sh /路径/文件.mov"
  echo "  整个文件夹：./run.sh /路径/文件夹/"
  exit 1
fi

TODAY=$(date +%Y%m%d)
PROJECT_DIR="$HOME/CutTheBro/outputs/${TODAY}_Project"
mkdir -p "$PROJECT_DIR"
echo "📁 输出目录：$PROJECT_DIR"

INPUT="$1"

if [ -d "$INPUT" ]; then
  echo "================================================"
  echo "📁 批量模式：$INPUT"
  echo "================================================"

  COUNT=0
  for FILE in "$INPUT"/*.mov "$INPUT"/*.mp4 "$INPUT"/*.MP4 "$INPUT"/*.MOV \
              "$INPUT"/*.mp3 "$INPUT"/*.m4a "$INPUT"/*.wav "$INPUT"/*.aac "$INPUT"/*.flac; do
    [ -f "$FILE" ] && COUNT=$((COUNT + 1))
  done

  if [ "$COUNT" -eq 0 ]; then
    echo "❌ 文件夹里没有找到支持的视频/音频文件"
    exit 1
  fi

  echo "📹 找到 $COUNT 个文件，开始批量处理..."
  DONE=0
  for FILE in "$INPUT"/*.mov "$INPUT"/*.mp4 "$INPUT"/*.MP4 "$INPUT"/*.MOV \
              "$INPUT"/*.mp3 "$INPUT"/*.m4a "$INPUT"/*.wav "$INPUT"/*.aac "$INPUT"/*.flac; do
    [ -f "$FILE" ] || continue
    DONE=$((DONE + 1))
    echo "================================================"
    echo "[$DONE/$COUNT] $(basename "$FILE")"
    echo "================================================"
    process_file "$FILE" "$PROJECT_DIR"
    echo ""
  done

  echo "================================================"
  echo "🎉 全部完成！共处理 $DONE 个文件"
  echo "📂 保存在：$PROJECT_DIR"
  echo "================================================"
else
  echo "================================================"
  echo "🎬 单个文件模式"
  echo "================================================"
  process_file "$INPUT" "$PROJECT_DIR"
  echo "📂 保存在：$PROJECT_DIR"
fi
