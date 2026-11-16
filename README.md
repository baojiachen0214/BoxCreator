# BoxCreator

把 **一个刀板 PDF + 一段风格说明 + 可选参考图**，变成完整、可编辑的矢量纸盒刀板，以及使用同一几何和画面的 Blender 成品视频。

这是给 ChatGPT 与 Codex 复用的 **AI 工作指南 + 小型验证工具**。它教 AI 如何读图、设计、矢量化、建模、排错和验收，不要求把创意工作写成固定流水线。代码不会自动理解任意 PDF 的刀线、猜出扣合结构或代替印厂打样。

**English:** An agent playbook and small verification toolkit for turning a dieline PDF and a short style brief into layered vector packaging and a Blender folding/orbit video. AI interprets the structure and makes design decisions; deterministic tools preserve dimensions, layers, holes and consistency. Start with [the agent skill](skills/boxcreator/SKILL.md).

## 直接让 AI 开始

在 Codex 中打开本项目，附上 PDF 和参考图，发送：

> 按 BoxCreator 的 AGENTS.md 和 skills/boxcreator/SKILL.md 完成这个纸盒。输入是附件刀板 PDF，风格为「在这里描述」。请先看懂结构并量尺寸，保留已确认的刀线与扣合方式，完成所有面的设计。最终交付 1:1 分层矢量 PDF、可编辑 SVG、纯画面与纯刀线 PDF、打包贴图的 Blender 工程、完整折叠与环绕 MP4，以及如实填写的验收报告。需要我判断时，只问会影响结果的具体问题；其他工作继续推进。

ChatGPT 可先读 [工作指南](docs/workflow.md)，承担需求、参考图分析、画稿和验收；Codex 在本地执行工具、维护文件和运行 Blender。没有本地执行能力的环境应明确交接文件与未完成项，不能把建议当成已交付结果。API 不是必需项，登录状态、额度、导出权限以当前环境实际验证为准。

用户不必写几何清单或学工具命令。`net.json` 是 AI 从刀板提取并复核的内部工作文件。参考图默认用于理解风格，不能覆盖刀板的真实尺寸。

## 如何复用

- 先读 [AGENTS.md](AGENTS.md) 与 [AI 入口](skills/boxcreator/SKILL.md)。保留整个仓库，以便访问其引用文档；入口文件本身不是独立安装包。
- 按任务需要读 [设计与制作](docs/workflow.md)、[几何约定](docs/geometry.md)、[验收](docs/acceptance.md)。
- 出现反复返工、长对话失控、工具卡顿时，读 [失败经验](docs/lessons.md) 与 [恢复与交付](docs/recovery.md)。

语言、风格数量、窗口比例、云端服务、纸盒尺寸都按本次任务决定，不继承历史案例的偏好。用户已确认的部分应冻结，修订只影响必要文件。

## 本地准备

需要 Python 3.10+、Poppler（`pdftoppm`、`pdftocairo`）、Blender。编码需要 FFmpeg；可安装系统 FFmpeg，或用下面的 `video` 可选依赖。先验证小样导入和导出，再投入完整制作。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[video]'
boxcreator --help
```

Windows 使用 `.venv\Scripts\activate`；Poppler、Blender、FFmpeg 需单独安装并加入 PATH。Python 工具与 Blender 自带 Python 分开运行，不向 Blender 内安装本项目依赖。可用 `--blender` 指定程序路径。

## 运行原创示例

这个示例仅展示矢量图层、真实开孔和折叠：六面彩色盒体，不含客户素材，也没有设计糊口或锁扣，**不可直接作为生产刀模**。

```bash
boxcreator demo output/demo
boxcreator check output/demo/artwork.pdf output/demo/dieline.pdf output/demo/layered.pdf --report output/demo/pdf-check.json
boxcreator svg output/demo/artwork.pdf output/demo/dieline.pdf output/demo/layered.svg
boxcreator render output/demo/artwork.pdf output/demo/artwork.png --dpi 180
boxcreator scene output/demo/net.json output/demo/artwork.png output/demo/scene.json
boxcreator animate output/demo/scene.json output/demo/animation --frames 192 --size 1280
boxcreator encode output/demo/animation/frames output/demo/folding.mp4
```

快速检查时，在 `animate` 后加 `--draft --frames 96 --size 640`。这是预览质量，正式交付需观看全片并按需求提高质量。每次动画使用新目录，避免旧帧混入。

已运行的示例可在 [Releases](https://github.com/baojiachen0214/BoxCreator/releases) 下载。源仓库只保存指南、代码和测试；PDF、视频、工程和中间帧不进入 Git 历史。

![原创几何示例的闭合预览](https://github.com/baojiachen0214/BoxCreator/releases/download/v0.1.0/preview.png)

示例视频与工程展示同一份带孔净片。它验证工具链，不代表插画创作水平或生产结构设计已经自动化。

## 工具能力与边界

| 命令 | 用途 | 不能证明什么 |
| --- | --- | --- |
| `inspect PDF` | 页尺寸、页面变换、位图、使用中的字体、图层与输出意图诊断 | 完整印前合格或 PDF/X 认证 |
| `validate net.json` | 连通性、平面重叠、真实开孔、共享铰链和折叠树 | 与原刀板一致、纸张强度和扣合公差 |
| `assemble art.pdf die.pdf out.pdf` | 原尺寸合成两层 PDF；工艺线层默认不打印 | 自动识别刀线、转换 CMYK 或添加出血 |
| `svg art.pdf die.pdf out.svg` | 每款单页导出为两个可编辑图层 | 保留专色与 ICC；印刷颜色以 PDF 为准 |
| `check art.pdf die.pdf out.pdf` | 逐页切换图层，像素对比纯图层源文件，检查位图和尺寸 | 主观美感、所有浏览器的图层行为 |
| `scene` / `animate` / `encode` | 有孔网格、层级折叠、全片取景检查、打包工程、视频解码 | 自动解决锁扣、碰撞、纸厚或物理仿真 |
| `audit` | 扫描暂存发布内容的常见密钥与私有文件 | 所有秘密类型、历史提交和附件均无泄漏 |

PDF 检查会递归扫描 Form、平铺 Pattern 和透明度遮罩中的图像，以及内联图像；颜色统计只是诊断。工具要求合成源 PDF 已经是纯矢量、页面坐标已规整、无原有图层与注释。工具拒绝的复杂源文件应由 AI 使用合适的矢量工具预处理并重新对照，不可截图替代。

## 交付与维护

完整交付清单和验收证据见 [验收标准](docs/acceptance.md)。实际任务保存在被忽略的 `input/`、`work/`、`output/` 内；公开案例需要另行确认素材权利并单独检查元数据、截图和工程引用。

```bash
python -m unittest discover -s tests -v
git add README.md AGENTS.md LICENSE pyproject.toml .gitignore src docs skills examples tests .github
boxcreator audit .
```

流程来自对六段相关设计对话与实际交付迭代的复盘；只保留抽象经验，未附聊天记录、账号、客户画稿或原始刀板。代码与项目文档采用 [MIT](LICENSE)。第三方软件、字体、生成服务和用户上传素材遵循各自许可。本项目不分发 Blender 或 FFmpeg。
