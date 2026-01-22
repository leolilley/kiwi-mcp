# Phase 23: Enterprise Features & Multi-Tenancy

**Duration:** 4 weeks  
**Status:** Vision  
**Last Updated:** 2026-01-22  

---

## Overview

Phase 23 adds enterprise-grade capabilities to Mission Control, enabling organizations to deploy the platform across teams, enforce governance, manage SLAs, and provide fine-grained access control.

**Core Focus:**
- Multi-tenancy (isolated workspaces per organization)
- RBAC (Role-Based Access Control)
- SLA management & monitoring
- Cost allocation & chargeback
- Compliance & audit logging
- Team management & permissions

---

## Architecture: Enterprise-Ready

```
┌────────────────────────────────────────────────────────┐
│                  ENTERPRISE LAYER                      │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │  Multi-Tenancy Manager                          │ │
│  │  • Org isolation (DB schema per tenant)         │ │
│  │  • Workspace management                         │ │
│  │  • Resource quota enforcement                   │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │  RBAC & Access Control                          │ │
│  │  • Role definitions (Admin, Manager, User)      │ │
│  │  • Fine-grained permissions                     │ │
│  │  • Service account management                   │ │
│  │  • API key/token management                     │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │  SLA Management                                 │ │
│  │  • SLA definition & tracking                    │ │
│  │  • Alert thresholds                            │ │
│  │  • SLA breach notifications                    │ │
│  │  • Uptime reporting                            │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │  Compliance & Audit                             │ │
│  │  • Compliance frameworks (SOC2, HIPAA, etc)    │ │
│  │  • Audit log retention policies                 │ │
│  │  • Data residency controls                      │ │
│  │  • Export for compliance audits                 │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │  Cost Management                                │ │
│  │  • Usage tracking & metering                    │ │
│  │  • Quota enforcement                           │ │
│  │  • Cost allocation                             │ │
│  │  • Chargeback reporting                        │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
└────────────────────────────────────────────────────────┘
```

---

## Week 23.1: Multi-Tenancy & Workspace Management

### Database Schema for Multi-Tenancy

```sql
-- Organizations (top level)
CREATE TABLE organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_id TEXT,
    subscription_tier TEXT,  -- 'free', 'pro', 'enterprise'
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Workspaces (per org)
CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,
    org_id TEXT REFERENCES organizations(id),
    name TEXT NOT NULL,
    description TEXT,
    
    -- Resource limits
    max_threads INT,
    max_log_retention_days INT,
    max_users INT,
    
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Team members with roles
CREATE TABLE team_members (
    id TEXT PRIMARY KEY,
    org_id TEXT REFERENCES organizations(id),
    user_id TEXT,
    email TEXT,
    role TEXT,  -- 'admin', 'manager', 'developer', 'viewer'
    permissions JSONB,
    invited_at TIMESTAMP,
    joined_at TIMESTAMP
);

-- Service accounts for automation
CREATE TABLE service_accounts (
    id TEXT PRIMARY KEY,
    org_id TEXT,
    workspace_id TEXT,
    name TEXT,
    api_key_hash TEXT,
    permissions JSONB,
    rate_limit INT,
    created_at TIMESTAMP,
    expires_at TIMESTAMP
);
```

### Workspace Isolation Implementation

```python
# app/middleware/tenant_isolation.py

from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from app.models import Workspace, TeamMember

class TenantContext:
    """Current tenant context for request"""
    def __init__(self, org_id: str, workspace_id: str, user_id: str):
        self.org_id = org_id
        self.workspace_id = workspace_id
        self.user_id = user_id

async def get_tenant_context(request: Request, db: Session) -> TenantContext:
    """Extract tenant from request headers/JWT"""
    
    # Get from JWT token
    token = request.headers.get("Authorization")
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Decode JWT
    claims = decode_jwt(token)
    org_id = claims['org_id']
    workspace_id = claims.get('workspace_id', None)
    user_id = claims['sub']
    
    # Verify membership
    membership = db.query(TeamMember).filter(
        TeamMember.org_id == org_id,
        TeamMember.user_id == user_id,
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this org")
    
    return TenantContext(org_id, workspace_id, user_id)

# Usage in endpoints
@app.get("/api/threads")
async def list_threads(
    tenant: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    # All queries automatically filtered by tenant
    threads = db.query(Thread).filter(
        Thread.org_id == tenant.org_id,
        Thread.workspace_id == tenant.workspace_id,
    ).all()
    
    return threads
```

---

## Week 23.2: RBAC & Access Control

### Role Definitions

```python
# app/auth/roles.py

from enum import Enum
from typing import Set

class Role(str, Enum):
    ADMIN = "admin"           # Full access
    MANAGER = "manager"       # Can manage team, view all
    DEVELOPER = "developer"   # Can view own threads
    VIEWER = "viewer"         # Read-only access
    GUEST = "guest"           # Limited read access

# Permission matrix
ROLE_PERMISSIONS = {
    Role.ADMIN: {
        "threads:create",
        "threads:read",
        "threads:update",
        "threads:delete",
        "logs:read",
        "logs:delete",
        "users:manage",
        "org:manage",
        "billing:manage",
        "compliance:audit",
    },
    Role.MANAGER: {
        "threads:read",
        "logs:read",
        "users:invite",
        "users:remove",
        "settings:view",
    },
    Role.DEVELOPER: {
        "threads:create",
        "threads:read",
        "threads:update",
        "logs:read:own",
    },
    Role.VIEWER: {
        "threads:read",
        "logs:read",
    },
    Role.GUEST: {
        "threads:read:shared",
        "logs:read:shared",
    },
}

def has_permission(role: Role, permission: str) -> bool:
    """Check if role has permission"""
    if role == Role.ADMIN:
        return True  # Admins have all permissions
    
    # Check specific permission
    if permission in ROLE_PERMISSIONS.get(role, set()):
        return True
    
    # Check wildcard permissions (e.g., "threads:*" covers all threads)
    base_perm = permission.split(":")[0]
    wildcard = f"{base_perm}:*"
    return wildcard in ROLE_PERMISSIONS.get(role, set())
```

### Service Accounts & API Keys

```typescript
// src/components/settings/ServiceAccounts.tsx
'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Copy, Trash2 } from 'lucide-react'

export function ServiceAccounts() {
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    permissions: ['threads:read', 'logs:read'],
    rateLimit: 1000,  // requests per minute
  })
  
  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/service-accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })
      return res.json()
    },
  })
  
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-semibold">Service Accounts</h3>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-2 bg-blue-700 hover:bg-blue-600 rounded text-sm"
        >
          Create Account
        </button>
      </div>
      
      {showForm && (
        <div className="bg-slate-900 border border-slate-800 rounded p-4 space-y-3">
          <input
            type="text"
            placeholder="Account name"
            value={formData.name}
            onChange={(e) => setFormData(f => ({ ...f, name: e.target.value }))}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
          />
          
          <div>
            <label className="text-sm font-medium mb-2 block">Permissions</label>
            <div className="space-y-2">
              {['threads:read', 'logs:read', 'directives:read', 'scripts:execute'].map(perm => (
                <label key={perm} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={formData.permissions.includes(perm)}
                    onChange={(e) => {
                      const perms = formData.permissions
                      if (e.target.checked) {
                        perms.push(perm)
                      } else {
                        perms.splice(perms.indexOf(perm), 1)
                      }
                      setFormData(f => ({ ...f, permissions: [...perms] }))
                    }}
                  />
                  {perm}
                </label>
              ))}
            </div>
          </div>
          
          <div>
            <label className="text-sm font-medium">Rate Limit (req/min)</label>
            <input
              type="number"
              value={formData.rateLimit}
              onChange={(e) => setFormData(f => ({ ...f, rateLimit: parseInt(e.target.value) }))}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm mt-1"
            />
          </div>
          
          <button
            onClick={() => createMutation.mutate()}
            disabled={createMutation.isPending}
            className="w-full px-4 py-2 bg-blue-700 hover:bg-blue-600 rounded disabled:opacity-50"
          >
            {createMutation.isPending ? 'Creating...' : 'Create'}
          </button>
        </div>
      )}
      
      {/* List existing accounts */}
      <ServiceAccountsList />
    </div>
  )
}

function ServiceAccountsList() {
  // Display existing service accounts with ability to regenerate keys, revoke, etc
  return <div>Accounts list here</div>
}
```

---

## Week 23.3: SLA Management

### SLA Tracking & Monitoring

```python
# app/services/sla_manager.py

from datetime import datetime, timedelta
from typing import Optional

class SLAManager:
    """Manage SLAs and track compliance"""
    
    async def create_sla(
        self,
        org_id: str,
        name: str,
        target_availability: float = 0.99,  # 99%
        max_response_time_ms: int = 1000,
        max_error_rate: float = 0.01,  # 1%
    ):
        """Create new SLA target"""
        
        sla = SLA(
            id=uuid.uuid4(),
            org_id=org_id,
            name=name,
            target_availability=target_availability,
            max_response_time_ms=max_response_time_ms,
            max_error_rate=max_error_rate,
            created_at=datetime.now(),
        )
        
        db.add(sla)
        db.commit()
        return sla
    
    async def check_sla_compliance(self, org_id: str) -> dict:
        """Check if org is meeting SLA targets"""
        
        slas = db.query(SLA).filter(SLA.org_id == org_id).all()
        
        compliance = {}
        
        for sla in slas:
            # Get metrics for last 24 hours
            metrics = await self._get_metrics(org_id, hours=24)
            
            # Calculate compliance
            availability = metrics['uptime_percent']
            avg_response_time = metrics['avg_response_time_ms']
            error_rate = metrics['error_rate']
            
            breaches = []
            
            if availability < sla.target_availability:
                breaches.append({
                    'metric': 'availability',
                    'target': sla.target_availability,
                    'actual': availability,
                    'breach_percent': (sla.target_availability - availability) * 100,
                })
            
            if avg_response_time > sla.max_response_time_ms:
                breaches.append({
                    'metric': 'response_time',
                    'target': sla.max_response_time_ms,
                    'actual': avg_response_time,
                })
            
            if error_rate > sla.max_error_rate:
                breaches.append({
                    'metric': 'error_rate',
                    'target': sla.max_error_rate,
                    'actual': error_rate,
                })
            
            compliance[sla.name] = {
                'is_compliant': len(breaches) == 0,
                'breaches': breaches,
                'metrics': {
                    'availability': availability,
                    'response_time': avg_response_time,
                    'error_rate': error_rate,
                },
            }
            
            # Alert if breaching
            if breaches:
                await self._send_sla_breach_alert(org_id, sla.name, breaches)
        
        return compliance
    
    async def generate_sla_report(self, org_id: str, month: int, year: int) -> dict:
        """Generate monthly SLA compliance report"""
        
        start = datetime(year, month, 1)
        end = start + timedelta(days=32)
        end = end.replace(day=1) - timedelta(days=1)
        
        # Get all metrics for the month
        metrics = await self._get_metrics_for_period(org_id, start, end)
        
        return {
            'period': f'{month}/{year}',
            'availability': metrics['availability'],
            'uptime_minutes': metrics['uptime_minutes'],
            'downtime_minutes': metrics['downtime_minutes'],
            'avg_response_time': metrics['avg_response_time'],
            'p99_response_time': metrics['p99_response_time'],
            'error_rate': metrics['error_rate'],
            'total_requests': metrics['total_requests'],
        }
```

### SLA Dashboard

```typescript
// src/components/enterprise/SLADashboard.tsx
'use client'

import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle } from 'lucide-react'

export function SLADashboard() {
  const { data: compliance } = useQuery({
    queryKey: ['sla-compliance'],
    queryFn: () => fetch('/api/sla/compliance').then(r => r.json()),
    refetchInterval: 3600000,  // Hourly
  })
  
  if (!compliance) return <div>Loading SLA status...</div>
  
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">SLA Compliance</h2>
      
      {Object.entries(compliance).map(([slaName, status]: [string, any]) => (
        <div
          key={slaName}
          className={`border rounded p-4 ${
            status.is_compliant
              ? 'bg-green-900/20 border-green-700'
              : 'bg-red-900/20 border-red-700'
          }`}
        >
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2">
              {status.is_compliant ? (
                <CheckCircle size={20} className="text-green-400" />
              ) : (
                <AlertTriangle size={20} className="text-red-400" />
              )}
              <h3 className="font-semibold">{slaName}</h3>
            </div>
            <span className={status.is_compliant ? 'text-green-400' : 'text-red-400'}>
              {status.is_compliant ? 'COMPLIANT' : 'BREACHED'}
            </span>
          </div>
          
          {/* Metrics */}
          <div className="grid grid-cols-3 gap-4 text-sm mb-3">
            <div>
              <div className="text-slate-400">Availability</div>
              <div className="font-mono text-lg">
                {(status.metrics.availability * 100).toFixed(2)}%
              </div>
            </div>
            <div>
              <div className="text-slate-400">Response Time</div>
              <div className="font-mono text-lg">
                {status.metrics.response_time.toFixed(0)}ms
              </div>
            </div>
            <div>
              <div className="text-slate-400">Error Rate</div>
              <div className="font-mono text-lg">
                {(status.metrics.error_rate * 100).toFixed(3)}%
              </div>
            </div>
          </div>
          
          {/* Breaches */}
          {status.breaches.length > 0 && (
            <div className="space-y-2 text-sm">
              {status.breaches.map((breach: any, idx: number) => (
                <div key={idx} className="bg-slate-950 rounded p-2 text-slate-300">
                  {breach.metric}: target {breach.target}, actual {breach.actual.toFixed(2)}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
      
      {/* Download report */}
      <button className="px-4 py-2 bg-blue-700 hover:bg-blue-600 rounded text-sm">
        Download Monthly Report
      </button>
    </div>
  )
}
```

---

## Week 23.4: Compliance & Cost Management

### Compliance Framework

```python
# app/services/compliance.py

from enum import Enum

class ComplianceFramework(str, Enum):
    SOC2 = "soc2"
    HIPAA = "hipaa"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    CCPA = "ccpa"

class ComplianceManager:
    """Manage compliance requirements"""
    
    async def enable_compliance_mode(
        self,
        org_id: str,
        framework: ComplianceFramework,
    ):
        """Enable compliance mode for org"""
        
        config = ComplianceConfig(
            org_id=org_id,
            framework=framework,
            audit_logging_enabled=True,
            encryption_at_rest=True,
            encryption_in_transit=True,
            mfa_required=True,
            data_residency=self._get_framework_residency(framework),
            audit_log_retention_days=self._get_framework_retention(framework),
        )
        
        # Enforce settings
        await self._enforce_compliance_settings(org_id, config)
        
        return config
    
    def _get_framework_residency(self, framework: ComplianceFramework) -> str:
        """Get required data residency for framework"""
        residency_map = {
            ComplianceFramework.GDPR: "eu-only",
            ComplianceFramework.CCPA: "us-only",
            ComplianceFramework.HIPAA: "us",
            ComplianceFramework.SOC2: "any",
        }
        return residency_map.get(framework, "any")
    
    def _get_framework_retention(self, framework: ComplianceFramework) -> int:
        """Get required audit log retention days"""
        retention_map = {
            ComplianceFramework.SOC2: 365,
            ComplianceFramework.HIPAA: 1825,  # 5 years
            ComplianceFramework.GDPR: 2555,   # 7 years
            ComplianceFramework.CCPA: 730,    # 2 years
        }
        return retention_map.get(framework, 365)
    
    async def generate_compliance_report(
        self,
        org_id: str,
        framework: ComplianceFramework,
    ) -> dict:
        """Generate compliance audit report"""
        
        # Check all controls
        controls_status = {}
        
        controls = self._get_framework_controls(framework)
        for control in controls:
            status = await self._check_control(org_id, control)
            controls_status[control] = status
        
        passing = sum(1 for s in controls_status.values() if s['compliant'])
        total = len(controls_status)
        
        return {
            'framework': framework,
            'compliance_percentage': (passing / total) * 100,
            'controls': controls_status,
            'generated_at': datetime.now(),
        }
```

### Cost Management

```python
# app/services/cost_manager.py

class CostManager:
    """Track usage and enforce quotas"""
    
    async def track_usage(self, org_id: str, metric_type: str, amount: int = 1):
        """Track org usage"""
        
        # Record usage
        usage = Usage(
            org_id=org_id,
            metric_type=metric_type,  # 'api_calls', 'storage_gb', 'threads', etc
            amount=amount,
            recorded_at=datetime.now(),
        )
        
        db.add(usage)
        
        # Check quota
        quota = await self._get_quota(org_id, metric_type)
        current_usage = await self._get_current_usage(org_id, metric_type)
        
        if current_usage + amount > quota:
            raise QuotaExceeded(
                f"Quota exceeded for {metric_type}: {current_usage}/{quota}"
            )
        
        db.commit()
    
    async def get_usage_report(self, org_id: str, period: str = 'month') -> dict:
        """Get detailed usage and cost report"""
        
        usage_by_type = await self._aggregate_usage(org_id, period)
        
        costs = {}
        total_cost = 0
        
        for metric_type, amount in usage_by_type.items():
            unit_cost = self._get_unit_cost(metric_type)
            cost = amount * unit_cost
            costs[metric_type] = {
                'amount': amount,
                'unit_cost': unit_cost,
                'total_cost': cost,
            }
            total_cost += cost
        
        return {
            'period': period,
            'costs': costs,
            'total_cost': total_cost,
            'forecast_monthly': total_cost if period == 'month' else total_cost * 30,
        }
```

---

## Deliverables

By end of Phase 23:

- [ ] Multi-tenancy fully implemented
- [ ] RBAC with all role types working
- [ ] Service accounts & API keys functional
- [ ] SLA management operational
- [ ] Compliance framework selectable (SOC2, HIPAA, GDPR, etc)
- [ ] Cost tracking & quota enforcement
- [ ] Enterprise dashboards
- [ ] Audit logging for all operations
- [ ] Documentation for enterprise deployment

---

## Success Metrics

- [ ] >99.9% SLA uptime maintained
- [ ] 100% audit logging coverage
- [ ] Support for 10+ orgs in single instance
- [ ] <10ms tenant isolation overhead
- [ ] Compliance checks automated
- [ ] Cost reporting accurate & timely

---

## Next Phase (Phase 24)

Phase 24 adds integration ecosystem with third-party tools.
