from flask import Flask, render_template_string, request, jsonify, Response
import subprocess
import os
import re
import json
import threading
import queue
import time
from datetime import datetime

app = Flask(__name__)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")

# 全局进度队列
progress_queues = {}

HTML = """
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>剪辑助手</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
  :root {
    --bg: #F7F5F2; --surface: #FFFFFF; --surface2: #F0EDE8; --border: #E2DDD8;
    --text: #1A1612; --text2: #6B6560; --text3: #A09890;
    --accent: #8B4513; --accent-light: #F5EDE6;
    --green: #2D6A4F; --green-light: #E8F4EE;
    --red: #9B2335; --red-light: #FCEEF0;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Inter', -apple-system, sans-serif; background: var(--bg); color: var(--text); font-size: 13px; height: 100vh; display: flex; flex-direction: column; }

  /* Header */
  .header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 24px; height: 52px; display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; }
  .logo { display: flex; align-items: center; gap: 8px; }
  .logo-mark { width: 26px; height: 26px; background: var(--accent); border-radius: 5px; display: flex; align-items: center; justify-content: center; font-size: 13px; }
  .logo-text { font-size: 14px; font-weight: 600; letter-spacing: -0.3px; }
  .stat-pill { background: var(--surface2); border: 1px solid var(--border); border-radius: 20px; padding: 3px 10px; font-size: 11px; color: var(--text2); }
  .stat-pill strong { color: var(--accent); }

  /* Tabs */
  .tabs { background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 24px; display: flex; gap: 0; flex-shrink: 0; }
  .tab { padding: 12px 16px; font-size: 12px; font-weight: 500; color: var(--text3); cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.15s; user-select: none; }
  .tab:hover { color: var(--text2); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }

  /* Tab content */
  .tab-content { display: none; flex: 1; overflow: hidden; }
  .tab-content.active { display: flex; }

  /* ===== TAB 1: PROCESS ===== */
  .process-layout { display: grid; grid-template-columns: 1fr 340px; width: 100%; }

  .file-panel { padding: 20px 24px; overflow-y: auto; border-right: 1px solid var(--border); }
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
  .section-title { font-size: 11px; font-weight: 600; color: var(--text3); text-transform: uppercase; letter-spacing: 1.2px; }

  .folder-input-row { display: flex; gap: 8px; margin-bottom: 16px; }
  .folder-input-row input { flex: 1; padding: 8px 10px; background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: 6px; font-size: 12px; outline: none; font-family: inherit; }
  .folder-input-row input:focus { border-color: var(--accent); }
  .btn-scan { padding: 8px 14px; background: var(--accent); border: none; color: white; border-radius: 6px; font-size: 12px; font-weight: 500; cursor: pointer; font-family: inherit; white-space: nowrap; }
  .btn-scan:hover { background: #7A3A0F; }

  .file-list { display: flex; flex-direction: column; gap: 4px; }
  .file-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; transition: all 0.12s; cursor: pointer; }
  .file-item:hover { border-color: #C17D52; }
  .file-item.selected { background: #FDF5EF; border-color: #C17D52; }
  .file-item.done { border-color: #B7DFC9; background: var(--green-light); cursor: default; }
  .file-item.processing { border-color: var(--accent); background: var(--accent-light); cursor: default; }
  .file-cb { width: 16px; height: 16px; border: 1.5px solid var(--border); border-radius: 4px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; background: white; transition: all 0.12s; }
  .file-item.selected .file-cb { background: var(--accent); border-color: var(--accent); }
  .file-item.selected .file-cb::after { content: '✓'; font-size: 9px; color: white; font-weight: 700; }
  .file-item.done .file-cb { background: var(--green); border-color: var(--green); }
  .file-item.done .file-cb::after { content: '✓'; font-size: 9px; color: white; font-weight: 700; }
  .file-info { flex: 1; overflow: hidden; }
  .file-name { font-size: 13px; color: var(--text); font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .file-meta { font-size: 11px; color: var(--text3); margin-top: 2px; }
  .file-badge { font-size: 10px; padding: 2px 7px; border-radius: 10px; flex-shrink: 0; font-weight: 500; }
  .badge-done { background: var(--green-light); color: var(--green); }
  .badge-new { background: var(--surface2); color: var(--text3); }
  .badge-processing { background: var(--accent-light); color: var(--accent); }

  .process-sidebar { background: var(--surface); padding: 20px 18px; display: flex; flex-direction: column; gap: 16px; overflow-y: auto; }
  .output-info { background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; font-size: 12px; color: var(--text2); line-height: 1.6; }
  .output-info strong { color: var(--text); display: block; margin-bottom: 4px; }

  .btn-start { width: 100%; padding: 12px; background: var(--accent); border: none; color: white; border-radius: 7px; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit; transition: all 0.15s; }
  .btn-start:hover:not(:disabled) { background: #7A3A0F; }
  .btn-start:disabled { opacity: 0.4; cursor: not-allowed; }

  .log-box { background: #1A1612; border-radius: 8px; padding: 12px; flex: 1; overflow-y: auto; min-height: 200px; max-height: 380px; font-family: 'SF Mono', monospace; font-size: 11px; line-height: 1.7; }
  .log-line { color: #A09890; }
  .log-line.info { color: #E2DDD8; }
  .log-line.success { color: #4ADE80; }
  .log-line.error { color: #F87171; }
  .log-line.step { color: #C17D52; font-weight: 600; }

  .progress-bar-wrap { background: var(--surface2); border-radius: 4px; height: 6px; overflow: hidden; }
  .progress-bar { height: 100%; background: var(--accent); border-radius: 4px; transition: width 0.3s; width: 0%; }

  /* ===== TAB 2: CLIP ===== */
  .clip-layout { display: grid; grid-template-columns: 1fr 320px; width: 100%; }

  .transcript-panel { overflow-y: auto; padding: 20px 24px; }
  .panel-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
  .btn-text { font-size: 11px; color: var(--accent); background: none; border: none; cursor: pointer; }
  .btn-text:hover { text-decoration: underline; }

  .line-group { border: 1px solid transparent; border-radius: 8px; margin-bottom: 3px; cursor: pointer; transition: all 0.12s; }
  .line-group:hover { background: var(--surface); border-color: var(--border); }
  .line-group.selected { background: #FDF5EF; border-color: #C17D52; }
  .line-en { display: flex; align-items: flex-start; gap: 10px; padding: 8px 12px 3px; }
  .line-zh { padding: 0 12px 8px; padding-left: 138px; }
  .cb { width: 16px; height: 16px; border: 1.5px solid var(--border); border-radius: 4px; flex-shrink: 0; margin-top: 2px; display: flex; align-items: center; justify-content: center; background: white; transition: all 0.12s; }
  .line-group.selected .cb { background: var(--accent); border-color: var(--accent); }
  .cb::after { content: '✓'; font-size: 9px; color: white; display: none; font-weight: 700; }
  .line-group.selected .cb::after { display: block; }
  .line-meta { display: flex; gap: 5px; align-items: center; width: 100px; flex-shrink: 0; }
  .spk { font-size: 9px; font-weight: 600; padding: 2px 5px; border-radius: 3px; white-space: nowrap; }
  .spk-0 { background: #EEF4FF; color: #3366CC; }
  .spk-1 { background: #E8F4EE; color: #2D6A4F; }
  .spk-2 { background: #FDF5EF; color: #8B4513; }
  .ts { font-size: 10px; color: var(--accent); font-family: monospace; }
  .text-en { font-size: 13px; color: var(--text); line-height: 1.55; flex: 1; }
  .text-zh { font-size: 12px; color: var(--text2); line-height: 1.5; font-style: italic; }

  .clip-sidebar { background: var(--surface); border-left: 1px solid var(--border); display: flex; flex-direction: column; overflow: hidden; }
  .sb-sec { padding: 14px 16px; border-bottom: 1px solid var(--border); }
  .sb-title { font-size: 10px; font-weight: 600; color: var(--text3); text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 8px; }

  .video-display { font-size: 12px; color: var(--text2); background: var(--surface2); padding: 6px 10px; border-radius: 6px; margin-bottom: 6px; word-break: break-all; min-height: 28px; }
  .video-display.matched { color: var(--green); background: var(--green-light); }
  .video-display.unmatched { color: var(--red); background: var(--red-light); }
  .inp { width: 100%; padding: 7px 10px; background: var(--surface2); border: 1px solid var(--border); color: var(--text); border-radius: 6px; font-size: 12px; outline: none; font-family: inherit; }
  .inp:focus { border-color: var(--accent); }
  .btn-sm { width: 100%; margin-top: 6px; padding: 7px; background: var(--surface2); border: 1px solid var(--border); color: var(--text2); border-radius: 6px; font-size: 12px; cursor: pointer; font-family: inherit; transition: all 0.12s; }
  .btn-sm:hover { border-color: var(--accent); color: var(--accent); }

  .project-group { margin-bottom: 8px; }
  .project-label { font-size: 10px; color: var(--text3); font-weight: 600; padding: 2px 4px; margin-bottom: 3px; }
  .report-list { display: flex; flex-direction: column; gap: 2px; max-height: 130px; overflow-y: auto; }
  .report-item { padding: 5px 10px; border-radius: 5px; font-size: 11px; color: var(--text2); cursor: pointer; border: 1px solid transparent; transition: all 0.12s; }
  .report-item:hover { background: var(--surface2); }
  .report-item.active { background: var(--accent-light); border-color: var(--accent); color: var(--accent); font-weight: 500; }
  .report-item.disabled { opacity: 0.3; cursor: not-allowed; pointer-events: none; }

  .sb-selected { padding: 14px 16px; flex: 1; overflow-y: auto; border-bottom: 1px solid var(--border); }
  .count-display { font-size: 24px; font-weight: 600; color: var(--accent); margin-bottom: 8px; letter-spacing: -1px; }
  .count-display span { font-size: 12px; color: var(--text3); font-weight: 400; }
  .chip-list { display: flex; flex-direction: column; gap: 4px; }
  .chip { background: var(--surface2); border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; display: flex; align-items: flex-start; gap: 6px; }
  .chip-ts { color: var(--accent); font-family: monospace; font-size: 10px; flex-shrink: 0; padding-top: 1px; }
  .chip-body { flex: 1; overflow: hidden; }
  .chip-en { font-size: 11px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .chip-zh { font-size: 10px; color: var(--text2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-style: italic; margin-top: 1px; }
  .chip-rm { color: var(--text3); cursor: pointer; font-size: 15px; flex-shrink: 0; }
  .chip-rm:hover { color: var(--red); }

  .sb-export { padding: 14px 16px; }
  .btn-export { width: 100%; padding: 11px; background: var(--accent); border: none; color: white; border-radius: 7px; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit; transition: all 0.15s; }
  .btn-export:hover:not(:disabled) { background: #7A3A0F; }
  .btn-export:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-clear { width: 100%; margin-top: 6px; padding: 7px; background: none; border: 1px solid var(--border); color: var(--text3); border-radius: 6px; font-size: 12px; cursor: pointer; font-family: inherit; transition: all 0.12s; }
  .btn-clear:hover { border-color: var(--red); color: var(--red); }
  .status { margin-top: 10px; padding: 9px 11px; border-radius: 6px; font-size: 12px; display: none; line-height: 1.6; }
  .status.success { background: var(--green-light); color: var(--green); display: block; }
  .status.error { background: var(--red-light); color: var(--red); display: block; }
  .status.loading { background: var(--accent-light); color: var(--accent); display: block; }

  .empty-state { color: var(--text3); font-size: 12px; text-align: center; padding: 32px 16px; line-height: 1.8; }
</style>
</head>
<body>

<div class="header">
  <div class="logo">
    <div class="logo-mark">🎬</div>
    <div class="logo-text">剪辑助手</div>
  </div>
  <div class="stat-pill">已选片段 <strong id="headerCount">0</strong></div>
</div>

<div class="tabs">
  <div class="tab active" onclick="switchTab('process')">① 处理视频</div>
  <div class="tab" onclick="switchTab('clip')">② 选取片段</div>
</div>

<!-- TAB 1: 处理视频 -->
<div class="tab-content active" id="tab-process">
  <div class="process-layout">
    <div class="file-panel">
      <div class="section-header">
        <div class="section-title">选择视频文件</div>
        <button class="btn-text" onclick="toggleSelectAll()">全选 / 取消</button>
      </div>
      <div class="folder-input-row">
        <input type="text" id="folderInput" placeholder="粘贴视频文件夹路径，例如 /Users/shen/Movies/节目素材">
        <button class="btn-scan" onclick="scanFolder()">扫描</button>
      </div>
      <div class="file-list" id="fileList">
        <div class="empty-state">粘贴文件夹路径后点击扫描</div>
      </div>
    </div>

    <div class="process-sidebar">
      <div>
        <div class="section-title" style="margin-bottom:8px">输出位置</div>
        <div class="output-info">
          <strong id="outputDirDisplay">今日项目文件夹</strong>
          自动生成于：<br>
          <span style="color:var(--accent);font-family:monospace;font-size:11px" id="outputDirPath">video-tool/outputs/今日日期_Project/</span>
        </div>
      </div>

      <div>
        <div class="section-title" style="margin-bottom:8px">处理进度</div>
        <div class="progress-bar-wrap" style="margin-bottom:8px">
          <div class="progress-bar" id="progressBar"></div>
        </div>
        <div style="font-size:11px;color:var(--text3);margin-bottom:8px" id="progressText">等待开始</div>
        <div class="log-box" id="logBox"></div>
      </div>

      <button class="btn-start" id="startBtn" onclick="startProcess()">开始处理选中视频</button>
    </div>
  </div>
</div>

<!-- TAB 2: 选取片段 -->
<div class="tab-content" id="tab-clip">
  <div class="clip-layout">
    <div class="transcript-panel">
      <div class="panel-header">
        <div class="section-title">对照文本</div>
        <button class="btn-text" onclick="selectAll()">全选</button>
      </div>
      <div id="transcriptList">
        <div class="empty-state">← 请在右侧选择分析报告</div>
      </div>
    </div>

    <div class="clip-sidebar">
      <div class="sb-sec">
        <div class="sb-title">视频文件</div>
        <div class="video-display" id="videoDisplay">未设置</div>
        <input class="inp" type="text" id="videoInput" placeholder="粘贴视频完整路径...">
        <button class="btn-sm" onclick="setVideo()">确认路径</button>
      </div>

      <div class="sb-sec">
        <div class="sb-title">分析报告</div>
        <div id="reportList"><div class="empty-state" style="padding:8px">加载中...</div></div>
      </div>

      <div class="sb-selected">
        <div class="sb-title">已选片段</div>
        <div class="count-display" id="countDisplay">0 <span>段</span></div>
        <div class="chip-list" id="chipList"></div>
      </div>

      <div class="sb-export">
        <button class="btn-export" id="exportBtn" onclick="exportAudio()">导出音频片段</button>
        <button class="btn-clear" onclick="clearAll()">清空选择</button>
        <div class="status" id="clipStatus"></div>
      </div>
    </div>
  </div>
</div>

<script>
// ===== TAB SWITCH =====
function switchTab(name) {
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', (i===0&&name==='process')||(i===1&&name==='clip')));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById('tab-'+name).classList.add('active');
  if (name === 'clip') loadReports();
}

// ===== TAB 1: PROCESS =====
let scannedFiles = [];
let selectedFiles = new Set();
let processing = false;
let jobId = null;
let eventSource = null;

async function scanFolder() {
  const folder = document.getElementById('folderInput').value.trim();
  if (!folder) return;
  const res = await fetch('/api/scan?folder=' + encodeURIComponent(folder));
  const data = await res.json();
  if (!data.success) { alert(data.error); return; }
  scannedFiles = data.files;
  selectedFiles.clear();
  renderFileList();
  updateOutputPath();
}

function updateOutputPath() {
  const today = new Date().toISOString().slice(0,10).replace(/-/g,'');
  document.getElementById('outputDirPath').textContent = `video-tool/outputs/${today}_Project/`;
}

function renderFileList() {
  const container = document.getElementById('fileList');
  if (!scannedFiles.length) {
    container.innerHTML = '<div class="empty-state">文件夹里没有找到视频文件</div>';
    return;
  }
  container.innerHTML = scannedFiles.map((f, idx) => {
    const done = f.has_report;
    const sel = selectedFiles.has(idx) && !done;
    return `<div class="file-item ${done?'done':sel?'selected':''}" onclick="${done?'':('toggleFile('+idx+')')}" id="file-${idx}">
      <div class="file-cb"></div>
      <div class="file-info">
        <div class="file-name">${f.name}</div>
        <div class="file-meta">${f.size}</div>
      </div>
      <div class="file-badge ${done?'badge-done':'badge-new'}">${done?'已完成':'待处理'}</div>
    </div>`;
  }).join('');
}

function toggleFile(idx) {
  if (scannedFiles[idx].has_report) return;
  if (selectedFiles.has(idx)) selectedFiles.delete(idx);
  else selectedFiles.add(idx);
  renderFileList();
}

function toggleSelectAll() {
  const unprocessed = scannedFiles.map((f,i) => i).filter(i => !scannedFiles[i].has_report);
  if (selectedFiles.size === unprocessed.length) selectedFiles.clear();
  else unprocessed.forEach(i => selectedFiles.add(i));
  renderFileList();
}

function addLog(msg, type='info') {
  const box = document.getElementById('logBox');
  const line = document.createElement('div');
  line.className = 'log-line ' + type;
  const time = new Date().toLocaleTimeString('zh', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
  line.textContent = `[${time}] ${msg}`;
  box.appendChild(line);
  box.scrollTop = box.scrollHeight;
}

async function startProcess() {
  if (selectedFiles.size === 0) { alert('请先选择要处理的视频'); return; }
  if (processing) return;
  processing = true;
  document.getElementById('startBtn').disabled = true;
  document.getElementById('logBox').innerHTML = '';

  const files = [...selectedFiles].map(i => scannedFiles[i].path);
  const res = await fetch('/api/process', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ files })
  });
  const data = await res.json();
  if (!data.success) { addLog('启动失败: ' + data.error, 'error'); processing = false; document.getElementById('startBtn').disabled = false; return; }

  jobId = data.job_id;
  addLog(`开始处理 ${files.length} 个视频`, 'step');

  // SSE 实时日志
  eventSource = new EventSource('/api/progress/' + jobId);
  eventSource.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === 'log') {
      addLog(msg.text, msg.level || 'info');
    } else if (msg.type === 'progress') {
      document.getElementById('progressBar').style.width = msg.pct + '%';
      document.getElementById('progressText').textContent = msg.text;
    } else if (msg.type === 'file_done') {
      const idx = scannedFiles.findIndex(f => f.path === msg.path);
      if (idx >= 0) { scannedFiles[idx].has_report = true; renderFileList(); }
    } else if (msg.type === 'done') {
      addLog('🎉 全部完成！', 'success');
      document.getElementById('progressBar').style.width = '100%';
      document.getElementById('progressText').textContent = '完成';
      eventSource.close();
      processing = false;
      document.getElementById('startBtn').disabled = false;
      selectedFiles.clear();
      renderFileList();
      loadReports();
    } else if (msg.type === 'error') {
      addLog('错误: ' + msg.text, 'error');
    }
  };
  eventSource.onerror = () => {
    eventSource.close();
    processing = false;
    document.getElementById('startBtn').disabled = false;
  };
}

// ===== TAB 2: CLIP =====
let transcriptData = [];
let selectedLines = new Set();
let videoPath = '';
let videoBasename = '';
let currentReport = '';
let currentReportPath = '';
let allReports = [];

async function loadReports() {
  const res = await fetch('/api/reports');
  allReports = await res.json();
  renderReports();
}

function renderReports() {
  const container = document.getElementById('reportList');
  if (!allReports.length) { container.innerHTML = '<div class="empty-state" style="padding:8px">没有找到报告</div>'; return; }
  const groups = {};
  allReports.forEach(r => { if (!groups[r.folder]) groups[r.folder]=[]; groups[r.folder].push(r); });
  container.innerHTML = Object.entries(groups).map(([folder, reports]) =>
    `<div class="project-group">
      <div class="project-label">📁 ${folder}</div>
      ${reports.map(r => {
        const matched = videoBasename && r.name.startsWith(videoBasename);
        const unmatched = videoBasename && !matched;
        const active = currentReportPath === r.path ? ' active' : '';
        const disabled = unmatched ? ' disabled' : '';
        return `<div class="report-item${active}${disabled}" onclick="loadReport('${r.path}','${r.name}')">${r.name.replace('_分析报告.txt','')}</div>`;
      }).join('')}
    </div>`
  ).join('');
}

async function loadReport(path, name) {
  currentReport = name; currentReportPath = path;
  renderReports();
  const res = await fetch('/api/transcript?path=' + encodeURIComponent(path));
  transcriptData = await res.json();
  selectedLines.clear();
  renderTranscript();
  updateSidebar();
}

function getSpeakerNum(s) { const m = s.match(/SPEAKER_(\d+)/); return m ? parseInt(m[1])%3 : 0; }

function renderTranscript() {
  const container = document.getElementById('transcriptList');
  if (!transcriptData.length) { container.innerHTML = '<div class="empty-state">没有找到对话内容</div>'; return; }
  container.innerHTML = transcriptData.map((item, idx) => {
    const sel = selectedLines.has(idx) ? ' selected' : '';
    const sn = getSpeakerNum(item.speaker);
    const spLabel = item.speaker.replace('[SPEAKER_','说话人').replace(']','');
    return `<div class="line-group${sel}" onclick="toggleLine(${idx},this)">
      <div class="line-en">
        <div class="cb"></div>
        <div class="line-meta"><span class="spk spk-${sn}">${spLabel}</span><span class="ts">${item.timestamp}</span></div>
        <div class="text-en">${item.text_en}</div>
      </div>
      ${item.text_zh ? `<div class="line-zh"><div class="text-zh">${item.text_zh}</div></div>` : ''}
    </div>`;
  }).join('');
}

function toggleLine(idx, el) {
  if (selectedLines.has(idx)) { selectedLines.delete(idx); el.classList.remove('selected'); }
  else { selectedLines.add(idx); el.classList.add('selected'); }
  updateSidebar();
}

function selectAll() { transcriptData.forEach((_,i) => selectedLines.add(i)); renderTranscript(); updateSidebar(); }

function updateSidebar() {
  const sorted = [...selectedLines].sort((a,b)=>a-b);
  document.getElementById('headerCount').textContent = sorted.length;
  document.getElementById('countDisplay').innerHTML = `${sorted.length} <span>段</span>`;
  document.getElementById('chipList').innerHTML = sorted.map(idx => {
    const item = transcriptData[idx];
    return `<div class="chip">
      <div class="chip-ts">${item.timestamp}</div>
      <div class="chip-body">
        <div class="chip-en">${item.text_en}</div>
        ${item.text_zh ? `<div class="chip-zh">${item.text_zh}</div>` : ''}
      </div>
      <div class="chip-rm" onclick="removeLine(${idx},event)">×</div>
    </div>`;
  }).join('');
}

function removeLine(idx, e) {
  e.stopPropagation(); selectedLines.delete(idx);
  document.querySelectorAll('.line-group')[idx]?.classList.remove('selected');
  updateSidebar();
}

function clearAll() { selectedLines.clear(); renderTranscript(); updateSidebar(); }

function setVideo() {
  const input = document.getElementById('videoInput').value.trim();
  if (!input) return;
  videoPath = input;
  videoBasename = input.split('/').pop().replace(/\.[^.]+$/,'');
  const display = document.getElementById('videoDisplay');
  const matching = allReports.find(r => r.name.startsWith(videoBasename));
  if (matching) {
    display.textContent = '✓ ' + input.split('/').pop();
    display.className = 'video-display matched';
    loadReport(matching.path, matching.name);
  } else {
    display.textContent = '⚠ 找不到对应报告：' + videoBasename;
    display.className = 'video-display unmatched';
  }
  renderReports();
}

async function exportAudio() {
  if (selectedLines.size === 0) { showClipStatus('请先选择至少一个片段','error'); return; }
  if (!videoPath) { showClipStatus('请先设置视频文件路径','error'); return; }
  if (currentReport && !currentReport.startsWith(videoBasename)) { showClipStatus('⚠ 报告与视频不匹配','error'); return; }
  const sorted = [...selectedLines].sort((a,b)=>a-b);
  const segments = sorted.map(idx => transcriptData[idx]);
  showClipStatus('⏳ 正在分段导出音频...','loading');
  document.getElementById('exportBtn').disabled = true;
  const res = await fetch('/api/export', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ video_path: videoPath, segments, report_path: currentReportPath })
  });
  const data = await res.json();
  document.getElementById('exportBtn').disabled = false;
  if (data.success) showClipStatus(`✓ 导出完成\n共 ${data.count} 个文件`, 'success');
  else showClipStatus('✕ ' + data.error, 'error');
}

function showClipStatus(msg, type) {
  const el = document.getElementById('clipStatus');
  el.className = 'status ' + type; el.textContent = msg;
}

updateOutputPath();
</script>
</body>
</html>
"""

# ===== BACKEND =====

def get_file_size(path):
    size = os.path.getsize(path)
    if size > 1024**3: return f"{size/1024**3:.1f} GB"
    if size > 1024**2: return f"{size/1024**2:.0f} MB"
    return f"{size/1024:.0f} KB"

def get_project_dir():
    today = datetime.now().strftime("%Y%m%d")
    d = os.path.join(OUTPUT_DIR, f"{today}_Project")
    os.makedirs(d, exist_ok=True)
    return d

def has_report(video_path):
    name = os.path.splitext(os.path.basename(video_path))[0]
    for folder in os.listdir(OUTPUT_DIR):
        folder_path = os.path.join(OUTPUT_DIR, folder)
        if os.path.isdir(folder_path):
            if os.path.exists(os.path.join(folder_path, f"{name}_分析报告.txt")):
                return True
    return False

def parse_report(report_path):
    lines = []
    if not os.path.exists(report_path): return lines
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    for marker in ["全文转录", "中英对照全文"]:
        if marker in content:
            content = content.split(marker)[1]; break
    raw = content.strip().split("\n")
    i = 0
    while i < len(raw):
        line = raw[i].strip()
        if not line or line.startswith("=") or line.startswith("-"):
            i += 1; continue
        m = re.match(r'(\[SPEAKER_\d+\])\s+(\d{2}:\d{2}):\s+(.+)', line)
        if m:
            speaker, timestamp, text_en = m.group(1), m.group(2), m.group(3).strip()
            text_zh = ""
            j = i + 1
            while j < len(raw) and not raw[j].strip(): j += 1
            if j < len(raw):
                zm = re.match(r'\[SPEAKER_\d+\]:\s*(.+)', raw[j].strip())
                if zm:
                    c = zm.group(1).strip()
                    if any('\u4e00' <= ch <= '\u9fff' for ch in c):
                        text_zh = c; i = j
            lines.append({"speaker": speaker, "timestamp": timestamp, "text_en": text_en, "text_zh": text_zh})
        i += 1
    return lines

def time_to_seconds(ts):
    if not ts or ts == "??:??": return 0
    p = ts.split(":"); return int(p[0])*60 + int(p[1])

def sanitize_filename(name):
    name = re.sub(r'[\\/:*?"<>|\n\r\t]', '', name).strip()
    return name[:40] or "片段"

def run_process(job_id, files, q):
    total = len(files)
    project_dir = get_project_dir()

    for idx, video_path in enumerate(files):
        name = os.path.splitext(os.path.basename(video_path))[0]
        pct_base = int(idx / total * 100)

        q.put({"type": "progress", "pct": pct_base, "text": f"[{idx+1}/{total}] 处理：{os.path.basename(video_path)}"})
        q.put({"type": "log", "text": f"▶ 开始处理：{os.path.basename(video_path)}", "level": "step"})

        # 转录
        q.put({"type": "log", "text": "📝 转录中（这一步较慢，请耐心等待）...", "level": "info"})
        result = subprocess.run([
            "python3.11", "-m", "whisperx", video_path,
            "--language", "en", "--diarize",
            "--output_dir", project_dir
        ], capture_output=True, text=True)

        txt_path = os.path.join(project_dir, f"{name}.txt")
        if not os.path.exists(txt_path):
            q.put({"type": "log", "text": f"❌ 转录失败：{name}", "level": "error"})
            continue

        q.put({"type": "log", "text": "✅ 转录完成", "level": "success"})
        q.put({"type": "progress", "pct": pct_base + int(1/total*70), "text": f"[{idx+1}/{total}] AI分析中..."})

        # AI分析
        q.put({"type": "log", "text": "🤖 AI分析中...", "level": "info"})
        ai_result = subprocess.run([
            "python3.11", os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyze.py"),
            txt_path, project_dir
        ], capture_output=True, text=True)

        report_path = os.path.join(project_dir, f"{name}_分析报告.txt")
        if os.path.exists(report_path):
            q.put({"type": "log", "text": f"✅ 分析完成：{name}_分析报告.txt", "level": "success"})
            q.put({"type": "file_done", "path": video_path})
        else:
            q.put({"type": "log", "text": f"❌ AI分析失败：{ai_result.stderr[-200:] if ai_result.stderr else '未知错误'}", "level": "error"})

        q.put({"type": "progress", "pct": int((idx+1)/total*100), "text": f"完成 {idx+1}/{total}"})

    q.put({"type": "done"})

@app.route("/")
def index(): return render_template_string(HTML)

@app.route("/api/scan")
def scan_folder():
    folder = request.args.get("folder", "").strip()
    if not folder or not os.path.isdir(folder):
        return jsonify({"success": False, "error": "文件夹不存在"})
    files = []
    for f in sorted(os.listdir(folder)):
        if f.lower().endswith(('.mov', '.mp4', '.mp4')):
            path = os.path.join(folder, f)
            files.append({
                "name": f,
                "path": path,
                "size": get_file_size(path),
                "has_report": has_report(path)
            })
    return jsonify({"success": True, "files": files})

@app.route("/api/process", methods=["POST"])
def process_videos():
    data = request.json
    files = data.get("files", [])
    if not files: return jsonify({"success": False, "error": "没有选择文件"})
    job_id = str(int(time.time()))
    q = queue.Queue()
    progress_queues[job_id] = q
    t = threading.Thread(target=run_process, args=(job_id, files, q), daemon=True)
    t.start()
    return jsonify({"success": True, "job_id": job_id})

@app.route("/api/progress/<job_id>")
def get_progress(job_id):
    def stream():
        q = progress_queues.get(job_id)
        if not q:
            yield f"data: {json.dumps({'type':'error','text':'任务不存在'})}\n\n"
            return
        while True:
            try:
                msg = q.get(timeout=30)
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                if msg.get("type") == "done":
                    break
            except queue.Empty:
                yield f"data: {json.dumps({'type':'ping'})}\n\n"
    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

@app.route("/api/reports")
def get_reports():
    reports = []
    if not os.path.exists(OUTPUT_DIR): return jsonify([])
    for folder in sorted(os.listdir(OUTPUT_DIR), reverse=True):
        folder_path = os.path.join(OUTPUT_DIR, folder)
        if os.path.isdir(folder_path):
            for f in sorted(os.listdir(folder_path)):
                if f.endswith("_分析报告.txt"):
                    reports.append({"folder": folder, "name": f, "path": os.path.join(folder_path, f)})
        elif folder.endswith("_分析报告.txt"):
            reports.append({"folder": "旧文件", "name": folder, "path": os.path.join(OUTPUT_DIR, folder)})
    return jsonify(reports)

@app.route("/api/transcript")
def get_transcript():
    path = request.args.get("path", "")
    return jsonify(parse_report(path) if path else [])

@app.route("/api/export", methods=["POST"])
def export_audio():
    data = request.json
    video_path = data.get("video_path", "")
    segments = data.get("segments", [])
    report_path = data.get("report_path", "")
    if not segments: return jsonify({"success": False, "error": "没有选择片段"})
    if not os.path.exists(video_path): return jsonify({"success": False, "error": f"找不到视频: {video_path}"})
    out_dir = os.path.dirname(report_path) if report_path else OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    try:
        exported = 0
        for i, seg in enumerate(segments):
            start = time_to_seconds(seg["timestamp"])
            name_source = seg.get("text_zh") or seg.get("text_en", f"片段{i+1}")
            filename = f"{i+1:02d}_{sanitize_filename(name_source)}.mp3"
            result = subprocess.run([
                "ffmpeg", "-y", "-i", video_path,
                "-ss", str(max(0, start)), "-t", "8",
                "-vn", "-acodec", "mp3", "-ab", "192k",
                os.path.join(out_dir, filename)
            ], capture_output=True)
            if result.returncode == 0: exported += 1
        return jsonify({"success": True, "count": exported, "output_dir": out_dir})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("🎬 剪辑助手启动中...")
    print("🌐 打开浏览器访问: http://localhost:5001")
    app.run(debug=False, port=5001, threaded=True)
