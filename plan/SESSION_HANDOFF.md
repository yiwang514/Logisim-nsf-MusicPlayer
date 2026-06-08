# 会话交接文档 · SESSION HANDOFF

> 给下一个 session 的接手说明。先读这份,再按需读 `plan/` 下的详细文档和 `memory/`。
> 项目:在 Logisim Evolution v4.1.0 里搭五段 CPU + Buzzer APU,播放真实 NES 音乐(NSF)。
> 角色:用户是 B 组(脚本),但**实际在单刷整个项目**,还要带队友(A/C/D)过答辩。
> 截稿:**2026-06-15**。用户的 Logisim **界面是中文**。

---

## 0. 最重要的当前状态(一句话)
脚本工具链**全部完成并验证**;**里程碑 1 已实测通过**(Buzzer 高位分频扫表听感正常,固定 440Hz 长音音高正确)。**里程碑 2、3 的手把手施工指引均已写好**:`plan/milestone2_guide.html`(APU:RegFile 写口 + 可复用 Channel_Pulse + 按帧采样门控 + 扩 4 通道封 APU;输出脚已定为 `regN_out` 避开同名判重)、`plan/milestone3_guide.html`(CPU:单周期五段 + WAIT 停顿状态机 + WRITE/END,接 M2 APU 播 track00)。下一步 = 用户照指引在 `apu.circ`/`cpu.circ` 里实搭并实测(2–4kHz 自动节拍下 track00 出声、节奏稳、会循环),然后进里程碑 4(ALU 变速 + 控制面板)。

---

## 1. 已完成 ✅

### 1.1 转换脚本(全在 `script/`,已验证)
- `script/gme_dump/` —— 阶段一 dumper。hook **game-music-emu(GME)** 的 `Nes_Apu::write_register`,跑 NSF dump 出寄存器写日志。
  - `dump_main.cpp` + `Makefile`(g++ 构建,NSF-only)+ 编好的 `nsfdump.exe` + `PATCH.md`(GME 3 处 `#ifdef GME_APU_DUMP` 补丁说明)。
  - 构建坑都记在 PATCH.md:**不要用 `NSF_EMU_APU_ONLY`**(MinGW 堆越界)、`emu2413.c` 要 gcc 单独编、需 `-DBLARGG_LITTLE_ENDIAN=1` + 静态链接。
- `script/encode.py` —— 阶段二。日志 → **16-bit 定长指令** → Logisim `v2.0 raw` ROM。
  - 关键参数 **`--frame-cycles`(默认 32)**:每帧固定占 32 个 CPU 周期(WAIT 补齐),保证**节奏等时**。这就是"调速旋钮"。
  - `--dedup` 去重复写;`--period-scale` 音高缩放(默认 1.0,Buzzer 用真实 Hz **不要动**)。
- `script/make_tables.py` —— 生成频率换算查找表 ROM(真实 NES Hz,**不缩放**)。
- `script/make_playlist.py` —— 一键产出 16 槽播放列表。

### 1.2 已生成的 ROM 资产(`script/out/`,可直接喂 Logisim)
| 文件 | 内容 | Logisim ROM 设置 |
|---|---|---|
| `track00..15.txt` | 16 首歌指令 ROM(slot0=Monitoring t0,slot1=FF3 t31,其余 FF3 填充),4 分钟/首,dedup,frame_cycles=32 | **addrWidth=16, dataWidth=16** |
| `freq_pulse.txt` | Pulse timer(11位)→真实 Hz | addrWidth=11, dataWidth=14 |
| `freq_triangle.txt` | Triangle timer→Hz(低八度) | addrWidth=11, dataWidth=14 |
| `freq_noise.txt` | Noise `$400E`低4位→Hz(16项) | addrWidth=4, dataWidth=14 |

最大 ROM = track11 = 41044 字 → 16 个统一设 16-bit 地址。频率表 timer=253 → 440Hz(A4),已核验。

### 1.3 计划/指引文档(`plan/`)
- `detailed_plan.html` —— 给评审 agent 的完整方案 + 可行性审计 + 风险。
- `project_brief_v6.html` —— 原始计划书(已加"勘误"框;**第 10 节四人分工保持原样,勿改**)。
- `reviewed_execution_guide.html` —— 另一个 agent 的审阅修正版(和我们的一致)。
- **`milestone1_guide.html`** —— 当前在用的手把手施工指引,已做成:**多 circ 形式** + **中文(English) 双语操作** + 已补 Counter 时钟脚/ROM 加载对话框/找脚两招等修正。
- **`milestone2_guide.html`** —— 里程碑 2 指引(已写并二审修正可行性):RegFile(译码器+寄存器组,reg_id/value/WR 写口) + Channel_Pulse(双 Splitter 拼 11 位 timer→freq_pulse→Buzzer,音量/占空比/使能) + §4.5 ~60Hz 按帧采样门控 + §5 扩 Pulse2/Triangle/Noise 封 APU。已按 `ref/logisim-evolution` 修正:寄存器 CLR/EN 明确接常量、去掉快捷键、frame_clk 给精确 Counter 位表、接 CPU 后建议改接 `frame_commit` 避免采到半更新寄存器组合。**RegFile 输出脚命名为 `regN_out`**(同子电路标签必须唯一、与部件类型无关,源码 `Circuit.isExistingLabel()`;寄存器本身仍叫 `regN`、Channel_Pulse 输入仍叫 `regN`)。
- **`milestone3_guide.html`** —— 里程碑 3 指引(CPU,据 `ref/logisim-evolution` 源码核实):单周期五段 IF/ID/EX/MEM/WB,在新文件 `cpu.circ` 里搭,联调时 `项目→加载库` 把 `apu.circ` 拉进来播 track00。锁定的设计:**PC = 向上 Counter、WAIT 倒计时 = 向下 Counter**(省掉加法器/比较器);**WAIT 停顿状态机**用 1 位 `busy` 触发器破"重装死循环",化简出 `stall == busy_next`;**WAIT 计数器的进位(Carry)是组合输出、向下时 = 值==0**,直接当 `at_zero`(`Counter.java` propagate 已核实:Carry 组合、加载优先于计数、清除异步、使能/方向悬空按真);`WR = is_write·clk`(门控脉冲,否则连续 WRITE 丢第二条)、`END→PC 装 0` 循环、`frame_commit = start·clk` 接 APU `frame_clk`。诚实交代:WAIT n 实占 n+2 拍(每帧一条 WAIT,均匀常数,被节拍频率吸收;M4 的 ALU 在装载路径上减掉)。track00 仅含 WAIT/WRITE/END、无 LWAIT。

### 1.4 项目 Skill 和 Memory
- **`.claude/skills/logisim-zh-terms/SKILL.md`** —— Logisim 中英术语对照表(全部源码核实)。**写任何 Logisim 面向用户的文档时必须套用 `中文（English）` 双语形式。**
- `memory/`:`nsf-toolchain-gme-build.md`(GME 构建)、`logisim-hardware-plan.md`(硬件计划+风险)、`MEMORY.md`(索引)。

---

## 2. 锁定的架构决策(改这些会返工,已定)
- **ISA = 16-bit 定长**,高 4 位 opcode:`0x0 WAIT`(+imm12)、`0x1 WRITE`(+reg4+val8)、`0x2 LWAIT`、`0x3 WKEY`、`0x4 LOADI`、`0x5 ADD`、`0x6 SUB`、`0x7 WRITEREG`、`0xF END`。回放只用 WAIT/WRITE/END。
- **PC = 16-bit**(非计划书旧版的 12;曲子最长 41044 条 > 4096)。指令 ROM 地址 16/数据 16。
- **`$4015` 声道使能 → 重映射到 reg_id 9**(4-bit reg 只够 $4000-$400F;借未用的 $4009 槽)。`$4009/$400D/$4017`/DMC 丢弃。
- **音高不缩放**:Buzzer Frequency 吃真实 Hz、按墙上时间发声,与 Logisim 时钟无关。频率表输出真实 NES Hz。
- **ALU 是老师硬性要求**("可控加减"):LOADI/ADD/SUB/WRITEREG + R0–R3 + 真 ALU,必做。
- **"五段 CPU" = 单周期五阶段,老师确认不要流水线。**
- **多 circ 结构**:`top.circ`(A:顶层+控制面板+计时,=现有 coolproject.circ)、`cpu.circ`(C:CPU+ALU)、`apu.circ`(D:4通道+Buzzer)。top 用 `项目→加载库→Logisim-evolution 库…` 把 cpu/apu 当库加载。
- **APU reg 映射**:reg0-3=Pulse1,4-7=Pulse2,8/10/11=Triangle,**9=声道使能**,12/14/15=Noise。
- 完整总线位宽表见 `detailed_plan.html` §4。

---

## 3. 当前硬件进度(里程碑 1)
- 用户已在 Logisim 里搭 **任务 A(BuzzerStress)**:时钟（Clock）→计数器（Counter）→`freq_pulse` ROM→蜂鸣器（Buzzer）。
- 已解决的具体卡点:ROM 位宽要先设 11/14 再 `加载映像`(否则 14 位被砍成 8 位、音高全错);计数器**时钟脚**在左边带 ▷ 的 `2,3,5+/C6`(建议换"经典 Logisim"外观更好认);ROM 的 **D 是右边单根 14 位总线**(IEEE 外观把它标成 `A 0…13` 是位编号注解,不是 14 个脚)。
- **任务 A 关键验证已通过**:直连低 11 位会高速扫频/爆音;改成用 Splitter（分线器）取计数器高位后,播放速度恢复到正常听感。用户实测可行,只有一点点卡顿,大概率是扫表/频率步进不是整数音乐事件导致,后续可优化。推荐配置:
  - `仿真 → 自动节拍频率（Simulate → Auto-Tick Frequency）` 设 1000Hz,左上角约 500Hz,取 `Counter[13:3]` 接 ROM 地址 → 500/8≈62.5 次/秒。
  - 若设 2kHz,左上角约 1000Hz,取 `Counter[14:4]` 接 ROM 地址 → 1000/16≈62.5 次/秒。
- **任务 B(PulseOneShot)也已通过**:不接时钟,用手形工具（Poke Tool）/固定地址给 ROM 地址 253,蜂鸣器（Buzzer）能输出正确音高(440Hz A4),没有明显问题。Buzzer 作为本项目音频输出可继续使用。

---

## 4. ★ 已排查并实测确认的关键环境问题(务必让下个 session 知道)
**现象**:Logisim 左上角红字(那是"实测时钟频率",= 设定节拍频率 ÷ 2)在节拍 ≤1000Hz 时**死死卡在 ~32**(512/256/128 都是 32,64→20,32→13),但**1000Hz 能冲到 500**。

**根因(源码 `Simulator.java` 调度逻辑确认)**:
- 节拍 **>1000Hz**(间隔<1ms)→ Logisim 用**忙等待(自旋)** → 精确。
- 节拍 **≤1000Hz**(间隔≥1ms)→ 用 `awaitNanos()` 睡眠 → 被 **Windows 默认 ~15.6ms 定时器精度**凑整 → 每拍≥15.6ms → 封顶 ~64 ticks/s = ~32 周期/s。
- **不是** Buzzer、**不是**渲染、**不是** Logisim bug(图形加速那条是误判,已撤回)。

**结论与对策**:
- **始终用 >1000Hz 的节拍**(压测/播放都用 2–4kHz),自动绕开。
- 改 Windows 全局定时器(注册表 `GlobalTimerResolutionRequests=1` + 重启 + 挂 Chrome/定时器工具)**可行但不必要**,且费电。

**用户的核心洞察(很对)**:1kHz 时钟驱动"每拍换频率"的裸扫频 → Buzzer 爆音,因为"每秒上千次换音不符合音乐逻辑"。音乐换音率本该 **~40–100Hz**。
**答案 = 时钟分频**:时钟跑快(4kHz,精确),在电路里分频成 ~60Hz 的"音乐节拍"才换音。
- **重要修正**:`frame_cycles=32` 不是 Logisim 自动分频。它只有在 CPU 真正解释 `WAIT` 并让 PC stall 时才生效。若电路是 `Counter → 曲目 ROM 地址` 直连,2kHz/4kHz 会变成超高速扫内存,音乐一瞬间播完。
- **真实播放器的正确路径**:CPU 执行 `WRITE/WAIT/END`;`WAIT` 装载等待计数器并暂停 PC。这样 `frame_cycles=32` → 约 2000 完整周期/s ÷ 32 ≈ **62.5Hz 音乐帧率**。
- **BuzzerStress 的正确路径**:它不是 CPU,所以必须显式分频。已由用户实测:用 Splitter（分线器）取计数器高位当 `freq_pulse` ROM 地址,丢掉低位,可把换频率速度压到约 62.5Hz,听感恢复正常。

---

## 5. 接下来要做的 ⏭️(按优先级)

1. **里程碑 2、3 指引均已写好** ✅(`plan/milestone2_guide.html` + `plan/milestone3_guide.html`) —— **下一步是用户照指引在 Logisim 里实搭并实测**:先在 `apu.circ` 搭 APU(M2),再在新文件 `cpu.circ` 搭 CPU(M3)、用 `项目→加载库` 把 APU 拉进来联调,2–4kHz 自动节拍下播 track00(出声、节奏稳、会循环)。下面是 M2 指引覆盖的设计要点,供接手快速了解(M3 要点见 §1.3):
   - 4 个 8-bit 寄存器接收 `$4000/$4002/$4003/$4015` 写入;
   - **用 Splitter（分线器）把 reg2(低8)+reg3(低3)拼成 11-bit timer** → `freq_pulse` ROM → 蜂鸣器（Buzzer）;
   - 音量/占空比/使能接好;
   - 复制成 Pulse2/Triangle/Noise 四通道 → 封装 `APU` 子电路;
   - **设计里不要让高速 Clock 直接每拍改 Buzzer 频率**。若暂未接 CPU/WAIT,就先带一个约 60Hz 的写入/采样保持门控;等接 CPU 后,由 `WAIT` stall 保证音乐帧率,并优先把采样脉冲改接 CPU 的 `frame_commit`(本帧寄存器写完/进入 WAIT 时打一拍),避免自由跑 frame_clk 采到半更新状态。
   - **务必用 logisim-zh-terms skill 出双语 + 一次只写一个里程碑**(用户明确要求,防上下文爆炸)。

2. **(可选)** 把"**时钟跑快 · BuzzerStress 靠 Splitter（分线器）取高位分频 · 真播放器靠 WAIT stall**"这条核心原理,补一个小框进 `milestone1_guide.html`。

3. **里程碑 4**:CPU 核心(五段 + WAIT-stall busy 状态机 + WRITE/END)已由 M3 指引覆盖;M4 = 补 **ALU 变速播放**(老师硬性要求「可控加减」,接 WAIT 装载路径算 `imm±tempo_delta`,顺手把 M3 的 +2 拍精确化、做快档下限钳位) + `LOADI/ADD/SUB/WRITEREG` + R0–R3 可视化 demo + **控制面板**(`top.circ`,16-ROM MUX 切歌 + 播放/暂停/停止/上下一首 + 计时) + LWAIT(0x2,2 字长等待,track00 用不到、长静音曲才需)。届时 `top.circ` 用 `项目→加载库` 正式组装 cpu/apu。

4. **队友答辩防身指南(A/C/D 三份)** —— 用户要求但**明确说最后再做**,暂缓。

---

## 6. 给下个 session 的工作方式提醒
- **一次只推进一个里程碑/一份文档**,用户怕上下文爆炸。
- 写 Logisim 面向用户的内容 → **必须用 `logisim-zh-terms` skill 的双语术语**;**不要写死键盘快捷键**(偏好可配);Logisim 行为论断要去 `ref/logisim-evolution` 源码/`doc/en/html` 核实,别凭记忆。
- 节拍频率结论:**始终 >1000Hz 或至少用 1000Hz 这个实测可达点**;不要低频硬跑 60Hz。BuzzerStress 靠 Splitter（分线器）取高位分频;真播放器靠 `WAIT` stall 让 `frame_cycles` 生效。
- 用户偏好:严谨(对官方文档/源码)、人类可读(像计划书那种漂亮的 HTML)、中文沟通。
- 不要改 `project_brief_v6.html` 的第 10 节(四人分工)。

---
*更新于 2026-06-08。配套必读:`plan/milestone2_guide.html`、`plan/milestone3_guide.html`、`plan/detailed_plan.html`、`memory/logisim-hardware-plan.md`、`.claude/skills/logisim-zh-terms/SKILL.md`。*
