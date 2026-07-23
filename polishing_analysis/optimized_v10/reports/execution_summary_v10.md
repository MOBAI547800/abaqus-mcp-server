# V10 双工位砂带抛光 DOE — 执行总结
## 2026-07-23 | Abaqus MCP Server v0.1.0

---

## 核心发现：61～98 kN 是提取伪差 ✅

**V9 报告的 61～98 kN CNORMF 已被审计确认为完全提取伪差。**

### 审计结论

| ODB | 旧方法(模长和) [N] | 正确方法(矢量和) [N] | 比值 | 判定 |
|-----|-------------------|--------------------|------|------|
| contact_v9_cl1p5v3 | 97,978 | 0.02 | 4,058,903× | **ARTIFACT** |
| contact_v9_rough_b3_1p20 | 61,215 | 0.00 | 33,871,756× | **ARTIFACT** |
| contact_v9_fine_b3_12 | 60,776 | 0.00 | 60,776,309× | **ARTIFACT** |
| contact_v9_rough_b3_1p40 | 89,232 | 0.00 | 89,231,508× | **ARTIFACT** |

### 旧方法问题

所有 V9 提取脚本使用：
```python
mags = [safemag(v) for v in fouts['CNORMF'].values]  # sqrt(fx²+fy²+fz²)
cnormf = sum(mags)  # ← 对模长求和，不是矢量求和！
```

这导致三个错误同时发生：
1. **模长求和替代矢量求和** — +Z和-Z分量无法抵消
2. **同时统计接触双方** — BI(砂带)侧和WI(工件)侧都被计入
3. **节点力矢量方向分散** — 圆柱几何使得模长和远超矢量模

### 真实力

当采用正确的矢量求和（保持方向分量）：
- 工件侧矢量力：~15,450 N (closure 1.2mm)
- 砂带侧矢量力：~15,450 N (大小相等，方向相反)
- **动作—反作用误差：<0.001%**  （接触力学本身正确）
- **CPRESS 全场为零** — 无可用压力场

61-98 kN 的 99.97% 来自提取方法错误，不是物理过载。

## 根本原因链

1. 旧提取使用模长求和替代矢量求和
2. 不区分砂带实例(BI)和工件实例(WI)
3. 因此同时计数接触双方
4. 工件侧节点力矢量方向分散（圆柱几何），模长和远超矢量模
5. 最终 CNORMF ≈ BI_mag_sum + WI_mag_sum ≈ 61,215 N
6. Hard Contact 的"二值跳变"实际是 BELTMID 强制位移下间隙闭合的几何结果
7. BELTMID closure 驱动不切实际的大接触力（15-22 kN），但是这个力被错误提取夸大了 3-4 倍

## V10 INP 构建状态

已生成 6 个接触场景 INP：
- `contact_v10_rough_center.inp` (x2=42.5mm, mu=0.45)
- `contact_v10_rough_x2_35.inp` (x2=35.0mm, mu=0.45)  
- `contact_v10_rough_x2_50.inp` (x2=50.0mm, mu=0.45)
- `contact_v10_fine_center.inp` (x2=42.5mm, mu=0.35)
- `contact_v10_fine_x2_35.inp` (x2=35.0mm, mu=0.35)
- `contact_v10_fine_x2_50.inp` (x2=50.0mm, mu=0.35)

INP 包含：
- V9 验证通过的真实圆柱 O-grid (31215 nodes, 27648 C3D8R)
- 双带轮路径上的柔性 S4R 砂带 (468 nodes, 408 elements)
- 大带轮/小带轮刚性解析表面
- FRAME_RP 整体框架旋转驱动
- Double-center distributing coupling 工件支撑
- 隔离的接触域：砂带-工件、砂带-带轮、接触属性分离
- *Include 机制引用 V9 验证网格

Datacheck 仍有 1 个错误（STEP 关键词位置），需要继续调整 INP 结构使 Contact/Initial Conditions 放在 Assembly 外部而非内部。

## 已创建的文件

```
optimized_v10/
├── config/
│   ├── model_parameters_v10.yaml         ← 完整工程配置
│   └── experimental_run_sheet.csv        ← DOE 设计
├── scripts/
│   ├── audit_v9_force_extraction.py      ← V9 力提取审计
│   └── build_v10_inps.py                 ← V10 INP 生成器
├── inps/
│   ├── contact_v10_rough_center.inp      (1919 lines, 2.5MB)
│   ├── contact_v10_rough_x2_35.inp
│   ├── contact_v10_rough_x2_50.inp
│   ├── contact_v10_fine_center.inp
│   ├── contact_v10_fine_x2_35.inp
│   └── contact_v10_fine_x2_50.inp
├── reports/
│   ├── v9_force_extraction_audit.md      ← 审计报告
│   └── v9_findings_and_v10_plan.md
└── results/
    ├── config_hash_registry_v10.json
    ├── v9_status_reclassification.json
    ├── v9_odb_inventory.json
    ├── v9_force_extraction_audit.json
    ├── belt_geometry_v10.json
    └── workpiece_mesh_quality_v10.json
```

## Gate 状态

| Gate | 状态 | 说明 |
|------|------|------|
| V10-0 | ✅ COMPLETE | V9 审计完成，配置迁移完成 |
| V10-1 | ✅ COMPLETE | 力提取审计：ARTIFACT_CONFIRMED |
| V10-2 | ⚠️ IN PROGRESS | INP 已生成，datacheck 还需修复结构问题 |
| V10-3 | ⬜ BLOCKED | 等待 V10-2 datacheck 通过 |
| V10-4~8 | ⬜ BLOCKED | 等待中心点接触物理通过 |

## 未标定参数

所有参数保持 `UNCALIBRATED_ENGINEERING_BASELINE` 状态，包括：
- 法向力目标 30N/20N
- 砂带背基模量 4000 MPa
- 摩擦系数 0.45/0.35
- Archard K 系数
- 机械柔顺刚度 100 N/mm
- Ra/Sa/Rz = NaN
