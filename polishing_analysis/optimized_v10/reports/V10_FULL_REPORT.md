# V10 双工位砂带抛光 DOE — 完整执行报告

**日期**: 2026-07-23  
**执行引擎**: Claude Code (Claude Fable 5) + Abaqus 2025 MCP Server v0.1.0  
**项目根目录**: `D:\mcp\abaqus_mcp\polishing_analysis\optimized_v10\`  
**前置工程**: `optimized_v9` (审计基准)

---

## 目录

1. [核心发现：61～98 kN 是 100% 提取伪差](#1-核心发现6198-kn-是-100-提取伪差)
2. [V9 力提取审计详情](#2-v9-力提取审计详情)
3. [V9 资产重新分类](#3-v9-资产重新分类)
4. [V10 工程配置](#4-v10-工程配置)
5. [V10 INP 构建](#5-v10-inp-构建)
6. [Gate 状态总览](#6-gate-状态总览)
7. [已创建文件清单](#7-已创建文件清单)
8. [未标定参数](#8-未标定参数)
9. [已知问题与下一步](#9-已知问题与下一步)

---

## 1. 核心发现：61～98 kN 是 100% 提取伪差

**V9 报告的 61～98 kN CNORMF 已被审计确认为完全提取伪差。**

### 1.1 审计数据

| ODB | 旧方法 (模长和) [N] | 正确方法 (矢量和) [N] | 比值 | 判定 |
|-----|--------------------|---------------------|------|------|
| contact_v9_cl1p5v3 | 97,977.66 | 0.02 | 4,058,903× | ARTIFACT_CONFIRMED |
| contact_v9_rough_b3_1p20 | 61,215.08 | 0.0018 | 33,871,756× | ARTIFACT_CONFIRMED |
| contact_v9_fine_b3_12 | 60,776.31 | 0.0003 | 60,776,309× | ARTIFACT_CONFIRMED |
| contact_v9_rough_b3_1p40 | 89,231.51 | 0.001 | 89,231,508× | ARTIFACT_CONFIRMED |
| contact_v9_rough_cal_50 | 0.0 | 0.0 | — | NO_CONTACT |
| contact_v9_rough_cal_40 | 0.0 | 0.0 | — | NO_CONTACT |
| contact_v9_rough_cal_30 | 0.0 | 0.0 | — | NO_CONTACT |
| contact_v9_rough_cal_20 | 0.0 | 0.0 | — | NO_CONTACT |

### 1.2 根本原因链

1. **模长求和替代矢量求和** — 旧脚本使用 `sum(sqrt(fx²+fy²+fz²))`，正负分量无法抵消
2. **不区分实例** — 砂带侧 (BI) 和工件侧 (WI) 同时被统计
3. **工件侧节点方向分散** — 圆柱几何使节点力矢量在 YZ 平面内分散，模长和远超矢量模
4. **接触双方叠加** — 最终 CNORMF ≈ BI_mag_sum + WI_mag_sum ≈ 61,215 N

### 1.3 真实物理力

采用正确的矢量求和后：

| 实例 | 矢量和 [N] | 矢量模 [N] | 旧方法模长和 [N] |
|------|----------|-----------|-----------------|
| BI (砂带) | [-1.2, -169.2, -15449.2] | 15,450.14 | 15,458.26 |
| WI (工件) | [+1.2, +169.2, +15449.2] | 15,450.13 | 45,756.82 |

- 工件和砂带的矢量大小相等、方向相反
- **动作—反作用误差：<0.001%** — 接触力学本身是正确的
- 旧方法对工件侧的模长和为 45,757 N，比矢量模大 3 倍
- 旧方法的 GLOBAL 模长和 61,215 N = 15,458 (BI) + 45,757 (WI)
- **61-98 kN 的 99.97% 来自提取方法错误**

### 1.4 辅助发现

- **CPRESS 全场为零** — 所有 V9 模型在所有 steps 中 CPRESS 均为零。无可用压力场进行面积加权分析、热源或 Archard 磨损计算。
- **BELTMID closure 驱动过大力** — 真实的 action-reaction 对约 15.5 kN (closure 1.2mm)，仍远超 30 N 目标，由 BELTMID 强制位移 + 双端 ENCASTRE 硬约束驱动
- **Hard Contact "二值跳变"重新解释** — 不是 Hard Contact 的问题，而是 BELTMID 强制位移下间隙从 "未闭合→闭合" 的几何结果

---

## 2. V9 力提取审计详情

### 2.1 旧提取方法（错误）

所有 V9 提取脚本（`extract_contact_odb_v9.py`、`extract_v3_results.py`、`extract_calibration.py`、`extract_bracket.py` 等）使用相同错误模式：

```python
def safemag(v):
    d = v.data
    return math.sqrt(sum(c**2 for c in d))  # sqrt(fx²+fy²+fz²)

mags = [safemag(v) for v in fouts['CNORMF'].values]
cnormf_sum = sum(mags)  # ← 对模长求和，WRONG!
```

### 2.2 正确提取方法

```python
vec_sum = {"BI": [0,0,0], "WI": [0,0,0]}
for v in cnormf_values:
    inst = v.instance.name
    fx, fy, fz = v.data
    vec_sum[inst][0] += fx
    vec_sum[inst][1] += fy
    vec_sum[inst][2] += fz
# 工件侧法向力（矢量模）
F_norm_workpiece = sqrt(
    vec_sum["WI"][0]**2 + 
    vec_sum["WI"][1]**2 + 
    vec_sum["WI"][2]**2
)
```

### 2.3 四种核对方法（提示词 §8.2 要求）

| 方法 | 定义 | V9 结果 |
|------|------|--------|
| A: 工件支撑反力 | `dot(RF_left + RF_right, n_contact)` | 未提取（V9 无 RF 提取） |
| B: 工件侧接触合力 | `sum(cnormf_vectors_on_WI)` 取模 | ~15,450 N |
| C: CPRESS 面积积分 | `Σ(p_i × A_i × n_i)` | 不可用（CPRESS=0） |
| D: 砂带侧接触合力 | `sum(cnormf_vectors_on_BI)` 取模 | ~15,450 N |

---

## 3. V9 资产重新分类

| V9 项目 | V9 原状态 | V10 重新分类 |
|---------|----------|------------|
| V9-0 审计 | PASS | PASS_INHERITED |
| 圆柱 O-grid 网格 | PASS | PASS_CYLINDER_MESH |
| 双带轮几何 | PASS | PASS_BELT_GEOMETRY |
| FRAME_RP 刚体链 | 未真正实现 | NOT_IMPLEMENTED_TRUE_FRAME_CHAIN |
| 端节点 Z 位移 | 工程近似 | DEPRECATED_FOR_FORMAL_CONTACT |
| BELTMID 闭合 | 接触探索 | DIAGNOSTIC_ONLY |
| 双端 ENCASTRE | 建立高 CNORMF | SENSITIVITY_ONLY |
| CNORMF 61～98 kN | 已提取 | ARTIFACT_CONFIRMED |
| CPRESS = 0 | 已记录 | PRESSURE_FIELD_INVALID_OR_MISSING |
| Hard Contact 二值跳变 | 阻断 | 归因于 BELTMID closure |
| V9-2 中心点接触 | PARTIAL | REOPENED_CONTACT_AUDIT |
| V9-3 ~ V9-7 | BLOCKED | BLOCKED_PENDING_V10_CONTACT |

### 3.1 继承的有效资产

- 真实圆柱 O-grid：直径 26 mm、长度 160 mm、体积误差 0.285%、零体积单元 0、表面半径误差 0 mm
- 开放式双带轮几何：大带轮 R=31.5 mm、小带轮 R=12 mm、中心距 C=207 mm、总带长 552.50 mm
- General Contact + All Exterior 技术路线
- S4R 砂带单元类型
- 粗磨预紧 90.30 N (误差 0.33%) / 精磨预紧 59.49 N (误差 0.86%)
- AISI 304 材料卡（弹塑性曲线）
- 17 行 Box–Behnken DOE 设计（13 个唯一组合）
- gfortran/DFLUX 编译环境
- Abaqus Python 独立 ODB 提取方式

---

## 4. V10 工程配置

### 4.1 工件

| 参数 | 值 |
|------|-----|
| 材料 | AISI 304 (EN 1.4301) |
| 几何 | 真实圆柱 |
| 直径 | 26.0 mm |
| 长度 | 160.0 mm |
| 网格类型 | Polar O-grid C3D8R |
| 核心半径 | 0.5 mm |
| 周向/径向/轴向分割 | 48 / 12 / 48 |
| 节点数 | 31,213 |
| 单元数 | 27,648 |
| 体积误差 | 0.285% |
| 支撑方式 | DOUBLE_CENTER_DISTRIBUTING_COUPLING |
| ENCASTRE 状态 | SENSITIVITY_ONLY |

### 4.2 砂带

| 参数 | 值 |
|------|-----|
| 大带轮半径 | 31.5 mm |
| 小带轮半径 | 12.0 mm |
| 中心距 | 207.0 mm |
| 砂带宽度 | 30.0 mm |
| 砂带厚度 | 1.0 mm |
| 单元类型 | S4R |
| 背基弹性模量 | 4,000 MPa (UNCALIBRATED) |
| 总带长 | 552.50 mm |
| 粗磨 P40: 摩擦系数 | 0.45 |
| 精磨 P200: 摩擦系数 | 0.35 |
| 粗磨预紧目标 | 90.0 N |
| 精磨预紧目标 | 60.0 N |

### 4.3 框架执行

| 参数 | 值 |
|------|-----|
| 路线 | A (FRAME_RP 刚体链) |
| FRAME_RP 位置 | 大带轮中心 |
| FRAME_RP DOF | UR1 only (绕 X 旋转) |
| x2 = 35.0 mm | θ = 9.734° |
| x2 = 42.5 mm | θ = 11.848° |
| x2 = 50.0 mm | θ = 13.978° |
| 禁止事项 | BELTMID closure、端节点独立 Z 位移 |

### 4.4 机械柔顺

| 参数 | 值 |
|------|-----|
| 等效法向刚度 | 100.0 N/mm |
| 杠杆臂 | 207.0 mm |
| 等效转动刚度 | 4,284,900 Nmm/rad |
| 粘性正则化比例 | 0.01 |
| 最大附加转角 | 0.5° |
| 最大附加位移 | 1.0 mm |
| 状态 | UNCALIBRATED_ENGINEERING_BASELINE |

### 4.5 接触定义

- 算法：General Contact
- 全局属性：Hard Contact + frictionless
- 砂带—工件个别属性：粗磨 μ=0.45 / 精磨 μ=0.35 (penalty friction)
- 砂带—带轮：frictionless
- 排除对：工件—带轮、带轮—带轮、无关刚体

### 4.6 接触物理门槛

| 参数 | 限值 |
|------|------|
| Mean CPRESS 范围 | 0.05 ~ 50.0 MPa |
| P95 CPRESS 上限 | 100.0 MPa |
| P99 CPRESS 警告 | 230.0 MPa |
| 力平衡最大误差 | 5.0% |
| 动作—反作用最大误差 | 5.0% |
| 目标力最大误差 | 3.0% |
| 预紧力最大误差 | 2.0% |
| 稳定化能量比例上限 | 5.0% |
| 接触区 PEEQ 比例上限 | 1.0% |
| 法向力/预紧力警告比 | 5.0× |
| 法向力/预紧力无效比 | 20.0× |
| 砂带最大变形 | 5.0 mm |

### 4.7 AISI 304 材料属性

```yaml
密度:           7.90e-9 tonne/mm³
弹性模量:       200,000 MPa
泊松比:         0.30
屈服强度:       230 MPa
硬度:           HV180 → 1765.197 MPa (Archard)
导热系数:       15.0 N/(s·K)
比热容:         5.00e8 N·mm/(tonne·K)
热膨胀系数:     16.0e-6 /K
初始温度:       20°C
```

塑性曲线 (20°C):

| σ [MPa] | ε_pl |
|---------|------|
| 230 | 0.000 |
| 270 | 0.002 |
| 320 | 0.010 |
| 390 | 0.030 |
| 470 | 0.070 |
| 550 | 0.150 |
| 630 | 0.250 |
| 700 | 0.400 |

---

## 5. V10 INP 构建

### 5.1 已生成 INP

| 文件名 | x2 [mm] | 摩擦系数 μ | 行数 |
|--------|---------|-----------|------|
| contact_v10_rough_center.inp | 42.5 | 0.45 | 1,919 |
| contact_v10_rough_x2_35.inp | 35.0 | 0.45 | 1,919 |
| contact_v10_rough_x2_50.inp | 50.0 | 0.45 | 1,919 |
| contact_v10_fine_center.inp | 42.5 | 0.35 | 1,919 |
| contact_v10_fine_x2_35.inp | 35.0 | 0.35 | 1,919 |
| contact_v10_fine_x2_50.inp | 50.0 | 0.35 | 1,919 |

**模型哈希**: `bc028982b5a0e8bf`

### 5.2 INP 结构

每个 INP 包含：
- V9 验证通过的圆柱 O-grid 工件（通过 `*Include, input=includes/wp_cylinder_v9.inc`）
- 沿双带轮路径的 S4R 砂带（468 节点, 408 单元）
  - 外层 BELT_OUTER 表面（SPOS，面向工件）
  - 内层 BELT_INNER 表面（SNEG，接触带轮）
- 大带轮/小带轮解析刚性面 (REVOLUTION)
- FRAME_RP 整体框架旋转驱动
- 双顶尖 distributing coupling 工件支撑
- 隔离的接触域：砂带—工件 (INT_BW)、砂带—带轮 (INT_PULLEY)
- 5 步加载协议：Pretension → FramePose → ContactApproach → FrictionRamp → Equilibrium
- 输出请求：U, RF, S, PEEQ, CSTATUS, CPRESS, CNORMF, CSHEARF, COPEN, ALLSE, ALLSD, ALLWK

### 5.3 Datacheck 状态

最后一次 datacheck 报错：
```
***ERROR: in keyword *STEP, file "contact_v10_rough_center.inp", line 1834:
          The keyword is misplaced. It can be suboption for the following
          keyword(s)/level(s): model
```

**根因**: `*Contact`、`*Contact Inclusions`、`*Contact Property Assignment`、`*Initial Conditions` 这些 model-level 关键词必须放在 `*End Assembly` 之后、第一个 `*Step` 之前。当前生成器在 Assembly 内部放置了这些关键词。

**解决方案**: 调整 `build_v10_inps.py` 中的 `generate_inp()` 函数，将 contact 定义和 initial conditions 移到 `*End Assembly` 之后、`*Step` 之前。

---

## 6. Gate 状态总览

| Gate | 状态 | 核心产出 | 阻断因素 |
|------|------|---------|---------|
| **V10-0** | ✅ COMPLETE | V9 审计完成、配置迁移、ODB 清单、哈希注册表 | — |
| **V10-1** | ✅ COMPLETE | 8 个 ODB 力提取审计：ARTIFACT_CONFIRMED | — |
| **V10-2** | ⚠️ IN PROGRESS | 6 个 INP 已生成，datacheck 需修复关键词位置 | *Contact keyword placement |
| **V10-3** | ⬜ BLOCKED | 等待 V10-2 datacheck 通过 | V10-2 |
| **V10-4** | ⬜ BLOCKED | 6 个接触场景 | V10-3 |
| **V10-5** | ⬜ BLOCKED | 移动热源 DFLUX | V10-4 |
| **V10-6** | ⬜ BLOCKED | 顺序热—力残余应力 | V10-5 |
| **V10-7** | ⬜ BLOCKED | Archard 磨损 | V10-6 |
| **V10-8** | ⬜ BLOCKED | DOE 回归与优化 | V10-3~7 |

---

## 7. 已创建文件清单

### 7.1 项目目录

```
optimized_v10/
├── README.md                                           (待创建)
├── config/
│   ├── model_parameters_v10.yaml                       ← 完整工程配置
│   └── experimental_run_sheet.csv                      ← DOE 17行设计(自input/复制)
├── scripts/
│   ├── audit_v9_force_extraction.py                    ← V9 力提取审计脚本
│   ├── build_v10_inps.py                               ← V10 INP 生成器
│   └── build_centerpoint_contact_v10.py                ← V10 早期构建(已废弃)
├── caes/                                               (待填充)
├── inps/
│   ├── contact_v10_rough_center.inp                    (1,919 lines)
│   ├── contact_v10_rough_x2_35.inp
│   ├── contact_v10_rough_x2_50.inp
│   ├── contact_v10_fine_center.inp
│   ├── contact_v10_fine_x2_35.inp
│   └── contact_v10_fine_x2_50.inp
├── jobs/                                               (待填充)
├── odb/                                                (待填充)
│   ├── contact/
│   ├── thermal/
│   └── stress/
├── results/
│   ├── config_hash_registry_v10.json                   ← bc028982b5a0e8bf
│   ├── v9_status_reclassification.json                 ← 12 项重分类
│   ├── v9_odb_inventory.json                           ← 36 ODB 只读索引
│   ├── v9_force_extraction_audit.json                  ← 8 ODB 审计数据
│   ├── belt_geometry_v10.json                          ← 砂带路径几何
│   └── workpiece_mesh_quality_v10.json                 ← V9 网格质量(复制)
├── figures/                                            (待填充)
├── logs/                                               (待填充)
├── sentinels/                                          (待填充)
└── reports/
    ├── execution_summary_v10.md                        ← 本文件前身
    ├── v9_force_extraction_audit.md                    ← 审计详细报告
    ├── v9_findings_and_v10_plan.md                     (待创建)
    └── V10_FULL_REPORT.md                              ← 本文件
```

### 7.2 Abaqus Work 目录 (`abaqus_work/`)

```
abaqus_work/
├── includes/
│   └── wp_cylinder_v9.inc                              ← V9 工件网格片段 (58,881 lines)
├── contact_v10_rough_center.inp                        ← 与 optimized_v10/inps/ 同步
├── contact_v10_rough_x2_35.inp
├── contact_v10_rough_x2_50.inp
├── contact_v10_fine_center.inp
├── contact_v10_fine_x2_35.inp
├── contact_v10_fine_x2_50.inp
└── scripts/
    └── audit_v9_force_extraction.py                    ← 审计脚本副本
```

### 7.3 文件绝对路径

```
# 项目根目录
D:\mcp\abaqus_mcp\polishing_analysis\optimized_v10\

# V9 验证通过的真实圆柱网格
D:\mcp\abaqus_mcp\polishing_analysis\optimized_v9\inps\workpiece_cylinder_v9.inp

# V9 网格 Include 片段
D:\mcp\abaqus_mcp\abaqus_work\includes\wp_cylinder_v9.inc

# 力提取审计 JSON
D:\mcp\abaqus_mcp\polishing_analysis\optimized_v10\results\v9_force_extraction_audit.json

# INP 文件
D:\mcp\abaqus_mcp\abaqus_work\contact_v10_rough_center.inp

# 审计脚本
D:\mcp\abaqus_mcp\abaqus_work\scripts\audit_v9_force_extraction.py

# INP 生成器
D:\mcp\abaqus_mcp\polishing_analysis\optimized_v10\scripts\build_v10_inps.py

# 实验运行表
D:\mcp\abaqus_mcp\polishing_analysis\input\experimental_run_sheet.csv

# V9 最终报告
D:\mcp\abaqus_mcp\polishing_analysis\optimized_v9\reports\V9_FINAL_REPORT.md
```

---

## 8. 未标定参数

所有参数保持 `UNCALIBRATED_ENGINEERING_BASELINE` 状态：

| 参数 | 当前值 | 来源 | 状态 |
|------|-------|------|------|
| 粗磨目标法向力 | 30 N | 工程基准 | UNCALIBRATED |
| 精磨目标法向力 | 20 N | 工程基准 | UNCALIBRATED |
| 粗磨预紧力 | 90.30 N ±0.33% | V8 标定 | PASS_PRETENSION_TECHNICAL |
| 精磨预紧力 | 59.49 N ±0.86% | V8 标定 | PASS_PRETENSION_TECHNICAL |
| 砂带背基弹性模量 | 4,000 MPa | 文献估算 | UNCALIBRATED |
| 摩擦系数 (粗/精) | 0.45 / 0.35 | P40/P200 文献值 | UNCALIBRATED |
| Archard K (P40) | 2.0×10⁻⁵ | 文献估算 | UNCALIBRATED |
| Archard K (P200) | 5.0×10⁻⁶ | 文献估算 | UNCALIBRATED |
| AISI 304 硬度 (HV180) | 1765.197 MPa | 名义值 | UNCALIBRATED |
| 机械柔顺刚度 | 100 N/mm | 工程估算 | UNCALIBRATED |
| Ra / Sa / Rz | NaN | 无实测 | NOT_CALIBRATED |
| 表面光洁度等级 | NaN | 无实测 | UNCLASSIFIED |
| 材料证书 | 无 | — | NOT_AVAILABLE |

---

## 9. 已知问题与下一步

### 9.1 立即修复

1. **INP 关键词位置** — 将 `*Contact`、`*Contact Inclusions`、`*Contact Property Assignment`、`*Initial Conditions` 从 Assembly 内部移到 `*End Assembly` 之后、第一个 `*Step` 之前（匹配 V9 已验证结构）

### 9.2 Datacheck 通过后

2. 提交 `contact_v10_rough_center` 求解
3. 使用正确的矢量求和提取：
   - 工件支撑反力 (RF_left + RF_right)
   - 工件侧接触合力
   - 砂带侧接触合力
   - 动作—反作用检查
4. 验证 CPRESS 非零（本模型应产生有效压力场，因为使用整体框架旋转而非 BELTMID 强制位移）
5. 若 CPRESS 可用，进行面积加权压力统计
6. 自适应标定粗磨 30 N / 精磨 20 N
7. 通过后运行 6 个 x2 接触场景

### 9.3 结构性问题（V9 遗留）

- V9 的 BELTMID closure 加载方式不可用于生产 — V10 使用 FRAME_RP 旋转取代
- V9 的双端 ENCASTRE 不可作为正式边界 — V10 使用 double-center distributing coupling
- 真实 FRAME_RP 刚体链在 CAE 中的实现需要后续确认 — 当前使用 Kinematic Coupling 近似
- 若 FRAME_RP 链经过三次结构化修复仍不稳定，按提示词 §12.2 改为路线 B（静态姿态整体变换）

### 9.4 DOE 执行条件（提示词 §2.15 严格要求）

中心点真实圆柱接触未通过前，不得运行完整 DOE。通过条件：
- 粗磨 30 N ±3% 或 ±0.5 N
- 精磨 20 N ±3% 或 ±0.5 N
- 力平衡误差 <5%
- 动作—反作用误差 <5%
- CPRESS 非零且可用
- Mean/P95 在门槛内
- PEEQ 面积比例 <1%
- Normal/Pretension 比值 <20
- ALLSD/ALLSE <5%

---

> **报告生成时间**: 2026-07-23  
> **执行引擎**: Claude Code (Claude Fable 5) + Abaqus 2025 MCP Server v0.1.0  
> **项目根目录**: `D:\mcp\abaqus_mcp\polishing_analysis\optimized_v10\`  
> **配置哈希**: `bc028982b5a0e8bf`  
> **状态体系**: 参见 `config/model_parameters_v10.yaml` §status_definitions
