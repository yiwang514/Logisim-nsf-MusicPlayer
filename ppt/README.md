# 答辩 PPT（10 分钟）

单文件 HTML 幻灯片：`index.html`，由 `deck-stage.js` 驱动，每页 1920×1080。
配色与字体仿照 `plan/project_brief_v6.html`（暖纸底 + Fraunces / Noto Serif SC / JetBrains Mono）。
共 **16 页**：15 页正片 + 1 页 Q&A 备份（仅被追问时使用）。

## 使用

- 直接双击打开 `index.html`（无需本地服务器；联网时加载 Google Fonts，离线时回退系统衬线体）。
- 方向键 / 翻页键 / 空格切换；左侧有缩略图导航栏（可右键 Skip/Delete、拖拽排序）。
- 投影时浏览器按 F11 全屏。
- 导出 PDF：浏览器 打印 → 另存为 PDF，自动一页一片。

## 截图（共 7 张，放进 `uploads/` 即自动出现在对应页）

页面里的虚线占位框会显示同样的指引；**文件名必须完全一致（小写）**。
建议统一用 Logisim 白底默认配色截图，PNG 格式，宽度 ≥1400px 保证投影清晰。

| 文件名 | 页 | 截什么 |
|---|---|---|
| `shot_m1_buzzerstress.png` | 06 | apu.circ 的 BuzzerStress 验证电路（运行中）：时钟（Clock）→ 计数器（Counter）→ Splitter（分线器）取高位 → freq_pulse ROM → 蜂鸣器（Buzzer） |
| `shot_apu_overview.png` | 09 | APU 顶层子电路：reg_id / value / WR / frame_clk / ch_mask 输入引脚 + RegFile（译码器 + 16 寄存器）+ 四个 Channel 实例 |
| `shot_apu_channel.png` | 10 | Channel_Pulse 内部：Splitter 拼 11 位 timer → freq_pulse ROM → Buzzer 的 FREQ/VOL/PW/ENABLE 接线 |
| `shot_cpu_datapath.png` | 11 | cpu.circ 的 CPU 全景：PC 计数器、pcbus/instr 引脚、Splitter + 译码器、WAITCNT、ALU 区、R0–R3、APU 输出 |
| `shot_cpu_wait.png` | 12 | WAIT 区局部放大：WAITCNT 向下计数器 + busy 寄存器 + start/en_count/busy_next/stall 逻辑门 + Carry→at_zero + PC 使能 |
| `shot_cpu_alu.png` | 13 | ALU + R0–R3：加法器/减法器/比较器、tempo_mode/tempo_delta 输入、ALU 输出接 WAITCNT 装载路径（探针显示 tempo_delta 更佳） |
| `shot_top_panel.png` | 14 | top.circ 顶层全貌（播放中）：控制面板 + 曲号计数器/数码管 + 4 个 track ROM + 4:1 多路复用器 + CPU/APU 实例 |

## 待手动修改

- 第 1 页（标题）：替换答辩人 / 组员姓名占位"＿＿＿"。
- 课程名默认写"数字逻辑课程设计"，按实际课程名改。

## 页结构与 10 分钟时间分配（每页右上角有建议时长）

| 部分 | 页 | 时间 |
|---|---|---|
| 标题 + 数据链总览 | 01–02 | ~1.0 min |
| 2A03 原理 + 波形科普 | 03–04 | ~1.0 min |
| Buzzer 可行性（源码 + 对策） | 05–06 | ~1.3 min |
| 工具链 + ISA | 07–08 | ~1.3 min |
| APU（结构 + 声道） | 09–10 | ~1.5 min |
| CPU（重点：通路 / WAIT / ALU） | 11–13 | ~2.7 min |
| top + 演示收束 | 14–15 | ~1.3 min |
| Q&A 备份 | 16 | 不计入正片 |

内容事实全部来自 `ppt/PPT_INFORMATION_SUMMARY.md`（信息规格书）；
讲稿要点已写入 `index.html` 的 `#speaker-notes`（JSON，每页一条）。
