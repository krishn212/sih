import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import client from '../api/client'

const CALIBRATION_OPTIONS = [
  { value:'ARUCO',    label:'ArUco Marker',  desc:'10cm×10cm printed marker — highest accuracy, full tilt correction', icon:'🎯' },
  { value:'ID_CARD',  label:'ID Card',        desc:'Aadhaar/PAN/DL (85.6mm×53.98mm) — geometry only, nothing stored', icon:'🪪' },
  { value:'COIN',     label:'Coin (₹5/₹1)',   desc:'Indian coin — scale only, no tilt correction', icon:'🪙' },
  { value:'NONE',     label:'No Reference',   desc:'Distance estimate — lowest confidence, MANUAL REVIEW likely', icon:'📏' },
]

const DEMO_PRESETS = [
  {
    file: 'compliant_sample.jpg',
    label: '🟢 Compliant Sample',
    badge: 'PASS',
    desc: 'NutriGold Almonds · All 10 Rules Pass',
    brand: 'NutriGold Almonds',
    category: 'Food',
    cal: 'ARUCO',
    color: 'var(--pass)',
  },
  {
    file: 'violation_sample.jpg',
    label: '🔴 Violation Sample',
    badge: 'FAIL',
    desc: 'Spicy Nuts · MRP, gm & Math Violations',
    brand: 'Crunchy Bites Spicy Nuts',
    category: 'Food',
    cal: 'ARUCO',
    color: 'var(--fail)',
  },
  {
    file: 'manual_review_sample.jpg',
    label: '🟡 Manual Review Sample',
    badge: 'MANUAL REVIEW',
    desc: 'Himalayan Tea · Uncalibrated Packaging',
    brand: 'Himalayan Organic Green Tea',
    category: 'Food',
    cal: 'ARUCO',
    color: 'var(--review)',
  },
]

const STEPS = ['Blur Check', 'Calibration', 'OCR', 'Field Detection', 'Rules', 'Done']

export default function ScanPage() {
  const navigate  = useNavigate()
  const fileRef   = useRef()
  const [file, setFile]         = useState(null)
  const [preview, setPreview]   = useState(null)
  const [dragging, setDragging] = useState(false)
  const [form, setForm]         = useState({
    calibration_type: 'ARUCO',
    surface_type: 'FLAT',
    brand_name: '',
    category: 'General',
    is_imported: false,
  })
  const [scanning, setScanning]     = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [error, setError]           = useState('')

  const pickFile = f => {
    if (!f) return
    setFile(f)
    setPreview(URL.createObjectURL(f))
    setError('')
  }

  const loadDemoSample = async (preset) => {
    try {
      const resp = await fetch(`http://localhost:8000/demo_samples/${preset.file}`)
      if (!resp.ok) throw new Error('Failed to fetch sample')
      const blob = await resp.blob()
      const f = new File([blob], preset.file, { type: 'image/jpeg' })
      pickFile(f)
      setForm(prev => ({
        ...prev,
        brand_name: preset.brand,
        category: preset.category,
        calibration_type: preset.cal,
      }))
    } catch (e) {
      setError(`Could not load preset "${preset.file}": Ensure backend is running.`)
    }
  }

  const onDrop = e => {
    e.preventDefault(); setDragging(false)
    pickFile(e.dataTransfer.files[0])
  }

  const handle = e => {
    const { name, value, type, checked } = e.target
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }))
  }

  const submit = async e => {
    e.preventDefault()
    if (!file) return setError('Please select a product label image.')
    setScanning(true); setCurrentStep(0); setError('')

    // Simulate step progression for UX
    const stepTimer = setInterval(() => setCurrentStep(s => Math.min(s + 1, STEPS.length - 2)), 1200)

    try {
      const fd = new FormData()
      fd.append('file', file)
      Object.entries(form).forEach(([k, v]) => fd.append(k, v))

      const { data } = await client.post('/scan/upload', fd)
      clearInterval(stepTimer)
      setCurrentStep(STEPS.length - 1)
      setTimeout(() => navigate(`/evidence/${data.scan_id}`, { state: { scanData: data } }), 600)
    } catch (err) {
      clearInterval(stepTimer)
      setScanning(false); setCurrentStep(0)
      setError(err.response?.data?.detail || 'Scan failed. Check your image and try again.')
    }
  }

  return (
    <div className="page">
      <div style={{ marginBottom:28 }}>
        <h1>New Inspection Scan</h1>
        <p style={{ color:'var(--text-secondary)', marginTop:4 }}>Photograph a product label to check compliance against Legal Metrology Rules 2011</p>
      </div>

      <form onSubmit={submit} className="scan-layout">
        {/* Left: upload + options */}
        <div style={{ display:'flex', flexDirection:'column', gap:20 }}>

          {/* Quick Demo Test Presets */}
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '14px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
                ⚡ Quick Load Test Packaging Samples:
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                One-click test suite for live inspection demo
              </span>
            </div>
            <div className="demo-presets-grid">
              {DEMO_PRESETS.map((p) => (
                <button
                  key={p.file}
                  type="button"
                  onClick={() => loadDemoSample(p)}
                  className="btn btn-ghost"
                  style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'flex-start',
                    padding: '10px 12px', borderRadius: 8,
                    border: `1px solid ${file?.name === p.file ? p.color : 'var(--border)'}`,
                    background: file?.name === p.file ? 'var(--bg-elevated)' : 'transparent',
                    cursor: 'pointer', textAlign: 'left', gap: 4,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                    <strong style={{ fontSize: 12, color: 'var(--text-primary)' }}>{p.label}</strong>
                    <span style={{ fontSize: 10, padding: '2px 6px', borderRadius: 4, background: `${p.color}22`, color: p.color, fontWeight: 700 }}>
                      {p.badge}
                    </span>
                  </div>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{p.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Drop zone */}
          <div
            className={`drop-zone ${dragging ? 'dragging' : ''}`}
            onClick={() => fileRef.current.click()}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <input ref={fileRef} type="file" accept="image/*" style={{ display:'none' }} onChange={e => pickFile(e.target.files[0])} />
            {preview ? (
              <div>
                <img src={preview} alt="Preview" style={{ maxHeight:280, margin:'0 auto', borderRadius:8 }} />
                <p style={{ color:'var(--text-muted)', marginTop:12, fontSize:13 }}>Click to change image</p>
              </div>
            ) : (
              <>
                <div className="drop-zone-icon">📷</div>
                <h3 style={{ marginBottom:8 }}>Drop product label image here</h3>
                <p style={{ color:'var(--text-muted)', fontSize:13 }}>or click to browse · JPG, PNG, WEBP supported</p>
              </>
            )}
          </div>

          {/* Product info */}
          <div className="card">
            <h4 style={{ marginBottom:16 }}>Product Information</h4>
            <div className="grid-2">
              <div className="form-group">
                <label htmlFor="brand_name">Brand / Product Name</label>
                <input id="brand_name" name="brand_name" value={form.brand_name} onChange={handle} placeholder="e.g. Maggi, Haldirams" />
              </div>
              <div className="form-group">
                <label htmlFor="category">Category</label>
                <select id="category" name="category" value={form.category} onChange={handle}>
                  <option>General</option>
                  <option>Food</option>
                  <option>Beverages</option>
                  <option>Personal Care</option>
                  <option>Household</option>
                  <option>Pharmaceuticals</option>
                </select>
              </div>
            </div>
            <div style={{ marginTop:12, display:'flex', alignItems:'center', gap:8 }}>
              <input id="is_imported" name="is_imported" type="checkbox" checked={form.is_imported} onChange={handle} style={{ width:'auto' }} />
              <label htmlFor="is_imported" style={{ textTransform:'none', letterSpacing:'normal', fontSize:14, fontWeight:500 }}>
                This is an imported product (country of origin check applies)
              </label>
            </div>
          </div>
        </div>

        {/* Right: calibration + surface + submit */}
        <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
          <div className="card">
            <h4 style={{ marginBottom:4 }}>Calibration Reference</h4>
            <p style={{ fontSize:12, color:'var(--text-muted)', marginBottom:16 }}>Place your reference object beside the product label</p>
            <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
              {CALIBRATION_OPTIONS.map(opt => (
                <label key={opt.value} style={{
                  display:'flex', alignItems:'flex-start', gap:12, padding:12, borderRadius:8, cursor:'pointer',
                  border: `1px solid ${form.calibration_type === opt.value ? 'var(--accent)' : 'var(--border)'}`,
                  background: form.calibration_type === opt.value ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                  transition: 'all 0.15s',
                }}>
                  <input type="radio" name="calibration_type" value={opt.value} checked={form.calibration_type === opt.value} onChange={handle} style={{ marginTop:2, width:'auto', accentColor:'var(--accent)' }} />
                  <div>
                    <div style={{ fontWeight:600, fontSize:13 }}>{opt.icon} {opt.label}</div>
                    <div style={{ fontSize:11, color:'var(--text-muted)', marginTop:2 }}>{opt.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="card">
            <h4 style={{ marginBottom:12 }}>Surface Type</h4>
            <div style={{ display:'flex', gap:8 }}>
              {[{v:'FLAT', l:'📦 Flat', d:'Boxes, cartons, pouches'}, {v:'CURVED', l:'🥫 Curved', d:'Bottles, cans'}].map(o => (
                <label key={o.v} style={{
                  flex:1, padding:12, borderRadius:8, cursor:'pointer', textAlign:'center',
                  border: `1px solid ${form.surface_type === o.v ? 'var(--accent)' : 'var(--border)'}`,
                  background: form.surface_type === o.v ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                  transition: 'all 0.15s',
                }}>
                  <input type="radio" name="surface_type" value={o.v} checked={form.surface_type === o.v} onChange={handle} style={{ display:'none' }} />
                  <div style={{ fontWeight:600, fontSize:13 }}>{o.l}</div>
                  <div style={{ fontSize:11, color:'var(--text-muted)' }}>{o.d}</div>
                </label>
              ))}
            </div>
          </div>

          {/* Processing steps indicator */}
          {scanning && (
            <div className="card">
              <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:16 }}>
                <span className="spinner" />
                <span style={{ fontWeight:600, fontSize:14 }}>Processing…</span>
              </div>
              {STEPS.map((step, i) => (
                <div key={step} style={{ display:'flex', alignItems:'center', gap:10, padding:'6px 0' }}>
                  <div style={{
                    width:20, height:20, borderRadius:'50%', flexShrink:0, display:'flex', alignItems:'center', justifyContent:'center', fontSize:11,
                    background: i < currentStep ? 'var(--pass)' : i === currentStep ? 'var(--accent)' : 'var(--border)',
                    color: i <= currentStep ? '#fff' : 'var(--text-muted)',
                  }}>
                    {i < currentStep ? '✓' : i + 1}
                  </div>
                  <span style={{ fontSize:13, color: i <= currentStep ? 'var(--text-primary)' : 'var(--text-muted)', fontWeight: i === currentStep ? 600 : 400 }}>
                    {step}
                  </span>
                </div>
              ))}
            </div>
          )}

          {error && <div className="alert alert-error">{error}</div>}

          <button type="submit" className="btn btn-primary btn-lg" disabled={scanning || !file}>
            {scanning ? <><span className="spinner" style={{width:18,height:18}} /> Scanning…</> : '🔍 Run Compliance Scan'}
          </button>

          <p style={{ fontSize:11, color:'var(--text-muted)', textAlign:'center' }}>
            Results are AI-assisted. All verdicts reference exact Legal Metrology Rules 2011 clauses.
          </p>
        </div>
      </form>
    </div>
  )
}
