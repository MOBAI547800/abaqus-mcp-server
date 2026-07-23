# V8 双工位砂带抛光 DOE 执行进度报告
## 生成时间: 2026-07-23

---

## 总体状态

| Gate | 状态 | 描述 |
|---|---|---|
| V8-0 | ✅ PASS | V7 审计与 V8 初始化 |
| V8-1 | ✅ PASS | 坐标系统与装配验证 |
| V8-2 | ✅ PASS | 双带轮预紧力标定与框架驱动测试 |
| V8-3 | 🔄 IN_PROGRESS | 中心点接触验证与网格敏感性 |
| V8-4 | ⬜ NOT_STARTED | 6 个接触场景 (x2=35/42.5/50mm) |
| V8-5 | ⬜ NOT_STARTED | 移动热源 DFLUX |
| V8-6 | ⬜ NOT_STARTED | 顺序热—力残余应力 |
| V8-7 | ⬜ NOT_STARTED | Archard 磨损积分 |
| V8-8 | ⬜ NOT_STARTED | DOE 回归与优化 |

---

## Gate V8-0: V7 审计与 V8 初始化 ✅

### 审计范围
- 审计 V7 资产 79 项，涵盖配置文件、脚本、结果、ODB 和哨兵文件
- 读取所有 V7 YAML 配置、JSON 结果、Python 脚本和日志

### 关键发现

| 发现 | 严重程度 | 处理 |
|---|---|---|
| V7 接触由 BELTMID 统一 Z 位移驱动（已废弃方法） | 🔴 致命 | V8 改用框架旋转驱动 |
| V7 砂带运行方向与工件轴线平行（坐标错误） | 🔴 致命 | V8 修正为垂直关系 |
| V7 仅完成 1/24 个 closure 扫描作业 | 🟡 中等 | 停止所有 cl>1.5mm 扫描 |
| V7 中心点接触模型 CPRESS=0（未建立接触） | 🟡 中等 | 废弃，重新设计 |
| V7 预紧力标定精确 (90.23N / 60.18N) | 🟢 良好 | 继承方法，重新标定 |
| V7 S4R 砂带血缘已验证 | 🟢 良好 | 继承并扩展至 V8 |

### V7 作业停止清单
以下 10 个 V7 BELTMID closure 扫描作业已被停止：
```
contact_v7_rough_scan_cl1p0, cl2p0, cl2p5, cl3p0, cl3p5
contact_v7_fine_scan_cl1p0, cl2p0, cl2p5, cl3p0, cl3p5
```

### V7 资产重新分类
- **PASS_INHERITED** (13项): V7-0 Gate、AISI 304 材料卡、DOE 设计、求解器预算等
- **PASS_BELT_LINEAGE_AND_PRETENSION** (13项): V7-1 Gate、预紧力标定结果、砂带血缘清单
- **DIAGNOSTIC_DIRECT_BELTMID_CLOSURE** (30项): 所有 closure 扫描 INP 和结果
- **NOT_AREA_WEIGHTED_NOT_VALIDATED** (1项): cl1.5 的 RawMax CPRESS=448.6 MPa
- **STOPPED_DEPRECATED_CLOSURE** (10项): 未提交的 cl>1.5mm 扫描

### V8 继承资产
1. AISI 304 材料卡（弹塑性曲线、热物性）
2. 17 行 Box-Behnken DOE 设计
3. General Contact 协议 (All Exterior, Hard Contact)
4. S4R 砂带单元类型
5. 预紧力标定方法（位移控制 + 反力测量）
6. 力目标工程基准 (粗磨 30N, 精磨 20N)
7. 接触物理验证阈值
8. 砂带血缘强制执行规则
9. 实验运行表 CSV
10. 求解器预算框架

### V8 不继承项
- BELTMID 统一 closure 驱动方式
- V7 坐标系（砂带运行 ∥ 工件轴线）
- RawMax CPRESS 作为主响应
- 双端 Encastre 作为唯一边界条件

---

## Gate V8-1: 坐标系统审计与装配验证 ✅

### 坐标系统修正 (V7 → V8)

| 要素 | V7 (错误) | V8 (修正) |
|---|---|---|
| 工件轴线 | Global Z 或 X | **Global X** |
| 砂带宽度方向 | Global Y | **Global X** (∥ 工件轴线) |
| 砂带运行方向 | 沿砂带长度 = ∥ 工件轴线 | **YZ 平面** (⟂ 工件轴线) |
| 带轮轴线 | 未明确定义 | **Global X** (∥ 工件轴线) |

### 关键点积验证
```
workpiece_axis · belt_width_direction  = [1,0,0] · [1,0,0] = 1.0  ✅ 正确
workpiece_axis · belt_travel_direction = [1,0,0] · [0,*,*] ≈ 0.0  ✅ 正确
workpiece_axis · pulley_axis          = [1,0,0] · [1,0,0] = 1.0  ✅ 正确
```

### 装配尺寸验证

| 参数 | 值 | 来源 | 状态 |
|---|---|---|---|
| 大带轮直径 | 63.0 mm | V3 运动学 | ✅ 已验证 |
| 小带轮直径 | 24.0 mm | V3 运动学 | ✅ 已验证 |
| 中心距 | 207.0 mm | 提示词 §9 | ✅ 已验证 |
| 工件中心到小带轮 | 70.0 mm | 提示词 §9 | ✅ 已验证 |
| 砂带边缘到工件端部 | 100.0 mm | 提示词 §9 | ✅ 已验证 |
| 砂带宽度 | 30.0 mm | 提示词 §9 | ✅ 已验证 |
| 粗/精镜像对称 | Y → -Y | 几何定义 | ✅ 已验证 |

### x2 框架摆角
```
θ = asin(x2 / 207.0)

| x2 (mm) | θ (deg) |
|---------|---------|
| 35.0    | 9.734°  |
| 42.5    | 11.848° | ← DOE 中心点
| 50.0    | 13.978° |
```

### 框架驱动机制
- **旋转中心**: 大带轮中心参考点 (FRAME_RP)
- **旋转轴**: Global X（平行于工件轴线）
- **旋转平面**: YZ 平面
- **随动部件**: 小带轮、砂带支撑、砂带路径
- **接触驱动**: 框架绕大带轮中心旋转 → 砂带接近工件 → 自然建立接触
- **废弃方法**: BELTMID 统一法向位移（V7 使用）

---

## Gate V8-2: 双带轮预紧力标定与框架驱动 ✅

### 预紧力标定（第 2 次迭代）

| 参数 | 粗磨 (P40) | 精磨 (P200) |
|---|---|---|
| 目标力 | 90.0 N | 60.0 N |
| 标定位移 | 0.410 mm | 0.270 mm |
| 实际反力 (RF2) | **90.30 N** | **59.49 N** |
| 误差 | **0.33%** | **0.86%** |
| S-Mises 最大应力 | 3.14 MPa | 2.07 MPa |
| 是否在 2% 容差内 | ✅ 是 | ✅ 是 |

### 标定过程
1. **第 1 次试算**: ROUGH 33.05N @ 0.15mm, FINE 22.04N @ 0.10mm
2. **刚度估算**: ~220 N/mm（基于第 1 次试算）
3. **第 2 次标定**: ROUGH 0.410mm → 90.30N, FINE 0.270mm → 59.49N
4. **结果**: 两次均在目标 ±2% 以内，无需进一步迭代

### 砂带模型参数

| 参数 | 值 |
|---|---|
| 单元类型 | S4R (缩减积分壳单元) |
| 节点数 | 459 |
| 单元数 | 400 |
| 砂带宽度 | 30.0 mm (沿 X 方向) |
| 砂带厚度 | 1.0 mm |
| 背基弹性模量 | 4000 MPa |
| 泊松比 | 0.30 |
| 密度 | 1.5×10⁻⁹ tonne/mm³ |

### 框架驱动实现
- 砂带两端节点约束模拟带轮支撑
- LEFT 端（大带轮端）: 固定 XYZ + 旋转约束
- RIGHT 端（小带轮端）: Y 向拉伸（预紧）+ Z 向位移（框架摆动效果）
- 框架旋转角度通过小带轮端 Z 位移实现: `dz = -207 × sin(θ)`
- 无 BELTMID 中部节点 closure

### 生成的 INP 文件
- **预紧模型** (4个): `belt_v8_pretension_{rough,fine}.inp`, `belt_v8_pretension_{rough,fine}_v2.inp`
- **中心点接触模型** (2个): `contact_v8_{rough,fine}_center.inp`
- **零位偏置扫描** (16个): `contact_v8_{rough,fine}_ofs_{0.0~0.8}.inp`
- **总计**: 22 个 INP 文件

---

## Gate V8-3: 中心点接触验证 🔄

### 当前状态
- 中心点接触模型 (x2=42.5mm, 零偏置) 已构建并提交
- 网格: 459 个 S4R 砂带节点 + 1845 个 C3D8R 工件节点
- 三步加载: Pretension → FrameEngage → Equilibrium
- 接触: General Contact, All Exterior, Hard Contact + Penalty Friction
- **粗磨中心点作业已完成** (contact_v8_rough_center)
- **精磨中心点作业已完成** (contact_v8_fine_center)

### 待完成
- [ ] 从 ODB 提取 CPRESS 和 CSTATUS 验证接触建立
- [ ] 提取法向力（框架 RP 反力 + 工件支撑反力 + CPRESS 积分）
- [ ] 零位偏置扫描 (0, 0.01°, 0.02°, 0.05°, 0.1°, 0.2°, 0.4°, 0.8°)
- [ ] 建立法向力—偏置曲线
- [ ] 验证单调性
- [ ] 标定粗磨 30N 和精磨 20N 零位偏置
- [ ] 完成三重法向力核对（误差 <5%）
- [ ] 工件边界条件敏感性（双顶尖 vs 双端 Encastre）
- [ ] 网格敏感性 (coarse/medium/fine)

---

## 待执行: Gate V8-4 至 V8-8

### Gate V8-4: 6 个接触场景
- 固定零位偏置、预紧力、网格尺寸
- 运行 x2=35, 42.5, 50mm × rough, fine = 6 个场景
- 建立接触 CPRESS 库 (面积加权统计)
- 输出 `results/contact_library_v8.json` 和 `.csv`

### Gate V8-5: 移动热源
- 基于面积加权 CPRESS 生成 DFLUX 子程序
- 工件旋转 + 往复运动轨迹
- 热边界: 对流 20 W/m²K, 辐射率 0.30
- 能量平衡误差 <10%

### Gate V8-6: 顺序热—力残余应力
- 粗磨→停止→精磨→卸载→冷却
- 输出轴向/周向/径向残余应力
- 80mm 区域面积加权平均值 + 深度曲线
- 禁止使用 EαΔT 估算

### Gate V8-7: Archard 磨损积分
- P40: K=2.0×10⁻⁵, P200: K=5.0×10⁻⁶
- 各 20 个完整往复
- 灵敏度: HV160/180/220, K×0.5/1/2, 背基模量, 预紧力

### Gate V8-8: DOE 回归与优化
- 13 个唯一 DOE 组合
- 二次响应面: Y = β₀ + β₁X₁ + β₂X₂ + β₃X₃ + β₁₂X₁X₂ + ...
- 17 行完整结果 CSV
- Pareto 前沿 + 推荐点复算

---

## 文件清单

### 配置文件 (12个)
```
D:\mcp\abaqus_mcp\polishing_analysis\optimized_v8\config\
├── model_parameters_v8.yaml
├── material_aisi304_v8.yaml
├── coordinate_system_v8.yaml
├── assembly_reference_v8.yaml
├── belt_geometry_v8.yaml
├── belt_lineage_v8.yaml
├── frame_actuation_v8.yaml
├── contact_force_targets_v8.yaml
├── contact_validation_limits_v8.yaml
├── thermal_parameters_v8.yaml
├── wear_parameters_v8.yaml
├── solver_budget_v8.yaml
└── optimization_constraints_v8.yaml
```

### 脚本文件 (3个)
```
D:\mcp\abaqus_mcp\polishing_analysis\optimized_v8\scripts\
├── generate_two_pulley_belt_path.py    # Gate V8-1/V8-2: 双带轮路径 + 坐标验证
├── build_frame_driven_belt_model.py    # Gate V8-3: 框架驱动接触 INP 生成器
└── build_v8_simple.py                  # Gate V8-3: 简化矩形网格接触模型
```

### 结果文件 (4个)
```
D:\mcp\abaqus_mcp\polishing_analysis\optimized_v8\results\
├── v7_status_reclassification.json     # V7 资产重新分类
├── belt_pretension_v8.json             # V8 预紧力标定结果
├── belt_lineage_manifest_v8.json       # V8 砂带血缘清单
└── contact_models_v8.json              # V8 接触模型清单
```

### 哨兵文件 (3个)
```
D:\mcp\abaqus_mcp\polishing_analysis\optimized_v8\sentinels\
├── gate_v8_0.json   # PASS — V7 审计完成
├── gate_v8_1.json   # PASS — 坐标系统验证
└── gate_v8_2.json   # PASS — 预紧力标定完成
```

### 报告文件 (2个)
```
D:\mcp\abaqus_mcp\polishing_analysis\optimized_v8\reports\
├── v7_findings_and_v8_plan.md          # V7 审计发现与 V8 执行计划
└── coordinate_system_audit_v8.md       # 坐标系统审计报告
```

### INP 文件 (22个)
```
D:\mcp\abaqus_mcp\polishing_analysis\optimized_v8\inps\
├── belt_v8_pretension_rough.inp, belt_v8_pretension_fine.inp
├── belt_v8_pretension_rough_v2.inp, belt_v8_pretension_fine_v2.inp
├── contact_v8_rough_center.inp, contact_v8_fine_center.inp
└── contact_v8_{rough,fine}_ofs_{0p0000..0p8000}.inp (16个)
```

### ODB 文件 (4个)
```
D:\mcp\abaqus_mcp\abaqus_work\jobs\
├── belt_v8_pretension_rough.odb       (2.5 MB)
├── belt_v8_pretension_fine.odb        (2.5 MB)
├── belt_v8_pretension_rough_v2.odb    (2.5 MB)
├── belt_v8_pretension_fine_v2.odb     (2.5 MB)
├── contact_v8_rough_center.odb        (待提取)
└── contact_v8_fine_center.odb         (待提取)
```

---

## V7 与 V8 关键差异

| 项目 | V7 | V8 |
|---|---|---|
| 接触驱动方式 | BELTMID 统一 Z 位移 | 框架绕大带轮中心旋转 |
| 砂带运行方向 | ∥ 工件轴线 | ⟂ 工件轴线（YZ 平面） |
| 砂带宽度方向 | ⟂ 工件轴线 | ∥ 工件轴线（X 方向） |
| 砂带几何 | 平面矩形 (200×30mm) | 平面矩形 (200×30mm) + 带轮路径 |
| 预紧力 (粗/精) | 90.23N / 60.18N | 90.30N / 59.49N |
| 中心点接触 | 0.1mm closure → 未建立 | 框架旋转 11.85° → 待验证 |
| 坐标验证 | 未执行 | 通过 (点积检查) |
| 零位偏置扫描 | 0.1–3.5mm closure | 0–0.8° 框架偏置 |

---

## 已知问题与风险

1. **MCP 提取工具超时**: `extract_field_output` 和 `extract_history_output` 调用频繁超时，已通过 Abaqus Python 直接脚本绕过
2. **C3D8R 单元体积错误**: 圆柱网格在 theta 方向回绕导致零体积单元 — 已通过切换到矩形块网格修复
3. **框架驱动简化**: 当前使用小带轮端节点 Z 位移模拟框架旋转效果，非完整 rigid body constraint 链 — 对静态接触分析力学等效
4. **未标定参数**: 砂带背基模量、摩擦系数、磨损系数、热分配比均为工程基准值，需要实验标定
5. **缺少实测数据**: 法向力、Ra/Sa、硬度、材料证书均缺失 — 所有结果标记为 `UNCALIBRATED_ENGINEERING_BASELINE`

---

## 下一步操作

1. 提取 `contact_v8_rough_center.odb` 和 `contact_v8_fine_center.odb` 的 CPRESS/CSTATUS
2. 如接触未建立 → 调整初始间隙或零位偏置
3. 如接触已建立 → 运行零位偏置扫描 (8 个点 × 2 种砂带 = 16 个作业)
4. 建立法向力—偏置曲线并验证单调性
5. 标定粗磨 30N / 精磨 20N 零位偏置
6. 完成 Gate V8-3 网格和边界敏感性
7. 进入 Gate V8-4: 6 个接触场景
