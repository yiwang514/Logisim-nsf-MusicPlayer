# GME hook 改动说明（ref/game-music-emu）

阶段一选用 **game-music-emu (GME)** 作为 hook 目标（而非 NSFPlay），原因：
`Nes_Apu::write_register` 是处理全部 `$4000-$4017` 写入的**单一函数**、自带 `time`
参数，且 CMake/g++ 都能编；NSFPlay 的写寄存器逻辑拆在 `nes_apu.cpp` + `nes_dmc.cpp`
两处、且没有现成时间戳。

为产出寄存器写日志，对 `ref/game-music-emu/` 做了 **3 处最小改动**，全部用
`#ifdef GME_APU_DUMP` 保护（不带该宏的正常构建零影响）：

## 1. gme/Nes_Apu.cpp —— write_register 加 hook
在 `$4000-$4017` 范围判断之后、`run_until_(time)` 之前插入：
```cpp
#ifdef GME_APU_DUMP
	{ extern void gme_apu_dump_write( int addr, int data ); gme_apu_dump_write( (int)addr, data ); }
#endif
```
每次对 APU 寄存器的写入都转发给 dumper（DMC `$4010-$4013` 在 dumper 侧跳过）。

## 2. gme/Nsf_Emu.cpp —— PLAY 帧计数
在 `run_clocks()` 里 `GME_FRAME_HOOK( this );` 之后插入：
```cpp
#ifdef GME_APU_DUMP
	{ extern void gme_apu_dump_frame(); gme_apu_dump_frame(); }
#endif
```
每次 PLAY 子程序被触发（NTSC ~60Hz）帧号 +1，作为日志时间戳。

## 3. gme/gme_types.h —— 精简为只启用 NSF/NSFE
把原本启用的 AY/GBS/GYM/HES/KSS/SAP/SPC/VGM 全部注释掉，只保留
`USE_GME_NSF` / `USE_GME_NSFE`。这样 `gme.cpp` 不会引用我们不编译的其它格式
模拟器（VGM 需要 Nuked OPN2 等）。如需恢复完整功能取消注释即可。

> 这三处改动都不影响 GME 的正常播放逻辑，只是把数据“旁路”出来。

## 构建注意事项（写进 Makefile 了，这里备忘）
- **不要用 `-DNSF_EMU_APU_ONLY`**：该精简路径在 MinGW 下会触发堆越界
  （`sram`/MMC5 边界判断），表现为运行期/teardown 不确定崩溃、退出码 127。
  改用 GME 默认的完整 NSF 链路（含全部扩展音源；示范曲是纯 2A03，扩展芯片只是
  链接进来不发声）。
- `-DBLARGG_LITTLE_ENDIAN=1`：MinGW 下 GME 字节序自动判定失效，手动指定。
- `ext/emu2413.c`（VRC7 用）是 **C** 代码，必须用 `gcc` 单独编成 `.o` 再链接，
  不能丢进 `g++`（有 `void*` 隐式转换等 C 习惯，C++ 报错）。
- `-static -static-libgcc -static-libstdc++`：静态链接，避免脱离 w64devkit 环境
  运行时找不到 DLL。
- `-std=c++14`：GME 0.6.6 老代码用到已废弃的 `register` 关键字等。

构建：`cd script/gme_dump && make`，产出 `nsfdump.exe`。
