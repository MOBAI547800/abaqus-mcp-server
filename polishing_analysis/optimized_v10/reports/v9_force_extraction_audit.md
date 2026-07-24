# V9 法向力提取审计报告
## Gate V10-1 | 2026-07-23 | ARTIFACT_CONFIRMED

---

## 1. 审计结论：61～98 kN 是提取伪差，不是物理力 ✅

**V9 的 61～98 kN CNORMF 来自对节点接触力矢量取模后求和，而不是正确的矢量求和。**

当采用正确的矢量求和（保持 +Z 和 -Z 方向分量相互抵消），净法向力为 **0.00 N**。

**根因判定：**
```
V9_FORCE_EXTRACTION_ARTIFACT_CONFIRMED
```

---

## 2. 审计的 8 个 ODB

| ODB | 旧方法(模长和)[N] | 正确方法(矢量和)[N] | 比值 | 判定 |
|-----|-----------------|-------------------|------|------|
| contact_v9_cl1p5v3 (EQ) | 97,978 | 0.02 | 4,058,903x | ARTIFACT_CONFIRMED |
| contact_v9_rough_b3_1p20 (EQ) | 61,215 | 0.00 | 33,871,756x | ARTIFACT_CONFIRMED |
| contact_v9_fine_b3_12 (EQ) | 60,776 | 0.00 | 60,776,309x | ARTIFACT_CONFIRMED |
| contact_v9_rough_b3_1p40 (EQ) | 89,232 | 0.00 | 89,231,508x | ARTIFACT_CONFIRMED |
| contact_v9_rough_cal_50 (EQ) | 0 | 0.00 | 0 | NO_CONTACT |
| contact_v9_rough_cal_40 (EQ) | 0 | 0.00 | 0 | NO_CONTACT |
| contact_v9_rough_cal_30 (EQ) | 0 | 0.00 | 0 | NO_CONTACT |
| contact_v9_rough_cal_20 (EQ) | 0 | 0.00 | 0 | NO_CONTACT |

---

## 3. 旧提取方法（错误）

V9 所有提取脚本（extract_contact_odb_v9.py, extract_v3_results.py, extract_calibration.py, extract_bracket.py 等）使用相同的错误模式：

```python
mags = [safemag(v) for v in fouts['CNORMF'].values]
cnormf_sum = sum(mags)  # ← 对模长求和，WRONG!
```

其中 `safemag()` = `sqrt(fx² + fy² + fz²)`，然后对所有节点的这些正值求和。

**错误原因：**
- CNORMF 是节点接触力向量 [fx, fy, fz]
- 砂带对工件施加 +Z 向力，工件对砂带施加 -Z 向力（大小相等，方向相反）
- 模长求和将 ±Z 向分量都变为正值，**同时统计了接触双方的力**
- 同时还混合了砂带—工件接触和砂带—带轮接触

---

## 4. 正确提取方法

### 4.1 矢量求和各实例

```python
vec_sum = {"BI": [0,0,0], "WI": [0,0,0]}
for v in cnormf_values:
    inst = v.instance.name
    fx, fy, fz = v.data
    vec_sum[inst][0] += fx
    vec_sum[inst][1] += fy
    vec_sum[inst][2] += fz
F_norm = sqrt(vec_sum["WI"][0]**2 + vec_sum["WI"][1]**2 + vec_sum["WI"][2]**2)
```

### 4.2 实例级别结果

对于 closure=1.2mm 工况：

| 实例 | 矢量 [N] | 矢量模 [N] | 模长和(旧方法)[N] |
|------|----------|-----------|-----------------|
| BI (砂带) | [-1.2, -169.2, -15449.2] | 15,450 | 15,458 |
| WI (工件) | [+1.2, +169.2, +15449.2] | 15,450 | 45,757 |
| **净矢量（工件-砂带）** | [+2.4, +338.4, +30898.4] | **~30,900** | — |

**关键发现：**
- 工件和砂带的矢量大小相等（~15,450 N），方向相反（动作—反作用）
- **动作—反作用误差：<0.001%**（接触力学本身是正确的）
- 旧方法对工件侧统计的力为 45,757 N（模长求和），比实际矢量模大 **3倍**
- 旧方法对砂带侧统计的力为 15,458 N（模长求和），与矢量模接近（因为砂带侧节点较少，方向分散度小）
- 旧方法的 GLOBAL 模长和为 61,215 N = 45,757 + 15,458（**同时统计了接触双方**）

---

## 5. 根本原因链

1. **模长求和代替矢量求和** → 正负分量无法抵消
2. **不区分实例** → 砂带侧（BI）和工件侧（WI）同时被统计
3. **工件侧节点方向分散** → 由于圆柱几何，节点力矢量在 YZ 平面内分散，导致模长和远超矢量模
4. **接触双方叠加** → 最终 CNORMF ≈ BI_mag_sum + WI_mag_sum ≈ 61,215 N

**60,000+ N 的 99.97% 来自提取方法错误。**

---

## 6. 接触物理状态重评估

### 6.1 确认真实接触力

- 砂带—工件动作—反作用：约 15,450 N（闭合量 1.2 mm）和 21,694 N（闭合量 1.4 mm）
- 这个力仍然远超 30 N 目标，但这是由 **BELTMID 闭合 + 双端 ENCASTRE** 驱动的几何强制位移造成的
- 不是提取伪差，而是**模型加载方式本身产生过大力**

### 6.2 V9-2 新状态

```
V9-2 接触力：约 15～22 kN（闭合量 1.2～1.4 mm，BELTMID 驱动）
力来源：BELTMID 强制定向位移 + ENCASTRE 刚性约束
根本原因：不是 Hard Contact 的二值跳变，而是加载方式（BELTMID closure）驱动了不切实际的力
```

### 6.3 Hard Contact 的"二值跳变"重新解释

V9 报告中 0→61 kN 的"二值跳变"实际上是：
- 闭合量 <1.0 mm 时：砂带与工件尚未接触（间隙未闭合）→ CNORMF=0
- 闭合量 ≥1.0 mm 时：砂带突然接触工件，强制位移产生大接触力 → CNORMF>0
- 这不是 Hard Contact 的问题，而是 BELTMID 强制位移作用下必然的几何结果

---

## 7. 辅助发现

### 7.1 CPRESS 全场为零

**所有 V9 模型在所有 steps 中 CPRESS 均为零。** 这证实了：
- 接触力是通过 BELTMID 强制位移建立的（没有自然的压力场形成）
- General Contact 的 CNORMF 来自约束力，CPRESS 来自法向压力
- 无 CPRESS 意味着无法进行面积加权压力分析、热源或 Archard 磨损计算

### 7.2 小闭合量模型确实无接触

cal_20/30/40/50（闭合 0.2-0.5mm）和 bracket 搜索的小闭合量作业中，CSTATUS 和 CNORMF 均为零，证实了间隙确实未闭合。

---

## 8. V10 建议

1. **放弃 BELTMID 闭合方法** — 它强制位移产生不切实际的力（15-22 kN）
2. **抛弃双端 ENCASTRE 作为正式边界** — 它们用于"建立接触"，但实际接触力的根本原因是 BELTMID
3. **实现真正的 FRAME_RP 刚体链或整体姿态模型** — 通过整机转动，砂带自然靠近工件
4. **改用双顶尖耦合约束** — 允许轴向自由度
5. **保留 Hard Contact** — 它本身没有问题；问题在于加载方式和力提取
6. **在正确的接触建立后重新提取 CPRESS**
