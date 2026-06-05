// ============================================================================
// dump_main.cpp  ——  NSF -> APU 寄存器写序列 dumper（阶段一）
//
// 思路：不自己实现 6502。借 game-music-emu(GME) 现成的、cycle-accurate 的
//       6502 + 2A03 APU。GME 内部"运行 6502 -> 写 APU 寄存器"时，每次对
//       $4000-$4017 的写都会经过 Nes_Apu::write_register。我们在那里加了一个
//       hook（见 gme/Nes_Apu.cpp，仅 -DGME_APU_DUMP 时启用），把每次写入转发到
//       本文件的 gme_apu_dump_write()，记录成一行 "frame addr value"。
//
//       帧号 frame = PLAY 子程序被调用的次数（NTSC ~60Hz），由 GME 的
//       GME_FRAME_HOOK 触发，转发到 gme_apu_dump_frame()。
//
// 用法： nsfdump <in.nsf> <track> <seconds> [out.log]
//   track   : 子曲目号，0-based（FF3 有 65 首=0..64；Monitoring 只有 0）
//   seconds : 录制秒数
//   out.log : 输出日志路径，默认 reg.log
//
// 输出每行： "<frame> <ADDR4hex> <VAL2hex>"，例如  12 4000 9F
//   - DMC 通道 $4010-$4013 按需求直接跳过、不记录。
// ============================================================================

#include "gme/gme.h"
#include <cstdio>
#include <cstdlib>

// ---- 与 GME 内部 hook 对接的两个全局回调（被 gme/*.cpp 里的 extern 声明调用）----
static FILE* g_dump_fp = 0;   // 日志文件句柄；为空时 hook 不记录（用于跳过 init 噪声）
static long  g_frame   = 0;   // 当前帧号 = PLAY 调用计数

// 每次 PLAY 触发：帧号 +1
void gme_apu_dump_frame()
{
    g_frame++;
}

// 每次对 $4000-$4017 的写入：记录一行
void gme_apu_dump_write( int addr, int data )
{
    if ( !g_dump_fp ) return;
    // DMC 通道 $4010-$4013 直接跳过（需求规定）
    if ( addr >= 0x4010 && addr <= 0x4013 ) return;
    fprintf( g_dump_fp, "%ld %04X %02X\n", g_frame, addr & 0xFFFF, data & 0xFF );
}

static void die( const char* msg, const char* extra )
{
    if ( extra ) fprintf( stderr, "error: %s: %s\n", msg, extra );
    else         fprintf( stderr, "error: %s\n", msg );
    exit( 1 );
}

int main( int argc, char** argv )
{
    if ( argc < 4 )
    {
        fprintf( stderr,
            "usage: %s <in.nsf> <track> <seconds> [out.log]\n"
            "  track  : 0-based subtune index\n"
            "  seconds: record duration\n", argv[0] );
        return 1;
    }

    const char* path    = argv[1];
    int         track   = atoi( argv[2] );
    int         seconds = atoi( argv[3] );
    const char* out     = ( argc >= 5 ) ? argv[4] : "reg.log";
    const int   sample_rate = 44100;   // 仅用于驱动模拟，不输出音频

    Music_Emu* emu = 0;
    gme_err_t err = gme_open_file( path, &emu, sample_rate );
    if ( err ) die( "gme_open_file", err );

    int tc = gme_track_count( emu );
    fprintf( stderr, "file=%s  track_count=%d  play track=%d  seconds=%d\n",
             path, tc, track, seconds );
    if ( track < 0 || track >= tc )
    {
        gme_delete( emu );
        die( "track index out of range", 0 );
    }

    // 关闭 GME 的静音检测，保证我们拿到原始的完整写序列
    gme_ignore_silence( emu, 1 );

    err = gme_start_track( emu, track );
    if ( err ) { gme_delete( emu ); die( "gme_start_track", err ); }

    // start_track 内部会做 APU 复位写入；此时 g_dump_fp 仍为空，自动被跳过。
    // 真正的歌曲写入发生在下面的 gme_play 期间（INIT/PLAY 跑 6502 代码）。
    g_dump_fp = fopen( out, "w" );
    if ( !g_dump_fp ) { gme_delete( emu ); die( "cannot open output log", out ); }
    g_frame = 0;

    const int BUF = 4096;
    short buf[BUF];
    long target_ms = (long)seconds * 1000L;
    while ( gme_tell( emu ) < target_ms )
    {
        err = gme_play( emu, BUF, buf );   // 推进模拟；样本丢弃，只为触发寄存器写
        if ( err ) { fprintf( stderr, "warning: gme_play: %s\n", err ); break; }
    }

    fclose( g_dump_fp );
    g_dump_fp = 0;
    gme_delete( emu );

    fprintf( stderr, "done. frames=%ld  log=%s\n", g_frame, out );
    return 0;
}
