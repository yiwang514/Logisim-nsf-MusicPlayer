#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================================
# make_flat_demo.py —— 把 WAIT/WRITE/END 指令 ROM "展开" 成无 WAIT 的平铺 ROM,
# 让一个傻瓜计数器(Counter)逐行扫描就能用里程碑 2 的 APU 试听真实曲目,
# 不需要 CPU / 不需要 WAIT 停顿状态机。
#
# 原理:节奏本来由 `WAIT n`(等 n 拍)表达,需要 CPU 解释。这里把每条 `WAIT n`
# 直接展开成 n 行 `NOP(0x0000)`,于是"等待"变成"扫过 n 行什么都不做"。
# 这样每一行都恰好占 1 个时钟步,计数器以"每帧 frame_cycles 步"的速率扫描
# 就是正确的实时节奏(默认 frame_cycles=32 -> 实时约需 60*32=1920 步/秒)。
#
# 输出每个 16-bit 字要么是 WRITE(0x1rvv)、要么是 NOP(0x0000):
#   do_write = 字的第 12 位(bit12)  —— 因为只有 WRITE 的高 4 位 opcode=0001,
#   即 bit12=1;NOP=0x0000 的 bit12=0。所以电路里"要不要写"只看 bit12,连译码器都省了。
#   reg_id = bits[11:8]   value = bits[7:0]
#
# 行数填满 2^addr_bits(尾部补 NOP),这样一个 addr_bits 位的计数器扫到头会自动
# 回绕 -> 整段无缝循环。
#
# 用法:  python script/make_flat_demo.py [输入指令ROM] [输出] [地址位宽]
#   默认  python script/make_flat_demo.py script/out/track00.txt script/out/flat_demo.txt 15
#   15 位 -> 32768 行 -> 实时约 17 秒(@1920 步/秒)。想长一点改 16(约 34 秒)。
# 纯标准库。
# ============================================================================

import sys

FRAME_CYCLES = 32  # 与 encode.py 默认一致;仅用于打印"实时秒数"估算


def read_words(path):
    """读 Logisim v2.0 raw;支持可选的 RLE 'count*value' 写法。"""
    words = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line == "v2.0 raw" or line.startswith("#"):
                continue
            for tok in line.split():
                if "*" in tok:
                    cnt, val = tok.split("*")
                    words.extend([int(val, 16)] * int(cnt))
                else:
                    words.append(int(tok, 16))
    return words


def expand(words, max_rows):
    """把指令流展开成 <= max_rows 行的平铺流(WRITE 原样保留, WAIT 展成 NOP)。"""
    out = []
    i = 0
    n = len(words)
    while i < n and len(out) < max_rows:
        w = words[i] & 0xFFFF
        op = (w >> 12) & 0xF
        if op == 0x1:                       # WRITE -> 一行"写"
            out.append(w)
        elif op == 0x0:                     # WAIT imm12 -> imm 行 NOP
            out.extend([0x0000] * (w & 0x0FFF))
        elif op == 0x2:                     # LWAIT -> 下一字是 16-bit 等待数
            i += 1
            if i < n:
                out.extend([0x0000] * (words[i] & 0xFFFF))
        elif op == 0xF:                     # END -> 截到这里(后面补 NOP, 计数器回绕即循环)
            break
        # 其它 opcode(回放不产生)忽略
        i += 1
    return out[:max_rows]


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    src = argv[0] if len(argv) > 0 else "script/out/track00.txt"
    out_path = argv[1] if len(argv) > 1 else "script/out/flat_demo.txt"
    addr_bits = int(argv[2]) if len(argv) > 2 else 15
    rows = 1 << addr_bits

    words = read_words(src)
    flat = expand(words, rows)
    used = len(flat)
    flat += [0x0000] * (rows - used)        # 补满到 2^addr_bits,便于计数器回绕循环

    with open(out_path, "w", encoding="ascii") as f:
        f.write("v2.0 raw\n")
        for k in range(0, rows, 16):
            f.write(" ".join("%x" % (x & 0xFFFF) for x in flat[k:k + 16]) + "\n")

    writes = sum(1 for x in flat[:used] if ((x >> 12) & 0xF) == 1)
    secs = rows / (60.0 * FRAME_CYCLES)
    print("flat ROM: %d 行 (addrWidth=%d, dataWidth=16);其中写入 %d 行、填充 NOP 到满。"
          % (rows, addr_bits, writes))
    print("实时约 %.1f 秒 (@ %d 步/秒);扫描计数器步进率=节拍频率/2,实时需≈%d 步/秒 -> 节拍≈%dHz。"
          % (secs, 60 * FRAME_CYCLES, 60 * FRAME_CYCLES, 2 * 60 * FRAME_CYCLES))
    print("-> %s" % out_path)


if __name__ == "__main__":
    main()
