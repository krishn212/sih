import { useEffect, useState } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import client, { API_BASE } from '../api/client'

const STATUS_CONFIG = {
  PASS:          { color: 'var(--pass)',   bg: 'var(--pass-dim)',   icon: '✅', label: 'PASS' },
  FAIL:          { color: 'var(--fail)',   bg: 'var(--fail-dim)',   icon: '❌', label: 'FAIL' },
  MANUAL_REVIEW: { color: 'var(--review)', bg: 'var(--review-dim)', icon: '⚠️', label: 'MANUAL REVIEW' },
}

function StatusBadge({ status, large }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.MANUAL_REVIEW
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: large ? '8px 20px' : '4px 12px',
      borderRadius: 99,
      fontSize: large ? 15 : 12,
      fontWeight: 700,
      letterSpacing: '0.05em',
      textTransform: 'uppercase',
      background: cfg.bg,
      color: cfg.color,
      border: `1px solid ${cfg.color}33`,
    }}>
      {cfg.icon} {cfg.label}
    </span>
  )
}

function EvidenceStep({ step, index, total }) {
  const isLast = index === total - 1
  const statusCfg = step.data?.status ? STATUS_CONFIG[step.data.status] : null

  return (
    <div style={{
      display: 'flex', gap: 16,
      animation: `stepIn 0.35s ease ${index * 0.08}s both`,
    }}>
      {/* Timeline connector */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
        <div style={{
          width: 36, height: 36, borderRadius: '50%',
          background: statusCfg?.bg || 'var(--accent-dim)',
          border: `2px solid ${statusCfg?.color || 'var(--accent)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16, flexShrink: 0, zIndex: 1,
        }}>
          {step.label.split(' ')[0]}
        </div>
        {!isLast && (
          <div style={{ width: 2, flex: 1, background: 'var(--border)', minHeight: 24, margin: '4px 0' }} />
        )}
      </div>

      {/* Content */}
      <div style={{ paddingBottom: isLast ? 0 : 24, flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 10, color: 'var(--text-primary)' }}>
          {step.label.substring(step.label.indexOf(' ') + 1)}
        </div>

        <div style={{
          background: 'var(--bg-elevated)',
          border: `1px solid ${statusCfg?.color ? statusCfg.color + '33' : 'var(--border)'}`,
          borderRadius: 10, padding: 16,
        }}>
          <StepContent step={step} />
        </div>
      </div>
    </div>
  )
}

function StepContent({ step }) {
  const d = step.data

  const toUrl = (path) => {
    if (!path) return null
    const norm = String(path).replace(/\\/g, '/')
    const withSlash = norm.startsWith('/') ? norm : `/${norm}`
    return `${API_BASE}${withSlash}`
  }

  // Step 1: Original image
  if (d.image_url) return (
    <div>
      <img src={toUrl(d.image_url)} alt="Original label scan"
        style={{ maxHeight: 200, borderRadius: 6, border: '1px solid var(--border)' }} />
      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>Scan ID: {d.scan_id}</p>
    </div>
  )

  // Step 2: Region crop
  if ('bounding_box' in d || 'crop_url' in d) return (
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-start' }}>
      {d.crop_url && (
        <img src={toUrl(d.crop_url)} alt="Evidence region"
          style={{ maxHeight: 110, maxWidth: 320, objectFit: 'contain', borderRadius: 6, border: '1px solid var(--border)', background: '#fff' }} />
      )}
      <div>
        {d.field_name && <div><span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Field: </span><strong>{d.field_name.replace(/_/g, ' ').toUpperCase()}</strong></div>}
        {d.source     && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Detection method: {d.source}</div>}
        {d.bounding_box && (
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, fontFamily: 'monospace' }}>
            x:{d.bounding_box.x} y:{d.bounding_box.y} w:{d.bounding_box.width} h:{d.bounding_box.height}
          </div>
        )}
        {!d.bounding_box && d.note && <div className="alert alert-warning" style={{ marginTop: 8 }}>{d.note}</div>}
      </div>
    </div>
  )

  // Step 3: OCR text
  if ('ocr_engine' in d || 'extracted_text' in d || 'text' in d) {
    const textToShow = d.text || d.extracted_text || d.detected || d.detected_value
    return (
      <div>
        <div style={{
          background: 'var(--bg-base)', borderRadius: 6, padding: 12,
          fontFamily: 'monospace', fontSize: 14, color: 'var(--text-primary)',
          border: '1px solid var(--border)', wordBreak: 'break-all',
        }}>
          {textToShow || <em style={{ color: 'var(--text-muted)' }}>— not detected —</em>}
        </div>
        <div style={{ display: 'flex', gap: 16, marginTop: 10 }}>
          <div><span style={{ color: 'var(--text-muted)', fontSize: 12 }}>Confidence: </span>
            <strong style={{ color: (d.confidence || 0.95) > 0.8 ? 'var(--pass)' : (d.confidence || 0.95) > 0.5 ? 'var(--review)' : 'var(--fail)' }}>
              {typeof d.confidence === 'number' ? (d.confidence * 100).toFixed(0) : '95'}%
            </strong>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{d.ocr_engine}</div>
        </div>
      </div>
    )
  }

  // Step 4: Measurement / Calibration
  if ('calibration_tier' in d || 'tier' in d) return (
    <div className="grid-2" style={{ gap: 10 }}>
      {[
        ['Calibration tier', d.calibration_tier || d.tier],
        ['Confidence', d.calibration_confidence || d.confidence],
        ['Scale (px/mm)', d.px_per_mm ?? 'N/A'],
        ['Tilt corrected', d.tilt_corrected ? 'Yes ✓' : 'No'],
        ...(d.measured_height_mm !== undefined ? [['Measured height', `${d.measured_height_mm?.toFixed(2) ?? '—'} mm`]] : []),
        ...(d.symbols_measured !== undefined ? [['Symbols measured', d.symbols_measured]] : []),
      ].map(([k, v]) => (
        <div key={k} style={{ fontSize: 13 }}>
          <span style={{ color: 'var(--text-muted)' }}>{k}: </span>
          <strong>{String(v)}</strong>
        </div>
      ))}
    </div>
  )

  // Step 5: Rule
  if ('source_clause' in d) return (
    <div>
      <div style={{
        borderLeft: '3px solid var(--accent)', paddingLeft: 12, marginBottom: 10,
        fontStyle: 'italic', color: 'var(--text-secondary)', fontSize: 13,
      }}>
        {d.source_clause}
      </div>
      {d.expected && <div style={{ fontSize: 13 }}><span style={{ color: 'var(--text-muted)' }}>Expected: </span>{d.expected}</div>}
      {!d.verified && (
        <div className="alert alert-warning" style={{ marginTop: 10, fontSize: 12 }}>
          ⚠️ Rule not yet verified against actual Legal Metrology Rules 2011 text
        </div>
      )}
    </div>
  )

  // Step 6: Decision
  if ('status' in d) return (
    <div>
      <StatusBadge status={d.status} large />
      {d.reason && <p style={{ marginTop: 12, fontSize: 14 }}>{d.reason}</p>}
      {d.detected && <div style={{ marginTop: 8, fontSize: 13 }}><span style={{ color: 'var(--text-muted)' }}>Detected: </span><code style={{ color: 'var(--text-primary)' }}>{d.detected}</code></div>}
    </div>
  )

  // Fallback
  return <pre style={{ fontSize: 11, color: 'var(--text-muted)', overflow: 'auto' }}>{JSON.stringify(d, null, 2)}</pre>
}

export default function EvidencePage() {
  const { scanId }  = useParams()
  const location    = useLocation()
  const navigate    = useNavigate()
  const [scanData, setScanData] = useState(location.state?.scanData || null)
  const [selected, setSelected] = useState(0)
  const [loading, setLoading]   = useState(!scanData)
  const [error, setError]       = useState('')
  const [downloading, setDownloading] = useState(false)
  const [viewMode, setViewMode]       = useState('chain') // 'chain' | 'all_text'

  useEffect(() => {
    if (!scanData && scanId) {
      client.get(`/scan/${scanId}`)
        .then(r => setScanData(r.data))
        .catch(err => {
          console.error('Error fetching scan data:', err)
          setError(err.response?.data?.detail || 'Could not load scan data.')
        })
        .finally(() => setLoading(false))
    }
  }, [scanId, scanData])

  const handleDownloadPdf = async () => {
    try {
      setDownloading(true)
      const res = await client.get(`/report/${scanId}/pdf`, { responseType: 'blob' })
      const blob = new Blob([res.data], { type: 'application/pdf' })
      const blobUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = `Form_A_Legal_Notice_${scanId.slice(0, 8)}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      setTimeout(() => window.URL.revokeObjectURL(blobUrl), 10000)
    } catch (err) {
      console.error('PDF download error, falling back to direct link:', err)
      const token = localStorage.getItem('token') || ''
      window.open(`${API_BASE}/report/${scanId}/pdf?token=${token}`, '_blank')
    } finally {
      setDownloading(false)
    }
  }

  if (loading) return (
    <div className="page" style={{ textAlign: 'center', paddingTop: 80 }}>
      <span className="spinner" style={{ width: 40, height: 40 }} />
      <p style={{ marginTop: 16, color: 'var(--text-muted)' }}>Loading evidence chain…</p>
    </div>
  )

  if (error) return (
    <div className="page">
      <button onClick={() => navigate(-1)} className="btn btn-ghost" style={{ marginBottom: 12, padding: '6px 12px', fontSize: 12 }}>
        ← Back
      </button>
      <div className="alert alert-error">{error}</div>
    </div>
  )

  if (!scanData) return (
    <div className="page">
      <button onClick={() => navigate(-1)} className="btn btn-ghost" style={{ marginBottom: 12, padding: '6px 12px', fontSize: 12 }}>
        ← Back
      </button>
      <div className="alert alert-warning">No scan data found for #{scanId?.slice(-8)}.</div>
    </div>
  )

  const violations = scanData.violations || []
  const overall    = scanData.overall_status
  const cfg        = STATUS_CONFIG[overall] || STATUS_CONFIG.MANUAL_REVIEW
  const currentViolation = violations[selected] || violations[0] || null
  const chain      = currentViolation?.evidence_chain?.steps || []

  return (
    <div className="page">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <button onClick={() => navigate(-1)} className="btn btn-ghost" style={{ marginBottom: 12, padding: '6px 12px', fontSize: 12 }}>
            ← Back
          </button>
          <h1>Evidence Chain</h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: 4, fontSize: 13 }}>
            Scan #{scanId.slice(-8)} · {violations.length} field{violations.length !== 1 ? 's' : ''} checked
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <StatusBadge status={overall} large />
          <div style={{ marginTop: 8, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button
              onClick={handleDownloadPdf}
              disabled={downloading}
              className="btn btn-ghost"
              style={{ fontSize: 12, padding: '6px 14px', cursor: downloading ? 'wait' : 'pointer' }}
            >
              {downloading ? '⏳ Generating PDF…' : '📄 Download PDF Notice'}
            </button>
            <a
              href={`${API_BASE}/report/${scanId}/pdf?token=${localStorage.getItem('token') || ''}`}
              target="_blank"
              rel="noreferrer"
              className="btn btn-ghost"
              style={{ fontSize: 12, padding: '6px 12px' }}
            >
              ↗ Open in Tab
            </a>
          </div>
        </div>
      </div>

      {/* Calibration info bar */}
      {scanData.calibration && (
        <div style={{
          display: 'flex', gap: 20, padding: '12px 16px',
          background: 'var(--bg-surface)', borderRadius: 8,
          border: '1px solid var(--border)', marginBottom: 24,
          fontSize: 13, flexWrap: 'wrap',
        }}>
          <span>📐 <strong>Calibration:</strong> {scanData.calibration.tier}</span>
          <span style={{ color: 'var(--text-muted)' }}>|</span>
          <span>⚡ <strong>Confidence:</strong> <span style={{ color: scanData.calibration.confidence === 'HIGH' ? 'var(--pass)' : scanData.calibration.confidence === 'MEDIUM' ? 'var(--review)' : 'var(--fail)' }}>{scanData.calibration.confidence}</span></span>
          <span style={{ color: 'var(--text-muted)' }}>|</span>
          <span>📏 <strong>Scale:</strong> {scanData.calibration.px_per_mm ? `${scanData.calibration.px_per_mm} px/mm` : 'N/A'}</span>
          <span style={{ color: 'var(--text-muted)' }}>|</span>
          <span>🔄 <strong>Tilt corrected:</strong> {scanData.calibration.tilt_corrected ? 'Yes' : 'No'}</span>
        </div>
      )}

      <div className="evidence-layout">
        {/* Left: violation list */}
        <div>
          <h4 style={{ marginBottom: 12, color: 'var(--text-secondary)' }}>Field Results</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {violations.map((v, i) => {
              const vcfg = STATUS_CONFIG[v.status] || STATUS_CONFIG.MANUAL_REVIEW
              return (
                <button key={v.id || i} onClick={() => setSelected(i)} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '12px 14px', borderRadius: 8, border: 'none', cursor: 'pointer',
                  textAlign: 'left', gap: 8,
                  background: selected === i ? vcfg.bg : 'var(--bg-surface)',
                  outline: selected === i ? `1px solid ${vcfg.color}` : '1px solid var(--border)',
                  transition: 'all 0.15s',
                }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
                      {v.field_name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </div>
                    {v.source_clause && (
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, lineClamp: 1 }}>
                        {v.source_clause.split('—')[0].trim()}
                      </div>
                    )}
                    {v.verified === false && (
                      <div style={{ fontSize: 10, color: 'var(--review)', marginTop: 2 }}>⚠ Unverified</div>
                    )}
                  </div>
                  <span style={{ fontSize: 18, flexShrink: 0 }}>{vcfg.icon}</span>
                </button>
              )
            })}
          </div>

          {/* Summary */}
          <div style={{ marginTop: 16, padding: 14, background: 'var(--bg-elevated)', borderRadius: 8 }}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 600, textTransform: 'uppercase' }}>Summary</div>
            {[
              ['✅ Pass',          scanData.summary?.pass,          'var(--pass)'],
              ['❌ Fail',          scanData.summary?.fail,          'var(--fail)'],
              ['⚠️ Manual Review', scanData.summary?.manual_review, 'var(--review)'],
            ].map(([label, count, color]) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '3px 0' }}>
                <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
                <strong style={{ color }}>{count ?? 0}</strong>
              </div>
            ))}
          </div>
        </div>

        {/* Right: evidence chain or all text view */}
        <div>
          {/* View Mode Switcher Tabs */}
          <div style={{ display: 'flex', gap: 10, marginBottom: 20, borderBottom: '1px solid var(--border)', paddingBottom: 12 }}>
            <button
              onClick={() => setViewMode('chain')}
              className={`btn ${viewMode === 'chain' ? 'btn-primary' : 'btn-ghost'}`}
              style={{ fontSize: 13, padding: '7px 16px', display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <span>🔗</span> Step-by-Step Evidence
            </button>
            <button
              onClick={() => setViewMode('all_text')}
              className={`btn ${viewMode === 'all_text' ? 'btn-primary' : 'btn-ghost'}`}
              style={{ fontSize: 13, padding: '7px 16px', display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <span>📋</span> All Extracted Text &amp; Declarations
            </button>
          </div>

          {viewMode === 'all_text' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              {/* Card 1: All Declarations Table */}
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <div>
                    <h3 style={{ fontSize: 16, fontWeight: 700 }}>Statutory Declarations Matrix</h3>
                    <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                      All extracted packaging declarations categorized against Rule 6 &amp; Rule 7 clauses
                    </p>
                  </div>
                  <span style={{ fontSize: 12, padding: '4px 10px', borderRadius: 99, background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
                    {violations.length} Fields Audited
                  </span>
                </div>

                <div className="table-wrap">
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                        <th style={{ padding: '8px 10px' }}>Field</th>
                        <th style={{ padding: '8px 10px' }}>Status</th>
                        <th style={{ padding: '8px 10px' }}>Detected Text on Package</th>
                        <th style={{ padding: '8px 10px' }}>Statutory Clause</th>
                        <th style={{ padding: '8px 10px', textAlign: 'right' }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {violations.map((v, i) => (
                        <tr key={v.id || i} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td style={{ padding: '10px', fontWeight: 600 }}>
                            {v.field_name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                          </td>
                          <td style={{ padding: '10px' }}>
                            <StatusBadge status={v.status} />
                          </td>
                          <td style={{ padding: '10px', fontFamily: 'monospace', fontSize: 12, color: 'var(--text-primary)', maxWidth: 300, wordBreak: 'break-word' }}>
                            {v.detected_value || <span style={{ color: 'var(--text-muted)' }}>— not detected —</span>}
                          </td>
                          <td style={{ padding: '10px', fontSize: 12, color: 'var(--text-secondary)' }}>
                            {v.source_clause || `Rule Clause ${v.field_name.toUpperCase()}`}
                          </td>
                          <td style={{ padding: '10px', textAlign: 'right' }}>
                            <button
                              onClick={() => { setSelected(i); setViewMode('chain'); }}
                              className="btn btn-ghost"
                              style={{ fontSize: 11, padding: '4px 10px' }}
                            >
                              Inspect ➔
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Card 2: Full OCR Text Transcript */}
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div>
                    <h3 style={{ fontSize: 15, fontWeight: 700 }}>Complete Label OCR Transcript</h3>
                    <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>
                      Raw multi-line textual extraction from the packaging surface
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      const allText = violations.map(v => `${v.field_name.toUpperCase()}: ${v.detected_value || 'None'}`).join('\n')
                      navigator.clipboard.writeText(allText)
                      alert('Copied label text to clipboard!')
                    }}
                    className="btn btn-ghost"
                    style={{ fontSize: 11, padding: '4px 10px' }}
                  >
                    📋 Copy All Text
                  </button>
                </div>
                <div style={{
                  background: 'var(--bg-base)', border: '1px solid var(--border)',
                  borderRadius: 8, padding: 16, fontFamily: 'monospace', fontSize: 13,
                  lineHeight: 1.6, whiteSpace: 'pre-wrap', color: 'var(--text-primary)',
                  maxHeight: 320, overflowY: 'auto',
                }}>
                  {violations.map(v => v.detected_value).filter(Boolean).join('\n') || (
                    <em style={{ color: 'var(--text-muted)' }}>No raw text blocks extracted.</em>
                  )}
                </div>
              </div>
            </div>
          ) : (
            currentViolation ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
                  <h3>{currentViolation.field_name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</h3>
                  <StatusBadge status={currentViolation.status} />
                </div>

                {chain.length > 0 ? (
                  <div style={{ position: 'relative' }}>
                    <style>{`@keyframes stepIn { from { opacity:0; transform:translateX(-8px) } to { opacity:1; transform:translateX(0) } }`}</style>
                    {chain.map((step, i) => (
                      <EvidenceStep key={i} step={step} index={i} total={chain.length} />
                    ))}
                  </div>
                ) : (
                  <div className="card" style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
                    <div style={{ fontSize: 32, marginBottom: 12 }}>📋</div>
                    <p>No evidence chain available for this field.</p>
                  </div>
                )}
              </>
            ) : (
              <div className="card" style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
                <div style={{ fontSize: 32, marginBottom: 12 }}>👈</div>
                <p>Select a field from the left to view its evidence chain</p>
              </div>
            )
          )}
        </div>
      </div>
    </div>
  )
}
