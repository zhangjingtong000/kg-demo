# 3D 知识图谱可视化 —— 开发过程记录

## 一、视觉风格探索

### 1.1 灵感来源

在 Dribbble 上搜索设计参考，找到了两个关键页面：
- [AI Legislative Intelligence Dashboard](https://dribbble.com/shots/27428420) — 节点有「水果糖/玻璃球」质感，连线是中间深两端淡的渐变
- [AI Policy Platform](https://dribbble.com/shots/27503829) — 整体页面融合一体，没有硬卡片边界

向 Claude 描述了这些视觉特征后，开始尝试实现。

### 1.2 初版：2D Canvas

第一版用 Canvas 2D 绘制：径向渐变模拟玻璃球、分段贝塞尔曲线模拟连线渐变。效果一般——2D 的「假装 3D」带着塑料味，不够高级。

### 1.3 转 Three.js 3D

改用 Three.js 构建真实 3D 场景：
- 自定义 ShaderMaterial 实现 liquid glass（菲涅尔边缘光 + 双高光 + 半透本体）
- 自定义管状几何体实现连线（端细中粗 + 顶点色渐变 + AdditiveBlending 发光）
- 深色空间背景 + FogExp2 雾效 + 背景星点粒子

### 1.4 材质迭代

| 版本 | 方案 | 问题 |
|------|------|------|
| V1 | Canvas 径向渐变 + 高光点 | 塑料感，2D 假 3D |
| V2 | MeshStandardMaterial (metalness:0.15, roughness:0.35) | 还是塑料 |
| V3 | MeshPhysicalMaterial (clearcoat:0.3) | 陶瓷感，不够透 |
| V4 | MeshPhysicalMaterial (transmission:0.82, ior:1.45) | 渲染太卡（每球一次 render pass）|
| V5 | **自定义 ShaderMaterial** | ✅ 单次渲染、液态玻璃感、不卡 |

## 二、交互系统

### 2.1 点击聚焦

点击节点 → BFS 计算到其他节点的图距离 → 按距离排成同心环 → 聚焦节点移到中心(0,0,0) → 全部节点平滑动画到位。

借鉴了 3d-force-graph 的 click-to-focus 思路，但布局算法是自己设计的（BFS 径向环）。

### 2.2 聚焦扩散暗度

聚焦后，离中心节点越远的节点和连线越暗。用 lerp 做平滑过渡，不是硬切。暗度公式：距离 0=100%，1=65%，2=35%，3=15%，4+=6%。

### 2.3 聚焦高亮环

聚焦节点外围加一个 AdditiveBlending 发光圆环，始终 face camera（lookAt），跟随节点位置和呼吸动画。

### 2.4 悬停高亮

鼠标悬停节点 150ms 后触发，高亮该节点及其直连的边，其他节点光晕隐藏。借鉴了 3d-force-graph 的 highlight 交互。

### 2.5 拖动回弹

拖节点 → 自由移动 → 邻居跟动（距离衰减）→ 松手后弹簧-阻尼模型回弹到原位。只从拖节点触发，旋转空白区域不触发。

## 三、踩坑记录

### 3.1 相机漂移

**问题**：旋转/缩放松手后画面自动漂回默认位置。

**定位**：`camera.position.lerp(cameraTarget, dt)` 每帧都在把相机拖回默认坐标。无论聚焦与否都在跑。

**解决**：改为聚焦时一次性 `camera.position.copy(focusCam)`，非聚焦时完全不碰相机位置。

### 3.2 拖动触发聚焦

**问题**：拖完节点松手，同时触发了 click 事件 → 节点被聚焦 → 整个图重排。

**定位**：mousedown 设置 dragNode → mouseup 清除 dragNode → click 触发时 dragNode 已经是 null，`if (dragNode) return` 挡不住。

**解决**：加 `didDrag` 标记。mousemove 时设为 true。click 时判断 `didDrag` 而非 `dragNode`。

### 3.3 拖动时悬停闪烁

**问题**：拖节点时鼠标经过其他节点上方，触发 hover 高亮。

**定位**：hoverTimeout 在 mousedown 之前已设置，拖拽过程中到时间就触发。

**解决**：mousedown 时 `clearTimeout(hoverTimeout)`。

### 3.4 悬停高亮相邻节点之间的边

**问题**：悬停 A 节点时，A 的邻居 B 和 C 之间如果也有边，B-C 边也会高亮。但 B-C 和 A 没有直接关系。

**定位**：判断条件是「任一端点在高亮集合中」。高亮集合包含邻居节点，邻居之间的边也被亮了。

**解决**：改为只判断「悬停节点是不是边的端点」：`from === hoveredIdx || to === hoveredIdx`。

### 3.5 回弹与旋转冲突

**问题**：松手后弹簧在跑，此时旋转画面会卡顿 + 节点自动弹回。

**定位**：之前以为是同一个问题，后来发现是两件事——弹簧是拖节点后用弹簧-阻尼模型回弹；旋转卡顿是相机 lerp 导致的（见 3.1）。修好相机问题后两者不再冲突。

**解决**：弹簧只从节点拖拽触发（mouseup 时 `if (dragNode)` 才启动），旋转不会启动弹簧。最终回弹保留。

### 3.6 性能优化

**问题**：连线位置每帧更新所有顶点 buffer，节点多了会卡。

**尝试**：降低几何体精度（节点 64→32 段、连线管体 6→4 边、连线 40→24 段）。

**结果**：节点降精度无视觉差异，连线管体边数降了画面直接废（线变细丝），线段数降了线变断断续续。最终只保留「每 2 帧刷新连线位置」这一项，视觉无差异。

**教训**：降精度前先测视觉效果，有些优化代价太大。

### 3.7 LLM 输出格式不一致

**问题**：提示词要求 `entity<|>Name<|>Type<|>Desc`，但不同模型输出不同——有的加上前缀，有的不加。

**解决**：解析器同时兼容两种格式，自动 strip 可选前缀。

### 3.8 本地模型超时 + thinking 模式

**问题**：本地 qwen3.5:9b 超时（9.7B 参数跑不动）。云端 Qwen3.5-9B 输出全去 thinking 字段，content 为空。

**解决**：改为纯云端 DeepSeek V4 Pro（快 6 倍）。thinking 模型加 `enable_thinking: false`。

## 四、借鉴记录

| 借鉴内容 | 来源 | 借鉴方式 |
|---------|------|---------|
| Dribbble 设计参考 | KG visualization / AI agent interface 搜索 | 视觉灵感，自己实现 |
| 悬浮高亮交互 | vasturiano/3d-force-graph | 思路借鉴，shader 自写 |
| 提示词分隔符格式 | LightRAG | 直接采用 `<\|>` 分隔符 |
| 两阶段抽取策略 | HiRAG | 先实体后关系 |
| 类型约束 | llm2kg | 预定义 EntityType/RelationType |
| 分隔符解析器兼容 | 实测发现 | 自动兼容有无前缀 |
| 结构感知分块 | Docling-Graph | 按段落边界切，保留标题上下文 |
| 滑动窗口重叠 | SLIDE (2025.3) | 30% 重叠，实体+24%/关系+39% |
| 同名去重 | MS GraphRAG | 精确名称匹配合并 |
| 同类型模糊去重 | DEG-RAG | 仅同类型内执行，不跨类型 |
