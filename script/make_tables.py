#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================================
# make_tables.py  ——  生成 APU 频率换算查找表 ROM（Logisim v2.0 raw）
#
# 计划书 S7：APU 每个通道把寄存器里的 timer 值换算成真实 Hz 喂给 Buzzer。
# 最简单的实现就是“查找 ROM”：地址=timer，数据=频率(Hz)。本脚本生成这些表。
#
# 关键：Buzzer 按真实墙上时间发声，所以这里输出的是【真实 NES 频率】，不做任何
#       Logisim 时钟缩放。音高就对了；节奏(WAIT)另由 CPU 时钟/encode 的
#       --ticks-per-frame 校准。
#
# 产物（都放 out/，v2.0 raw，数据按十六进制）：
#   freq_pulse.txt     2048 项(addr 11-bit)  Pulse1/2 共用：timer -> Hz
#   freq_triangle.txt  2048 项(addr 11-bit)  Triangle：     timer -> Hz
#   freq_noise.txt       16 项(addr  4-bit)  Noise：$400E低4位索引 -> Hz
#
# Buzzer 的 Frequency 引脚是 14-bit（S4：20–20000Hz），最大 16383，故频率值
# 钳到 [0,16383]。频率 ROM 的数据位宽建议设 14（或 16 留余量）。
#
# 公式（NTSC，CPU 时钟 1789773 Hz）：
#   Pulse    f = 1789773 / (16 * (timer+1))
#   Triangle f = 1789773 / (32 * (timer+1))      （三角比方波低八度）
#   Noise    —— 不能用 NES 的 LFSR 时钟频率（见下）！
#
# ★ 噪声（重要修正 2026-06-09）：Logisim 蜂鸣器（Buzzer）的"白噪声"不是真白噪——它把一段
#   长度=sampleRate/hz 的随机块【按 hz 周期性平铺】（见 ref/.../Buzzer.java 缓冲构建），
#   听感是"基频=hz 的带噪嗡声"，hz 越高越像尖锐纯音。所以【绝不能】把 NES 的 LFSR 时钟
#   (CPU/period，几百~几十万 Hz)当 hz 喂进去（否则刺耳）。改为把 16 档映射到一个"低而像
#   噪声"的频率区间(对数等分)：index 0(最快/最亮)->NOISE_HZ_MAX、index 15->NOISE_HZ_MIN。
# ============================================================================

import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, "out")

CPU_HZ = 1789773.0          # NTSC 2A03 主频
FREQ_MAX = 16383            # Buzzer Frequency 14-bit 上限
PULSE_TIMER_BITS = 11       # timer 11-bit -> 2048 项
NOISE_PERIODS = [4, 8, 16, 32, 64, 96, 128, 160,
                 202, 254, 380, 508, 762, 1016, 2034, 4068]  # NTSC（仅作参考，不再直接算频率）
# 噪声 16 档映射到的频率区间（见上方说明；蜂鸣器噪声=按 hz 平铺的随机块，必须用"低"频）。
# index 0(最快/最亮)=上限、index 15(最慢/最闷)=下限。还嫌尖锐就把 MAX 调更低（如 250）。
NOISE_HZ_MAX = 200.0   # 蜂鸣器上：hz>~200 平铺随机块周期太短→听出音高(变尖)，故压到 200
NOISE_HZ_MIN = 40.0


def clamp_hz(f):
    f = int(round(f))
    if f < 0:
        f = 0
    if f > FREQ_MAX:
        f = FREQ_MAX
    return f


def write_rom(values, path, per_line=16):
    lines = ["v2.0 raw"]
    row = []
    for v in values:
        row.append("%x" % (v & 0xFFFF))
        if len(row) == per_line:
            lines.append(" ".join(row)); row = []
    if row:
        lines.append(" ".join(row))
    with open(path, "w", encoding="ascii") as f:
        f.write("\n".join(lines) + "\n")


def gen_pulse(divisor):
    n = 1 << PULSE_TIMER_BITS
    vals = []
    for t in range(n):
        f = CPU_HZ / (divisor * (t + 1))
        vals.append(clamp_hz(f))
    return vals


def gen_noise():
    # 对数等分映射到 [NOISE_HZ_MIN, NOISE_HZ_MAX]，index 0=最亮(高)、15=最闷(低)。
    n = len(NOISE_PERIODS)                       # 16
    r = (NOISE_HZ_MIN / NOISE_HZ_MAX) ** (1.0 / (n - 1))
    return [clamp_hz(NOISE_HZ_MAX * (r ** i)) for i in range(n)]


def main():
    os.makedirs(OUTDIR, exist_ok=True)

    pulse = gen_pulse(16)        # Pulse1/2
    tri = gen_pulse(32)          # Triangle 低八度
    noise = gen_noise()

    write_rom(pulse, os.path.join(OUTDIR, "freq_pulse.txt"))
    write_rom(tri, os.path.join(OUTDIR, "freq_triangle.txt"))
    write_rom(noise, os.path.join(OUTDIR, "freq_noise.txt"))

    print("生成频率查找表 ROM (out/):")
    print("  freq_pulse.txt     %d 项  addrWidth=11 dataWidth=14" % len(pulse))
    print("  freq_triangle.txt  %d 项  addrWidth=11 dataWidth=14" % len(tri))
    print("  freq_noise.txt     %d 项  addrWidth= 4 dataWidth=14" % len(noise))
    print()
    print("抽样校验（timer -> Hz）：")
    for t in (8, 253, 1023, 2047):
        print("  Pulse    timer=%4d -> %5d Hz   Triangle -> %5d Hz"
              % (t, pulse[t], tri[t]))
    print("  （Pulse timer=253 ≈ 440Hz=A4，对得上真实 NES 音高）")
    print("  Noise 索引->Hz:", noise)


if __name__ == "__main__":
    main()
