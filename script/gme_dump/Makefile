# ============================================================================
# GME NSF dumper 构建文件（NSF-only / 2A03-APU-only 精简构建）
#   make            构建 nsfdump(.exe)
#   make clean      清理
#
# 设计说明：
#   - 不需要 cmake：GME 自带非 cmake 用的 gme/gme_types.h。
#     我们把它精简成只启用 NSF/NSFE（见 nsfplay_patch 说明），
#     这样 gme.cpp 不会去引用 VGM/SPC/AY 等其它格式的模拟器。
#   - 不需要 zlib：默认未定义 HAVE_ZLIB_H，普通 .nsf 不走 gzip 路径。
#   - -DNSF_EMU_APU_ONLY=1：只保留标准 2A03 APU，去掉 VRC6/7、FDS、MMC5、
#     Namco、FME7 等扩展音源。我们的示范曲(Monitoring/FF3)都是纯 2A03，
#     这样既正确又省去 emu2413(OPLL) 等额外依赖。
#   - -DBLARGG_LITTLE_ENDIAN=1：MinGW 下 GME 的字节序自动判定失效，手动指定。
#   - -DGME_APU_DUMP：启用我们在 gme/Nes_Apu.cpp 和 gme/Nsf_Emu.cpp 里加的 hook。
#   - -std=c++14：GME 0.6.6 老代码（用到已废弃的 register 关键字等），c++14 最稳。
#
# 因此只编译 NSF 链路真正需要的源文件（见 GME_SRCS），而不是 gme/*.cpp 全编。
# ============================================================================

GME    := ../../ref/game-music-emu
GMEDIR := $(GME)/gme

CXX      := g++
CC       := gcc
# 注意：不使用 NSF_EMU_APU_ONLY —— 该精简路径在 MinGW 下会触发堆越界（teardown 崩溃/
# 运行期不确定崩溃）。改用 GME 默认的"完整 NSF 链路"（含全部扩展音源），这是 CMake/
# 上游一直在用的、经测试的配置。我们的示范曲是纯 2A03，扩展音源只是链接进来但不参与发声。
CXXFLAGS := -std=c++14 -O2 -w \
            -DGME_APU_DUMP -DBLARGG_LITTLE_ENDIAN=1 \
            -I$(GME) -I$(GMEDIR)
# emu2413 是 C 代码（含 void*→指针 的隐式转换等 C 习惯），必须用 gcc 按 C 编译。
CFLAGS   := -O2 -w -I$(GMEDIR)/ext

# ---- GME 核心（所有格式共用）----
GME_CORE := Blip_Buffer Classic_Emu Data_Reader Dual_Resampler Effects_Buffer \
            Fir_Resampler Gme_File M3u_Playlist Multi_Buffer Music_Emu gme

# ---- NSF 链路 + 2A03 APU/CPU + 全部 NES 扩展音源（MMC5 为纯头文件，无 .cpp）----
GME_NSF  := Nsf_Emu Nsfe_Emu Nes_Apu Nes_Cpu Nes_Oscs \
            Nes_Fds_Apu Nes_Fme7_Apu Nes_Namco_Apu Nes_Vrc6_Apu Nes_Vrc7_Apu

GME_SRCS := $(addprefix $(GMEDIR)/,$(addsuffix .cpp,$(GME_CORE) $(GME_NSF)))

SRCS := $(GME_SRCS) dump_main.cpp

# 静态链接 libstdc++/libgcc/winpthread，避免在没有 w64devkit 环境的 shell 里
# 运行时找不到 DLL（否则启动直接失败/退出码 127）。
LDFLAGS := -static -static-libgcc -static-libstdc++

nsfdump: $(SRCS) emu2413.o
	$(CXX) $(CXXFLAGS) $(SRCS) emu2413.o $(LDFLAGS) -o nsfdump

# VRC7(OPLL) 依赖的 emu2413：单独用 gcc 编成 C 目标文件再链接。
emu2413.o: $(GMEDIR)/ext/emu2413.c
	$(CC) $(CFLAGS) -c $(GMEDIR)/ext/emu2413.c -o emu2413.o

clean:
	rm -f nsfdump nsfdump.exe emu2413.o

.PHONY: clean
