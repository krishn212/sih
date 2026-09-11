import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'

const STATUS_COLORS = {
  PASS:          { color: 'var(--pass)',   bg: 'var(--pass-dim)',   icon: '✅' },
  FAIL:          { color: 'var(--fail)',   bg: 'var(--fail-dim)',   icon: '❌' },
  MANUAL_REVIEW: { color: 'var(--review)', bg: 'var(--review-dim)', icon: '⚠️' },
}

function StatusBadge({ status }) {
  const cfg = STATUS_COLORS[status] || STATUS_COLORS.MANUAL_REVIEW
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '3px 10px', borderRadius: 99, fontSize: 11,
      fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em',
      background: cfg.bg, color: cfg.color,
    }}>
      {cfg.icon} {status?.replace('_', ' ')}
    </span>
  )
}

export default function HistoryPage() {
  const navigate = useNavigate()
  const [scans, setScans]           = useState([])
  const [loading, setLoading]       = useState(true)
  const [filter, setFilter]         = useState('')
  const [search, setSearch]         = useState('')

  useEffect(() => {
    const params = filter ? `?status_filter=${filter}` : ''
    client.get(`/scans${params}`)
      .then(r => setScans(r.data.scans || []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filter])

  const role = localStorage.getItem('role')

  const filtered = scans.filter(s =>
    !search || s.brand_name?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="page">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1>Scan History</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 13 }}>
            {role === 'ADMIN' ? 'All scans across all inspectors' : 'Your inspection scans'}
          </p>
        </div>
        <button onClick={() => navigate('/scan')} className="btn btn-primary">
          + New Scan
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <input
          placeholder="🔍 Search by brand name…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ flex: 1, minWidth: 200 }}
        />
        <select value={filter} onChange={e => setFilter(e.target.value)} style={{ width: 180 }}>
          <option value="">All Statuses</option>
          <option value="PASS">✅ PASS</option>
          <option value="FAIL">❌ FAIL</option>
          <option value="MANUAL_REVIEW">⚠️ Manual Review</option>
        </select>
      </div>

      {/* Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {loading ? (
          <div style={{ padding: 60, textAlign: 'center' }}>
            <span className="spinner" style={{ width: 32, height: 32 }} />
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>📋</div>
            <p>{scans.length === 0 ? 'No scans yet. Start by scanning a product.' : 'No scans match your filter.'}</p>
            {scans.length === 0 && (
              <button onClick={() => navigate('/scan')} className="btn btn-primary" style={{ marginTop: 16 }}>
                Scan a Product
              </button>
            )}
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Brand / Product</th>
                  <th>Violations</th>
                  <th>Calibration</th>
                  <th>Scanned At</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(scan => (
                  <tr key={scan.id} onClick={() => navigate(`/evidence/${scan.id}`)} style={{ cursor: 'pointer' }}>
                    <td><StatusBadge status={scan.overall_status} /></td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{scan.brand_name || '—'}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                        #{scan.id.slice(-8)}
                      </div>
                    </td>
                    <td>
                      <span style={{
                        fontWeight: 700, fontSize: 14,
                        color: scan.violation_count > 0 ? 'var(--fail)' : 'var(--pass)',
                      }}>
                        {scan.violation_count}
                      </span>
                      <span style={{ color: 'var(--text-muted)', fontSize: 12 }}> fail{scan.violation_count !== 1 ? 's' : ''}</span>
                    </td>
                    <td>
                      <span style={{
                        fontSize: 12, padding: '3px 8px', borderRadius: 4,
                        background: 'var(--bg-elevated)',
                        color: scan.calibration_used === 'ARUCO' ? 'var(--accent)'
                            : scan.calibration_used === 'COIN' ? 'var(--review)'
                            : 'var(--text-muted)',
                      }}>
                        {scan.calibration_used}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
                      {new Date(scan.scanned_at).toLocaleString('en-IN', {
                        day: '2-digit', month: 'short', year: 'numeric',
                        hour: '2-digit', minute: '2-digit',
                      })}
                    </td>
                    <td>
                      <button className="btn btn-ghost" style={{ padding: '5px 10px', fontSize: 12 }}
                        onClick={e => { e.stopPropagation(); navigate(`/evidence/${scan.id}`) }}>
                        View →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {!loading && filtered.length > 0 && (
        <p style={{ textAlign: 'right', fontSize: 12, color: 'var(--text-muted)', marginTop: 12 }}>
          Showing {filtered.length} scan{filtered.length !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  )
}
