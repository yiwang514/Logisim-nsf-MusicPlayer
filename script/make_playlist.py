#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================================
# make_playlist.py  ——  一键构建 16 槽播放列表的 Logisim ROM
#
# 电路侧用 4-bit 曲目计数器 + MUX 在 16 个 ROM 之间切换（上一首/下一首）。
# 本脚本为每个槽位 (slot 0..15) 生成一个独立的 ROM 文本：
#   slot 0 : Monitoring  track 0
#   slot 1 : FF3         track 31   （指定曲目）
#   slot 2..15 : FF3 其它若干子曲目填充
#
# 流程：对每个槽位
#   1) 调 gme_dump/nsfdump.exe 把该 (文件,曲目) dump 成寄存器日志
#   2) 调 encode.py 把日志编码成 ROM 文本 out/trackNN.txt
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
FF3 = os.path.join(RAW, "Final Fantasy III (1990-04-27)(Square).nsf")

SECONDS = 240          # 每首录制秒数（4 分钟，足够装下整首主体）
FRAME_CYCLES = 32      # 每帧固定周期数（节奏等时；须 >= 单帧最大写入数=16）
PERIOD_SCALE = 1.0     # 音高缩放（Buzzer 用真实 Hz，默认 1.0 直通）
DEDUP = True           # ROM 体积优化（音乐无损）

# 16 个槽位：(标签, NSF 文件, 子曲目号)
# slot1 固定 FF3#31；其余用一组分散的 FF3 子曲目填充（“随机”但确定，便于复现）。
FF3_FILL = [1, 2, 5, 8, 12, 18, 24, 30, 36, 42, 48, 54, 58, 62]
PLAYLIST = [("monitoring", MONITORING, 0), ("ff3", FF3, 31)]
for t in FF3_FILL:
    PLAYLIST.append(("ff3", FF3, t))
PLAYLIST = PLAYLIST[:16]   # 4-bit 选择器，最多 16 槽


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

    print("\n完成：%d 个 ROM 写入 %s/track00.txt .. track%02d.txt"
          % (len(PLAYLIST), OUTDIR, len(PLAYLIST) - 1))


if __name__ == "__main__":
    main()
