# 最终答辩 PPT 讲解信息摘要

> 目标：这不是视觉稿，也不是 HTML 幻灯片。它是“10 分钟答辩应当讲什么”的内容规格书。  
> 原则：每页只服务一个论点；所有技术事实必须能追溯到本项目文档、脚本源码、Logisim Evolution 源码或 NESdev Wiki；不要凭常识扩写。

## 0. 使用边界

- 本文只描述每页的信息目标、讲解内容、证据来源和截图建议。
- 不描述 UI 样式、配色、字体、版式美感。
- 涉及 Logisim 操作词、部件名、菜单名时，按 `.claude/skills/logisim-zh-terms/SKILL.md` 使用中英双语，例如 蜂鸣器（Buzzer）、计数器（Counter）、寄存器（Register）、译码器（Decoder）、多路复用器（Multiplexer）、Splitter（分线器）、项目 → 加载库 → Logisim-evolution 库…（Project → Load Library → Logisim-evolution Library…）。
- 不写死快捷键。Logisim 加速键可配置，答辩材料不要出现“按 Ctrl+...”之类操作指令。
- 当前实现应按最终状态讲：`apu.circ`、`cpu.circ`、`top.circ` 已存在；最终播放列表是 4 首，不再按早期 16 槽讲。

## 1. 核心叙事

一句话总线：

> NSF 里保存的是 NES 音乐播放代码；运行后本质上会按帧写 2A03 APU 寄存器。我们先用 GME 把这些寄存器写入录下来，再编码成 Logisim ROM；最后由自制 16-bit 五段 CPU 执行 `WAIT/WRITE/END`，驱动简化 Buzzer APU 发声。

答辩中的三个关键词：

- **真实性**：输入是真实 `.nsf`，不是手写旋律；GME dumper 记录真实播放过程中的 APU 寄存器写入。
- **可行性**：Logisim 蜂鸣器（Buzzer）源码提供真实 Hz 频率输入和方波（Square）/三角波（Triangle）/白噪声（White noise）等波形；用查表 ROM 把 NES timer 转成 Hz 即可承接音高。
- **硬件性**：播放不是脚本直接播放音频，而是 Logisim 电路中的 CPU 取指、译码、WAIT 停顿、ALU 调速、APU 寄存器驱动蜂鸣器（Buzzer）。

建议总页数：13 页正片 + 1 页备选 Q&A。  
建议时间：约 10 分钟。CPU 部分必须占最多时间。

## 2. 参考依据总表

### 2.1 项目计划和里程碑文档

- `plan/SESSION_HANDOFF.md`
  - 项目整体状态、锁定架构、时钟/Buzzer 关键结论、4 通道 APU、CPU WAIT 状态机、ALU 变速、Logisim 双语术语要求。
  - 特别参考：ISA 固定 16-bit、PC 16-bit、`$4015 → reg_id=9`、Buzzer 真实 Hz、五段 CPU 不要求流水线、APU reg 映射、BuzzerStress/WAIT 分频结论。
- `plan/detailed_plan.html`
  - 项目总架构、工具链、ISA、总线位宽、CPU、APU、控制面板、风险审计。
  - 特别参考：§2 工具链，§3 ISA，§4 位宽，§5 CPU，§6 APU，§8 Buzzer 风险。
- `plan/milestone1_guide.html`
  - BuzzerStress 与 PulseOneShot 验证：频率表可驱动 Buzzer；timer=253 输出约 440Hz；高位分频避免高速扫频。
- `plan/milestone2_guide.html`
  - RegFile、Channel_Pulse、四通道 APU、按帧采样、`ch_mask` 声道开关、Buzzer 音质边界。
- `plan/milestone3_guide.html`
  - 单周期五段 CPU、PC/WAIT 计数器、WAIT busy 状态机、`WR=is_write·clk`、`frame_commit=start·clk`、END 循环。
- `plan/milestone4_guide.html`
  - ALU 接入 WAIT 变速、R0-R3、`LOADI/ADD/SUB/WRITEREG`、top 控制面板、多曲 ROM 外置、4:1 多路复用器（Multiplexer）。

### 2.2 脚本源码

- `script/gme_dump/dump_main.cpp`
  - 注释说明：借 game-music-emu 的 6502 + 2A03 APU；每次 `$4000-$4017` 写入都会经过 `Nes_Apu::write_register`；记录 `"frame addr value"`。
  - DMC `$4010-$4013` 在 dumper 侧跳过。
- `script/gme_dump/PATCH.md`
  - 说明选择 GME 而非 NSFPlay 的原因：`Nes_Apu::write_register` 是单一写入口，带 time 参数；3 处 `#ifdef GME_APU_DUMP` 最小改动。
- `script/encode.py`
  - 指令编码：`WAIT/WRITE/LWAIT/END`；`$4015 → reg_id=9`；音高不缩放；`frame_cycles` 等时逻辑；颤音/音量节流选项。
  - 关键行：开头注释的 ISA 与寄存器映射；`encode()` 中“先 WRITE、再补 WAIT”；`words.append(0xF000)` 加 END。
- `script/make_tables.py`
  - 频率查找表：`freq_pulse.txt`、`freq_triangle.txt`、`freq_noise.txt`。
  - 关键公式：Pulse `f = 1789773 / (16 * (timer+1))`；Triangle `f = 1789773 / (32 * (timer+1))`；Noise 不直接用 NES LFSR 时钟，而映射到 40-200Hz 的 Buzzer 近似区间。
- `script/make_playlist.py`
  - 最终 4 曲播放列表；`FRAME_CYCLES=32`；`PERIOD_SCALE=1.0`；`DEDUP=True`；清理旧 16 槽残留。

### 2.3 Logisim Evolution 源码

- `ref/logisim-evolution/src/main/java/com/cburch/logisim/std/io/extra/Buzzer.java`
  - 端口：`FREQ` 14-bit、`ENABLE` 1-bit、`VOL`、`PW` 8-bit。
  - 波形：Sine / Square / Triangle / Sawtooth / Noise。
  - 行为边界：输入变化会 `updateRequired=true`；线程重建 1 秒缓冲 `byte[4*sampleRate]` 并打开 `Clip`；频率有效范围 20-20000Hz；源码注释警告不要把 4kHz 时钟接 enable。
- `ref/logisim-evolution/src/main/java/com/cburch/logisim/std/memory/Counter.java`
  - `propagate()` 确认：清除异步；加载优先于计数；使能悬空不等于 false；方向悬空按向上；向下计数时 Carry 与当前值是否为 0 相关，可作为 WAIT 的 `at_zero`。
- `ref/logisim-evolution/src/main/java/com/cburch/logisim/circuit/Simulator.java`
  - 自动节拍调度：低频用 `awaitNanos()` 睡眠，高频用更紧的等待策略；解释 Windows 上低频自动节拍不准。
- `ref/logisim-evolution/src/main/java/com/cburch/logisim/gui/main/TickCounter.java`
  - 显示频率是 full cycles per second，代码里 `ticksPerSecond / 2.0`。
- `ref/logisim-evolution/src/main/java/com/cburch/logisim/circuit/Circuit.java`
  - 标签判重不区分大小写；解释为什么 RegFile 输出脚要用 `regN_out`，不能和寄存器（Register）本体同名。

### 2.4 NESdev Wiki

引用时只用这些页面承载的事实，不要扩写：

- [NESdev Wiki: APU](https://www.nesdev.org/wiki/APU)
  - NES APU 是 RP2A03/RP2A07 内的音频处理单元；寄存器映射在 `$4000-$4013`、`$4015`、`$4017`；五个通道：two pulse, triangle, noise, DMC。
- [NESdev Wiki: APU Pulse](https://www.nesdev.org/wiki/APU_Pulse)
  - 两个 pulse/square 通道；可变 duty；包含 timer 等结构。
- [NESdev Wiki: APU Triangle](https://www.nesdev.org/wiki/APU_Triangle)
  - Triangle 产生 pseudo-triangle；没有音量控制，波形要么运行要么暂停。
- [NESdev Wiki: APU Noise](https://www.nesdev.org/wiki/APU_Noise)
  - Noise 产生 pseudo-random 1-bit noise，16 种频率，包含 timer 与 LFSR。
- [NESdev Wiki: NSF](https://www.nesdev.org/wiki/NSF)
  - NSF 存储 NES 音乐代码和头信息；NSF player 把代码装入内存，初始化声音硬件，然后运行以产生音乐；包含 init/play address 与 play speed 等概念。

### 2.5 关键事实的可复查定位

这张表用于避免答辩稿“凭印象讲”。如果某页被追问依据，优先回到这些源码/脚本位置核对。

| 事实 | 本地可复查位置 |
|---|---|
| GME dumper 不是自己实现 6502，而是借 GME 运行 6502 + 2A03，并 hook APU 写寄存器。 | `script/gme_dump/dump_main.cpp:4-11`、`script/gme_dump/PATCH.md:4-18` |
| dump 输出格式是 `frame addr value`，DMC `$4010-$4013` 在 dumper 侧跳过。 | `script/gme_dump/dump_main.cpp:18-19`、`script/gme_dump/dump_main.cpp:37-42` |
| `encode.py` 输出 Logisim `v2.0 raw`，每个 token 是 16-bit 指令字。 | `script/encode.py:7`、`script/encode.py:218-220` |
| `$4015` 映射到 `reg_id=9`，`$4009/$400D/$4017` 等丢弃。 | `script/encode.py:20-21`、`script/encode.py:56-63` |
| DMC 地址范围在编码器侧也被跳过。 | `script/encode.py:47`、`script/encode.py:82` |
| 每帧先输出 WRITE，再补 WAIT 到 `frame_cycles`；默认 32，并要求 CPU 真解释 WAIT 才有节奏意义。 | `script/encode.py:33-37`、`script/encode.py:172-192` |
| ROM 结尾追加 `END`。 | `script/encode.py:214` |
| 频率表输出真实 NES Hz，不按 Logisim 时钟缩放。 | `script/make_tables.py:9-10` |
| Pulse/Triangle 频率公式、Buzzer 14-bit 频率范围、Noise 近似边界。 | `script/make_tables.py:18-23`、`script/make_tables.py:38-46` |
| 频率 ROM 文件和位宽：Pulse/Triangle 11→14，Noise 4→14。 | `script/make_tables.py:94-101` |
| `timer=253` 约 440Hz 的校验点。 | `script/make_tables.py:103-108` |
| 最终播放列表脚本是 4 曲，`FRAME_CYCLES=32`、`PERIOD_SCALE=1.0`、`DEDUP=True`。 | `script/make_playlist.py:4`、`script/make_playlist.py:40-45` |
| 生成 4 个曲目槽，并清理旧 `track04..15`。 | `script/make_playlist.py:70-96` |
| 蜂鸣器（Buzzer）端口常量：`FREQ/ENABLE/VOL/PW`。 | `ref/logisim-evolution/src/main/java/com/cburch/logisim/std/io/extra/Buzzer.java:53-56` |
| 蜂鸣器（Buzzer）波形选项包含 Sine/Square/Triangle/Sawtooth/Noise。 | `ref/logisim-evolution/src/main/java/com/cburch/logisim/std/io/extra/Buzzer.java:66-79` |
| 蜂鸣器（Buzzer）`propagate()` 读取 `ENABLE/FREQ/PW/VOL` 并设置 `updateRequired=true`。 | `ref/logisim-evolution/src/main/java/com/cburch/logisim/std/io/extra/Buzzer.java:224-254` |
| 蜂鸣器（Buzzer）端口位宽：`FREQ` 14-bit，`ENABLE` 1-bit，`PW` 8-bit，`VOL` 可配。 | `ref/logisim-evolution/src/main/java/com/cburch/logisim/std/io/extra/Buzzer.java:262-286` |
| 蜂鸣器（Buzzer）有效频率 20-20000Hz，重建缓冲并重新打开 `Clip`。 | `ref/logisim-evolution/src/main/java/com/cburch/logisim/std/io/extra/Buzzer.java:343-352`、`ref/logisim-evolution/src/main/java/com/cburch/logisim/std/io/extra/Buzzer.java:358-412` |
| 源码注释提醒不要把 4kHz 时钟直接接到 enable。 | `ref/logisim-evolution/src/main/java/com/cburch/logisim/std/io/extra/Buzzer.java:432` |
| 计数器（Counter）清零异步、加载优先于计数、`EN/UD` 悬空不等于 false、向下计数目标为 0、Carry 由当前目标比较得到。 | `ref/logisim-evolution/src/main/java/com/cburch/logisim/std/memory/Counter.java:521-595` |
| Logisim 左上角显示 full cycles per second，源码里 `ticksPerSecond / 2.0`。 | `ref/logisim-evolution/src/main/java/com/cburch/logisim/gui/main/TickCounter.java:119-120` |
| 低频自动节拍依赖睡眠等待，Windows 下会受毫秒级定时器精度影响。 | `ref/logisim-evolution/src/main/java/com/cburch/logisim/circuit/Simulator.java:456-463` |
| `cpu.circ` 有 CPU 子电路、`instr` 输入、`pcbus` 输出、`wr/frame_commit` 输出。 | `cpu.circ:56`、`cpu.circ:152`、`cpu.circ:336`、`cpu.circ:360-366` |
| `cpu.circ` 有 WAITCNT、busy、R0-R3、加法器（Adder）/减法器（Subtractor）/比较器（Comparator）。 | `cpu.circ:928-967` |
| `apu.circ` 有 RegFile、Channel_Pulse、Channel_Triangle、Channel_Noise、APU 顶层和四通道实例。 | `apu.circ:797`、`apu.circ:1100`、`apu.circ:1361`、`apu.circ:1545`、`apu.circ:1681`、`apu.circ:1786-1794` |
| `apu.circ` 的 Channel 子电路包含频率 ROM、蜂鸣器（Buzzer）和采样寄存器。 | `apu.circ:1167-1177`、`apu.circ:1417-1427`、`apu.circ:1592-1602` |
| `top.circ` 装配 CPU、APU、4 个 ROM 和 4:1 多路复用器（Multiplexer）。 | `top.circ:478-480`、`top.circ:484`、`top.circ:5049`、`top.circ:9726`、`top.circ:15887` |
| `top.circ` 控制面板含 reset、tempo、四路声道开关。 | `top.circ:110-158` |

## 3. 建议 PPT 页结构

### 第 1 页：标题与项目一句话

**页标题建议**  
Logisim NSF 音乐播放器

**本页任务**  
让评委在 20 秒内知道项目不是普通播放器，而是在 Logisim 里用 CPU + APU 播真实 NES 音乐。

**本页必须传达**

- 输入：真实 `.nsf` 文件。
- 核心：自制 16-bit 五段 CPU。
- 输出：简化 2A03 APU，用 Logisim 蜂鸣器（Buzzer）发声。
- 价值：把 NES 音乐播放过程拆成“软件 dump → ROM 指令 → 硬件执行 → 声音输出”的闭环。

**建议讲稿**

> 我们做的不是把音频文件塞进 Logisim，也不是手写几段旋律。输入是真实 NES 的 NSF 音乐文件。我们先把 NSF 运行过程中对 2A03 APU 的寄存器写入记录下来，转成 Logisim 能读的 ROM；然后用自制 16-bit 五段 CPU 逐条执行这些指令，驱动一个简化的 Buzzer APU 发声。

**证据来源**

- `plan/SESSION_HANDOFF.md`：项目目标、五段 CPU + Buzzer APU、真实 NES NSF。
- `plan/detailed_plan.html`：总架构 `.nsf → GME dumper → register log → ROM → CPU + APU → Buzzer`。

**不要展开**

- 不要在第一页讲具体电路细节。
- 不要先讲 UI、按钮、截图。

### 第 2 页：整体数据流

**页标题建议**  
从 NSF 到 Logisim 出声：一条确定的数据链

**本页任务**  
建立整场答辩的骨架，后面每部分都回到这条链。

**本页必须传达**

数据链：

```text
.nsf
  → GME 运行 6502/2A03
  → hook APU 写寄存器
  → frame addr value 日志
  → encode.py 生成 WAIT/WRITE/END 指令 ROM
  → CPU 执行 ROM
  → APU RegFile 和通道逻辑
  → Buzzer 出声
```

**每个环节一句解释**

- NSF：NES 音乐格式，内部是音乐播放代码，不是 WAV。
- GME：成熟模拟器，负责正确运行 NSF 的 6502/2A03 逻辑。
- dump：记录“每帧写了哪个 APU 寄存器、写了什么值”。
- encode：把写入事件变成 CPU 指令。
- CPU：按时序重放这些写入。
- APU：把寄存器值翻译成 Buzzer 输入。

**建议讲稿**

> 我们把问题拆成两半：离线阶段只负责把真实 NSF 变成确定的寄存器写入序列；硬件阶段只负责按时序重放这些写入。这样 Logisim 里不需要实现完整 6502 和完整 2A03，只需要实现本项目需要的 CPU 指令和简化 APU。

**证据来源**

- `script/gme_dump/dump_main.cpp` 注释：GME 运行 6502 + 2A03，hook 写寄存器。
- `script/encode.py` 注释和 `encode()`：日志转 16-bit 指令 ROM。
- NESdev NSF 页面：NSF player 加载音乐代码、初始化声音硬件并运行。

**截图建议**

- 本页可以不放电路截图，放数据链文字即可。
- 如果必须放图，放脚本目录和 `script/out/track00.txt` 的文件列表截图即可，不要占用太多讲解时间。

### 第 3 页：2A03 / APU 出声原理

**页标题建议**  
2A03 的声音本质：CPU 写 APU 寄存器

**本页任务**  
用最少背景知识解释 NES 声音为什么可以被“寄存器写入序列”描述。

**本页必须传达**

- NES 的 RP2A03 里包含 CPU 和 APU。
- APU 寄存器映射在 `$4000-$4013`、`$4015`、`$4017`。
- APU 有 5 个通道：2 个 Pulse、Triangle、Noise、DMC。
- 本项目实现前 4 类声音，DMC 采样通道按范围裁剪。
- CPU 播放音乐时反复运行 PLAY 例程，改变这些 APU 寄存器。

**可以讲的波形科普**

- Pulse：方波/脉冲波，可变占空比；适合主旋律、和声。
- Triangle：三角波；NESdev 说明没有音量控制，常用于低音或稳定旋律。
- Noise：伪随机 1-bit 噪声，16 种频率；常用于鼓点和噪声效果。
- DMC：采样通道；本项目不实现，脚本直接跳过 `$4010-$4013`。

**建议讲稿**

> NES 音乐不是普通音频流，而是 CPU 不断写 APU 寄存器。比如方波通道的 timer 决定音高，占空比决定音色，音量寄存器决定响度，`$4015` 决定声道开关。只要我们能记录这些写入，再按相同节奏重放，就能复现旋律和主要配器。

**证据来源**

- NESdev APU 页面：APU 所在芯片、寄存器范围、5 个通道。
- NESdev APU Pulse / Triangle / Noise 页面：各通道基本性质。
- `script/gme_dump/dump_main.cpp`：DMC `$4010-$4013` 跳过。
- `script/encode.py`：`$4015`、`$4009/$400D/$4017`、DMC 的处理策略。

**不要讲错**

- 不要说本项目完整还原 2A03。应说“保留主要四通道，DMC 与扩展音源是已知裁剪”。
- 不要说 Noise 完全等同 NES LFSR。项目的 Noise 是 Buzzer 近似。

### 第 4 页：为什么能搬到 Logisim 蜂鸣器（Buzzer）

**页标题建议**  
Logisim 蜂鸣器（Buzzer）刚好提供频率、音量、占空比和波形

**本页任务**  
解释“真实 2A03 的寄存器逻辑”怎样落到 Logisim 现成 Buzzer 组件上。

**本页必须传达**

Buzzer 源码确认的接口：

- `FREQ`：14-bit 输入。
- `ENABLE`：1-bit 输入。
- `VOL`：音量输入，位宽可配置。
- `PW`：8-bit duty cycle。
- 波形（Waveform）：Sine、Square、Triangle、Sawtooth、Noise。

项目映射：

- Pulse timer → `freq_pulse` ROM → Buzzer `FREQ`。
- Pulse duty → Buzzer `PW`。
- Pulse/Noise volume → Buzzer `VOL`。
- `$4015` 声道使能 + `ch_mask` → Buzzer `ENABLE`。
- Triangle 用 Buzzer Triangle 波形，固定音量。
- Noise 用 Buzzer Noise 波形，但频率映射做低频近似。

**建议讲稿**

> 我们没有自己在 Logisim 里做高频波形发生器，而是把 2A03 寄存器解释成 Buzzer 的四个输入。Buzzer 本身负责按真实时间生成波形，所以我们只要把 NES 的 timer 查表成真实 Hz，就能让音高正确。

**证据来源**

- `Buzzer.java`：
  - `FREQ/ENABLE/VOL/PW` 常量定义。
  - `updateports()` 中 `FREQ` 14-bit、`ENABLE` 1-bit、`PW` 8-bit。
  - `BuzzerWaveform` enum 中 Sine/Square/Triangle/Sawtooth/Noise。
- `make_tables.py`：Buzzer Frequency 14-bit、真实 Hz、不做时钟缩放。

**截图建议**

- 截 `apu.circ` 的 `BuzzerStress` 或 `PulseOneShot`。
- 要能看清：时钟（Clock）/计数器（Counter）/Splitter（分线器）取高位/`freq_pulse` ROM/蜂鸣器（Buzzer）。
- 本页截图用途：证明 Buzzer 链路已经实测，而不是只停留在理论。

### 第 5 页：Buzzer 源码边界与工程对策

**页标题建议**  
Buzzer 可用，但不能让高速时钟每拍改它

**本页任务**  
主动解释 Buzzer 的风险和项目为什么没有踩坑。

**本页必须传达**

源码边界：

- `propagate()` 每次输入变化都会设置 `data.updateRequired = true`。
- 音频线程发现 update 后，会按当前 `hz/wf/pw/vol` 重算缓冲。
- 源码中构造 `byte[4 * sampleRate]`，然后用 `AudioSystem.getClip()` 打开新的 `Clip`。
- 有效频率范围是 20-20000Hz。
- 源码注释明确提醒：不要把 4kHz 时钟接到 enable。

工程对策：

- BuzzerStress 中不能让计数器低位直接高速扫 ROM；要用 Splitter（分线器）取计数器高位，约 60Hz 换频。
- 真播放器里不是计数器扫曲谱，而是 CPU 执行 `WAIT` 停 PC，让音乐帧率约 60Hz。
- APU 内部用采样寄存器，CPU 用 `frame_commit` 在一帧写完后更新 Buzzer 参数，避免采到半更新寄存器组合。
- `encode.py` 还提供颤音死区、音量保持、最大更新率等软件侧节流选项。

**建议讲稿**

> Buzzer 的最大风险是参数变化太频繁。源码里每次输入变化都会触发音频缓冲重建，所以我们不能把 2kHz 或 4kHz 时钟直接变成每拍换音。我们的处理是两层：测试电路里用高位分频，真实播放器里靠 CPU 的 WAIT 把快时钟分成音乐帧率，并且一帧写完后才提交到 Buzzer。

**证据来源**

- `Buzzer.java`：`updateRequired`、缓冲构建、`Clip` 重建、20-20000Hz、4kHz enable 注释。
- `plan/SESSION_HANDOFF.md`：BuzzerStress 高位分频实测通过；真播放器靠 WAIT stall。
- `milestone2_guide.html`：按帧采样门控与 `frame_commit`。
- `encode.py`：节流函数 `throttle()` 和相关参数。

**不要讲错**

- 不要说 Buzzer 完全没有音质问题。要说“音高和主旋律可用；每帧包络/颤音可能有重建噪，项目有硬件限速和软件过滤对策”。
- 不要说低频 60Hz 自动节拍直接可靠。Windows 上 Logisim 低频自动节拍不准，项目采用 >1000Hz 时钟 + 电路/WAIT 分频。

### 第 6 页：NSF 转 Logisim ROM 的脚本工具链

**页标题建议**  
脚本不是生成声音，而是生成 CPU 能执行的谱面

**本页任务**  
证明脚本链路合理、可复现、和硬件边界清楚。

**本页必须传达**

阶段一：GME dumper

- 不自己实现 6502。
- 借 game-music-emu 运行 NSF。
- hook `Nes_Apu::write_register`。
- 每次 APU 写入记录成 `frame addr value`。
- PLAY 帧号来自 GME frame hook。
- DMC `$4010-$4013` 跳过。

阶段二：`encode.py`

- 输入寄存器日志。
- 输出 Logisim `v2.0 raw` ROM。
- 指令 16-bit 定长。
- 每帧先发本帧的 `WRITE`。
- 再补 `WAIT = frame_cycles - 本帧写入数`。
- 空帧合并为整段等待。
- 最后追加 `END`。

一句话可行性：

> NSF 播放最终会表现为每帧对 APU 寄存器的确定写入序列；记录并按相同时序重放这些写入，就能驱动简化 APU 复现主要音乐信息。

**建议讲稿**

> 这里的关键不是“脚本替硬件播放”，而是脚本把真实 NSF 的播放行为离线展开成 ROM。进入 Logisim 以后，所有时序仍由 CPU 的 PC、WAIT 和写脉冲决定。

**证据来源**

- `dump_main.cpp` 注释和 `gme_apu_dump_write()`。
- `PATCH.md`：GME hook 点和 3 处最小改动。
- `encode.py`：指令格式、`map_reg()`、`encode()`、`emit_wait()`、`write_rom()`。
- NESdev NSF 页面：NSF player 加载代码并运行以产生音乐。

**截图建议**

- 可放脚本输出目录 `script/out/` 的文件列表。
- 可放 `track00.txt` 开头几行，展示 `v2.0 raw` 与十六进制指令。
- 不建议放大段 Python 代码，答辩时间不够。

### 第 7 页：ROM、ISA 与寄存器映射

**页标题建议**  
CPU 读的 ROM 是 16-bit 定长指令流

**本页任务**  
让评委理解 CPU 为什么能“读谱”：ROM 的每个字就是一条固定格式指令。

**本页必须传达**

ISA 基础：

| opcode | 指令 | 作用 | 本项目用途 |
|---|---|---|---|
| `0x0` | `WAIT imm12` | 等待若干周期 | 形成音乐帧间时值 |
| `0x1` | `WRITE reg,val` | 写 APU 寄存器 | 回放主体 |
| `0x2` | `LWAIT` | 长等待 | 兼容，普通曲少用 |
| `0x4` | `LOADI` | 写通用寄存器 | ALU demo |
| `0x5` | `ADD` | 加法 | ALU demo / 可控加减 |
| `0x6` | `SUB` | 减法 | ALU demo / 可控加减 |
| `0x7` | `WRITEREG` | R 值写 APU | ALU 结果参与 APU |
| `0xF` | `END` | 曲目结束/循环 | PC 装 0 |

寄存器映射：

- `reg0-3`：Pulse1，原 `$4000-$4003`。
- `reg4-7`：Pulse2，原 `$4004-$4007`。
- `reg8/10/11`：Triangle，原 `$4008/$400A/$400B`。
- `reg9`：重映射 `$4015` 声道使能。
- `reg12/14/15`：Noise，原 `$400C/$400E/$400F`。
- `$4009/$400D/$4017` 和 DMC 写入丢弃。

位宽：

- PC 16-bit。
- 指令 ROM：`addrWidth=16`、`dataWidth=16`。
- 频率表：
  - `freq_pulse.txt`：addr 11 / data 14。
  - `freq_triangle.txt`：addr 11 / data 14。
  - `freq_noise.txt`：addr 4 / data 14。

**建议讲稿**

> 固定 16 位指令让硬件简单：PC 给地址，ROM 出一条 16 位指令，Splitter 拆高 4 位 opcode 和低位操作数。真实播放主要靠 WAIT、WRITE、END；ALU 相关指令用于满足可控加减和演示。

**证据来源**

- `encode.py`：指令格式、`map_reg()`、`emit_wait()`、`words.append(0xF000)`。
- `detailed_plan.html`：ISA 表、寄存器映射、总线位宽。
- `SESSION_HANDOFF.md`：PC 16-bit、`$4015 → reg_id=9`、APU reg 映射。
- `make_tables.py`：频率 ROM 位宽。

**不要讲错**

- 不要说 `frame_cycles=32` 自己会让 ROM 慢下来。必须强调：只有 CPU 真执行 `WAIT` 并停 PC，`frame_cycles` 才有意义。
- 不要继续讲 16 槽最终播放列表。当前 `make_playlist.py` 是 4 曲。

### 第 8 页：APU 总体结构

**页标题建议**  
APU：CPU 写口、RegFile 和四个独立声道

**本页任务**  
从电路角度解释 APU 的模块边界。

**本页必须传达**

APU 对外输入：

- `reg_id(4)`：写哪个 APU 寄存器。
- `value(8)`：写入的字节。
- `WR(1)`：写脉冲。
- `frame_clk(1)`：把稳定寄存器值提交到 Buzzer 前采样寄存器。
- `ch_mask(4)`：手动声道开关，bit0=Pulse1, bit1=Pulse2, bit2=Triangle, bit3=Noise。

APU 内部：

- `RegFile`：译码器（Decoder）+ 8-bit 寄存器（Register）组。
- `Channel_Pulse`：复用于 Pulse1/Pulse2。
- `Channel_Triangle`。
- `Channel_Noise`。
- 声道使能：歌曲 `$4015` 低 4 位 AND `ch_mask`。

**建议讲稿**

> APU 对 CPU 很简单，就是一个内存映射写口。CPU 不需要知道每个声道怎么发声，只要把 `reg_id/value` 和 `WR` 给到 APU。APU 内部的 RegFile 保存这些寄存器，再由各声道把寄存器解释成 Buzzer 输入。

**证据来源**

- `apu.circ`：
  - `RegFile` 子电路。
  - `Channel_Pulse`、`Channel_Triangle`、`Channel_Noise`。
  - `APU` 顶层输入 `ch_mask/frame_clk/WR/reg_id/value`。
- `milestone2_guide.html`：RegFile、Channel_Pulse、四通道、`ch_mask`。
- `SESSION_HANDOFF.md`：APU reg 映射。

**截图建议**

- 截 `apu.circ` 的 `APU` 顶层。
- 截图要能看清：
  - `reg_id/value/WR/frame_clk/ch_mask` 入口。
  - RegFile。
  - 四个 Channel 子电路。
  - 声道使能分线。
- 如果 APU 总览太大，就另截 RegFile 局部：译码器（Decoder）+ 多个寄存器（Register）+ `regN_out`。

### 第 9 页：APU 每个声道怎么实现，ROM 值怎么来

**页标题建议**  
声道实现：寄存器拼 timer，查频率 ROM，喂 Buzzer

**本页任务**  
回答“APU 每个 channel 的实现方案”和“ROM 值怎么定”。

**本页必须传达**

Pulse1 / Pulse2：

- 寄存器：
  - Pulse1：`reg0/reg2/reg3`。
  - Pulse2：`reg4/reg6/reg7`。
- timer 拼接：
  - 低 8 位来自 timer low 寄存器。
  - 高 3 位来自 timer high 寄存器。
  - 得到 11-bit timer。
- 频率表：
  - 查 `freq_pulse.txt`。
  - 公式：`f = 1789773 / (16 * (timer + 1))`。
  - `timer=253` 约为 440Hz A4，已作为音高校验点。
- Buzzer：
  - 波形 Square。
  - `VOL` 来自低 4 位音量。
  - `PW` 来自 duty 位映射。
  - `ENABLE` 来自 `$4015` 与 `ch_mask`。

Triangle：

- 寄存器：`reg10/reg11` 组成 11-bit timer。
- 频率表：`freq_triangle.txt`。
- 公式：`f = 1789773 / (32 * (timer + 1))`。
- Buzzer 波形 Triangle。
- 真实 Triangle 没有音量控制，本项目固定音量、用 enable 控制响/不响。

Noise：

- 寄存器：`reg12` 音量，`reg14[3:0]` 噪声索引。
- 频率表：`freq_noise.txt`，16 项。
- 不是直接用 NES LFSR 时钟；因为 Buzzer 的 Noise 是按 Hz 周期铺随机块，直接用高频会刺耳。
- 本项目把 16 档映射到 40-200Hz 的低频区间，作为可听近似。

**建议讲稿**

> 所有声道结构都一样：从寄存器里取参数，转成 Buzzer 能理解的频率、音量、占空比和使能。Pulse 和 Triangle 的核心是 11-bit timer 查表；Noise 的核心是 4-bit code 查表。ROM 值不是手填，是 `make_tables.py` 根据 NES 公式和 Buzzer 边界生成。

**证据来源**

- `make_tables.py`：
  - Pulse/Triangle 公式。
  - `freq_pulse/freq_triangle/freq_noise` 位宽。
  - Noise 的 Buzzer 近似说明。
- NESdev APU Pulse / Triangle / Noise 页面。
- `apu.circ`：Channel_Pulse、Channel_Triangle、Channel_Noise 内部 ROM 和 Buzzer。
- `milestone1_guide.html`：PulseOneShot timer=253 输出 440Hz。

**截图建议**

- 截 `Channel_Pulse` 内部。
- 必须看清：
  - Splitter（分线器）拼 11-bit timer。
  - `freq_pulse` ROM。
  - 蜂鸣器（Buzzer）FREQ/VOL/PW/ENABLE。
- 如果时间允许，可备一张 `Channel_Noise` 截图作为 Q&A 附录，不一定进正片。

### 第 10 页：CPU 总体数据通路

**页标题建议**  
CPU：单周期五段，重点是控制而不是流水线

**本页任务**  
进入答辩重点：CPU 的整体组织。

**本页必须传达**

CPU 五段：

- IF：PC → 指令 ROM / 外部 `instr` 总线。
- ID：Splitter（分线器）拆 `opcode/reg_id/value/imm/Rd/Ra/Rb`。
- EX：ALU、WAIT 状态机。
- MEM：APU 写口，产生 `reg_id/value/wr/frame_commit`。
- WB：PC 更新、R0-R3 写回。

实现选择：

- 单周期五段，不做流水线；老师已确认不要求流水线。
- PC 用 16-bit 计数器（Counter），不是普通寄存器 + 加法器。
- 最终 top 中指令 ROM 外置：
  - CPU 输出 `pcbus`。
  - top 中多个 ROM 并联地址。
  - 多路复用器（Multiplexer）选当前曲目的 `instr` 回灌 CPU。
- 这样 CPU 和存储器边界更清晰，也支持多曲切换。

**建议讲稿**

> 这里的五段是逻辑阶段，不是流水线。我们把一条指令在一个时钟周期内走完 IF、ID、EX、MEM、WB。只有 WAIT 是多周期指令，它通过状态机让 PC 保持。最终版 CPU 不内置固定曲目 ROM，而是暴露 `pcbus` 和 `instr`，让 top 用多个 ROM 和多路复用器（Multiplexer）做切歌。

**证据来源**

- `milestone3_guide.html`：单周期五段、PC 计数器、WAIT 状态机。
- `milestone4_guide.html`：指令 ROM 外置、CPU ↔ 存储器分离、4 曲 4:1 多路复用器（Multiplexer）。
- `cpu.circ`：`CPU` 子电路、PC、WAITCNT、ALU、R0-R3。
- `top.circ`：CPU 实例、APU 实例、4 个 ROM、多路复用器（Multiplexer）。

**截图建议**

- 截 `cpu.circ` 的 CPU 全景。
- 重点框住：
  - PC 计数器（Counter）。
  - `pcbus` 输出与 `instr` 输入。
  - Splitter（分线器）和译码器（Decoder）。
  - WAITCNT。
  - ALU 区。
  - R0-R3。
  - APU 输出信号。

### 第 11 页：WAIT 停顿状态机

**页标题建议**  
WAIT 是 CPU 正确播放节奏的关键

**本页任务**  
讲清楚整个项目最容易被问的控制逻辑：为什么 WAIT 不死循环、为什么能形成音乐帧率。

**本页必须传达**

问题：

- `WAIT imm` 要让 PC 停在当前指令若干周期。
- 如果“看到 WAIT 就装载计数器”，PC 不动时会反复装载同一条 WAIT，进入死循环。

解决：

- 加 1-bit `busy` 寄存器（Register）。
- `start = is_wait AND !busy`：
  - 第一次遇到 WAIT，装载 WAITCNT，置 busy。
- `en_count = busy AND !at_zero`：
  - busy 期间 WAITCNT 向下计数。
- `at_zero`：
  - 来自 WAITCNT 的 Carry；Logisim 计数器（Counter）源码中向下计数的目标是 0。
- `busy_next = start OR en_count`。
- `stall = busy_next`：
  - stall=1 时 PC 不走。
  - 倒数到 0 后 stall 放行，PC+1，busy 清零。

写脉冲：

- `wr = (is_write OR is_writereg) AND clk`。
- 不能直接把 `is_write` 接 APU 的 WR，因为连续 WRITE 时电平不下降，会丢写入边沿。

帧提交：

- `frame_commit = start AND clk`。
- 含义：本帧 WRITE 全部执行完，遇到 WAIT 时，APU 才采样 Buzzer 参数。

**建议讲稿**

> WAIT 的核心不是“慢时钟”，而是高速时钟下 CPU 主动停 PC。busy 标志防止 WAIT 被反复重装；WAITCNT 倒到 0 后 PC 才放行。这样 `frame_cycles=32` 这种编码器节奏预算才真正生效。

**证据来源**

- `milestone3_guide.html`：WAIT busy 状态机、`WR=is_write·clk`、`frame_commit=start·clk`。
- `Counter.java`：加载优先于计数、向下计数目标为 0、Carry 输出。
- `SESSION_HANDOFF.md`：WAIT n 实占 n+2 拍，但每帧均匀常数，可由节拍频率/ALU 修正。
- `encode.py`：每帧补 WAIT 到固定 `frame_cycles`。

**截图建议**

- 截 CPU 的 WAIT 局部。
- 必须看清：
  - WAITCNT 向下计数器（Counter）。
  - busy 寄存器（Register）。
  - `start/en_count/busy_next/stall` 逻辑门。
  - Carry → `at_zero`。
  - PC 的计数使能由 `!stall` 控制。

**不要讲错**

- 不要说 WAIT 精确占 imm 拍。当前结构实占 `imm+2`，但每帧常数均匀；里程碑 4 ALU 可在装载路径上修正。
- 不要把 `frame_cycles=32` 说成 ROM 自带分频。它必须依赖 CPU WAIT 停 PC。

### 第 12 页：ALU、R0-R3 与存储单元

**页标题建议**  
ALU 不是孤立 demo：它参与真实播放变速

**本页任务**  
回应老师“可控加减运算”的要求，并说明 CPU 存储单元/寄存器堆设计。

**本页必须传达**

ALU 参与主功能：

```text
normal: effective_wait = imm
slow  : effective_wait = imm + tempo_delta
fast  : effective_wait = max(1, imm - tempo_delta)
```

- ALU 插在 `IMM → WAITCNT.D` 的路径。
- 慢速档用加法器（Adder）。
- 快速档用减法器（Subtractor）+ 比较器（Comparator）做下限钳位。
- 这意味着真实曲目播放时，每帧 WAIT 都经过 ALU，而不是只做展示。

R0-R3：

- 4 个 8-bit 通用寄存器（Register）。
- `LOADI`：立即数写 R。
- `ADD/SUB`：读两个 R，经 ALU，写回 Rd。
- `WRITEREG`：把 R 的值写到 APU 寄存器。
- 用多路复用器（Multiplexer）选择读口，用译码器（Decoder）选择写回寄存器。

存储单元：

- PC：16-bit 计数器（Counter）。
- WAITCNT：16-bit 向下计数器（Counter）。
- busy：1-bit 寄存器（Register）。
- R0-R3：4 个 8-bit 寄存器（Register）。
- APU RegFile：多组 8-bit 寄存器（Register）。

**建议讲稿**

> 这页最重要的是证明 ALU 不是摆设。我们不是只跑一个 `5+3=8` 的小实验，而是把 ALU 接到 WAIT 装载路径。切 slow/fast 时，真实音乐每一帧的等待长度都被加法器或减法器改变。R0-R3 和显式 ADD/SUB 保留，用来现场证明 CPU 也能执行通用加减指令。

**证据来源**

- `detailed_plan.html`：ALU 不能只做 demo，主线是 WAIT 变速播放。
- `milestone4_guide.html`：ALU 接 WAIT，快档钳位，R0-R3，`LOADI/ADD/SUB/WRITEREG`。
- `cpu.circ`：加法器（Adder）、减法器（Subtractor）、比较器（Comparator）、R0-R3 寄存器。

**截图建议**

- 截 CPU 的 ALU + R0-R3 区。
- 必须看清：
  - 加法器（Adder）。
  - 减法器（Subtractor）。
  - 比较器（Comparator）。
  - `tempo_mode/tempo_delta`。
  - ALU 输出接 WAITCNT 装载路径。
  - R0-R3 寄存器和读写多路复用器（Multiplexer）。

### 第 13 页：top.circ 顶层和控制面板

**页标题建议**  
top.circ 把 CPU、APU、曲目 ROM 和控制面板组装起来

**本页任务**  
讲清楚最终成品如何从子电路变成播放器。

**本页必须传达**

顶层组成：

- 通过 项目 → 加载库 → Logisim-evolution 库…（Project → Load Library → Logisim-evolution Library…）加载 `cpu.circ` 与 `apu.circ`。
- 放 CPU 实例。
- 放 APU 实例。
- 放 4 个 track ROM。
- 4 个 ROM 地址都接 CPU `pcbus`。
- 4 个 ROM 数据接 4:1 多路复用器（Multiplexer）。
- 曲号计数器（Counter）选择当前曲。
- 多路复用器（Multiplexer）输出 `instr` 回到 CPU。
- CPU 输出 `reg_id/value/wr/frame_commit` 接 APU。
- `ch_mask` 控制四路声道开关。

控制逻辑：

- 播放/暂停：门控 CPU 时钟。
- 停止：复位 CPU，并通过 `ch_mask=0` 静音。
- 上/下一首：曲号计数器加/减，同时复位 PC。
- 速度：`tempo_mode/tempo_delta` 送 CPU ALU。
- 声道开关：单独开/关 Pulse1、Pulse2、Triangle、Noise。

**建议讲稿**

> top 不是新算法，而是把 CPU、APU 和存储器按清晰边界接起来。这里最重要的设计是把指令 ROM 放到 CPU 外部：CPU 输出地址，top 选择当前曲目的 ROM 数据回灌 CPU，这样同一颗 CPU 可以播放多首曲子。

**证据来源**

- `milestone4_guide.html`：CPU_EXT/外部 ROM、4 曲 4:1 多路复用器（Multiplexer）、控制面板、`ch_mask`。
- `make_playlist.py`：最终 4 曲播放列表。
- `top.circ`：CPU、APU、4 个 ROM、Multiplexer、曲号计数器。

**截图建议**

- 截 `top.circ` 全景。
- 必须看清：
  - 控制按钮/开关。
  - 曲号计数器（Counter）。
  - 4 个 track ROM。
  - 4:1 多路复用器（Multiplexer）。
  - CPU 实例、APU 实例。
  - `tempo_mode/tempo_delta`。
  - `ch_mask` 四路开关/探针。
  - CPU→APU 的 `reg_id/value/wr/frame_commit`。

### 第 14 页：演示顺序、边界与结论

**页标题建议**  
演示收束：先证明能播，再证明为什么是硬件

**本页任务**  
把答辩从细节拉回项目贡献，并预留对缺陷的主动解释。

**本页必须传达**

演示顺序：

1. 打开 `top.circ`，播放一首真实 NSF 转出的曲目。
2. 切 normal / slow / fast，说明 ALU 正在改变 WAIT 时长。
3. 逐个关 Pulse1 / Pulse2 / Triangle / Noise，证明 APU 四通道独立。
4. 放大 CPU 局部：讲 PC、译码、WAIT busy、写脉冲、R0-R3。
5. 展示脚本输出：`.nsf → log → trackNN.txt`。

项目结论：

- 输入真实性：NSF 真实音乐文件。
- 转换可信：GME 运行真实播放逻辑，hook APU 写寄存器。
- 硬件完整：Logisim 里由 CPU 取指执行，不是脚本直接播放。
- 音高可信：Buzzer 吃真实 Hz，频率表来自 NES timer 公式。
- 节奏可信：CPU WAIT 停 PC，`frame_cycles` 形成音乐帧率。
- 可控加减：ALU 参与 WAIT 变速，并有 R0-R3 指令证明。

主动说明边界：

- DMC 和扩展音源裁剪。
- Noise 是 Buzzer 近似，不是真 NES LFSR 原声。
- Buzzer 参数变化会重建音频缓冲，所以强颤音/包络可能有爆破感；项目用 frame_commit 和脚本节流缓解。
- Logisim 低频自动节拍在 Windows 上不可靠，所以采用 >1000Hz 自动节拍 + WAIT/电路分频。

**建议讲稿**

> 最后可以总结成三点：第一，输入是真实 NSF；第二，转换的是 APU 寄存器写入，不是音频采样；第三，Logisim 里由 CPU 和 APU 电路按时序执行。项目的取舍是 DMC、扩展音源和完整噪声细节没有做，但 Pulse、Triangle 的音高、主要和声、节奏控制和 CPU/ALU 结构是完整可解释的。

**证据来源**

- `SESSION_HANDOFF.md`：当前状态、风险、时钟结论。
- `make_playlist.py`：最终 4 曲、VRC6 自动丢弃说明。
- `Buzzer.java`：Buzzer 重建缓冲与限制。
- `make_tables.py`：Noise 近似说明。
- `milestone4_guide.html`：top 演示建议、ALU 必做。

## 4. 可选备份页：答辩 Q&A

这页不一定放进正片，可以作为备注或最后备份。

### Q1：为什么不直接在 Logisim 里实现完整 6502 和完整 2A03？

回答：

> 课程目标是数字逻辑 CPU + APU 播放器，不是完整 NES 模拟器。完整 6502 和 2A03 工程量过大，所以我们把 NSF 的复杂执行离线交给 GME，把结果抽象成 APU 寄存器写入序列。Logisim 中实现的是播放所需的定长指令 CPU、WAIT 时序、ALU、APU 寄存器和声道逻辑。

依据：

- `dump_main.cpp`：借 GME 现成 6502+2A03。
- `detailed_plan.html`：项目范围和风险审计。

### Q2：为什么 Buzzer 频率不按 Logisim 时钟缩放？

回答：

> Buzzer 的 FREQ 输入由组件内部音频线程按真实墙上时间解释。Logisim 时钟影响的是 CPU 执行指令速度，也就是节奏；音高必须给真实 Hz。否则会把音高也一起拉快/拉慢。

依据：

- `make_tables.py`：真实 Hz、不缩放。
- `detailed_plan.html`：音高不缩放。
- `Buzzer.java`：FREQ 输入与音频线程。

### Q3：为什么 `frame_cycles=32` 能控制节奏？

回答：

> 编码器保证每帧固定预算：本帧 WRITE 执行完后补 WAIT。CPU 遇到 WAIT 会暂停 PC，所以每帧实际消耗固定数量的 CPU 周期。若没有 CPU WAIT，只用计数器扫 ROM，`frame_cycles` 完全不起作用。

依据：

- `encode.py`：每帧补 WAIT。
- `milestone3_guide.html`：WAIT stall 状态机。
- `SESSION_HANDOFF.md`：`frame_cycles=32` 只有 CPU 解释 WAIT 才生效。

### Q4：为什么 `$4015` 映射到 `reg_id=9`？

回答：

> 指令里的 `reg_id` 只有 4 bit，只能表示 16 个槽。`$4015` 超出 `$4000-$400F`，所以借真实 NES 未用的 `$4009` 槽，也就是 `reg_id=9`，承载声道使能。真实 `$4009/$400D` 写入丢弃，避免冲突。

依据：

- `encode.py`：`map_reg()`。
- `detailed_plan.html`：reg 映射说明。
- `SESSION_HANDOFF.md`：锁定架构决策。

### Q5：为什么有 `wr = is_write AND clk`？

回答：

> APU 的 WR 被寄存器（Register）当时钟边沿使用。连续两条 WRITE 时，如果直接接 `is_write`，电平会连续为 1，中间没有下降再上升，第二条可能不会形成写入边沿。用 `is_write AND clk` 可以保证每个 WRITE 周期都有一个干净脉冲。

依据：

- `milestone3_guide.html`：WRITE 写脉冲。
- `SESSION_HANDOFF.md`：`WR = is_write·clk` 避免连续 WRITE 丢第二条。

### Q6：ALU 是否只是为了展示？

回答：

> 不是。ALU 接在 WAIT 装载路径上，真实播放时每一帧都会计算 `effective_wait = imm ± tempo_delta`。所以切 normal/slow/fast 会影响真实曲目的节奏。R0-R3 的 ADD/SUB 只是额外可视化证明。

依据：

- `detailed_plan.html`：ALU 必须参与真实播放。
- `milestone4_guide.html`：ALU 接 WAIT 变速。
- `cpu.circ`：Adder/Subtractor/Comparator/R0-R3。

### Q7：为什么 Noise 不完全像原曲？

回答：

> NES Noise 是 LFSR 伪随机噪声；Logisim Buzzer 的 Noise 源码是随机值按 Hz 周期生成/平铺，听感不是完整 NES 噪声模型。因此本项目对 Noise 做 16 档低频近似，保留鼓点层次，但不承诺完全还原音色。

依据：

- NESdev APU Noise 页面：LFSR 与 16 种频率。
- `Buzzer.java`：Noise 波形和缓冲构建。
- `make_tables.py`：Noise 频率映射修正说明。

### Q8：为什么最终是 4 首，不是早期 16 首？

回答：

> 早期计划有 16 槽，但实际 Logisim 装 16 个大 ROM 会很重，而且会切到空槽。最终 `make_playlist.py` 生成 4 首连续槽位，top 用 2-bit 曲号和 4:1 多路复用器（Multiplexer），功能正确且更稳。

依据：

- `make_playlist.py`：最终 4 曲播放列表和清理旧槽位。
- `milestone4_guide.html`：按真实曲数 N 放 ROM，4 首用 4:1 多路复用器（Multiplexer）。
- `top.circ`：4 个 ROM + Multiplexer。

## 5. 截图清单

这些截图服务“证明你真的搭了电路”，不服务美观。

| 文件建议名 | 用在哪页 | 截图内容 | 必须看清 |
|---|---:|---|---|
| `01_buzzerstress.png` | 第 4 或 5 页 | `apu.circ` 的 BuzzerStress | 时钟（Clock）、计数器（Counter）、Splitter（分线器）取高位、`freq_pulse` ROM、蜂鸣器（Buzzer） |
| `02_apu_regfile.png` | 第 8 页 | `apu.circ` 的 APU 顶层或 RegFile | `reg_id/value/WR/frame_clk/ch_mask`，译码器（Decoder），寄存器（Register），四通道 |
| `03_apu_channel_pulse.png` | 第 9 页 | Channel_Pulse | `reg2/reg3` 拼 timer，`freq_pulse` ROM，Buzzer 的 FREQ/VOL/PW/ENABLE |
| `04_cpu_datapath.png` | 第 10 页 | `cpu.circ` CPU 全景 | PC、`pcbus/instr`、Splitter（分线器）、译码器（Decoder）、WAITCNT、ALU、R0-R3、APU 输出 |
| `05_cpu_wait.png` | 第 11 页 | WAIT 局部 | WAITCNT、busy、`start/en_count/busy_next/stall`、Carry→`at_zero`、PC 计数使能 |
| `06_cpu_alu_regs.png` | 第 12 页 | ALU + R0-R3 | 加法器（Adder）、减法器（Subtractor）、比较器（Comparator）、调速多路复用器（Multiplexer）、R0-R3 |
| `07_top_panel.png` | 第 13 页 | `top.circ` 总览 | 控制面板、4 个 ROM、4:1 多路复用器（Multiplexer）、CPU/APU、`ch_mask`、调速输入 |

## 6. 时间分配建议

| 部分 | 页 | 时间 | 目的 |
|---|---:|---:|---|
| 项目总览 | 1-2 | 1:00 | 让评委知道你做了什么 |
| 2A03 原理 | 3 | 1:00 | 建立“写寄存器=音乐”的基础 |
| Buzzer 可行性 | 4-5 | 1:40 | 证明 Logisim 声音方案不是拍脑袋 |
| 工具链与 ROM | 6-7 | 1:40 | 证明真实 NSF 如何进入电路 |
| APU | 8-9 | 1:40 | 解释四声道和频率表 |
| CPU | 10-12 | 2:40 | 答辩重点：五段、WAIT、ALU、寄存器 |
| Top 与演示 | 13-14 | 1:20 | 收束到成品和演示 |

如果时间被压缩到 8 分钟：

- 合并第 6、7 页，只讲脚本链路和 ISA 三条主指令。
- APU 第 9 页只讲 Pulse 和一句 Triangle/Noise。
- CPU 第 10-12 页不能删，只能压缩讲稿。

## 7. 最容易讲错的点

- 不要说“Buzzer 完整模拟 NES APU”。应说“Buzzer 负责基础波形，APU 负责寄存器解释，是简化近似”。
- 不要说“Logisim 时钟越快音高越高”。Buzzer 音高吃真实 Hz，时钟影响节奏。
- 不要说“`frame_cycles=32` 自动分频”。必须靠 CPU WAIT 停 PC。
- 不要说“低频 60Hz 自动节拍可靠”。本项目用 >1000Hz 自动节拍，再在电路里分频或用 WAIT。
- 不要说“Noise 完全还原”。Noise 是 Buzzer 近似，DMC 被裁剪。
- 不要说“ALU 只是演示”。ALU 参与 WAIT 变速，这是 CPU 重点之一。
- 不要说“16 首最终播放列表”。当前最终脚本和 top 是 4 首、4:1 多路复用器（Multiplexer）。
- 不要讲 Logisim 快捷键。
