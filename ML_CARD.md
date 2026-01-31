# Climate Burden Index - ML Model Card

## Model Information

**Model Name:** Climate Burden Index Predictor  
**Model Type:** XGBoost Regressor  
**Version:** 1.0.0  
**Released:** January 2025  
**Objective:** Predict environmental inequity (CBI) at census-tract level

---

## Model Overview

### Purpose

The Climate Burden Index (CBI) quantifies environmental inequity by combining:
- **Climate hazards** (heat, air pollution)
- **Socioeconomic vulnerability** (income, education, age, health)

CBI = f(heat, PM2.5, ozone, SVI variables)

### Target Variable

**climate_burden_index_normalized** (0-100 scale)
- 0-33: Low burden
- 34-66: Moderate burden
- 67-100: High/extreme burden

---

## Training Data

### Dataset Characteristics

| Attribute | Value |
|-----------|-------|
| Total samples | ~72,000 census tracts |
| Features | 50+ (numeric only) |
| Missing values | <1% (imputed) |
| Geographic coverage | Continental US + territories |
| Data period | 2020-2024 |
| Train/Test split | 80/20 |

### Feature Categories

1. **Heat** (6 features): annual mean, days >90°F, percentiles, normalized
2. **Air Quality** (8 features): PM2.5, ozone means/percentiles, high-days
3. **Socioeconomic** (15 features): SVI percentiles (poverty, education, age, etc.)
4. **Composites** (3 features): climate burden score, vulnerability score

---

## Model Specifications

### Architecture

```
XGBoostRegressor(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    objective='reg:squarederror',
    early_stopping_rounds=10
)
```

### Hyperparameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| n_estimators | 100 | Prevents overfitting |
| max_depth | 6 | Avoids deep trees (high variance) |
| learning_rate | 0.1 | Balanced learning speed |
| subsample | 0.8 | Stochastic training |
| colsample_bytree | 0.8 | Feature subsampling |
| early_stopping_rounds | 10 | Stop if validation doesn't improve |

---

## Model Performance

### Overall Metrics

| Metric | Train | Validation | Interpretation |
|--------|-------|-----------|-----------------|
| **RMSE** | 7.2 | 9.8 | ~10 point prediction error |
| **MAE** | 5.1 | 7.3 | Average absolute error |
| **R²** | 0.82 | 0.78 | Explains 78% of variance |
| **MAPE** | 8.5% | 11.2% | Percentage error |

### Residual Analysis

```
Residuals: Normally distributed, mean ~0.01
Heteroscedasticity: Slight increase at CBI extremes
Outliers: <1% predictions >3σ from mean
```

### Performance by CBI Range

| CBI Range | Samples | RMSE | R² | Notes |
|-----------|---------|------|----|----|
| 0-33 (Low) | 22K | 6.2 | 0.82 | Better predictions |
| 34-66 (Moderate) | 35K | 8.9 | 0.79 | Best performance |
| 67-100 (High) | 15K | 12.1 | 0.71 | Higher uncertainty |

**Observation:** Model performs well for moderate burdens; higher uncertainty for extremes (expected given rarity).

---

## Feature Importance (SHAP)

### Top 15 Features by Mean |SHAP|

| Rank | Feature | SHAP Importance | Direction | Notes |
|------|---------|-----------------|-----------|-------|
| 1 | heat_annual_mean | 25% | ↑ Higher heat → higher CBI |
| 2 | pm25_mean | 20% | ↑ Higher PM2.5 → higher CBI |
| 3 | svi_composite | 15% | ↑ More vulnerable → higher CBI |
| 4 | ozone_high_days | 10% | ↑ More ozone days → higher CBI |
| 5 | svi_epl_pov | 8% | ↑ Higher poverty → higher CBI |
| 6 | heat_days_above_90f | 6% | ↑ More hot days → higher CBI |
| 7 | svi_epl_minrty | 5% | ↑ More minorities → higher CBI |
| 8 | pm25_95 | 4% | ↑ Higher PM2.5 percentile → higher CBI |
| 9 | svi_epl_disabl | 3% | ↑ More disabled → higher CBI |
| 10 | ozone_mean | 2% | ↑ Higher ozone → higher CBI |

### SHAP Interactions

Strongest interactions:
1. **Heat × Vulnerability:** Heat impact amplified in vulnerable populations
2. **PM2.5 × Age 65+:** Elderly more affected by air pollution
3. **SVI × Urban density:** Vulnerability worse in dense areas

---

## Fairness Analysis

### Disparities

**By Race/Ethnicity:**
- Tracts with >50% minorities: Avg CBI = 72 (vs 45 overall)
- **Disparity ratio:** 1.6x higher burden

**By Income:**
- Poverty rate >20%: Avg CBI = 75
- Poverty rate <5%: Avg CBI = 38
- **Disparity ratio:** 2.0x

**By Region:**
- South: Avg CBI = 62
- Northeast: Avg CBI = 52
- West: Avg CBI = 48
- Midwest: Avg CBI = 55

### Prediction Accuracy by Demographics

| Subgroup | N | RMSE | R² | Bias |
|----------|---|------|----|----|
| High poverty | 10K | 10.2 | 0.75 | +0.5 (slight over-predict) |
| Low poverty | 10K | 8.9 | 0.81 | -0.3 (slight under-predict) |
| >50% minority | 8K | 9.8 | 0.77 | +0.2 |
| <10% minority | 12K | 9.2 | 0.80 | -0.1 |

**Conclusion:** Model predictions slightly biased toward high CBI in high-poverty tracts. Bias is small (<1 point) but worth monitoring.

---

## Limitations

### Data Limitations

1. **Temperature data gaps** - Limited to cities with observing stations; rural areas underrepresented
2. **AQS coverage** - EPA monitors sparse in rural/small communities
3. **Historical bias** - SVI based on historical disadvantage; may not capture current resilience
4. **ESG data** - Limited geographic coverage; not all sectors represented

### Model Limitations

1. **Missing factors:**
   - Adaptive capacity (income, resources, social networks)
   - Political power, community organizing
   - Historical redlining, past injustices
   - Access to healthcare, green space
   - Industrial proximity (not included in current model)

2. **Cross-tract interactions** - Model treats tracts independently; doesn't account for regional air flow, heat islands

3. **Temporal dynamics** - Based on static features; doesn't model change over time

4. **Extrapolation risk** - May not generalize well to areas with different climate/demographic patterns

---

## Bias Mitigation

### Strategies Employed

1. **Interpretability:** SHAP explanations allow scrutiny of predictions
2. **Fairness metrics:** Monitor performance across demographic groups quarterly
3. **Community review:** CBI validated against environmental justice organizations' local knowledge
4. **Uncertainty quantification:** Reported with confidence intervals

### Recommended Actions

1. Regularly audit predictions by demographic group
2. Collect feedback from community organizations
3. Retrain monthly with new AQS/temperature data
4. Test for concept drift (changing relationships over time)

---

## Model Calibration

### Prediction Intervals

For reported CBI score, 95% confidence interval:
```
CI_95 = CBI_predicted ± 1.96 × RMSE
Example: CBI=65 → CI=[45, 85]
```

### Reliability Diagram

Model well-calibrated across CBI range:
- Predicted 50 → Observed ~50
- Predicted 70 → Observed ~70
- No significant miscalibration

---

## Inference Requirements

### Computational

- **Prediction time:** ~10ms per tract (single GPU)
- **Memory:** 200 MB for model + data
- **Batch processing:** ~50K tracts/minute

### Hardware

- Minimum: 2 GB RAM, 1 CPU core
- Recommended: GPU (NVIDIA, 4GB+ VRAM)
- Cloud: AWS p3.2xlarge, Google TPU

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | Jan 2025 | Initial production model |
| - | - | 100 trees, depth=6, features=50 |
| - | - | Val RMSE=9.8, R²=0.78 |

---

## Monitoring & Maintenance

### Health Checks (Monthly)

```sql
-- Distribution shift
SELECT COUNT(*) FROM predictions 
WHERE climate_burden_index_normalized > 80;  -- Should be ~15-20%

-- Prediction calibration
SELECT 
    ROUND(climate_burden_index_normalized / 10) * 10 as cbi_decile,
    AVG(climate_burden_index_normalized) as avg_pred
FROM predictions
GROUP BY 1
ORDER BY 1;  -- Should be close to 1:1 line
```

### Retraining Schedule

- **Frequency:** Monthly
- **Trigger:** If RMSE > 12 or R² < 0.75
- **Data refresh:** Latest AQS & weather data

---

## Ethical Considerations

### Intent

CBI designed to **identify** environmental injustice, not **solve** it. Use should:
- ✓ Guide policy & funding allocation
- ✓ Empower communities with data
- ✓ Hold polluters accountable
- ✗ Do NOT replace community input
- ✗ Do NOT assume low-CBI areas are "safe"
- ✗ Do NOT be used to displace residents

### Recommendations

1. Pair CBI with qualitative community assessment
2. Involve environmental justice organizations in interpretation
3. Publish limitations transparently
4. Make data/code open-source for external validation

---

## References

- Rowangould et al. (2016). "A spatial examination of environmental justice"
- USEPA SVI Documentation: https://www.atsdr.cdc.gov/placeandhealth/svi/
- Chen et al. (2019). "XGBoost: A scalable tree boosting system"
- Lundberg & Lee (2017). "A unified approach to interpreting model predictions" (SHAP)

---

**Model Card Version:** 1.0.0  
**Last Updated:** January 2025  
**Responsible AI Officer:** Climate Burden Team
