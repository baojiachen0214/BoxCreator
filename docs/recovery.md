# 长任务恢复、版本和公开交付

## 保持一个可以接手的当前状态

私有任务使用 `input/`（原件只读）、`work/`（中间结果）和 `output/`（稳定交付名）。这些目录已被 Git 忽略。大型中间文件按任务需要保留，不靠几十个“最终版2修正版”来表达状态。

维护一个短 `work/checkpoint.local.json`，只记录：

```json
{
  "variant": "variant-a",
  "current_stage": "vector-review",
  "approved": ["structure", "front-composition"],
  "frozen": ["all-cut-paths", "window-outline"],
  "next_action": "Inspect exported paths, then complete remaining faces",
  "blocked_on": null,
  "geometry_sha256": null,
  "artwork_sha256": null,
  "deliverables": {},
  "manual_checks_pending": ["paper sample"]
}
```

使用项目内相对路径和文件摘要；不存账号、Cookie、密钥、完整聊天和浏览器状态。重要决定只留一句当前结论和依据，不反复复制历史。可以补充“已撤回的要求”，避免接手后重做旧需求。

## 根据依赖重建

原 PDF/结构清单 → 纯刀线与模型几何；最终画面 → 纯画面 PDF → 预览贴图；两份纯 PDF → 分层母版/SVG；模型 + 贴图 + 动作/相机 → Blender 工程 → 帧序列 → MP4。

改画面后重新生成贴图和视频，结构可复用；改孔、折痕或面尺寸后重新生成刀线、几何及相关构图，再做全部受影响检查；改相机或动作后重新渲染视频。摘要让过期结果可识别，不能用改文件名掩盖不同步。

## 卡住时怎么做

先看证据：进程还在计算、页面等待上传、导出额度不足、下载控件未提交、浏览器状态丢失，还是路径/权限错误。不要凭“工具在转圈”保证任务正常，也不要一直按同一按钮。

Blender 启动就报找不到 Python/字体/资源时，检查程序是否通过应用目录外的符号链接启动，改用真实可执行文件路径；CLI 已解析这种链接。GPU 初始化失败则先确认环境是否可访问本机图形设备，或选择适合当前环境的渲染器，不能反复提交同一失败渲染。

对可恢复操作进行有限重试，观察每次状态变化。长处理分段等待，主动报告已完成内容和下一项验证；一次导出尝试失败后检查真实表单/下载产物，再决定是否重试。无进展就保存断点、切换已具备能力的路径，或明确缺少的用户操作。不要暴露密钥和完整工具日志。

接手时先看 checkpoint、当前交付和最新用户要求。复核文件摘要与实际内容，再继续未完成部分；不要从头生成全部画稿，也不要要求用户重复仍有效的授权。

## 公开项目保持干净

项目源码仅包含通用指南、工具、测试和原创示例生成器。实际输入、参考图、生成图、客户工程、环境、模型、账号截图、聊天导出、日志和密钥不进入版本控制。`.gitignore` 是第一层保护，不能代替检查。

发布前审阅暂存清单和实际差异，运行 `boxcreator audit .`，再检查历史提交、远程仓库可见性和 release 附件。工具只报告命中的文件和规则名，不回显值；它不是完备的秘密扫描器。如果历史曾包含秘密，不能仅删除当前文件；先按凭据泄漏处理，再清理历史。

对公开示例单独检查素材许可、PDF 元数据、SVG 链接、Blender 打包图像和外部路径。发布的示例包不带私有 `scene.json`、渲染日志、缓存或整段帧序列；保留必要的可编辑源文件、预览与诚实报告。工程中的图像和渲染输出使用可迁移路径。

注意隐藏元数据：Blender 的 PNG 默认可能包含工程绝对路径；`Image.filepath` 改成相对路径后，`Image.packed_files` 仍可能保留原路径，文件浏览器的已存目录也可能带用户名。示例脚本清理了这些字段并关闭文件名戳。公开预览还应检查 PNG 文本/EXIF；可重存无元数据副本，同时保留需要的色彩配置。压缩 `.blend` 需解压检查内部数据；只对压缩字节运行文本搜索会漏检。路径清理后必须再次在新目录重开渲染，确认没有破坏打包资源。

## 维护依据

接口、导出权限、服务价格与 Blender API 会变化。更新时核对官方资料，并用小样验证实际行为：

- [pypdf 文档](https://pypdf.readthedocs.io/en/stable/)：页面变换、内容流与对象克隆。
- [Blender Python API](https://docs.blender.org/api/current/)：变换、打包图像和渲染。
- [Blender 手册](https://docs.blender.org/manual/en/latest/)：UV、相机与动画。
- [Shapely 文档](https://shapely.readthedocs.io/en/stable/)：多边形与带约束三角化。
- [Poppler](https://poppler.freedesktop.org/)：PDF 渲染与 SVG 导出。
- [FFmpeg 文档](https://ffmpeg.org/documentation.html)：帧序列编码和解码验证。

本项目自动测试覆盖几何和文件层面的可观察行为；实际验证环境与命令写在发行示例报告中。新增复杂盒型时增加有意义的案例，不把客户文件直接加入测试。
