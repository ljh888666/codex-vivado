# 本机验收记录

machine=PC2 · 2026-11-16 · codex-vivado 0.1.0

## 现象与目的

按用户提供的 dsh-vivado 仓库设计制作 Codex 原生插件。
为什么采用真实 CLI 与 stdio 测试：仅 JSON 格式正确无法证明 Codex 能安装、重定位缓存路径或调用后端。
为什么不综合或上板：本轮目标是插件开发，未获对应板级操作授权；工程目录规范要求产物限于 pc2。

## 输入与环境

- 上游 dsh-vivado：`1c78db4e3344641d32dd6f00a490055f068d654c`，package 版本 `0.2.4`。
- 固定参考文件另存 `pc2/_reference/dsh-vivado-1c78db4e-review/`；`provenance.json` 含每文件 URL、SHA256 与 machine=PC2。
- Codex CLI：`0.169.0-alpha.11.1`，桌面程序提供的本机可执行文件。
- Python：`D:/vivado-mcp/codex/.venv/Scripts/python.exe`，3.12.10。
- 后端：该解释器实际导入的 `vivado-mcp 0.3.26`、`mcp 2.3.0`。
- 配置 Vivado：`VIVADO_PATH` 解析的 `D:/vavido/Vivado/2023.1/bin/vivado.bat` 文件存在；未运行版本探针。
- part 配置为 `xcku060-ffva1156-2-i`，只是预期值，未作硬件识别。

## 实验与结果

| 验收 | 实际动作 | 结果与证明范围 |
|---|---|---|
| 单元测试 | `python -B -X utf8 -m unittest discover -s tests -v` | 28/28 PASS：配置/导入隔离、stdio/退出码、HTTP/SSE、错误保留与参数校验 |
| 技能验证 | skill-creator `quick_validate.py` 逐项检查 | 4/4 PASS；元数据、默认提示词与 `$skill-name` 一致 |
| 环境体检 | `tools/doctor.py` | PASS；实际后端注册 32 个工具；未启动 Vivado |
| 原生安装 | `tools/verify_native.py`，CODEX_HOME=`.runtime/native-home` | marketplace add、plugin add、list、mcp get 全部成功 |
| 缓存路径 | `codex mcp get vivado --json` | enabled=true；解释器为绝对路径；cwd 重定位到实际插件缓存；120/1800 秒配置保留 |
| stdio 通路 | `tools/smoke_mcp.py` | initialize、tools/list、list_sessions、parse_xpr、list_sessions 成功 |
| 离线解析 | 随包合成 `tests/fixtures/minimal.xpr` | 返回预期 part 和 top；前后会话均为空，未启动 Vivado |
| 完整性 | `git diff --check`、JSON 解析与 Python AST | PASS；完整脚本与清单可读取 |

首次 stdio 测试发现验收脚本误用 MCP SDK 2.x 的 `isError` 属性；SDK 返回 `is_error`。
已修正验收脚本以兼容字段变化，并增加失败结果/错误文本回归检查；未更改外部 MCP 代码。
这是验收脚本 API 不匹配的直接异常证据，不是对 Vivado 或硬件的归因。

## 结论与未测项

**[L3-软件本机直接观测，非硬件定案]** 本机原生 Codex CLI 可安装并加载该插件，缓存路径与 MCP 配置有效；真实 MCP stdio 可列工具和离线解析 XPR。
此结论限软件接入，不推断 RTL、时序或板级功能。

- 未修改日常用户 CODEX_HOME；隔离安装的成功不表示当前聊天已挂载新工具。
- 未启动 Vivado、hw_server、xsct；未运行综合/实现/烧录、ILA/VIO 或跨板实验。
- 未测 AMD hosted 服务连通性；文档桥通过的是离线协议测试。
- 未测其它 Vivado/SDK/Codex 版本；不把参考项目的 PC1 测量或版本行为当作 PC2 实测。

原始本轮输出在 `.runtime/evidence/{configure,doctor,native,mcp,unit}.json`（不入 git）。
这些输出记录命令、退出码、完整 stdout/stderr，可用 README 命令重新生成。

## 2026-11-16 安装补记

machine=PC2。隔离验收后，用户明确要求安装到日常 Codex，已完成 marketplace add、plugin add。
`codex mcp get vivado --json` 返回 enabled=true；从日常缓存插件进行真实 stdio 测试，通过 initialize、32 工具发现与离线 XPR 解析。
未启动 Vivado 或连接硬件。原文“未修改日常用户 CODEX_HOME”仅描述前述隔离阶段。

上传前补齐通用克隆/安装说明，将默认 project_root 改为独立源码仓库根，并显式忽略 environment.json，避免误提交机器配置。
