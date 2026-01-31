# API Documentation

## Base URL

```
http://localhost:8000
```

## Authentication

Currently unauthenticated. Future versions will support JWT.

## Endpoints

### 1. Score Endpoint

**GET /score**

Get Climate Burden Index score for a geographic location.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| lat | float | Yes | Latitude (-90 to 90) |
| lon | float | Yes | Longitude (-180 to 180) |
| explain | bool | No | Include SHAP explanation (default: false) |

#### Example Request

```bash
curl "http://localhost:8000/score?lat=40.7128&lon=-74.0060&explain=true"
```

#### Success Response (200 OK)

```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "geoid": "36061000100",
  "climate_burden_index": 62.5,
  "percentile": 75.3,
  "climate_burden_score": 0.65,
  "vulnerability_score": 0.96,
  "cluster_kmeans": 2,
  "cluster_hdbscan": 1,
  "shap_explanation": {
    "top_factors": [
      {
        "feature": "heat_annual_mean",
        "contribution": 0.25
      },
      {
        "feature": "pm25_mean",
        "contribution": 0.20
      },
      {
        "feature": "svi_composite",
        "contribution": 0.15
      }
    ]
  }
}
```

#### Error Responses

**404 Not Found**
```json
{
  "detail": "Location not in service area"
}
```

**400 Bad Request**
```json
{
  "detail": "Invalid latitude or longitude"
}
```

---

### 2. Clusters Endpoint

**GET /clusters**

Get cluster assignments and statistics.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| method | str | No | "kmeans" or "hdbscan" (default: "kmeans") |

#### Example Request

```bash
curl "http://localhost:8000/clusters?method=kmeans"
```

#### Success Response (200 OK)

```json
{
  "method": "kmeans",
  "n_clusters": 5,
  "summaries": [
    {
      "cluster_id": 0,
      "method": "kmeans",
      "size": 15234,
      "avg_climate_burden_index": 45.2,
      "avg_vulnerability_score": 0.42,
      "geographic_distribution": null
    },
    {
      "cluster_id": 1,
      "method": "kmeans",
      "size": 12456,
      "avg_climate_burden_index": 62.8,
      "avg_vulnerability_score": 0.68,
      "geographic_distribution": null
    }
  ]
}
```

#### Cluster Interpretation

| Cluster | Size | Avg CBI | Avg Vulnerability | Meaning |
|---------|------|---------|-------------------|---------|
| 0 | 15K | 45 | 0.42 | Low burden, low vulnerability |
| 1 | 12K | 63 | 0.68 | High burden, high vulnerability |
| 2 | 10K | 55 | 0.55 | Moderate burden/vulnerability |
| 3 | 8K | 75 | 0.85 | Extreme burden & vulnerability |
| 4 | 5K | 35 | 0.35 | Rural, low burden |

---

### 3. NLP Insights Endpoint

**GET /nlp-insights**

Get LLM-generated insights for a census tract.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| geoid | str | Yes | 11-digit census tract GEOID |

#### Example Request

```bash
curl "http://localhost:8000/nlp-insights?geoid=36061000100"
```

#### Success Response (200 OK)

```json
{
  "geoid": "36061000100",
  "summary": "Census tract 36061000100 experiences moderate climate burden with high vulnerability. Heat exposure and air quality concerns combine with socioeconomic vulnerability to create significant environmental inequity.",
  "risk_factors": [
    "Elevated particulate matter (PM2.5) exposure",
    "Heat exposure above median",
    "High social vulnerability index",
    "Limited adaptive capacity"
  ],
  "recommendations": [
    "Prioritize cooling centers and emergency response",
    "Improve air quality monitoring and alerts",
    "Invest in community resilience programs",
    "Support green infrastructure and tree planting"
  ]
}
```

#### Error Responses

**400 Bad Request**
```json
{
  "detail": "GEOID must be 11-digit string"
}
```

**404 Not Found**
```json
{
  "detail": "GEOID not found in service area"
}
```

---

## Response Schema

### ScoreResponse

```typescript
interface ScoreResponse {
  latitude: number;           // Input latitude
  longitude: number;          // Input longitude
  geoid: string;              // 11-digit census tract ID
  climate_burden_index: number; // 0-100 scale
  percentile: number;         // 0-100, relative rank
  climate_burden_score: number; // 0-1, climate hazard
  vulnerability_score: number; // 0-1, socioeconomic
  cluster_kmeans?: number;    // Cluster ID (0-4) or null
  cluster_hdbscan?: number;   // Cluster ID or -1 for noise
  shap_explanation?: {
    top_factors: {
      feature: string;
      contribution: number;   // 0-1, relative importance
    }[];
  };
}
```

### ClustersResponse

```typescript
interface ClustersResponse {
  method: "kmeans" | "hdbscan";
  n_clusters: number;
  summaries: ClusterSummary[];
}

interface ClusterSummary {
  cluster_id: number;
  method: "kmeans" | "hdbscan";
  size: number;               // Number of tracts
  avg_climate_burden_index: number;
  avg_vulnerability_score: number;
  geographic_distribution?: object;
}
```

### InsightResponse

```typescript
interface InsightResponse {
  geoid: string;
  summary: string;            // Human-readable summary
  risk_factors: string[];     // Key concerns
  recommendations: string[];  // Action items
}
```

---

## Rate Limiting

Currently disabled. Will be implemented with:
- 100 requests/minute per IP
- 1000 requests/hour per API key

---

## Caching

- `/clusters` responses cached for 30 minutes
- `/score` responses not cached (always fresh)
- Cache-Control headers included in responses

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid params) |
| 404 | Resource not found |
| 500 | Internal server error |

### Error Response Format

```json
{
  "detail": "Error message describing the issue"
}
```

---

## Example Workflows

### Workflow 1: Get Score for User Location

```python
import requests

response = requests.get(
    "http://localhost:8000/score",
    params={
        "lat": 40.7128,
        "lon": -74.0060,
        "explain": True
    }
)

result = response.json()
print(f"CBI: {result['climate_burden_index']}")
print(f"Percentile: {result['percentile']}")
print(f"Risk factors: {result['shap_explanation']['top_factors']}")
```

### Workflow 2: Compare Clusters

```python
# Get K-Means clusters
kmeans = requests.get("http://localhost:8000/clusters?method=kmeans").json()

# Get HDBSCAN clusters
hdbscan = requests.get("http://localhost:8000/clusters?method=hdbscan").json()

# Compare sizes
for km_cluster in kmeans["summaries"]:
    print(f"K-Means Cluster {km_cluster['cluster_id']}: {km_cluster['size']} tracts")

for hdb_cluster in hdbscan["summaries"]:
    print(f"HDBSCAN Cluster {hdb_cluster['cluster_id']}: {hdb_cluster['size']} tracts")
```

### Workflow 3: Get Insights for All Tracts in a State

```python
# This would require a /search or /list endpoint (future)
geoids = [...]  # List of GEOIDs for a state

for geoid in geoids:
    insights = requests.get(
        "http://localhost:8000/nlp-insights",
        params={"geoid": geoid}
    ).json()
    
    print(f"{geoid}: {insights['summary']}")
```

---

## OpenAPI/Swagger Docs

Interactive API documentation available at:
```
http://localhost:8000/docs
```

Alternative (ReDoc):
```
http://localhost:8000/redoc
```

---

## WebSocket (Future)

Planned for real-time updates:
```
ws://localhost:8000/ws/live-updates
```

---

## Versioning

API version: `v1`

Future versions will support:
```
/v2/score
/v2/clusters
```

---

**Last Updated:** January 2025  
**Stability:** Production Ready
