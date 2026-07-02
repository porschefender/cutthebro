import anthropic
import os
import sys
import re

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

def ms_to_time(ms):
    ms = int(ms)
    secs = ms // 1000
    mins = secs // 60
    secs = secs % 60
    return f"{mins:02d}:{secs:02d}"

def load_transcript(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def load_tsv(path):
    timestamps = {}
    if not os.path.exists(path):
        return timestamps
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) >= 3 and parts[0] != "start":
                start, end, text = parts[0], parts[1], parts[2].strip()
                timestamps[text] = ms_to_time(start)
    return timestamps

def ask_claude(prompt, max_tokens=4096):
    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()

def get_summary(transcript):
    print("📝 生成摘要...")
    return ask_claude(f"""以下是一段短视频的转录文本。博主去陌生人家蹭饭，用100美元请陌生人做一顿饭，目标剪成4分钟爆款短视频。

请用中文写一段200字以内的视频摘要，概括主要内容和最打动人的点。只返回摘要文字，不要任何其他内容。

转录文本：
{transcript}""")

def get_highlights(transcript):
    print("⭐ 分析高光片段...")
    return ask_claude(f"""你是短视频爆款剪辑顾问，服务抖音、小红书、TikTok、Instagram平台。

以下是博主去陌生人家蹭饭的视频转录，目标剪成4分钟爆款视频。

请推荐5-8个高光片段，每个片段用以下格式：

【片段N】爆款指数：X/10
适合平台：xxx
为什么爆：xxx（中文）
原文台词：
  英文台词1
  英文台词2
中文翻译：
  对应中文翻译1
  对应中文翻译2

优先选择：情绪爆发点、反转时刻、金句、适合做开头钩子的片段。

转录文本：
{transcript}""", max_tokens=8192)

def get_captions(transcript):
    print("📱 生成各平台文案...")
    return ask_claude(f"""你是短视频运营专家。根据以下视频转录，生成各平台发布文案。

视频内容：博主花100美元请陌生人做饭，记录真实人情味故事。

请生成：

【抖音】
标题+文案+话题标签（中文，带钩子，100字以内）

【小红书】
标题+正文（中文，温情风格，200字以内，带标签）

【TikTok】
Caption（英文，带hashtags，100字以内）

【Instagram】
Caption（英文，storytelling风格，150字以内，带hashtags）

转录文本（节选）：
{transcript[:2000]}""")

def get_hook(transcript):
    print("🎣 生成开场钩子...")
    return ask_claude(f"""根据以下视频转录，推荐最强的开场3秒钩子，说明为什么能留住观众。只需要一个最好的，简短回答。

转录文本：
{transcript[:1000]}""")

def build_transcript_with_timestamps(transcript, timestamps):
    lines = transcript.strip().split("\n")
    result = []
    for line in lines:
        if "]: " in line:
            speaker = line.split("]: ")[0] + "]"
            text = line.split("]: ")[1].strip()
            ts = timestamps.get(text, "??:??")
            result.append(f"{speaker} {ts}: {text}")
        else:
            result.append(line)
    return "\n".join(result)

def save_report(transcript, summary, highlights, captions, hook, timestamps, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("📊 AI 爆款视频分析报告\n")
        f.write("=" * 60 + "\n\n")

        f.write("📝 视频摘要\n")
        f.write("-" * 40 + "\n")
        f.write(summary + "\n\n")

        f.write("🎣 最强开场钩子\n")
        f.write("-" * 40 + "\n")
        f.write(hook + "\n\n")

        f.write("⭐ 高光片段推荐（含中文翻译）\n")
        f.write("-" * 40 + "\n")
        f.write(highlights + "\n\n")

        f.write("=" * 60 + "\n")
        f.write("📱 各平台发布文案\n")
        f.write("=" * 60 + "\n\n")
        f.write(captions + "\n\n")

        f.write("=" * 60 + "\n")
        f.write("📄 全文转录（含时间戳）\n")
        f.write("=" * 60 + "\n\n")
        f.write(build_transcript_with_timestamps(transcript, timestamps))

    print(f"✅ 报告已保存到 {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3.11 analyze.py 转录文件.txt [输出文件夹]")
        sys.exit(1)

    txt_path = sys.argv[1]
    
    # 支持自定义输出文件夹（第二个参数）
    if len(sys.argv) >= 3:
        output_dir = sys.argv[2]
    else:
        output_dir = os.path.dirname(os.path.abspath(txt_path))
    
    os.makedirs(output_dir, exist_ok=True)
    
    base_name = os.path.basename(txt_path).replace(".txt", "")
    tsv_path = os.path.join(os.path.dirname(txt_path), base_name + ".tsv")
    output_path = os.path.join(output_dir, base_name + "_分析报告.txt")

    print("📖 读取转录文本...")
    transcript = load_transcript(txt_path)

    print("⏱️  读取时间戳...")
    timestamps = load_tsv(tsv_path)
    if timestamps:
        print(f"   找到 {len(timestamps)} 条时间戳")
    else:
        print("   未找到tsv文件，时间戳显示为??:??")

    summary    = get_summary(transcript)
    highlights = get_highlights(transcript)
    captions   = get_captions(transcript)
    hook       = get_hook(transcript)

    print("💾 生成报告...")
    save_report(transcript, summary, highlights, captions, hook, timestamps, output_path)

    print("\n📊 摘要预览：")
    print(summary)
