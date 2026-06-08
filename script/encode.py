#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================================
# encode.py  ——  阶段二：寄存器写日志 -> 16-bit 定长指令 -> Logisim ROM 映像
#
# 输入：阶段一(GME dumper)产出的寄存器日志，每行 "frame addr value"。
# 输出：Logisim ROM image 文本（v2.0 raw），每个 token 是一个 16-bit 指令字
#       （最多 4 位十六进制）。指令 ROM 的数据位宽 = 16，地址 = 字地址。
#
# 指令编码（16-bit 定长，与计划书 S6 一致）：高 4 位 opcode，低 12 位操作数。
#   0x0  WAIT   :  0000 | imm12            等待 imm12 个时间单位（0-4095）
#   0x1  WRITE  :  0001 | reg(4) | val(8)  APU[reg] = 立即数 val
#   0x2  LWAIT  :  0010 | 0000 ; 下一字=16-bit 等待数  （仅 wait>4095 时用）
#   0xF  END    :  1111 | 0000             曲目结束 / 循环点
#   （0x3 WKEY / 0x4-0x7 LOADI/ADD/SUB/WRITEREG 由计划书 CPU 支持，但直采回放
#     用不到，本编码器不生成——它们留给后续“颤音/音量渐变”优化。）
#
#   reg(4) 映射（只有 16 个槽 $4000-$400F）：
#     $4000-$4008,$400A-$400C,$400E,$400F -> reg = addr-0x4000
#     $4015（声道使能）-> reg 9   （借真实 NES 未用的 $4009 槽位）
#     $4009/$400D（真实未用）、$4017、其它 -> 丢弃
#   APU 译码器据此：reg 9 解释为“声道使能”，其余按 $4000-$400F 原义。
#
# 关于缩放（重要修正）：
#   - 音高不缩放！Buzzer 的 Frequency 引脚吃真实 Hz、按墙上时间发声，与 Logisim
#     时钟快慢无关。所以频率寄存器值原样写入，APU 侧用频率换算 ROM 输出真实 Hz。
#     (--period-scale 默认 1.0，一般不要动；保留只为极端实验。)
#
# 关于节奏“等时”（修正：每帧固定耗时）：
#   原始 NES 每帧(1/60s)里 PLAY 快速写完寄存器，剩下时间就是等待。若我们每帧只补
#   WAIT 1，而各帧 WRITE 条数不等(本数据 3~16) → 每帧实际占用的 CPU 周期数不等
#   → 节奏忽快忽慢。修法：每帧固定预算 --frame-cycles 个周期，
#       WAIT = frame_cycles - 本帧写入数   （空帧整段 = frame_cycles）
#   于是不管写多少，每帧都恰好 frame_cycles 个时钟，节奏均匀。
#   frame_cycles 必须 >= 各曲单帧最大写入数(本数据=16)，默认 32。
#   实时正确节奏所需 CPU 时钟 ≈ 60 * frame_cycles Hz（默认 32 -> ~1920Hz）。
#   整个播放列表要用同一个 frame_cycles，否则不同曲速度不一致。
#
# 纯标准库实现。
# ============================================================================

import argparse
import sys

PERIOD_LO = {0x4002, 0x4006, 0x400A}
PERIOD_HI = {0x4003, 0x4007, 0x400B}
DMC_RANGE = range(0x4010, 0x4014)

# 节流(throttle)用：周期寄存器 -> 通道号；音量寄存器集合。
PERIOD_LO_CH = {0x4002: 0, 0x4006: 1, 0x400A: 2}   # Pulse1/2/Triangle 的 timer 低字节
PERIOD_HI_CH = {0x4003: 0, 0x4007: 1, 0x400B: 2}   # timer 高 3 位
VOL_REGS = {0x4000, 0x4004, 0x400C}                # 低4位=音量；脉冲高4位=占空比/标志
NOISE_PERIOD = 0x400E

# 寄存器 -> 4-bit reg_id 的映射；返回 None 表示丢弃该写入
def map_reg(addr):
    if addr == 0x4015:
        return 9                       # 声道使能借用未用槽 reg 9
    if 0x4000 <= addr <= 0x400F:
        if addr in (0x4009, 0x400D):   # 真实 NES 未用寄存器，丢弃（避免和 reg9 冲突）
            return None
        return addr - 0x4000
    return None                        # $4017 等其它一律丢弃


def parse_log(path):
    events = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) != 3:
                continue
            try:
                frame = int(parts[0], 10)
                addr = int(parts[1], 16)
                value = int(parts[2], 16)
            except ValueError:
                continue
            if addr in DMC_RANGE:
                continue
            events.append((frame, addr, value))
    return events


def throttle(events, freq_deadband=0, vol_deadband=0, max_update_hz=0):
    """颤音/包络节流：减少喂给 Buzzer 的「每帧微小变化」，从而压制 Buzzer 每次输入变化
    就重开 Clip 造成的 ~60Hz 爆破（见 ref/.../io/extra/Buzzer.java：propagate 一变就
    updateRequired=true，后台线程随即关旧 Clip、开新 Clip）。这是纯过滤器：丢掉「变化
    太小 / 太频繁」的写入；on/off（音量进出 0）与占空比变化始终保留，所以音不会断。
      freq_deadband K —— 通道 11 位 timer 相对上次「已发出」值变化 <=K 就丢（杀小颤音）。
      vol_deadband  K —— 音量低 4 位变化 <=K（且占空比不变、且非 0 进出）就丢（压音量包络）。
      max_update_hz H —— 每个调制寄存器每秒最多变 H 次（最小间隔 60/H 帧）。
    三个都为 0 时原样返回（默认行为不变）。拿表现力换平滑，逐曲可调。"""
    if not (freq_deadband or vol_deadband or max_update_hz):
        return events
    min_gap = (60.0 / max_update_hz) if max_update_hz > 0 else 0.0
    mod_regs = set(PERIOD_LO_CH) | set(PERIOD_HI_CH) | VOL_REGS | {NOISE_PERIOD}
    raw_lo, raw_hi = {}, {}             # 各通道最新「原始」周期字节（跟踪曲子真实意图）
    emit_timer, emit_vol, emit_duty = {}, {}, {}   # 各通道/寄存器「已发出」的值
    last_frame = {}                     # 每个寄存器上次发出的帧（限速用）
    out = []
    for frame, addr, value in events:
        keep = True
        cand = None
        if addr in PERIOD_LO_CH or addr in PERIOD_HI_CH:
            if addr in PERIOD_LO_CH:
                ch = PERIOD_LO_CH[addr]; raw_lo[ch] = value & 0xFF
            else:
                ch = PERIOD_HI_CH[addr]; raw_hi[ch] = value & 0x07
            timer = ((raw_hi.get(ch, 0) & 0x07) << 8) | (raw_lo.get(ch, 0) & 0xFF)
            if freq_deadband > 0 and ch in emit_timer and abs(timer - emit_timer[ch]) <= freq_deadband:
                keep = False
            cand = ("t", ch, timer)
        elif addr in VOL_REGS:
            vol, duty = value & 0x0F, value & 0xF0
            if (vol_deadband > 0 and addr in emit_vol and emit_duty.get(addr) == duty
                    and abs(vol - emit_vol[addr]) <= vol_deadband and vol != 0 and emit_vol[addr] != 0):
                keep = False
            cand = ("v", addr, vol, duty)
        if keep and min_gap > 0 and addr in mod_regs:
            lf = last_frame.get(addr)
            if lf is not None and (frame - lf) < min_gap:
                keep = False
        if keep:
            out.append((frame, addr, value))
            last_frame[addr] = frame
            if cand and cand[0] == "t":
                emit_timer[cand[1]] = cand[2]
            elif cand and cand[0] == "v":
                emit_vol[cand[1]] = cand[2]; emit_duty[cand[1]] = cand[3]
    return out


def scale_period_value(addr, value, channel_period, period_scale):
    """可选的周期(音高)缩放；period_scale=1.0 时完全直通（默认）。"""
    if period_scale == 1.0:
        return value
    if addr in PERIOD_LO:
        ch = (addr - 0x4002) // 4
        cur = (channel_period.get(ch, 0) & 0x700) | (value & 0xFF)
        scaled = int(round(cur * period_scale)) & 0x7FF
        channel_period[ch] = scaled
        return scaled & 0xFF
    if addr in PERIOD_HI:
        ch = (addr - 0x4003) // 4
        cur = (channel_period.get(ch, 0) & 0x0FF) | ((value & 0x07) << 8)
        scaled = int(round(cur * period_scale)) & 0x7FF
        channel_period[ch] = scaled
        return (value & 0xF8) | ((scaled >> 8) & 0x07)
    return value


def emit_wait(words, units):
    """把 units 个等待编码成 WAIT(0x0NNN)/LWAIT(0x2000 + 一个 16-bit 字)。"""
    while units > 0:
        if units <= 0x0FFF:
            words.append(0x0000 | units)          # WAIT imm12
            units = 0
        elif units <= 0xFFFF:
            words.append(0x2000)                  # LWAIT
            words.append(units & 0xFFFF)          # 后随 16-bit 等待数
            units = 0
        else:
            words.append(0x2000)
            words.append(0xFFFF)
            units -= 0xFFFF


def encode(events, frame_cycles=32, period_scale=1.0, dedup=False):
    """每帧固定 frame_cycles 个周期：先发本帧 WRITE，再补 WAIT 把这帧填到预算；
    中间没有写入的空帧也各占 frame_cycles。返回 (指令字列表, 超预算帧数)。"""
    words = []
    channel_period = {}
    last_written = {}
    cur_frame = None
    frame_writes = []          # 当前帧缓存的 WRITE 指令字
    overruns = [0]             # 写入数 > frame_cycles 的帧数（无法补 WAIT）

    def flush(next_frame):
        w = len(frame_writes)
        words.extend(frame_writes)
        # 本帧补齐到预算（写满或超了就不补）
        pad = frame_cycles - w if w < frame_cycles else 0
        if w > frame_cycles:
            overruns[0] += 1
        total = pad
        # 合并中间空帧（每个空帧 = 整段 frame_cycles）
        if next_frame is not None:
            total += frame_cycles * (next_frame - cur_frame - 1)
        emit_wait(words, total)
        frame_writes.clear()

    for frame, addr, value in events:
        reg = map_reg(addr)
        if reg is None:
            continue
        if cur_frame is None:
            cur_frame = frame
        if frame != cur_frame:
            flush(frame)
            cur_frame = frame

        vv = scale_period_value(addr, value, channel_period, period_scale) & 0xFF
        if dedup and last_written.get(reg) == vv:
            continue
        last_written[reg] = vv
        frame_writes.append(0x1000 | (reg << 8) | vv)   # WRITE reg, val

    if cur_frame is not None:
        flush(None)            # 末帧也补齐，使循环接缝处节奏均匀
    words.append(0xF000)       # END
    return words, overruns[0]


def write_rom(words, path, per_line=16):
    """输出 Logisim v2.0 raw；每个 token 是 16-bit 指令字（最多 4 位 hex）。"""
    lines = ["v2.0 raw"]
    row = []
    for w in words:
        row.append("%x" % (w & 0xFFFF))
        if len(row) == per_line:
            lines.append(" ".join(row))
            row = []
    if row:
        lines.append(" ".join(row))
    with open(path, "w", encoding="ascii") as f:
        f.write("\n".join(lines) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="NSF 寄存器日志 -> 16-bit 定长指令 Logisim ROM (.txt)")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--frame-cycles", type=int, default=32,
                    help="每帧固定占用的 CPU 周期数（节奏等时；须 >= 单帧最大写入数，默认 32）")
    ap.add_argument("--period-scale", type=float, default=1.0,
                    help="音高缩放（默认 1.0，Buzzer 用真实 Hz 时不要改）")
    ap.add_argument("--dedup", action="store_true",
                    help="跳过与上次相同值的寄存器写（缩小 ROM，音乐无损）")
    ap.add_argument("--freq-deadband", type=int, default=0,
                    help="颤音死区：通道 timer 变化<=该值就丢，减少 Buzzer 爆破（0=关；试 2~4）")
    ap.add_argument("--vol-deadband", type=int, default=0,
                    help="音量死区：音量低4位变化<=该值就丢，压音量包络（0=关；试 3~6）")
    ap.add_argument("--vol-hold", action="store_true",
                    help="保持音量（等价 --vol-deadband 16，只留 on/off 与占空比变化）")
    ap.add_argument("--max-update-hz", type=float, default=0,
                    help="每个调制寄存器每秒最多变化次数（限速；0=关）")
    ap.add_argument("--max-frames", type=int, default=0)
    args = ap.parse_args(argv)

    events = parse_log(args.input)
    if args.max_frames > 0:
        events = [e for e in events if e[0] < args.max_frames]

    n_raw = len(events)
    vol_db = 16 if args.vol_hold else args.vol_deadband
    events = throttle(events, freq_deadband=args.freq_deadband,
                      vol_deadband=vol_db, max_update_hz=args.max_update_hz)
    if len(events) != n_raw:
        print("throttle: %d -> %d events (丢 %d, %.0f%%)  [freq_db=%d vol_db=%d max_hz=%s]"
              % (n_raw, len(events), n_raw - len(events),
                 100.0 * (n_raw - len(events)) / max(1, n_raw),
                 args.freq_deadband, vol_db, args.max_update_hz or "off"))

    words, overruns = encode(events,
                             frame_cycles=args.frame_cycles,
                             period_scale=args.period_scale,
                             dedup=args.dedup)
    write_rom(words, args.output)

    import math
    bits = max(2, math.ceil(math.log2(len(words)))) if words else 2
    warn = ("  [警告] %d 帧写入数>预算，已不补WAIT(略快)" % overruns) if overruns else ""
    print("encoded %d events -> %d instr words (addrWidth>=%d, dataWidth=16, frame_cycles=%d) -> %s%s"
          % (len(events), len(words), bits, args.frame_cycles, args.output, warn))


if __name__ == "__main__":
    main()
