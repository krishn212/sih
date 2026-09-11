import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend,
} from 'recharts'
import client from '../api/client'

const FIELD_LABELS = {
  mrp: 'MRP', net_quantity: 'Net Quantity', manufacturer: 'Manufacturer',
  mfg_date: 'Mfg. Date', consumer_care: 'Consumer Care',
  country_of_origin: 'Country of Origin', font_size: 'Font Size',
}

function StatCard({ label, value, color, icon }) {
  return (
    <div className="stat-card">
      <div style={{ fontSize: 24, marginBottom: 4 }}>{icon}</div>
      <div className="stat-value" style={{ color }}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload?.length) return (
    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', fontSize: 13 }}>
      <p style={{ color: 'var(--text-muted)', marginBottom: 4 }}>{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color, fontWeight: 700 }}>{p.name}: {p.value}</p>
      ))}
    </div>
  )
  return null
}

export default function DashboardPage() {
  const navigate  = useNavigate()
  const [stats, setStats]   = useState(null)
  const [rules, setRules]   = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab]       = useState('overview') // 'overview' | 'rules'

  useEffect(() => {
    Promise.all([
      client.get('/dashboard/stats'),
      client.get('/dashboard/rules'),
    ])
      .then(([s, r]) => { setStats(s.data); setRules(r.data.rules || []) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="page" style={{ textAlign: 'center', paddingTop: 80 }}>
      <span className="spinner" style={{ width: 40, height: 40 }} />
      <p style={{ marginTop: 16, color: 'var(--text-muted)' }}>Loading dashboard…</p>
    </div>
  )

  const pieData = stats ? [
    { name: 'PASS',          value: stats.pass_count,          color: 'var(--pass)' },
    { name: 'FAIL',          value: stats.fail_count,          color: 'var(--fail)' },
    { name: 'Manual Review', value: stats.manual_review_count, color: 'var(--review)' },
  ].filter(d => d.value > 0) : []

  return (
    <div className="page">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1>Admin Dashboard</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 13 }}>
            System-wide compliance analytics · Legal Metrology (PC) Rules 2011
          </p>
        </div>
        <button onClick={() => navigate('/scan')} className="btn btn-primary">+ New Scan</button>
      </div>

      {/* Tab switcher */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 24, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, padding: 4, width: 'fit-content' }}>
        {[['overview', '📊 Overview'], ['rules', '⚖️ Rules Manager']].map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)} style={{
            padding: '8px 18px', borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer',
            background: tab === key ? 'var(--accent)' : 'transparent',
            color: tab === key ? '#fff' : 'var(--text-muted)',
            transition: 'all 0.15s',
          }}>{label}</button>
        ))}
      </div>

      {/* ── Overview Tab ───────────────────────────────────────── */}
      {tab === 'overview' && stats && (
        <>
          {/* Stat cards */}
          <div className="grid-4" style={{ marginBottom: 24 }}>
            <StatCard label="Total Scans"   value={stats.total_scans}          color="var(--text-primary)" icon="🔍" />
            <StatCard label="PASS Rate"     value={`${stats.pass_rate}%`}       color="var(--pass)"         icon="✅" />
            <StatCard label="FAIL"          value={stats.fail_count}            color="var(--fail)"         icon="❌" />
            <StatCard label="Manual Review" value={stats.manual_review_count}   color="var(--review)"       icon="⚠️" />
          </div>

          <div className="grid-2" style={{ gap: 20, marginBottom: 24 }}>
            {/* Scans over time */}
            <div className="card">
              <h4 style={{ marginBottom: 20 }}>Scans Over Last 14 Days</h4>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={stats.scans_over_time}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} allowDecimals={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Line type="monotone" dataKey="scans" stroke="var(--accent)" strokeWidth={2} dot={{ fill: 'var(--accent)', r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Result distribution */}
            <div className="card">
              <h4 style={{ marginBottom: 20 }}>Result Distribution</h4>
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={75} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`} labelLine={false}>
                      {pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                  No scan data yet
                </div>
              )}
            </div>
          </div>

          {/* Top violated fields */}
          <div className="card" style={{ marginBottom: 24 }}>
            <h4 style={{ marginBottom: 20 }}>Most Frequently Violated Fields</h4>
            {stats.top_violated_fields?.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={stats.top_violated_fields.map(f => ({ ...f, label: FIELD_LABELS[f.field] || f.field }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="label" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 12 }} allowDecimals={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="count" name="Violations" radius={[4, 4, 0, 0]}>
                    {stats.top_violated_fields.map((_, i) => (
                      <Cell key={i} fill={i === 0 ? 'var(--fail)' : i === 1 ? '#f97316' : 'var(--accent)'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 40 }}>No violation data yet</p>
            )}
          </div>

          {/* Calibration breakdown */}
          <div className="card">
            <h4 style={{ marginBottom: 16 }}>Calibration Method Breakdown</h4>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              {Object.entries(stats.calibration_breakdown || {}).map(([tier, count]) => (
                <div key={tier} style={{
                  flex: 1, minWidth: 100, padding: '16px 12px', textAlign: 'center',
                  background: 'var(--bg-elevated)', borderRadius: 8, border: '1px solid var(--border)',
                }}>
                  <div style={{ fontSize: 24, fontWeight: 800, color: tier === 'ARUCO' ? 'var(--accent)' : tier === 'COIN' ? 'var(--review)' : 'var(--text-primary)' }}>{count}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', marginTop: 4 }}>{tier}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* ── Rules Manager Tab ──────────────────────────────────── */}
      {tab === 'rules' && (
        <div>
          {rules.length === 0 ? (
            <div className="card" style={{ textAlign: 'center', padding: 32, color: 'var(--text-muted)' }}>
              <p>No rules currently loaded from database.</p>
              <button
                className="btn btn-ghost"
                style={{ marginTop: 12, fontSize: 13 }}
                onClick={() => client.get('/dashboard/rules').then(r => setRules(r.data.rules || []))}
              >
                🔄 Refresh Rules
              </button>
            </div>
          ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {rules.map(rule => (
              <div key={rule.id} className="card card-sm" style={{
                borderLeft: `3px solid ${rule.verified ? 'var(--pass)' : 'var(--review)'}`,
              }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                      <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--accent)', background: 'var(--accent-dim)', padding: '2px 8px', borderRadius: 4 }}>{rule.rule_code}</span>
                      <span style={{
                        fontSize: 11, padding: '2px 8px', borderRadius: 99, fontWeight: 700,
                        background: rule.verified ? 'var(--pass-dim)' : 'var(--review-dim)',
                        color: rule.verified ? 'var(--pass)' : 'var(--review)',
                      }}>
                        {rule.verified ? '✅ VERIFIED' : '⚠️ UNVERIFIED'}
                      </span>
                      {rule.severity && (
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
                          {rule.severity}
                        </span>
                      )}
                    </div>
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{rule.source_clause}</div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>Condition: <code style={{ color: 'var(--text-primary)' }}>{rule.condition}</code></div>
                    {rule.threshold && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Threshold: {rule.threshold}</div>}
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6 }}>
                      Effective: {rule.effective_from} {rule.effective_until ? `→ ${rule.effective_until}` : '(current)'}
                    </div>
                  </div>
                  {!rule.verified && (
                    <button
                      className="btn btn-ghost"
                      style={{ fontSize: 12, padding: '5px 10px', flexShrink: 0, color: 'var(--pass)', borderColor: 'var(--pass)' }}
                      onClick={async () => {
                        await client.patch(`/dashboard/rules/${rule.id}`, { verified: true })
                        setRules(rs => rs.map(r => r.id === rule.id ? { ...r, verified: true } : r))
                      }}
                    >
                      Mark Verified
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
          )}
        </div>
      )}
    </div>
  )
}
