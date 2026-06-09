#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================================
# make_playlist.py  ——  构建最终 4 曲播放列表的 Logisim ROM
#
# 电路侧用一个曲目计数器 + MUX 在 N 个 ROM 之间切换（上一首/下一首）。
# 经验：装 16 个大 ROM 容易拖垮 Logisim、且会切到一堆空槽，故最终只用 4 首。
# 本脚本为每个槽位生成一个独立的 ROM 文本（连续槽位 0..N-1）：
#   slot 0 : Monitoring          track 0
#   slot 1 : ano_bando           track 0
#   slot 2 : FF3 #30「悠久之风」  track 30   （65 子曲目中的第 30 首）
#   slot 3 : sparkling_daydream  track 0    （2A03+VRC6；VRC6 写入不在 2A03
#            APU 通路上，dumper 只钩 Nes_Apu::write_register，故 VRC6 自动丢弃）
#
# 流程：对每个槽位
#   1) 调 gme_dump/nsfdump.exe 把该 (文件,曲目) dump 成寄存器日志
#   2) 调 encode.py 把日志编码成 ROM 文本 out/trackNN.txt
# 缺失的 .nsf 会被跳过（告警），已有槽位照常生成。
#
# 纯标准库；只是把已验证的两个工具串起来，方便复现与答辩讲解。
# ============================================================================

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DUMPER = os.path.join(HERE, "gme_dump", "nsfdump.exe")
ENCODER = os.path.join(HERE, "encode.py")
LOGDIR = os.path.join(HERE, "gme_dump", "logs")
OUTDIR = os.path.join(HERE, "out")
RAW = os.path.join(HERE, "..", "data", "raw")

MONITORING = os.path.join(RAW, "Monitoring.nsf")
ANO_BANDO = os.path.join(RAW, "ano_bando.nsf")
FF3 = os.path.join(RAW, "Final Fantasy III (1990-04-27)(Square).nsf")
SPARKLING = os.path.join(RAW, "sparkling_daydream.nsf")

SECONDS = 240          # 每首录制秒数（4 分钟，足够装下整首主体）
FRAME_CYCLES = 32      # 每帧固定周期数（节奏等时；须 >= 单帧最大写入数=16）
PERIOD_SCALE = 1.0     # 音高缩放（Buzzer 用真实 Hz，默认 1.0 直通）
DEDUP = True           # ROM 体积优化（音乐无损）

# 最终 4 首：(标签, NSF 文件, 子曲目号)。连续槽位 0..3。
PLAYLIST = [
    ("monitoring", MONITORING, 0),
    ("ano_bando",  ANO_BANDO,  0),
    ("ff3",        FF3,        30),   # 「悠久之风」= FF3 65 子曲目中的第 30 首（之前误用 31）
    ("sparkling",  SPARKLING,  0),    # 2A03+VRC6，VRC6 自动丢弃
]


def run(cmd):
    print("  $", " ".join(os.path.basename(c) if i == 0 else c
                           for i, c in enumerate(cmd)))
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       text=True)
    if r.returncode != 0:
        print(r.stdout)
        raise SystemExit("命令失败：%s" % cmd)
    return r.stdout.strip()


def main():
    if not os.path.exists(DUMPER):
        raise SystemExit("找不到 nsfdump.exe，请先在 gme_dump/ 下 make")
    os.makedirs(LOGDIR, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)

    for slot, (label, nsf, track) in enumerate(PLAYLIST):
        log = os.path.join(LOGDIR, "slot%02d_%s_t%d.log" % (slot, label, track))
        rom = os.path.join(OUTDIR, "track%02d.txt" % slot)
        if not os.path.exists(nsf):
            print("[slot %2d] 跳过 %s：找不到 %s" % (slot, label, nsf))
            continue
        print("[slot %2d] %s track %d" % (slot, label, track))
        # 1) dump
        run([DUMPER, nsf, str(track), str(SECONDS), log])
        # 2) encode
        cmd = [sys.executable, ENCODER, log, rom,
               "--frame-cycles", str(FRAME_CYCLES),
               "--period-scale", str(PERIOD_SCALE)]
        if DEDUP:
            cmd.append("--dedup")
        print("  ->", run(cmd))

    # 清掉超出本播放列表长度的旧 trackNN.txt（之前 16 槽留下的），
    # 以免生成器把过期槽位也读进电路。
    for s in range(len(PLAYLIST), 16):
        stale = os.path.join(OUTDIR, "track%02d.txt" % s)
        if os.path.exists(stale):
            os.remove(stale)
            print("  清理旧槽位 track%02d.txt" % s)

    print("\n完成：%d 个 ROM 写入 %s/track00.txt .. track%02d.txt"
          % (len(PLAYLIST), OUTDIR, len(PLAYLIST) - 1))


if __name__ == "__main__":
    main()
