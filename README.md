# codex-vivado

machine=PC2 · v0.1.0 · 2026-11-16

把 [dsh-vivado](https://github.com/chemmy-11/dsh-vivado) 的「MCP 工具 + 工作流技能 + 环境配置 + 体检」设计迁移到 **Codex 原生插件**。
本项目采用 `.codex-plugin/plugin.json`、`.mcp.json` 与本地 marketplace，可由 `codex plugin` 安装。
参考版本固定为 `1c78db4e3344641d32dd6f00a490055f068d654c`（0.2.4）；[验收记录](VALIDATION.md)说明实测范围。
源码仓库：https://github.com/ljh888666/codex-vivado 。机器配置须在克隆后生成；请先执行下面的准备步骤，再安装生成的本地 marketplace。

## 得到什么

| 能力 | 实现 | 本机验收 |
|---|---|---|
| Vivado MCP | 连接用户已有的 `vivado-mcp`，不复制或修改其源码 | stdio 握手、列出 32 工具、离线 XPR 解析通过 |
| 工程工作流 | `$vivado-workflow`：检查、异步构建、证据分级与串行协调 | 技能格式验证通过 |
| 报告分析 | `$vivado-reports`：日志、时序、CDC、XDC 的离线分析 | 技能格式验证通过 |
| 硬件流程 | `$vivado-hardware`：授权、现场设备识别、ILA/VIO/烧录流程 | 技能格式验证；未连接硬件 |
| 官方文档 | `$amd-doc-search`：随包 stdlib HTTP/SSE 检索桥 | 离线协议测试通过；未做 AMD 服务连通实测 |
| 环境准备 | `tools/configure.py`、`tools/doctor.py`、`tools/verify_native.py` | 渲染、体检、原生隔离安装通过 |

32 是本机 `vivado-mcp==0.3.26` 的实际工具数；其它后端版本以当次 `tools/list` 为准。
硬件能力经现有后端工具/Tcl 调用，技能本身不会添加新的 MCP 工具。

## 快速准备

前提：Windows、支持 `codex plugin` 的 Codex、Python ≥3.10、已安装的 Vivado 与合法许可，以及可导入 `vivado_mcp.server` 的独立 Python 环境。
本机通过的是 Codex CLI `0.169.0-alpha.11.1`、Python `3.12.10`、`vivado-mcp 0.3.26`、MCP SDK `2.3.0`；这不是对所有版本的兼容性保证。

其它机器可先克隆源码，并将解释器、Vivado 和器件参数换成本机实际值：

```powershell
git clone https://github.com/ljh888666/codex-vivado.git
cd codex-vivado
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -Python 'D:/tools/vivado-mcp/.venv/Scripts/python.exe' -Vivado 'D:/Xilinx/Vivado/2023.1/bin/vivado.bat' -Part '<your-fpga-part>'
```

`-Python` 指向已经安装 `vivado-mcp` 的解释器。`--project-root` 未指定时默认本仓库根，只作元数据；操作其它工程时显式传入路径。
本机 PC2 的复现命令如下，在此仓库根目录执行：

```powershell
# 仅写本仓库 .runtime，渲染本机 marketplace；不会改 ~/.codex。
& 'D:/vivado-mcp/codex/.venv/Scripts/python.exe' -B -X utf8 tools/configure.py --project-root 'D:/fpga/FPGA_Project/EIF-master' --part xcku060-ffva1156-2-i

# 环境检查不启动 Vivado；真实 MCP 冒烟仅调用列会话和离线解析。
& 'D:/vivado-mcp/codex/.venv/Scripts/python.exe' -B -X utf8 tools/doctor.py
& 'D:/vivado-mcp/codex/.venv/Scripts/python.exe' -B -X utf8 tools/smoke_mcp.py

# 用 .runtime/native-home 隔离测试 Codex 原生安装和配置加载。
& 'D:/vivado-mcp/codex/.venv/Scripts/python.exe' -B -X utf8 tools/verify_native.py
```

也可以用 `powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1` 一次完成准备与隔离验证。
解释器/安装位置不同时，显式传 `--python`、`--vivado`、`--project-root`。
`configure.py` 优先读取 `CODEX_VIVADO_PYTHON`、`VIVADO_PATH`，并校验实际文件存在；版本号由路径或参数标注，**未启动 Vivado 测量版本**。
`config.example.json` 展示字段；机器配置生成在 `.runtime/marketplace/plugins/codex-vivado/environment.json`，不入 git。

## 安装到日常 Codex

开发验收先在隔离 CODEX_HOME 内完成；随后已按用户指令安装到 PC2 日常 Codex。
其他用户可在克隆后的仓库根、普通终端中运行以下命令（不要沿用隔离测试的 `CODEX_HOME`）：

```powershell
$marketplace = (Resolve-Path '.runtime/marketplace').Path
codex plugin marketplace add $marketplace --json
codex plugin add codex-vivado@codex-vivado-local --json
codex mcp get vivado --json
```

安装后在 Codex 中开启新会话，检查插件的技能和 `vivado` MCP 是否加载；已有会话不会因本项目的文件写入而自动获得工具。
原生安装会复制生成后的插件及配置到 Codex 缓存。配置或源码更新时，重跑准备并移除/重新安装插件以刷新副本；仅重写源文件不代表缓存更新。
不要直接安装未渲染的源码 marketplace：其中的通用 `.mcp.json` 尚无机器配置。
卸载命令为 `codex plugin remove codex-vivado@codex-vivado-local`；marketplace 管理参数以本机 `codex plugin marketplace --help` 为准。

## 使用例子

- 「用 `$vivado-workflow` 检查这个 XPR，先汇报已有 run 和结果，再决定下一步。」
- 「用 `$vivado-reports` 分析这个 timing summary，列清 setup/hold、约束和证据缺口。」
- 「用 `$amd-doc-search` 核对 Vivado 2023.1 的公开 Tcl 命令文档，给出官方链接和版本信息。」
- 「用 `$vivado-hardware` 准备板 B 的验证单。」真正连接、烧录或抓取前须有对应授权。

直接调用文档检索：

```powershell
& 'D:/vivado-mcp/codex/.venv/Scripts/python.exe' -B -X utf8 plugins/codex-vivado/scripts/amd_doc_search.py 'report_timing_summary UG835' --version 2023.1 --limit 3 --timeout 30 --json
```

查询发往 `https://ross.amd.com/mcp/doc-search`，只用公开产品词；每个结果的 family/version 仍须逐条核对。
网络/协议错误退出 1，参数/工具错误退出 2，完整返回保留在 JSON 输出中。

## 设计与边界

| dsh-vivado 的构件 | Codex 版对应 |
|---|---|
| DSH 预设/persona/profile patch | 原生插件 + 按需技能，无 DSH 运行时依赖 |
| MCP client 配置 | `.mcp.json`，相对 `cwd` 由 Codex 重定位到缓存插件根 |
| 机器路径配置 | 独立的本机 marketplace 渲染，不编辑全局 TOML |
| 8 个原包技能 | 4 个针对 Codex 新写的入口；未复制 AMD VSIX 技能树 |
| install/doctor | configure、doctor、原生隔离安装验证 |

launcher 透传 stdin/stdout；诊断只走 stderr。后端通过所选解释器的 `-I -B -m vivado_mcp` 运行，去除继承的 `PYTHONPATH/PYTHONHOME`，防止导入错误副本。
`project_root` 是定位元数据，**不会自动打开工程**；后端工作目录是 `work_dir`，工具操作须提供实际工程路径。
`work_dir`、`temp_dir` 在配置阶段创建，供后端可写；PC2 必须继续设在 `pc2` 内。工程/TEMP/MCP 路径要求 ASCII。
插件启动的是 Python MCP 服务；实际综合/实现/烧录仍通过明确工具请求触发。
本插件**没有跨进程、跨客户端或跨机器全局锁**；DSH、GUI、xsct、其它 Codex 会话之间仍须协调串行访问。

## 开发与许可

```powershell
& 'D:/vivado-mcp/codex/.venv/Scripts/python.exe' -B -X utf8 -m unittest discover -s tests -v
git diff --check
```

原生结构参照 [OpenAI plugins](https://github.com/openai/plugins/tree/d420d13051bffe4543ed39e30fa46b87148e47dd)；路径处理参照 [Codex plugin_config.rs](https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/plugin_config.rs)。
代码为 MIT，来源/改动见 [NOTICE](NOTICE)；文档桥保留 chemmy-11 的 MIT 版权。
未打包 Vivado、许可、AMD VSIX、DSH 本体、`vivado-mcp` 或其依赖。机器配置、运行时、日志和构建产物不入库。
